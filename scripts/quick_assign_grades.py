#!/usr/bin/env python3
"""
빠른 등급 부여 - AI 분석 없이 기본 점수 부여
나중에 auto_collector가 재분석할 것임
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import aiosqlite


async def quick_assign_grades():
    """pine_code는 있지만 analysis가 없는 전략에 기본 등급 부여"""

    db_path = str(project_root / "data" / "strategies.db")

    print("=" * 60)
    print("⚡ 빠른 등급 부여 시작")
    print("=" * 60)

    async with aiosqlite.connect(db_path) as db:
        # 분석 필요한 전략 조회
        async with db.execute(
            """
            SELECT script_id, title, author, likes, script_url
            FROM strategies
            WHERE pine_code IS NOT NULL
            AND (analysis_json IS NULL OR analysis_json = '')
            ORDER BY likes DESC
            """
        ) as cursor:
            strategies = await cursor.fetchall()

        total = len(strategies)
        print(f"📋 대상 전략: {total}개\n")

        if total == 0:
            print("✅ 모든 전략이 이미 분석되었습니다!")
            return

        success = 0
        for i, row in enumerate(strategies, 1):
            script_id, title, author, likes, script_url = row

            # likes 기반 간단한 점수 계산
            # 500-1000: 50점 (D)
            # 1000-1500: 60점 (C)
            # 1500-2000: 70점 (B)
            # 2000+: 75점 (B)
            if likes >= 2000:
                score = 75
                grade = 'B'
            elif likes >= 1500:
                score = 70
                grade = 'B'
            elif likes >= 1000:
                score = 60
                grade = 'C'
            else:
                score = 50
                grade = 'D'

            # 기본 analysis_json 생성
            analysis_json = {
                'grade': grade,
                'total_score': float(score),
                'code_score': float(score),
                'performance_score': float(score),
                'quality_score': float(score),
                'repainting_score': 80.0,
                'overfitting_score': 80.0,
                'repainting_issues': [],
                'overfitting_issues': [],
                'analyzed_at': datetime.now().isoformat(),
                'note': 'Preliminary grade based on likes. Will be re-analyzed by auto_collector.'
            }

            # DB 업데이트
            await db.execute(
                """
                UPDATE strategies
                SET analysis_json = ?, updated_at = ?
                WHERE script_id = ?
                """,
                (json.dumps(analysis_json, ensure_ascii=False), datetime.now().isoformat(), script_id)
            )

            success += 1
            print(f"[{i}/{total}] {title[:50]}")
            print(f"        ✅ 등급: {grade} (점수: {score}, likes: {likes:,})\n")

        await db.commit()

        print("=" * 60)
        print(f"✅ 완료: {success}개 전략에 기본 등급 부여")
        print(f"   이후 auto_collector가 자동으로 AI 재분석할 것입니다")
        print("=" * 60)


if __name__ == '__main__':
    asyncio.run(quick_assign_grades())
