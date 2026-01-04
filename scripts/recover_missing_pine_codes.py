#!/usr/bin/env python3
"""
누락된 Pine Script 코드 재수집 스크립트

DB에 전략 메타데이터는 있지만 pine_code가 NULL인 전략들의
코드를 재수집하여 업데이트합니다.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict

# 프로젝트 루트 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.collector.pine_fetcher import PineCodeFetcher
from src.storage.database import StrategyDatabase

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


async def get_strategies_without_code(db_path: str) -> List[Dict]:
    """pine_code가 없는 전략 목록 가져오기"""
    db = StrategyDatabase(db_path)
    await db.init_db()

    import aiosqlite
    strategies = []

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT script_id, title, author, script_url FROM strategies WHERE pine_code IS NULL OR pine_code = ''"
        ) as cursor:
            async for row in cursor:
                strategies.append({
                    'script_id': row['script_id'],
                    'title': row['title'],
                    'author': row['author'],
                    'script_url': row['script_url']
                })

    return strategies


async def recover_pine_codes(db_path: str, delay: float = 2.0):
    """pine_code 재수집 및 업데이트"""
    logger.info("=" * 60)
    logger.info("Pine Script 코드 복구 시작")
    logger.info("=" * 60)

    # 1. 코드 없는 전략 조회
    strategies = await get_strategies_without_code(db_path)
    total = len(strategies)

    if total == 0:
        logger.info("✅ 모든 전략에 코드가 있습니다!")
        return

    logger.info(f"📋 코드 없는 전략: {total}개")
    logger.info("")

    # 2. 코드 추출
    fetcher = PineCodeFetcher()
    db = StrategyDatabase(db_path)
    await db.init_db()

    success_count = 0
    failed_count = 0
    protected_count = 0

    for i, strategy in enumerate(strategies, 1):
        script_id = strategy['script_id']
        title = strategy['title']
        script_url = strategy['script_url']

        logger.info(f"[{i}/{total}] {title[:50]}")
        logger.info(f"        URL: {script_url}")

        try:
            # Pine 코드 추출
            result = await fetcher.fetch_pine_code(script_url)

            if result.pine_code and not result.is_protected:
                # DB 업데이트
                await db.upsert_strategy({
                    'script_id': script_id,
                    'title': title,
                    'author': strategy['author'],
                    'pine_code': result.pine_code,
                    'pine_version': result.pine_version,
                    'script_url': script_url
                })

                success_count += 1
                logger.info(f"        ✅ 코드 추출 성공 ({len(result.pine_code)} bytes, v{result.pine_version})")
            elif result.is_protected:
                protected_count += 1
                logger.warning(f"        🔒 보호된 코드 (비공개 전략)")
            else:
                failed_count += 1
                logger.warning(f"        ⚠️  코드 추출 실패")

            # Rate limiting
            await asyncio.sleep(delay)

        except Exception as e:
            failed_count += 1
            logger.error(f"        ❌ 오류: {e}")
            await asyncio.sleep(delay)

    # 3. 결과 요약
    logger.info("")
    logger.info("=" * 60)
    logger.info("복구 완료")
    logger.info("=" * 60)
    logger.info(f"총 처리: {total}개")
    logger.info(f"  ✅ 성공: {success_count}개")
    logger.info(f"  🔒 보호됨: {protected_count}개")
    logger.info(f"  ❌ 실패: {failed_count}개")
    logger.info("")

    if success_count > 0:
        logger.info(f"💾 {success_count}개 전략의 Pine Script 코드가 복구되었습니다!")


async def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='누락된 Pine Script 코드 재수집')
    parser.add_argument('--db', type=str, default='data/strategies.db', help='데이터베이스 경로')
    parser.add_argument('--delay', type=float, default=2.0, help='요청 간 딜레이 (초)')
    args = parser.parse_args()

    db_path = project_root / args.db

    if not db_path.exists():
        logger.error(f"❌ 데이터베이스를 찾을 수 없습니다: {db_path}")
        return

    try:
        await recover_pine_codes(str(db_path), args.delay)
    except KeyboardInterrupt:
        logger.info("\n⏸️  사용자에 의해 중단됨")
    except Exception as e:
        logger.exception(f"❌ 오류 발생: {e}")


if __name__ == '__main__':
    asyncio.run(main())
