#!/usr/bin/env python3
"""Pine Script 추출 디버깅"""

import asyncio
from playwright.async_api import async_playwright

JS_EXTRACT_CODE = """
() => {
    // Look for Monaco editor view lines
    const monacoLines = document.querySelectorAll(".view-line");
    if (monacoLines.length > 0) {
        let code = "";
        monacoLines.forEach(line => code += line.innerText + "\\n");
        if (code.length > 50) {
            return { source: "monaco", code: code };
        }
    }

    // Look for ACE editor
    const aceLines = document.querySelectorAll(".ace_line");
    if (aceLines.length > 0) {
        let code = "";
        aceLines.forEach(line => code += line.innerText + "\\n");
        if (code.length > 50) {
            return { source: "ace", code: code };
        }
    }

    // Look for code lines with line numbers stripped
    const codeArea = document.querySelector("[class*='codeBlock'], [class*='sourceCode'], [class*='content-']");
    if (codeArea) {
        const text = codeArea.innerText;
        // Split by newline and filter out pure numbers
        const lines = text.split("\\n").filter(l => !l.match(/^\\d+$/));
        if (lines.some(l => l.includes("indicator(") || l.includes("strategy(") || l.includes("//@version"))) {
            return { source: "codeArea", code: lines.join("\\n") };
        }
    }

    // Fallback - search whole document
    const body = document.body.innerText;
    if (body.includes("//@version=")) {
        const startIdx = body.indexOf("//@version=");
        // Get a chunk of text from version marker
        const chunk = body.slice(startIdx, startIdx + 5000);
        return { source: "body-search", code: chunk };
    }

    return { source: "not_found", code: null };
}
"""

async def get_source_code():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        url = 'https://www.tradingview.com/script/h5TO1j8H-Pivot-Levels-BigBeluga/'
        print(f'Loading: {url}')
        await page.goto(url, wait_until='networkidle', timeout=60000)
        await asyncio.sleep(3)

        # Click Source code button
        source_btn = page.locator('button:has-text("Source code")')
        if await source_btn.count() > 0:
            print('Clicking Source code button...')
            await source_btn.first.click()
            await asyncio.sleep(3)

            # Extract code
            result = await page.evaluate(JS_EXTRACT_CODE)

            print(f"\nSource: {result.get('source')}")
            if result.get('code'):
                code = result['code']
                print(f"Code length: {len(code)} chars")
                print(f"\n--- Code Preview (first 1000 chars) ---\n{code[:1000]}")
            else:
                print('No code found')

                # Debug: print page structure
                structure = await page.evaluate("""
                () => {
                    const selectors = [
                        ".view-line",
                        ".ace_line",
                        "[class*='code']",
                        "[class*='source']",
                        "[class*='pine']",
                        "[class*='editor']",
                        "pre",
                        "code"
                    ];
                    const found = [];
                    for (const sel of selectors) {
                        const count = document.querySelectorAll(sel).length;
                        if (count > 0) {
                            found.push({ selector: sel, count: count });
                        }
                    }
                    return found;
                }
                """)
                print("\nFound selectors:")
                for item in structure:
                    print(f"  {item['selector']}: {item['count']} elements")
        else:
            print('No Source code button found')

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_source_code())
