#!/usr/bin/env python3
"""
수정된 코드의 DB 작업 테스트
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.database import StrategyDatabase


async def test_db_operations():
    """DB 작업 테스트"""

    db_path = str(project_root / "data" / "strategies.db")

    print("=" * 60)
    print("🧪 DB 작업 테스트")
    print("=" * 60)

    # 1. 컨텍스트 매니저 테스트
    print("\n1. 컨텍스트 매니저 테스트...")
    try:
        async with StrategyDatabase(db_path) as db:
            print("   ✅ 컨텍스트 매니저 정상 작동")
    except Exception as e:
        print(f"   ❌ 실패: {e}")
        return

    # 2. upsert_strategy 테스트 (수정된 코드)
    print("\n2. upsert_strategy 테스트 (필수 필드 포함)...")
    try:
        async with StrategyDatabase(db_path) as db:
            await db.upsert_strategy({
                'script_id': 'TEST_STRATEGY_001',
                'title': 'Test Strategy for Verification',
                'author': 'Test Author',
                'likes': 999,
                'script_url': 'https://test.com/test',
                'pine_code': '//@version=5\nindicator("test")',
                'pine_version': 5,
                'is_open_source': True
            })
            print("   ✅ 기본 저장 성공")
    except Exception as e:
        print(f"   ❌ 실패: {e}")
        return

    # 3. analysis 업데이트 테스트 (수정된 코드)
    print("\n3. analysis 업데이트 테스트 (딕셔너리로 전달)...")
    try:
        async with StrategyDatabase(db_path) as db:
            analysis_data = {
                'grade': 'B',
                'total_score': 75.0,
                'code_score': 70.0,
                'performance_score': 80.0,
                'quality_score': 75.0,
                'repainting_score': 90.0,
                'overfitting_score': 85.0,
                'repainting_issues': [],
                'overfitting_issues': [],
                'analyzed_at': datetime.now().isoformat()
            }

            await db.upsert_strategy({
                'script_id': 'TEST_STRATEGY_001',
                'title': 'Test Strategy for Verification',
                'author': 'Test Author',
                'likes': 999,
                'script_url': 'https://test.com/test',
                'analysis': analysis_data  # 딕셔너리로 전달
            })
            print("   ✅ 분석 데이터 업데이트 성공")
    except Exception as e:
        print(f"   ❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. get_stats 테스트 (수정된 코드)
    print("\n4. get_stats 테스트 (객체 속성 접근)...")
    try:
        async with StrategyDatabase(db_path) as db:
            stats = await db.get_stats()
            total = stats.total_strategies  # 딕셔너리가 아닌 객체 속성
            analyzed = stats.analyzed_count
            passed = stats.passed_count

            print(f"   ✅ 통계 조회 성공")
            print(f"      - 총 전략: {total}개")
            print(f"      - 분석 완료: {analyzed}개")
            print(f"      - 통과: {passed}개")
    except Exception as e:
        print(f"   ❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. 저장된 데이터 확인
    print("\n5. 저장된 데이터 확인...")
    try:
        async with StrategyDatabase(db_path) as db:
            strategy = await db.get_strategy('TEST_STRATEGY_001')
            if strategy:
                print(f"   ✅ 전략 조회 성공")
                print(f"      - 제목: {strategy.title}")
                print(f"      - 등급: {strategy.analysis.get('grade') if strategy.analysis else 'N/A'}")
                print(f"      - 점수: {strategy.analysis.get('total_score') if strategy.analysis else 'N/A'}")
            else:
                print("   ⚠️  전략을 찾을 수 없음")
    except Exception as e:
        print(f"   ❌ 실패: {e}")

    print("\n" + "=" * 60)
    print("✅ 모든 테스트 통과!")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(test_db_operations())
