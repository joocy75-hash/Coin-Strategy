#!/usr/bin/env python3
"""전략 수집만 실행하는 스크립트.

TradingView에서 전략 메타데이터와 Pine Script 코드를 수집합니다.

Usage:
    python scripts/run_collector.py
    python scripts/run_collector.py --max-strategies 50 --min-likes 1000
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.collector import TVScriptsScraper, PineCodeFetcher


async def main():
    parser = argparse.ArgumentParser(description="TradingView 전략 수집기")
    parser.add_argument("--max-strategies", "-m", type=int, default=50)
    parser.add_argument("--min-likes", "-l", type=int, default=500)
    parser.add_argument("--sort-by", "-s", choices=["popularity", "recent"], default="popularity")
    parser.add_argument("--output", "-o", type=str, default=None, help="결과 저장 경로 (JSON)")
    parser.add_argument("--fetch-code", action="store_true", help="Pine Script 코드도 수집")
    parser.add_argument("--debug", "-d", action="store_true")

    args = parser.parse_args()

    config = Config.load()
    config.ensure_directories()

    print("=" * 60)
    print("TradingView Strategy Collector")
    print("=" * 60)

    # 1. 전략 메타데이터 수집
    print(f"\n전략 수집 중 (최대 {args.max_strategies}개, 좋아요 {args.min_likes}+)...")

    async with TVScriptsScraper(headless=not args.debug) as scraper:
        strategies = await scraper.scrape_strategies(
            max_count=args.max_strategies,
            min_likes=args.min_likes,
            sort_by=args.sort_by
        )

    print(f"수집 완료: {len(strategies)}개 전략")

    if not strategies:
        print("수집된 전략이 없습니다.")
        return

    # 2. Pine Script 코드 수집 (옵션)
    results = []
    if args.fetch_code:
        print(f"\nPine Script 코드 수집 중...")
        fetcher = PineCodeFetcher(headless=not args.debug)

        for i, strategy in enumerate(strategies, 1):
            print(f"  [{i}/{len(strategies)}] {strategy.title}...")
            try:
                pine_data = await fetcher.fetch_pine_code(strategy.script_url)

                result = {
                    "script_id": strategy.script_id,
                    "title": strategy.title,
                    "author": strategy.author,
                    "likes": strategy.likes,
                    "views": strategy.views,
                    "script_url": strategy.script_url,
                    "is_open_source": strategy.is_open_source,
                    "description": strategy.description,
                    "scraped_at": str(strategy.scraped_at),
                }
                if pine_data:
                    result["pine_code"] = pine_data.source_code
                    result["pine_version"] = pine_data.version
                results.append(result)
            except Exception as e:
                print(f"    ⚠️ 코드 수집 실패: {e}")
                results.append({
                    "script_id": strategy.script_id,
                    "title": strategy.title,
                    "author": strategy.author,
                    "likes": strategy.likes,
                    "script_url": strategy.script_url,
                    "scraped_at": str(strategy.scraped_at),
                })

            await asyncio.sleep(config.rate_limit_delay)
    else:
        results = [
            {
                "script_id": s.script_id,
                "title": s.title,
                "author": s.author,
                "likes": s.likes,
                "views": s.views,
                "script_url": s.script_url,
                "is_open_source": s.is_open_source,
                "description": s.description,
                "scraped_at": str(s.scraped_at),
            }
            for s in strategies
        ]

    # 3. 결과 저장
    output_path = args.output or f"data/collected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n결과 저장: {output_file}")
    print(f"총 {len(results)}개 전략")

    # 4. 코드가 있는 전략 수
    if args.fetch_code:
        code_count = sum(1 for r in results if r.get("pine_code"))
        print(f"Pine 코드 수집: {code_count}개")


if __name__ == "__main__":
    asyncio.run(main())
