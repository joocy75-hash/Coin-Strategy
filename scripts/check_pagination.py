#!/usr/bin/env python3
"""페이지네이션 확인"""

import asyncio
from playwright.async_api import async_playwright

async def check_pagination():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, "webdriver", {get: () => undefined});
        """)

        # 페이지 로드
        await page.goto("https://www.tradingview.com/scripts/", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        # Strategies 필터
        all_types_btn = page.locator('button:has-text("All types")')
        if await all_types_btn.count() > 0:
            await all_types_btn.first.click()
            await asyncio.sleep(1)
            strategies_opt = page.locator('text="Strategies"')
            if await strategies_opt.count() > 0:
                await strategies_opt.first.click()
                await asyncio.sleep(2)

        # Popular 정렬
        popular_link = page.locator('a:has-text("Popular")')
        if await popular_link.count() > 0:
            await popular_link.first.click()
            await asyncio.sleep(3)

        # 현재 URL 확인
        print(f"Current URL: {page.url}")

        # 페이지네이션 요소 찾기
        pagination_elements = await page.evaluate("""
            () => {
                const elements = [];

                // 페이지 번호 버튼
                document.querySelectorAll('[class*="page"], [class*="pagination"]').forEach(el => {
                    elements.push({type: 'pagination', text: el.textContent.slice(0, 50), tag: el.tagName});
                });

                // Load More / Show More 버튼
                document.querySelectorAll('button, a').forEach(el => {
                    const text = el.textContent.toLowerCase();
                    if (text.includes('more') || text.includes('load') || text.includes('next')) {
                        elements.push({type: 'load-more', text: el.textContent.slice(0, 50), tag: el.tagName});
                    }
                });

                // 스크롤 트리거
                document.querySelectorAll('[class*="infinite"], [class*="scroll"]').forEach(el => {
                    elements.push({type: 'infinite', text: el.className.slice(0, 100), tag: el.tagName});
                });

                return elements;
            }
        """)

        print("\n페이지네이션 요소:")
        for el in pagination_elements[:20]:
            print(f"  [{el['type']}] {el['tag']}: {el['text']}")

        # 스크롤해서 더 많은 요소 확인
        print("\n스크롤 후...")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(3)

        # article 수 확인
        article_count = await page.locator('article').count()
        print(f"Article 수: {article_count}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_pagination())
