#!/usr/bin/env python3
"""빠른 전략 수집 테스트"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

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

        const descEl = art.querySelector('a[data-qa-id="ui-lib-card-link-paragraph"]');
        const description = descEl ? descEl.textContent.trim().slice(0, 500) : "";

        return { scriptId, title, author, likes, href, isOpenSource, description };
    }).filter(card => card.scriptId && card.title);
}
"""

async def collect_strategies(max_count=20, min_likes=100):
    print("=" * 60)
    print("Quick Strategy Collector")
    print("=" * 60)
    print(flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, "webdriver", {get: () => undefined});
        """)

        # 1. 기본 페이지 로드
        print("1. Loading TradingView scripts page...", flush=True)
        await page.goto("https://www.tradingview.com/scripts/", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        # 2. Strategies 필터 적용
        print("2. Applying Strategies filter...", flush=True)
        all_types_btn = page.locator('button:has-text("All types")')
        if await all_types_btn.count() > 0:
            await all_types_btn.first.click()
            await asyncio.sleep(1)
            strategies_opt = page.locator('text="Strategies"')
            if await strategies_opt.count() > 0:
                await strategies_opt.first.click()
                await asyncio.sleep(2)
                print("   ✓ Strategies filter applied", flush=True)

        # 3. 인기순 정렬
        print("3. Applying popularity sort...", flush=True)
        popular_link = page.locator('a:has-text("Popular")')
        if await popular_link.count() > 0:
            await popular_link.first.click()
            await asyncio.sleep(3)
            print("   ✓ Popularity sort applied", flush=True)

        # 4. "Show more" 버튼 클릭으로 더 많은 전략 로드
        print("4. Loading more strategies...", flush=True)
        all_strategies = []
        click_count = 0
        max_clicks = 10  # 최대 10번 클릭

        while len(all_strategies) < max_count and click_count < max_clicks:
            # 현재 페이지 데이터 추출
            data = await page.evaluate(JS_EXTRACT)

            # 조건에 맞는 전략 필터링
            for item in data:
                if item['isOpenSource'] and item['likes'] >= min_likes:
                    # 중복 체크
                    if not any(s['scriptId'] == item['scriptId'] for s in all_strategies):
                        all_strategies.append(item)
                        print(f"   [{len(all_strategies)}] {item['title'][:40]}... ({item['likes']} likes)", flush=True)

            if len(all_strategies) >= max_count:
                break

            # "Show more publications" 버튼 찾기 및 클릭
            show_more = page.locator('button:has-text("Show more publications")')
            if await show_more.count() > 0:
                print(f"   Clicking 'Show more' button (click #{click_count + 1})...", flush=True)
                await show_more.first.click()
                click_count += 1
                await asyncio.sleep(3)  # 콘텐츠 로드 대기
            else:
                print("   No more 'Show more' button found.", flush=True)
                break

        await browser.close()

    # 결과
    results = all_strategies[:max_count]
    print(f"\n총 {len(results)}개 전략 수집 완료", flush=True)

    # 저장
    output_path = f"data/collected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path("data").mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"결과 저장: {output_path}", flush=True)

    # 상위 10개 출력
    print("\n=== 수집된 전략 (상위 10개) ===", flush=True)
    for i, s in enumerate(results[:10], 1):
        print(f"{i}. {s['title']}", flush=True)
        print(f"   작성자: {s['author']}, 좋아요: {s['likes']}", flush=True)

    return results

if __name__ == "__main__":
    # 품질 우선: 좋아요 200+ 전략 최대 50개 수집
    asyncio.run(collect_strategies(max_count=50, min_likes=200))
