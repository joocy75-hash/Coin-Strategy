#!/usr/bin/env python3
"""전략 분석만 실행하는 스크립트.

기존에 수집된 전략의 Pine Script 코드를 분석합니다.

Usage:
    python scripts/run_analyzer.py --input data/collected.json
    python scripts/run_analyzer.py --input data/collected.json --skip-llm
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.analyzer import StrategyScorer
from src.storage import StrategyDatabase


async def main():
    parser = argparse.ArgumentParser(description="Pine Script 전략 분석기")
    parser.add_argument("--input", "-i", type=str, required=True, help="분석할 JSON 파일")
    parser.add_argument("--skip-llm", action="store_true", help="LLM 분석 스킵")
    parser.add_argument("--limit", "-l", type=int, default=None, help="분석할 전략 수 제한")
    parser.add_argument("--output", "-o", type=str, default=None, help="결과 저장 경로")
    parser.add_argument("--save-to-db", action="store_true", help="데이터베이스에 저장")

    args = parser.parse_args()

    config = Config.load()
    config.ensure_directories()

    print("=" * 60)
    print("Pine Script Strategy Analyzer")
    print("=" * 60)

    # 입력 파일 로드
    with open(args.input, "r", encoding="utf-8") as f:
        strategies = json.load(f)

    print(f"로드된 전략: {len(strategies)}개")

    # 분석 제한
    to_analyze = strategies[:args.limit] if args.limit else strategies

    # 분석기 초기화
    scorer = StrategyScorer(
        openai_api_key=config.openai_api_key,
        model=config.llm_model
    )

    # 데이터베이스 (옵션)
    db = None
    if args.save_to_db:
        db = StrategyDatabase(config.db_path)
        await db.initialize()

    results = []
    for i, strategy in enumerate(to_analyze, 1):
        title = strategy.get("title", f"Strategy {i}")
        pine_code = strategy.get("pine_code")

        if not pine_code:
            print(f"[{i}] {title} - Pine Script 코드 없음, 스킵")
            continue

        print(f"[{i}/{len(to_analyze)}] {title} 분석 중...")

        try:
            score = await scorer.score_strategy(
                pine_code=pine_code,
                skip_llm=args.skip_llm
            )

            result = {
                **strategy,
                "analysis": {
                    "total_score": score.total_score,
                    "repainting_score": score.repainting_score,
                    "overfitting_score": score.overfitting_score,
                    "risk_management_score": score.risk_management_score,
                    "repainting_risk": score.repainting_analysis.risk_level.value,
                    "overfitting_risk": score.overfitting_analysis.risk_level,
                    "has_stop_loss": score.risk_analysis.has_stop_loss,
                    "has_take_profit": score.risk_analysis.has_take_profit,
                }
            }

            if score.llm_analysis:
                result["analysis"]["llm_summary"] = score.llm_analysis.summary

            results.append(result)

            print(f"  총점: {score.total_score:.1f}/100")
            print(f"  리페인팅: {score.repainting_analysis.risk_level.value}")
            print(f"  오버피팅: {score.overfitting_analysis.risk_level}")

        except Exception as e:
            print(f"  분석 실패: {e}")

    # 결과 저장
    if results:
        output_path = args.output or f"data/analyzed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n결과 저장: {output_file}")

    # 통계 출력
    if results:
        avg_score = sum(r["analysis"]["total_score"] for r in results) / len(results)
        print(f"\n분석 완료: {len(results)}개 전략")
        print(f"평균 점수: {avg_score:.1f}/100")

    if db:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
