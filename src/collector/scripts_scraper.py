# src/collector/scripts_scraper.py

import asyncio
import random
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser

logger = logging.getLogger(__name__)

@dataclass
class StrategyMeta:
    """수집된 전략 메타데이터"""
    script_id: str
    title: str
    author: str
    likes: int
    views: int = 0
    published_date: Optional[str] = None
    updated_date: Optional[str] = None
    script_url: str = ""
    is_open_source: bool = False
    category: str = "strategy"
    description: str = ""
    pine_version: int = 5
    scraped_at: datetime = field(default_factory=datetime.now)

class TVScriptsScraper:
    """TradingView Scripts 페이지 스크래퍼"""

    BASE_URL = "https://www.tradingview.com/scripts"

    # User Agent 풀
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/120.0.0.0",
    ]

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.browser: Optional[Browser] = None
        self._playwright = None

    async def __aenter__(self):
        await self._init_browser()
        return self

    async def __aexit__(self, *args):
        await self._close_browser()

    async def _init_browser(self):
        """브라우저 초기화"""
        self._playwright = await async_playwright().start()

        launch_options = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        }

        if self.proxy:
            launch_options["proxy"] = {"server": self.proxy}

        self.browser = await self._playwright.chromium.launch(**launch_options)
        logger.info("Browser initialized")

    async def _close_browser(self):
        """브라우저 종료"""
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser closed")

    async def _create_context(self):
        """새 브라우저 컨텍스트 생성"""
        return await self.browser.new_context(
            user_agent=random.choice(self.USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
        )

    async def scrape_strategies(
        self,
        max_count: int = 1000,
        min_likes: int = 100,
        sort_by: str = "popularity",
        max_scrolls: int = 50,
    ) -> List[StrategyMeta]:
        """
        전략 목록 스크래핑 (무한 스크롤 방식)

        Args:
            max_count: 최대 수집 개수
            min_likes: 최소 좋아요 수 (사전 필터)
            sort_by: 정렬 기준 (popularity, recent)
            max_scrolls: 최대 스크롤 횟수
        """
        strategies = []
        seen_ids = set()

        context = await self._create_context()
        page = await context.new_page()

        await self._bypass_detection(page)

        try:
            # 전략 필터 및 정렬 적용
            await self._apply_strategy_filter(page, sort_by)
            await self._random_delay(2, 3)

            # Load More 버튼 클릭
            try:
                load_more = await page.query_selector('button:has-text("Load more")')
                if load_more and await load_more.is_visible():
                    await load_more.click()
                    await asyncio.sleep(3)
                    logger.info("Clicked 'Load more' button")
            except Exception:
                pass

            # 스크롤하면서 수집
            no_new_count = 0
            last_strategy_count = 0

            for scroll_num in range(max_scrolls):
                # 스크롤
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

                # 카드 추출
                cards = await self._extract_cards(page)

                # 각 카드 처리
                for card_data in cards:
                    script_id = card_data.get('scriptId', '')
                    if not script_id or script_id in seen_ids:
                        continue
                    seen_ids.add(script_id)

                    meta = self._parse_card_data(card_data)
                    if meta and meta.is_open_source and meta.likes >= min_likes:
                        strategies.append(meta)
                        logger.info(f"✓ [{len(strategies)}] {meta.title} ({meta.likes:,} boosts)")

                        if len(strategies) >= max_count:
                            break

                # 진행 상황 로깅
                if (scroll_num + 1) % 5 == 0:
                    logger.info(f"Scroll {scroll_num+1}: {len(cards)} cards, {len(strategies)} qualifying")

                # 종료 조건
                if len(strategies) >= max_count:
                    break

                if len(strategies) == last_strategy_count:
                    no_new_count += 1
                    if no_new_count >= 5:
                        logger.info("No new strategies after 5 scrolls. Stopping.")
                        break
                else:
                    no_new_count = 0
                    last_strategy_count = len(strategies)

        except Exception as e:
            logger.error(f"Scraping error: {e}", exc_info=True)

        finally:
            await context.close()

        logger.info(f"Scraping complete: {len(strategies)} strategies collected")
        return strategies[:max_count]

    async def _extract_cards(self, page: Page) -> List[dict]:
        """페이지에서 스크립트 카드 데이터 추출"""

        # 스크롤하여 모든 카드 로드
        await self._scroll_to_load(page)

        # JavaScript로 카드 데이터 추출 (2025년 12월 기준 TradingView 구조)
        cards = await page.evaluate("""
            () => {
                const articles = document.querySelectorAll('article');
                return Array.from(articles).map(art => {
                    // 제목 및 링크
                    const titleLink = art.querySelector('a[data-qa-id="ui-lib-card-link-title"]');
                    const title = titleLink ? titleLink.textContent.trim() : '';
                    const href = titleLink ? titleLink.getAttribute('href') : '';

                    // 스크립트 ID 추출
                    const scriptIdMatch = href.match(/script\\/([^/]+)/);
                    const scriptId = scriptIdMatch ? scriptIdMatch[1] : '';

                    // 작성자 (/u/ 패턴 링크에서)
                    let author = '';
                    const allLinks = art.querySelectorAll('a');
                    for (const link of allLinks) {
                        const h = link.getAttribute('href') || '';
                        if (h.includes('/u/')) {
                            author = link.textContent.trim().replace(/^by\\s*/i, '');
                            break;
                        }
                    }

                    // 좋아요/부스트 수 추출 (2025년 12월 TradingView 구조)
                    let likes = 0;

                    // 방법 1: data-qa-id로 like 버튼 찾기
                    const boostBtn = art.querySelector('[data-qa-id="ui-lib-card-like-button"]');
                    if (boostBtn) {
                        // aria-label에서 숫자 추출 (예: "123 boosts")
                        const ariaEl = boostBtn.querySelector('[aria-label]');
                        if (ariaEl) {
                            const labelText = ariaEl.getAttribute('aria-label') || '';
                            const match = labelText.match(/(\\d[\\d,]*)\\s*boost/i);
                            if (match) {
                                likes = parseInt(match[1].replace(/,/g, '')) || 0;
                            }
                        }

                        // 버튼 텍스트에서 직접 숫자 추출
                        if (likes === 0) {
                            const btnText = boostBtn.textContent || '';
                            const numMatch = btnText.match(/(\\d[\\d,]*)/);
                            if (numMatch) {
                                likes = parseInt(numMatch[1].replace(/,/g, '')) || 0;
                            }
                        }

                        // digit 클래스에서 추출
                        if (likes === 0) {
                            const digits = boostBtn.querySelectorAll('[class*="digit"]');
                            if (digits.length > 0) {
                                let numStr = '';
                                digits.forEach(d => numStr += d.textContent.trim());
                                likes = parseInt(numStr) || 0;
                            }
                        }
                    }

                    // 방법 2: boost/like 관련 버튼이나 span 찾기 (백업)
                    if (likes === 0) {
                        const allBtns = art.querySelectorAll('button, [role="button"]');
                        for (const btn of allBtns) {
                            const text = btn.textContent || '';
                            // K, M 단위 처리 (예: 1.2K, 500)
                            const numMatch = text.match(/(\\d+\\.?\\d*)\\s*([KMkm])?/);
                            if (numMatch) {
                                let num = parseFloat(numMatch[1]);
                                const unit = (numMatch[2] || '').toUpperCase();
                                if (unit === 'K') num *= 1000;
                                else if (unit === 'M') num *= 1000000;
                                if (num >= 10) {  // 최소 10 이상이면 likes로 간주
                                    likes = Math.round(num);
                                    break;
                                }
                            }
                        }
                    }

                    // 방법 3: SVG 하트/rocket 아이콘 옆 숫자 찾기
                    if (likes === 0) {
                        const svgParents = art.querySelectorAll('svg');
                        for (const svg of svgParents) {
                            const parent = svg.parentElement;
                            if (parent) {
                                const text = parent.textContent || '';
                                const numMatch = text.match(/(\\d+\\.?\\d*)\\s*([KMkm])?/);
                                if (numMatch) {
                                    let num = parseFloat(numMatch[1]);
                                    const unit = (numMatch[2] || '').toUpperCase();
                                    if (unit === 'K') num *= 1000;
                                    else if (unit === 'M') num *= 1000000;
                                    if (num >= 10) {
                                        likes = Math.round(num);
                                        break;
                                    }
                                }
                            }
                        }
                    }

                    // 오픈소스 여부 (아이콘 title 확인)
                    const scriptIcon = art.querySelector('[class*="script-icon-wrap"]');
                    const iconTitle = scriptIcon ? scriptIcon.getAttribute('title') || '' : '';
                    // 대안: 전체 카드 내 open-source 관련 요소 확인
                    const cardHtml = art.innerHTML.toLowerCase();
                    const isOpenSource = !iconTitle.toLowerCase().includes('invite') &&
                                         !iconTitle.toLowerCase().includes('protected') &&
                                         !cardHtml.includes('invite-only') &&
                                         !cardHtml.includes('protected');

                    // 타입 확인 (strategy vs indicator)
                    const isStrategy = iconTitle.toLowerCase().includes('strategy') ||
                                       cardHtml.includes('strategy');

                    // 설명
                    const descEl = art.querySelector('a[data-qa-id="ui-lib-card-link-paragraph"]');
                    const description = descEl ? descEl.textContent.trim().slice(0, 500) : '';

                    return {
                        scriptId,
                        title,
                        author,
                        likes,
                        href,
                        isOpenSource,
                        isStrategy,
                        description
                    };
                }).filter(card => card.scriptId && card.title);
            }
        """)

        return cards

    def _parse_card_data(self, card_data: dict) -> Optional[StrategyMeta]:
        """카드 데이터를 StrategyMeta로 변환"""
        try:
            return StrategyMeta(
                script_id=card_data.get('scriptId', ''),
                title=card_data.get('title', ''),
                author=card_data.get('author', ''),
                likes=card_data.get('likes', 0),
                script_url=card_data.get('href', '') if card_data.get('href', '').startswith('http') else f"https://www.tradingview.com{card_data.get('href', '')}",
                is_open_source=card_data.get('isOpenSource', False),
                description=card_data.get('description', ''),
            )
        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None

    async def _scroll_to_load(self, page: Page, max_scrolls: int = 50, target_cards: int = 500):
        """무한 스크롤 + Load More 버튼으로 추가 콘텐츠 로드"""
        scroll_count = 0
        no_new_count = 0
        last_card_count = 0

        # 먼저 Load More 버튼 클릭 시도
        try:
            load_more = await page.query_selector('button:has-text("Load more")')
            if load_more and await load_more.is_visible():
                await load_more.click()
                await asyncio.sleep(3)
                logger.info("Clicked 'Load more' button")
        except Exception:
            pass

        while scroll_count < max_scrolls and no_new_count < 5:
            # 페이지 끝까지 스크롤
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            # 현재 카드 수 확인
            card_count = await page.evaluate("document.querySelectorAll('article').length")

            if card_count == last_card_count:
                no_new_count += 1
            else:
                no_new_count = 0
                last_card_count = card_count

            scroll_count += 1

            # 진행 상황 로깅 (10회마다)
            if scroll_count % 10 == 0:
                logger.info(f"Scroll {scroll_count}: {card_count} cards loaded")

            # 목표 도달 시 중단
            if card_count >= target_cards:
                logger.info(f"Target reached: {card_count} cards")
                break

    async def _bypass_detection(self, page: Page):
        """봇 탐지 우회"""
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = {runtime: {}};
        """)

    async def _apply_strategy_filter(self, page: Page, sort_by: str = "popularity"):
        """전략 필터 및 정렬 적용"""
        logger.info("Navigating to scripts page and applying strategy filter...")

        # 기본 페이지 로드
        await page.goto(f"{self.BASE_URL}/", wait_until="networkidle", timeout=30000)
        await self._random_delay(2, 3)

        try:
            # 1. "All types" 버튼 찾기 및 클릭
            all_types_btn = page.locator('button:has-text("All types")')
            if await all_types_btn.count() > 0:
                await all_types_btn.first.click()
                await self._random_delay(0.5, 1)

                # "Strategies" 옵션 클릭
                strategies_opt = page.locator('text="Strategies"')
                if await strategies_opt.count() > 0:
                    await strategies_opt.first.click()
                    await self._random_delay(2, 3)
                    logger.info("Strategy filter applied successfully")
                else:
                    logger.warning("Could not find 'Strategies' option")
            else:
                logger.warning("Could not find 'All types' button")

            # 2. 인기순 정렬 적용
            if sort_by == "popularity":
                popular_link = page.locator('a:has-text("Popular")')
                if await popular_link.count() > 0:
                    await popular_link.first.click()
                    await self._random_delay(2, 3)
                    logger.info("Popularity sort applied successfully")
                else:
                    logger.warning("Could not find 'Popular' link")

        except Exception as e:
            logger.error(f"Error applying strategy filter: {e}")

    def _build_url(self, sort_by: str, page: int) -> str:
        """URL 생성"""
        # 전략 필터가 적용된 URL (세션 내에서만 작동)
        # sort_by 파라미터는 현재 사용되지 않음 (기본 정렬 사용)
        del sort_by  # unused
        if page == 1:
            return f"{self.BASE_URL}/?script_type=strategies"
        return f"{self.BASE_URL}/?script_type=strategies&page={page}"

    async def _random_delay(self, min_sec: float, max_sec: float):
        """랜덤 딜레이"""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def _exponential_backoff(self, attempt: int):
        """지수 백오프"""
        delay = min(300, (2 ** attempt) + random.uniform(0, 1))
        logger.info(f"Backoff: waiting {delay:.1f}s (attempt {attempt})")
        await asyncio.sleep(delay)
