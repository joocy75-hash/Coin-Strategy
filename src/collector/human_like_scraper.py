#!/usr/bin/env python3
"""
인간 행동 시뮬레이션 스크래퍼

봇 탐지를 우회하기 위해 사람처럼 천천히 행동합니다.
- 긴 랜덤 딜레이 (10-30초)
- 자연스러운 마우스 움직임
- 점진적 스크롤
- 세션 지속성

사용법:
    python human_like_scraper.py --count 100 --min-boost 200
"""

import asyncio
import json
import logging
import random
import sqlite3
import math
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple

from playwright.async_api import async_playwright, Page, Browser

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('HumanScraper')


@dataclass
class StrategyData:
    """수집된 전략 데이터"""
    script_id: str
    title: str
    author: str
    boosts: int
    script_url: str
    is_open_source: bool = True
    collected_at: str = ""

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.now().isoformat()


class HumanLikeScraper:
    """인간 행동을 시뮬레이션하는 스크래퍼"""

    BASE_URL = "https://www.tradingview.com/scripts/"

    # 실제 브라우저 User-Agent
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]

    def __init__(
        self,
        headless: bool = False,  # 기본적으로 브라우저 보이기
        slow_mode: bool = True,   # 천천히 동작
        session_file: Optional[str] = None  # 세션 저장/복원
    ):
        self.headless = headless
        self.slow_mode = slow_mode
        self.session_file = session_file or "data/.tv_session.json"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._playwright = None

    async def __aenter__(self):
        await self._init_browser()
        return self

    async def __aexit__(self, *args):
        await self._close()

    async def _init_browser(self):
        """브라우저 초기화 - 실제 사용자처럼"""
        logger.info("🌐 브라우저 시작 중...")

        self._playwright = await async_playwright().start()

        # 실제 브라우저와 동일한 설정
        self.browser = await self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=100 if self.slow_mode else 0,  # 모든 동작 100ms 지연
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        )

        # 컨텍스트 생성 (세션 복원 시도)
        context_options = {
            "user_agent": random.choice(self.USER_AGENTS),
            "viewport": {"width": 1920, "height": 1080},
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "color_scheme": "light",
        }

        # 저장된 세션이 있으면 복원
        session_path = Path(self.session_file)
        if session_path.exists():
            try:
                storage_state = json.loads(session_path.read_text())
                context_options["storage_state"] = storage_state
                logger.info("📂 이전 세션 복원됨")
            except Exception as e:
                logger.warning(f"세션 복원 실패: {e}")

        context = await self.browser.new_context(**context_options)
        self.page = await context.new_page()

        # 봇 탐지 우회 스크립트
        await self.page.add_init_script("""
            // webdriver 속성 숨기기
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

            // plugins 배열 추가
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // languages 설정
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'ko']
            });

            // Chrome 객체 추가
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // permissions 쿼리 오버라이드
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(parameters)
            );
        """)

        logger.info("✅ 브라우저 준비 완료")

    async def _close(self):
        """브라우저 종료 및 세션 저장"""
        if self.page:
            # 세션 저장
            try:
                context = self.page.context
                storage_state = await context.storage_state()
                session_path = Path(self.session_file)
                session_path.parent.mkdir(parents=True, exist_ok=True)
                session_path.write_text(json.dumps(storage_state))
                logger.info("💾 세션 저장됨")
            except Exception as e:
                logger.warning(f"세션 저장 실패: {e}")

        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()

        logger.info("👋 브라우저 종료")

    # =========================================================================
    # 인간 행동 시뮬레이션
    # =========================================================================

    async def _human_delay(self, min_sec: float = 2, max_sec: float = 5):
        """사람처럼 랜덤하게 대기"""
        delay = random.uniform(min_sec, max_sec)
        logger.debug(f"⏳ {delay:.1f}초 대기...")
        await asyncio.sleep(delay)

    async def _think_time(self):
        """페이지를 읽는 시간 (길게)"""
        delay = random.uniform(5, 15)
        logger.info(f"📖 페이지 읽는 중... ({delay:.0f}초)")
        await asyncio.sleep(delay)

    async def _human_mouse_move(self, target_x: int, target_y: int):
        """자연스러운 마우스 움직임 (베지어 곡선)"""
        if not self.page:
            return

        # 현재 마우스 위치 (랜덤 시작점)
        start_x = random.randint(100, 800)
        start_y = random.randint(100, 600)

        # 컨트롤 포인트 (곡선을 위해)
        ctrl_x = (start_x + target_x) / 2 + random.randint(-100, 100)
        ctrl_y = (start_y + target_y) / 2 + random.randint(-100, 100)

        # 베지어 곡선을 따라 이동
        steps = random.randint(20, 40)
        for i in range(steps + 1):
            t = i / steps
            # 2차 베지어 곡선 공식
            x = (1-t)**2 * start_x + 2*(1-t)*t * ctrl_x + t**2 * target_x
            y = (1-t)**2 * start_y + 2*(1-t)*t * ctrl_y + t**2 * target_y

            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.01, 0.03))

    async def _human_scroll(self, times: int = 3):
        """사람처럼 천천히 스크롤"""
        if not self.page:
            return

        for i in range(times):
            # 스크롤 양 랜덤
            scroll_amount = random.randint(300, 700)

            # 점진적 스크롤 (부드럽게)
            for _ in range(5):
                await self.page.evaluate(f"window.scrollBy(0, {scroll_amount // 5})")
                await asyncio.sleep(random.uniform(0.1, 0.3))

            # 읽는 시간
            await asyncio.sleep(random.uniform(1, 3))

            logger.debug(f"📜 스크롤 {i+1}/{times}")

    async def _human_click(self, selector: str, description: str = ""):
        """사람처럼 클릭 (마우스 이동 후 클릭)"""
        if not self.page:
            return False

        try:
            element = await self.page.query_selector(selector)
            if not element:
                return False

            # 요소 위치 가져오기
            box = await element.bounding_box()
            if not box:
                return False

            # 요소 중심으로 마우스 이동 (약간의 오프셋 추가)
            target_x = box['x'] + box['width'] / 2 + random.randint(-5, 5)
            target_y = box['y'] + box['height'] / 2 + random.randint(-3, 3)

            await self._human_mouse_move(target_x, target_y)
            await asyncio.sleep(random.uniform(0.1, 0.3))

            # 클릭
            await self.page.mouse.click(target_x, target_y)

            if description:
                logger.info(f"🖱️ 클릭: {description}")

            return True

        except Exception as e:
            logger.debug(f"클릭 실패 ({selector}): {e}")
            return False

    # =========================================================================
    # 스크래핑 로직
    # =========================================================================

    async def navigate_to_strategies(self):
        """전략 페이지로 이동"""
        logger.info("🚀 TradingView 전략 페이지로 이동...")

        await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=60000)
        await self._think_time()

        # Strategies 필터 적용
        logger.info("🔍 전략 필터 적용 중...")

        # "All types" 버튼 클릭
        if await self._human_click('button:has-text("All types")', "All types 버튼"):
            await self._human_delay(1, 2)

            # "Strategies" 옵션 클릭
            await self._human_click('text="Strategies"', "Strategies 옵션")
            await self._human_delay(2, 4)

        # Popular 정렬
        if await self._human_click('a:has-text("Popular")', "Popular 정렬"):
            await self._human_delay(2, 4)

        logger.info("✅ 전략 페이지 준비 완료")

    async def collect_strategies(
        self,
        target_count: int = 100,
        min_boosts: int = 100,
        max_pages: int = 100
    ) -> List[StrategyData]:
        """전략 수집 - 페이지네이션 사용"""

        # 먼저 전략 페이지로 이동
        await self.navigate_to_strategies()

        logger.info(f"📊 수집 시작: 목표 {target_count}개, 최소 {min_boosts} 부스트")

        strategies = []
        seen_ids = set()
        current_page = 1
        empty_pages = 0

        while len(strategies) < target_count and current_page <= max_pages:
            logger.info(f"📄 페이지 {current_page} 수집 중...")

            # 현재 페이지의 카드 추출
            cards = await self._extract_visible_cards()
            new_count = 0

            for card in cards:
                script_id = card.get('scriptId', '')

                if not script_id or script_id in seen_ids:
                    continue

                seen_ids.add(script_id)
                boosts = card.get('likes', 0)

                # 조건 확인
                if card.get('isOpenSource', False) and boosts >= min_boosts:
                    strategy = StrategyData(
                        script_id=script_id,
                        title=card.get('title', ''),
                        author=card.get('author', ''),
                        boosts=boosts,
                        script_url=card.get('href', ''),
                        is_open_source=True
                    )
                    strategies.append(strategy)
                    new_count += 1

                    logger.info(
                        f"✅ [{len(strategies):3d}] {boosts:>5,} 부스트 | "
                        f"{strategy.title[:40]}"
                    )

                    if len(strategies) >= target_count:
                        break

            # 진행 상황
            logger.info(
                f"📈 페이지 {current_page}: "
                f"총 {len(strategies)}개 수집 (+{new_count})"
            )

            # 종료 조건
            if len(strategies) >= target_count:
                break

            if new_count == 0:
                empty_pages += 1
                if empty_pages >= 15:
                    logger.info("🏁 15페이지 연속 조건 만족 전략 없음. 수집 완료.")
                    break
            else:
                empty_pages = 0

            # 다음 페이지로 이동
            next_clicked = await self._go_to_next_page()
            if not next_clicked:
                logger.info("🏁 다음 페이지 없음. 수집 완료.")
                break

            current_page += 1

            # 사람처럼 대기 (페이지 로딩 + 읽는 시간)
            await self._human_delay(3, 6)

            # 가끔 긴 휴식
            if current_page % 10 == 0:
                rest_time = random.uniform(15, 30)
                logger.info(f"☕ 잠시 휴식... ({rest_time:.0f}초)")
                await asyncio.sleep(rest_time)

        logger.info(f"🎉 수집 완료: 총 {len(strategies)}개 전략 ({current_page} 페이지)")
        return strategies

    async def _go_to_next_page(self) -> bool:
        """다음 페이지로 이동"""
        try:
            # 페이지 하단으로 스크롤 (페이지네이션 보이도록)
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            # 페이지네이션 버튼 찾기
            btns = await self.page.query_selector_all('[class*="pagination"] button')

            for btn in btns:
                aria = await btn.get_attribute("aria-label") or ""
                if "next" in aria.lower():
                    # 마우스로 자연스럽게 클릭
                    box = await btn.bounding_box()
                    if box:
                        await self._human_mouse_move(
                            box['x'] + box['width'] / 2,
                            box['y'] + box['height'] / 2
                        )
                        await asyncio.sleep(random.uniform(0.2, 0.5))
                        await btn.click()
                        await asyncio.sleep(2)
                        return True

            return False

        except Exception as e:
            logger.warning(f"다음 페이지 이동 실패: {e}")
            return False

    async def _extract_visible_cards(self) -> List[dict]:
        """현재 화면에 보이는 카드 추출"""
        cards = await self.page.evaluate("""
            () => {
                const articles = document.querySelectorAll('article');
                return Array.from(articles).map(art => {
                    const titleLink = art.querySelector('a[data-qa-id="ui-lib-card-link-title"]');
                    const title = titleLink ? titleLink.textContent.trim() : '';
                    const href = titleLink ? titleLink.getAttribute('href') : '';

                    const scriptIdMatch = href.match(/script\\/([^/]+)/);
                    const scriptId = scriptIdMatch ? scriptIdMatch[1] : '';

                    let author = '';
                    const allLinks = art.querySelectorAll('a');
                    for (const link of allLinks) {
                        const h = link.getAttribute('href') || '';
                        if (h.includes('/u/')) {
                            author = link.textContent.trim().replace(/^by\\s*/i, '');
                            break;
                        }
                    }

                    // 부스트 수 추출
                    let likes = 0;
                    const boostBtn = art.querySelector('[data-qa-id="ui-lib-card-like-button"]');
                    if (boostBtn) {
                        const btnText = boostBtn.textContent || '';
                        const numMatch = btnText.match(/(\\d[\\d,]*\\.?\\d*)\\s*([KMkm])?/);
                        if (numMatch) {
                            let num = parseFloat(numMatch[1].replace(/,/g, ''));
                            const unit = (numMatch[2] || '').toUpperCase();
                            if (unit === 'K') num *= 1000;
                            else if (unit === 'M') num *= 1000000;
                            likes = Math.round(num);
                        }
                    }

                    // 오픈소스 여부
                    const cardHtml = art.innerHTML.toLowerCase();
                    const isOpenSource = !cardHtml.includes('invite-only') &&
                                         !cardHtml.includes('protected');

                    return { scriptId, title, author, likes, href, isOpenSource };
                }).filter(c => c.scriptId && c.title);
            }
        """)
        return cards

    # =========================================================================
    # 데이터 저장
    # =========================================================================

    def save_to_database(self, strategies: List[StrategyData], db_path: str):
        """수집된 전략을 DB에 저장"""
        logger.info(f"💾 DB 저장: {db_path}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        saved = 0
        for strategy in strategies:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO strategies
                    (script_id, title, author, likes, script_url, is_open_source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy.script_id,
                    strategy.title,
                    strategy.author,
                    strategy.boosts,
                    strategy.script_url,
                    strategy.is_open_source,
                    strategy.collected_at
                ))
                saved += 1
            except Exception as e:
                logger.warning(f"저장 실패 ({strategy.script_id}): {e}")

        conn.commit()
        conn.close()

        logger.info(f"✅ {saved}/{len(strategies)}개 저장 완료")

    def save_to_json(self, strategies: List[StrategyData], json_path: str):
        """수집된 전략을 JSON으로 저장"""
        data = [asdict(s) for s in strategies]

        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

        logger.info(f"📄 JSON 저장: {json_path} ({len(strategies)}개)")


async def main():
    """메인 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="인간 행동 시뮬레이션 TradingView 스크래퍼")
    parser.add_argument("--count", type=int, default=50, help="수집할 전략 수")
    parser.add_argument("--min-boost", type=int, default=100, help="최소 부스트 수")
    parser.add_argument("--headless", action="store_true", help="헤드리스 모드")
    parser.add_argument("--db", default="data/strategies.db", help="DB 경로")
    parser.add_argument("--json", default="data/collected_strategies.json", help="JSON 저장 경로")

    args = parser.parse_args()

    print("=" * 60)
    print("🤖 인간 행동 시뮬레이션 스크래퍼")
    print("=" * 60)
    print(f"목표: {args.count}개 전략")
    print(f"최소 부스트: {args.min_boost}")
    print(f"모드: {'헤드리스' if args.headless else '브라우저 표시'}")
    print("=" * 60)
    print()

    async with HumanLikeScraper(headless=args.headless) as scraper:
        # 전략 페이지로 이동
        await scraper.navigate_to_strategies()

        # 전략 수집
        strategies = await scraper.collect_strategies(
            target_count=args.count,
            min_boosts=args.min_boost,
            max_pages=200
        )

        if strategies:
            # JSON 저장
            scraper.save_to_json(strategies, args.json)

            # DB 저장 (DB가 있으면)
            if Path(args.db).exists():
                scraper.save_to_database(strategies, args.db)

            # 결과 출력
            print()
            print("=" * 60)
            print(f"✅ 수집 완료: {len(strategies)}개 전략")
            print("=" * 60)
            print()
            print("=== 상위 20개 ===")
            for i, s in enumerate(sorted(strategies, key=lambda x: x.boosts, reverse=True)[:20], 1):
                print(f"{i:2}. {s.boosts:>5,} 부스트 | {s.title[:45]}")
        else:
            print("❌ 수집된 전략 없음")


if __name__ == "__main__":
    asyncio.run(main())
