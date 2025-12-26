#!/usr/bin/env python3
"""인기순 전략 테스트"""

import asyncio
from playwright.async_api import async_playwright

JS_EXTRACT = """
() => {
    const articles = document.querySelectorAll("article");
    return Array.from(articles).map(art => {
        const titleLink = art.querySelector('a[data-qa-id="ui-lib-card-link-title"]');
        const title = titleLink ? titleLink.textContent.trim() : "";
        const href = titleLink ? titleLink.getAttribute("href") : "";
        const scriptIdMatch = href.match(/script\\/([^/]+)/);
        const scriptId = scriptIdMatch ? scriptIdMatch[1] : "";

        let author = "";
        const allLinks = art.querySelectorAll("a");
        for (const link of allLinks) {
            const h = link.getAttribute("href") || "";
            if (h.includes("/u/")) {
                author = link.textContent.trim().replace(/^by\\s*/i, "");
                break;
            }
        }

        let likes = 0;
        const boostBtn = art.querySelector('[data-qa-id="ui-lib-card-like-button"]');
        if (boostBtn) {
            const ariaLabel = boostBtn.querySelector("[aria-label]");
            if (ariaLabel) {
                const labelText = ariaLabel.getAttribute("aria-label") || "";
                const match = labelText.match(/(\\d+)\\s*boost/i);
                if (match) likes = parseInt(match[1]) || 0;
            }
        }
        if (likes === 0 && boostBtn) {
            const digits = boostBtn.querySelectorAll('[class*="digit"]');
            if (digits.length > 0) {
                let numStr = "";
                digits.forEach(d => numStr += d.textContent.trim());
                likes = parseInt(numStr) || 0;
            }
        }

        const scriptIcon = art.querySelector('[class*="script-icon-wrap"]');
        const iconTitle = scriptIcon ? scriptIcon.getAttribute("title") || "" : "";
        const isOpenSource = !iconTitle.toLowerCase().includes("invite") &&
                             !iconTitle.toLowerCase().includes("protected");

        return { scriptId, title, author, likes, href, isOpenSource };
    }).filter(card => card.scriptId && card.title);
}
"""

async def test_popular():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, "webdriver", {get: () => undefined});
        """)

        # 1. 기본 페이지 로드
        print("1. Loading base page...")
        await page.goto("https://www.tradingview.com/scripts/", wait_until="networkidle", timeout=60000)
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
                await asyncio.sleep(2)
                print("   Strategies filter applied!")

        # 3. 탭/정렬 확인
        print("3. Checking available tabs/sorts...")
        tabs = await page.evaluate("""
            () => {
                const tabs = document.querySelectorAll('[role="tab"], button, a');
                return Array.from(tabs).slice(0, 30).map(t => ({
                    text: t.textContent.trim().slice(0, 30),
                    tag: t.tagName
                })).filter(t => t.text.length > 0 && t.text.length < 20);
            }
        """)

        # 관련 탭 출력
        for tab in tabs:
            text = tab['text'].lower()
            if any(k in text for k in ['top', 'popular', 'best', 'trending', 'hot', 'new', 'recent']):
                print(f"   Found: {tab}")

        # Popular 링크 클릭
        popular_link = page.locator('a:has-text("Popular")')
        if await popular_link.count() > 0:
            print(f"   Found {await popular_link.count()} 'Popular' links, clicking first...")
            await popular_link.first.click()
            await asyncio.sleep(3)
        else:
            print("   'Popular' link not found")

        # 4. 스크롤
        print("4. Scrolling to load more...")
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.5)

        # 5. 데이터 추출
        data = await page.evaluate(JS_EXTRACT)

        print(f"\n총 {len(data)}개 전략 발견")

        # 좋아요 500+ 전략
        high_likes = [d for d in data if d.get("likes", 0) >= 500]
        print(f"좋아요 500+인 전략: {len(high_likes)}개\n")

        print("=== 전략 목록 (상위 15개) ===")
        for i, d in enumerate(data[:15]):
            print(f"{i+1}. {d['title'][:50]}")
            print(f"   작성자: {d['author']}, 좋아요: {d['likes']}, 오픈소스: {d['isOpenSource']}")
            print()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_popular())
