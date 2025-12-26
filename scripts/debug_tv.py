#!/usr/bin/env python3
"""TradingView 스크래퍼 테스트 - 전략 필터 적용"""

import asyncio
from playwright.async_api import async_playwright

JS_EXTRACT = """
() => {
    const articles = document.querySelectorAll("article");
    return Array.from(articles).map(art => {
        // 제목 및 링크
        const titleLink = art.querySelector('a[data-qa-id="ui-lib-card-link-title"]');
        const title = titleLink ? titleLink.textContent.trim() : "";
        const href = titleLink ? titleLink.getAttribute("href") : "";

        // 스크립트 ID 추출
        const scriptIdMatch = href.match(/script\\/([^/]+)/);
        const scriptId = scriptIdMatch ? scriptIdMatch[1] : "";

        // 작성자 (/u/ 패턴 링크에서)
        let author = "";
        const allLinks = art.querySelectorAll("a");
        for (const link of allLinks) {
            const h = link.getAttribute("href") || "";
            if (h.includes("/u/")) {
                author = link.textContent.trim().replace(/^by\\s*/i, "");
                break;
            }
        }

        // 좋아요/부스트 수 (aria-label에서 추출)
        let likes = 0;
        const boostBtn = art.querySelector('[data-qa-id="ui-lib-card-like-button"]');
        if (boostBtn) {
            const ariaLabel = boostBtn.querySelector("[aria-label]");
            if (ariaLabel) {
                const labelText = ariaLabel.getAttribute("aria-label") || "";
                const match = labelText.match(/(\\d+)\\s*boost/i);
                if (match) {
                    likes = parseInt(match[1]) || 0;
                }
            }
        }

        // 대안: 버튼 내 숫자 직접 추출
        if (likes === 0 && boostBtn) {
            const digits = boostBtn.querySelectorAll('[class*="digit"]');
            if (digits.length > 0) {
                let numStr = "";
                digits.forEach(d => numStr += d.textContent.trim());
                likes = parseInt(numStr) || 0;
            }
        }

        // 오픈소스 여부 (아이콘 title 확인)
        const scriptIcon = art.querySelector('[class*="script-icon-wrap"]');
        const iconTitle = scriptIcon ? scriptIcon.getAttribute("title") || "" : "";
        const isOpenSource = !iconTitle.toLowerCase().includes("invite") &&
                             !iconTitle.toLowerCase().includes("protected");

        // 타입 확인 (strategy vs indicator)
        const isStrategy = iconTitle.toLowerCase().includes("strategy");

        // 설명
        const descEl = art.querySelector('a[data-qa-id="ui-lib-card-link-paragraph"]');
        const description = descEl ? descEl.textContent.trim().slice(0, 200) : "";

        return {
            scriptId,
            title,
            author,
            likes,
            href,
            isOpenSource,
            isStrategy,
            iconTitle,
            description
        };
    }).filter(card => card.scriptId && card.title);
}
"""

async def test_scraper():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, "webdriver", {get: () => undefined});
        """)

        # 1. 기본 페이지 로드
        url = "https://www.tradingview.com/scripts/"
        print(f"1. Loading base page: {url}")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        # 2. Strategies 필터 적용
        print("2. Applying Strategies filter...")
        all_types_btn = page.locator('button:has-text("All types")')
        if await all_types_btn.count() > 0:
            await all_types_btn.first.click()
            await asyncio.sleep(1)

            strategies_opt = page.locator('text="Strategies"')
            if await strategies_opt.count() > 0:
                await strategies_opt.first.click()
                await asyncio.sleep(3)
                print("   Filter applied!")

        # 3. 스크롤하여 더 많은 카드 로드
        print("3. Scrolling to load more cards...")
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.5)

        # 4. 데이터 추출
        data = await page.evaluate(JS_EXTRACT)

        print(f"\n총 {len(data)}개 전략 발견\n")

        # 좋아요 500+ 전략
        high_likes = [d for d in data if d.get("likes", 0) >= 500]
        print(f"좋아요 500+인 전략: {len(high_likes)}개\n")

        print("=== 전략 목록 (상위 10개) ===")
        for i, d in enumerate(data[:10]):
            print(f"{i+1}. {d['title']}")
            print(f"   작성자: {d['author']}")
            print(f"   좋아요: {d['likes']}")
            print(f"   오픈소스: {d['isOpenSource']}")
            print()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_scraper())
