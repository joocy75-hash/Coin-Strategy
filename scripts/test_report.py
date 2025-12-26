#!/usr/bin/env python3
"""
리포트 생성 기능 테스트 스크립트
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_report import generate_html_report
from src.storage import StrategyDatabase


async def test_report():
    """리포트 생성 테스트"""
    print("=" * 60)
    print("리포트 생성 기능 테스트")
    print("=" * 60)
    
    # 1. 데이터베이스 확인
    print("\n1. 데이터베이스 확인...")
    db = StrategyDatabase("data/strategies.db")
    await db.init_db()
    
    stats = await db.get_stats()
    print(f"   총 전략: {stats.total_strategies}")
    print(f"   분석 완료: {stats.analyzed_count}")
    print(f"   통과: {stats.passed_count}")
    
    if stats.total_strategies == 0:
        print("\n   ⚠️  데이터베이스에 전략이 없습니다.")
        print("   먼저 main.py를 실행하여 데이터를 수집하세요.")
        await db.close()
        return False
    
    await db.close()
    
    # 2. 리포트 생성
    print("\n2. HTML 리포트 생성...")
    report_path = await generate_html_report(
        db_path="data/strategies.db",
        output_path="data/report.html"
    )
    
    # 3. 파일 확인
    print("\n3. 생성된 파일 확인...")
    report_file = Path(report_path)
    if not report_file.exists():
        print(f"   ✗ 파일이 생성되지 않았습니다: {report_path}")
        return False
    
    file_size = report_file.stat().st_size
    print(f"   ✓ 파일 생성 완료: {report_path}")
    print(f"   크기: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    # 4. HTML 내용 검증
    print("\n4. HTML 내용 검증...")
    html_content = report_file.read_text(encoding="utf-8")
    
    checks = [
        ("<!DOCTYPE html>", "DOCTYPE 선언"),
        ("<title>TradingView Strategy Research Lab", "제목"),
        ("strategiesData", "JavaScript 데이터"),
        ("function sortTable", "정렬 함수"),
        ("class=\"stat-card\"", "통계 카드"),
    ]
    
    all_passed = True
    for check_str, check_name in checks:
        if check_str in html_content:
            print(f"   ✓ {check_name}")
        else:
            print(f"   ✗ {check_name} 누락")
            all_passed = False
    
    # 5. 결과
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 모든 테스트 통과!")
        print("=" * 60)
        print(f"\n리포트 열기:")
        print(f"  open {report_path}")
        print(f"  또는")
        print(f"  python scripts/view_report.py")
        return True
    else:
        print("✗ 일부 테스트 실패")
        print("=" * 60)
        return False


async def main():
    try:
        success = await test_report()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
