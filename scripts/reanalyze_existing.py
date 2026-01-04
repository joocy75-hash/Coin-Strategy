#!/usr/bin/env python3
"""
기존 수집된 전략들을 AI 분석하여 analysis_json 생성

이미 수집되었지만 analysis_json이 없거나 grade가 없는 전략들을
분석하여 프론트엔드에서 볼 수 있도록 합니다.
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
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


async def reanalyze_existing_strategies():
    """기존 전략들을 재분석"""

    db_path = str(project_root / "data" / "strategies.db")
    db = StrategyDatabase(db_path)
    await db.init_db()

    # analysis_json이 없거나 grade가 없는 전략 조회
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # pine_code가 있는 전략 중 분석이 필요한 전략 찾기
    cur.execute("""
        SELECT script_id, title, author, likes, script_url, pine_code
        FROM strategies
        WHERE pine_code IS NOT NULL AND pine_code != ''
    """)

    strategies = cur.fetchall()
    conn.close()

    if not strategies:
        logger.info("분석할 전략이 없습니다.")
        return

    # grade가 있는지 확인
    needs_analysis = []
    for row in strategies:
        script_id = row['script_id']
        cur = sqlite3.connect(db_path).cursor()
        cur.execute("SELECT analysis_json FROM strategies WHERE script_id = ?", [script_id])
        result = cur.fetchone()

        needs_reanalysis = True
        if result and result[0]:
            try:
                analysis = json.loads(result[0])
                if analysis.get('grade') and analysis.get('grade') != 'N/A':
                    needs_reanalysis = False
            except:
                pass

        if needs_reanalysis:
            needs_analysis.append(row)

    logger.info(f"총 {len(strategies)}개 전략 중 {len(needs_analysis)}개가 분석 필요")

    if not needs_analysis:
        logger.info("모든 전략이 이미 분석되었습니다.")
        return

    # 분석 시작
    analyzer = StrategyAnalyzer(headless=True)
    analyzed_count = 0

    for i, row in enumerate(needs_analysis, 1):
        script_id = row['script_id']
        title = row['title']
        author = row['author']
        likes = row['likes']
        script_url = row['script_url']

        try:
            logger.info(f"[{i}/{len(needs_analysis)}] {title[:40]}... 분석 중")

            # StrategyAnalyzer에 필요한 형식으로 변환
            strategy_dict = {
                'scriptId': script_id,
                'title': title,
                'author': author,
                'likes': likes,
                'href': script_url
            }

            # AI 분석 실행
            analysis = await analyzer.analyze_strategy(strategy_dict)

            # 등급 계산 (A, B, C, D, F)
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

            # DB 업데이트
            await db.upsert_strategy({
                'script_id': script_id,
                'analysis_json': json.dumps(analysis_json)
            })

            analyzed_count += 1
            logger.info(f"   ✅ 등급: {grade} (점수: {total_score:.1f})")

            # Rate limiting
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"   ❌ 분석 실패: {e}")

    logger.info(f"\n{'='*60}")
    logger.info(f"재분석 완료: {analyzed_count}/{len(needs_analysis)}개 성공")
    logger.info(f"{'='*60}")


if __name__ == '__main__':
    asyncio.run(reanalyze_existing_strategies())
