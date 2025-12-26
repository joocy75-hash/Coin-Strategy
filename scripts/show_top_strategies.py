#!/usr/bin/env python3
"""
상위 전략 간단 리포트 출력 + Pine Script 코드

사용법:
    python scripts/show_top_strategies.py              # 상위 5개 전략
    python scripts/show_top_strategies.py --top 10     # 상위 10개 전략
    python scripts/show_top_strategies.py --grade A B  # A, B 등급만
    python scripts/show_top_strategies.py --code       # 코드 포함 출력
    python scripts/show_top_strategies.py --save       # 코드 파일로 저장
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import StrategyDatabase
from src.storage.models import SearchFilters
from src.storage.exporter import SimpleReportGenerator


async def show_top_strategies(
    db_path: str = "data/strategies.db",
    top_n: int = 5,
    grades: list[str] | None = None,
    min_score: float | None = None,
    include_code: bool = False,
    save_code: bool = False,
) -> None:
    """
    상위 전략을 간단한 리포트 형식으로 출력

    Args:
        db_path: 데이터베이스 경로
        top_n: 상위 N개
        grades: 필터링할 등급 (예: ["A", "B"])
        min_score: 최소 점수
        include_code: 터미널에 코드 출력
        save_code: 코드를 파일로 저장
    """
    db_file = Path(db_path)

    if not db_file.exists():
        print("\n" + "=" * 60)
        print("❌ 데이터베이스가 없습니다!")
        print("=" * 60)
        print("""
아직 전략을 수집하지 않았습니다. 다음 단계를 진행하세요:

1. 환경 설정:
   cp .env.example .env

2. 의존성 설치:
   pip install -r requirements.txt

3. Playwright 브라우저 설치:
   playwright install chromium

4. 전략 수집 실행:
   python scripts/run_collector.py --max-strategies 50 --min-likes 500

5. 분석 실행:
   python main.py --step analyze

6. 다시 이 스크립트 실행:
   python scripts/show_top_strategies.py
""")
        return

    # 데이터베이스 연결
    async with StrategyDatabase(str(db_file)) as db:
        # 필터 설정
        filters = SearchFilters(
            has_analysis=True,
            has_pine_code=True if (include_code or save_code) else None,
            grade=grades,
            min_score=min_score,
            order_by="score",  # 점수 기준 정렬
            order_desc=True,
            limit=top_n * 2,  # 여유있게 가져오기
        )

        # 전략 검색
        strategies = await db.search_strategies(filters)

        if not strategies:
            print("\n" + "=" * 60)
            print("⚠️ 분석된 전략이 없습니다!")
            print("=" * 60)
            print("""
전략 분석을 먼저 실행하세요:

    python main.py --step analyze

또는 필터 조건을 완화해보세요:

    python scripts/show_top_strategies.py --grade A B C D
""")
            return

        # 리포트 생성 및 출력
        reporter = SimpleReportGenerator()
        reporter.print_top_strategies(strategies, top_n=top_n, include_code=include_code)

        # 코드 파일로 저장
        if save_code:
            save_grades = grades or ["A", "B"]
            saved_files = reporter.save_strategies_with_code(
                strategies[:top_n],
                output_dir="data/exports/strategies",
                grades=save_grades
            )

            if saved_files:
                print("\n" + "=" * 60)
                print(f"📁 {len(saved_files)}개 전략 코드 저장 완료!")
                print("=" * 60)
                for f in saved_files:
                    print(f"  • {f}")
                print("")
            else:
                print("\n⚠️ 저장할 코드가 없습니다. (Pine 코드가 없거나 등급 필터에 해당하는 전략 없음)")

        # 추가 통계
        stats = await db.get_stats()
        print(f"\n📊 전체 통계: {stats.total_strategies}개 수집 / {stats.analyzed_count}개 분석 완료")
        print(f"   통과: {stats.passed_count}개 | 검토 필요: {stats.review_count}개 | 거부: {stats.rejected_count}개")


def main():
    parser = argparse.ArgumentParser(
        description="AI 추천 트레이딩 전략 리포트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
    python scripts/show_top_strategies.py              # 상위 5개 (코드 없이)
    python scripts/show_top_strategies.py --code       # 상위 5개 + 코드 출력
    python scripts/show_top_strategies.py --save       # 상위 5개 + 코드 파일 저장
    python scripts/show_top_strategies.py --top 10 --code  # 상위 10개 + 코드
    python scripts/show_top_strategies.py --grade A B --save  # A,B 등급만 저장
""",
    )

    parser.add_argument(
        "--db",
        default="data/strategies.db",
        help="데이터베이스 경로 (기본: data/strategies.db)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="상위 N개 전략 출력 (기본: 5)",
    )
    parser.add_argument(
        "--grade",
        nargs="+",
        choices=["A", "B", "C", "D", "F"],
        help="필터링할 등급 (예: --grade A B)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        help="최소 점수 (0-100)",
    )
    parser.add_argument(
        "--code",
        action="store_true",
        help="Pine Script 코드를 터미널에 함께 출력",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Pine Script 코드를 개별 파일로 저장 (data/exports/strategies/)",
    )

    args = parser.parse_args()

    asyncio.run(
        show_top_strategies(
            db_path=args.db,
            top_n=args.top,
            grades=args.grade,
            min_score=args.min_score,
            include_code=args.code,
            save_code=args.save,
        )
    )


if __name__ == "__main__":
    main()
