#!/usr/bin/env python3
"""
수정된 코드로 기존 전략 재분석
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.database import StrategyDatabase
from scripts.analyze_strategies import StrategyAnalyzer

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s'
)
logger = logging.getLogger(__name__)


async def reanalyze_strategies_fixed():
    """수정된 upsert_strategy로 재분석"""

    db_path = str(project_root / "data" / "strategies.db")

    logger.info("=" * 60)
    logger.info("🤖 AI 재분석 시작 (수정된 코드)")
    logger.info("=" * 60)

    # pine_code는 있지만 analysis_json이 없는 전략 조회
    import aiosqlite
    strategies_to_analyze = []

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            """
            SELECT script_id, title, author, likes, script_url
            FROM strategies
            WHERE pine_code IS NOT NULL
            AND (analysis_json IS NULL OR analysis_json = '')
            ORDER BY likes DESC
            """
        ) as cursor:
            async for row in cursor:
                strategies_to_analyze.append({
                    'script_id': row['script_id'],
                    'title': row['title'],
                    'author': row['author'],
                    'likes': row['likes'],
                    'script_url': row['script_url']
                })

    total = len(strategies_to_analyze)
    logger.info(f"📋 분석 대상: {total}개 전략\n")

    if total == 0:
        logger.info("✅ 모든 전략이 이미 분석되었습니다!")
        return

    analyzer = StrategyAnalyzer(headless=True)
    analyzed = 0
    failed = 0

    async with StrategyDatabase(db_path) as db:
        for i, strategy in enumerate(strategies_to_analyze, 1):
            try:
                logger.info(f"[{i}/{total}] {strategy['title'][:50]}")

                # AI 분석 실행
                analysis = await analyzer.analyze_strategy({
                    'scriptId': strategy['script_id'],
                    'title': strategy['title'],
                    'author': strategy['author'],
                    'likes': strategy['likes'],
                    'href': strategy['script_url']
                })

                # 등급 계산
                total_score = analysis.total_score
                if total_score >= 80:
                    grade = 'A'
                elif total_score >= 70:
                    grade = 'B'
                elif total_score >= 60:
                    grade = 'C'
                elif total_score >= 50:
                    grade = 'D'
                else:
                    grade = 'F'

                # analysis_json 생성
                analysis_json = {
                    'grade': grade,
                    'total_score': round(total_score, 1),
                    'code_score': round(analysis.code_score, 1),
                    'performance_score': round(analysis.performance_score, 1),
                    'quality_score': round(analysis.quality_score, 1),
                    'repainting_score': 100 - len(analysis.repainting_issues) * 10,
                    'overfitting_score': 100 - len(analysis.overfitting_issues) * 10,
                    'repainting_issues': analysis.repainting_issues,
                    'overfitting_issues': analysis.overfitting_issues,
                    'analyzed_at': datetime.now().isoformat()
                }

                # 수정된 upsert_strategy 호출 (모든 필수 필드 포함)
                await db.upsert_strategy({
                    'script_id': strategy['script_id'],
                    'title': strategy['title'],
                    'author': strategy['author'],
                    'likes': strategy['likes'],
                    'script_url': strategy['script_url'],
                    'analysis': analysis_json  # 딕셔너리로 전달
                })

                analyzed += 1
                logger.info(f"        ✅ 등급: {grade} (점수: {total_score:.1f})\n")

                await asyncio.sleep(1)  # Rate limiting

            except Exception as e:
                failed += 1
                logger.error(f"        ❌ 분석 실패: {e}\n")
                await asyncio.sleep(1)

    logger.info("=" * 60)
    logger.info(f"📊 재분석 완료")
    logger.info(f"   성공: {analyzed}개")
    logger.info(f"   실패: {failed}개")
    logger.info("=" * 60)


if __name__ == '__main__':
    asyncio.run(reanalyze_strategies_fixed())
