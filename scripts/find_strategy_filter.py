#!/usr/bin/env python3
"""전략 필터 찾기"""

import asyncio
from playwright.async_api import async_playwright

async def find_filter():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        url = "https://www.tradingview.com/scripts/"
        print(f"Loading: {url}")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)

        # "All types" 버튼 클릭
        try:
            all_types_btn = page.locator('button:has-text("All types")')
            if await all_types_btn.count() > 0:
                print("Found 'All types' button, clicking...")
                await all_types_btn.first.click()
                await page.wait_for_timeout(1000)

                # 드롭다운 옵션 확인
                options = await page.evaluate("""
                    () => {
                        const items = document.querySelectorAll('[role="menuitem"], [role="option"], [class*="dropdown"] [class*="item"]');
                        return Array.from(items).map(item => ({
                            text: item.textContent.trim().slice(0, 50),
                            className: item.className
                        }));
                    }
                """)

                print("\n드롭다운 옵션:")
                for opt in options[:15]:
                    print(f"  - {opt['text']}")

                # Strategies 옵션 클릭
                strategies_opt = page.locator('text="Strategies"')
                if await strategies_opt.count() > 0:
                    print("\nClicking 'Strategies' option...")
                    await strategies_opt.first.click()
                    await page.wait_for_timeout(3000)

                    # URL 확인
                    current_url = page.url
                    print(f"\nNew URL: {current_url}")

                    # 아이콘 타이틀 확인
                    icons = await page.evaluate("""
                        () => {
                            const icons = document.querySelectorAll('[class*="script-icon-wrap"]');
                            return Array.from(icons).slice(0, 5).map(icon => icon.getAttribute('title'));
                        }
                    """)
                    print("\n아이콘 타이틀:")
                    for icon in icons:
                        print(f"  - {icon}")

        except Exception as e:
            print(f"Error: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_filter())
