#!/usr/bin/env python3
"""
TradingView 전략 페이지에서 수집 가능한 품질 지표 조사
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright

# 전략 상세 페이지에서 품질 지표 추출
JS_INSPECT_STRATEGY_PAGE = """
() => {
    const result = {
        // === 기본 정보 ===
        title: "",
        author: "",
        authorProfile: "",

        // === 인기도 지표 ===
        likes: 0,
        comments: 0,
        views: 0,
        shares: 0,
        favorites: 0,

        // === 작성자 신뢰도 ===
        authorFollowers: 0,
        authorReputation: 0,
        authorScriptsCount: 0,
        isVerified: false,
        isPremium: false,

        // === 게시 정보 ===
        publishDate: "",
        updateDate: "",
        pineVersion: 0,

        // === 전략 성과 (Strategy Tester) ===
        performance: {},

        // === 코드 정보 ===
        isOpenSource: false,
        codeLength: 0,

        // === 추가 메타 ===
        tags: [],
        category: "",

        // === DOM 조사용 (디버깅) ===
        foundElements: []
    };

    // 제목
    const titleEl = document.querySelector('h1, [class*="title"]');
    if (titleEl) result.title = titleEl.textContent.trim();

    // 작성자 정보
    const authorLink = document.querySelector('a[href*="/u/"]');
    if (authorLink) {
        result.author = authorLink.textContent.trim();
        result.authorProfile = authorLink.href;
    }

    // 좋아요/Boosts
    const boostElements = document.querySelectorAll('[class*="boost"], [class*="like"], [data-name*="boost"]');
    boostElements.forEach(el => {
        const text = el.textContent.trim();
        const match = text.match(/(\\d+)/);
        if (match && parseInt(match[1]) > result.likes) {
            result.likes = parseInt(match[1]);
            result.foundElements.push({type: 'likes', selector: el.className, value: text});
        }
    });

    // 댓글 수
    const commentElements = document.querySelectorAll('[class*="comment"], [data-name*="comment"]');
    commentElements.forEach(el => {
        const text = el.textContent.trim();
        const match = text.match(/(\\d+)/);
        if (match) {
            result.comments = parseInt(match[1]);
            result.foundElements.push({type: 'comments', selector: el.className, value: text});
        }
    });

    // 조회수
    const viewElements = document.querySelectorAll('[class*="view"], [class*="eye"]');
    viewElements.forEach(el => {
        const text = el.textContent.trim();
        const match = text.match(/([\\d.]+)([KkMm])?/);
        if (match) {
            let num = parseFloat(match[1]);
            if (match[2] === 'K' || match[2] === 'k') num *= 1000;
            if (match[2] === 'M' || match[2] === 'm') num *= 1000000;
            if (num > result.views) {
                result.views = Math.floor(num);
                result.foundElements.push({type: 'views', selector: el.className, value: text});
            }
        }
    });

    // 작성자 팔로워 수
    const followerElements = document.querySelectorAll('[class*="follower"], [class*="subscriber"]');
    followerElements.forEach(el => {
        const text = el.textContent.trim();
        const match = text.match(/([\\d.]+)([KkMm])?/);
        if (match) {
            let num = parseFloat(match[1]);
            if (match[2] === 'K' || match[2] === 'k') num *= 1000;
            if (match[2] === 'M' || match[2] === 'm') num *= 1000000;
            result.authorFollowers = Math.floor(num);
            result.foundElements.push({type: 'followers', selector: el.className, value: text});
        }
    });

    // 게시일/업데이트일
    const dateElements = document.querySelectorAll('[class*="date"], time, [datetime]');
    dateElements.forEach(el => {
        const datetime = el.getAttribute('datetime') || el.textContent.trim();
        if (datetime) {
            result.foundElements.push({type: 'date', selector: el.className || el.tagName, value: datetime});
            if (!result.publishDate) result.publishDate = datetime;
        }
    });

    // 태그
    const tagElements = document.querySelectorAll('[class*="tag"], [class*="label"]');
    tagElements.forEach(el => {
        const text = el.textContent.trim();
        if (text.length < 30 && text.length > 1) {
            result.tags.push(text);
        }
    });

    // Pine Script 버전
    const bodyText = document.body.innerText;
    const versionMatch = bodyText.match(/\\/\\/@version=(\\d+)/);
    if (versionMatch) result.pineVersion = parseInt(versionMatch[1]);

    // 오픈소스 여부
    result.isOpenSource = bodyText.includes('Open-source script') ||
                          bodyText.includes('오픈 소스 스크립트');

    // Strategy Tester 성과 지표 찾기
    const performanceLabels = [
        'Net Profit', 'Profit Factor', 'Max Drawdown', 'Total Trades',
        'Win Rate', 'Percent Profitable', 'Sharpe Ratio', 'Sortino Ratio'
    ];

    performanceLabels.forEach(label => {
        // 테이블에서 찾기
        const rows = document.querySelectorAll('tr');
        rows.forEach(row => {
            if (row.textContent.includes(label)) {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 2) {
                    result.performance[label] = cells[cells.length - 1].textContent.trim();
                }
            }
        });

        // 일반 텍스트에서 찾기
        const regex = new RegExp(label + '[:\\s]+([\\d.%$,+-]+)', 'i');
        const match = bodyText.match(regex);
        if (match && !result.performance[label]) {
            result.performance[label] = match[1];
        }
    });

    // 전체 페이지에서 모든 숫자 관련 요소 수집 (디버깅용)
    const allNumericElements = document.querySelectorAll('[class*="count"], [class*="stat"], [class*="metric"], [class*="number"]');
    allNumericElements.forEach(el => {
        result.foundElements.push({
            type: 'numeric',
            selector: el.className,
            value: el.textContent.trim().slice(0, 100)
        });
    });

    return result;
}
"""

async def inspect_strategy_page(url: str):
    """전략 상세 페이지 조사"""
    print(f"\n조사 중: {url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)

        # Source code 버튼 클릭 시도
        source_btn = page.locator('button:has-text("Source code")')
        if await source_btn.count() > 0:
            await source_btn.first.click()
            await asyncio.sleep(2)

        result = await page.evaluate(JS_INSPECT_STRATEGY_PAGE)

        await browser.close()

    return result


async def main():
    # 인기 전략 몇 개 조사
    test_urls = [
        "https://www.tradingview.com/script/Bbh7836m-Impulsive-Trend-Detector-dtAlgo/",
        "https://www.tradingview.com/script/QgqxLgLT-Smart-Money-Concepts-with-EMA-RSI-DrSaf/",
    ]

    print("=" * 70)
    print("TradingView 전략 페이지 품질 지표 조사")
    print("=" * 70)

    for url in test_urls[:1]:  # 일단 1개만 테스트
        result = await inspect_strategy_page(url)

        print("\n=== 기본 정보 ===")
        print(f"제목: {result['title']}")
        print(f"작성자: {result['author']}")
        print(f"Pine 버전: {result['pineVersion']}")
        print(f"오픈소스: {result['isOpenSource']}")

        print("\n=== 인기도 지표 ===")
        print(f"좋아요: {result['likes']}")
        print(f"댓글: {result['comments']}")
        print(f"조회수: {result['views']}")
        print(f"작성자 팔로워: {result['authorFollowers']}")

        print("\n=== 날짜 정보 ===")
        print(f"게시일: {result['publishDate']}")

        print("\n=== 성과 지표 ===")
        for k, v in result['performance'].items():
            print(f"  {k}: {v}")

        print("\n=== 발견된 요소들 (디버깅) ===")
        for elem in result['foundElements'][:20]:
            print(f"  [{elem['type']}] {elem['selector'][:50]}... = {elem['value'][:50]}")

        print("\n" + "-" * 70)


if __name__ == "__main__":
    asyncio.run(main())
