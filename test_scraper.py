#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent / "strategy-research-lab"
sys.path.insert(0, str(PROJECT_ROOT))

from src.collector.scripts_scraper import TVScriptsScraper

async def test():
    async with TVScriptsScraper(headless=True) as scraper:
        strategies = await scraper.scrape_strategies(max_count=10, min_likes=50, max_pages=5)
        print(f"\n=== 수집 결과 ===")
        for s in strategies:
            print(f"  {s.title}: likes={s.likes}, open_source={s.is_open_source}")
        print(f"\nTotal: {len(strategies)}")

asyncio.run(test())
