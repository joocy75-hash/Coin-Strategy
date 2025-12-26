#!/usr/bin/env python3
"""아이콘 타이틀 확인"""

import asyncio
from playwright.async_api import async_playwright

JS_CHECK = """
() => {
    const icons = document.querySelectorAll('[class*="script-icon-wrap"]');
    return Array.from(icons).map(icon => ({
        title: icon.getAttribute('title') || 'no title'
    }));
}
"""

async def check_icons():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        url = "https://www.tradingview.com/scripts/"
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)

        icons = await page.evaluate(JS_CHECK)

        print("아이콘 타이틀 목록:")
        unique_titles = set()
        for icon in icons:
            unique_titles.add(icon["title"])

        for title in unique_titles:
            print(f"  - {title}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_icons())
