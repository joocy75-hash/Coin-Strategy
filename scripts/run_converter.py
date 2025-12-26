#!/usr/bin/env python3
"""전략 변환만 실행하는 스크립트.

분석된 전략을 Python 코드로 변환합니다.

Usage:
    python scripts/run_converter.py --input data/analyzed.json
    python scripts/run_converter.py --input data/analyzed.json --min-score 70
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.converter import StrategyGenerator


async def main():
    parser = argparse.ArgumentParser(description="Pine Script to Python 변환기")
    parser.add_argument("--input", "-i", type=str, required=True, help="변환할 JSON 파일")
    parser.add_argument("--min-score", type=float, default=50.0, help="최소 점수 (기본: 50)")
    parser.add_argument("--limit", "-l", type=int, default=None, help="변환할 전략 수 제한")
    parser.add_argument("--output-dir", "-o", type=str, default=None, help="출력 디렉토리")

    args = parser.parse_args()

    config = Config.load()
    config.ensure_directories()

    output_dir = args.output_dir or config.output_dir

    print("=" * 60)
    print("Pine Script to Python Converter")
    print("=" * 60)

    # 입력 파일 로드
    with open(args.input, "r", encoding="utf-8") as f:
        strategies = json.load(f)

    print(f"로드된 전략: {len(strategies)}개")

    # 점수 기준 필터링
    eligible = [
        s for s in strategies
        if s.get("analysis", {}).get("total_score", 0) >= args.min_score
        and s.get("pine_code")
    ]

    print(f"변환 대상 ({args.min_score}점 이상): {len(eligible)}개")

    # 점수 높은 순 정렬
    eligible.sort(key=lambda x: x["analysis"]["total_score"], reverse=True)

    # 제한 적용
    to_convert = eligible[:args.limit] if args.limit else eligible

    # 변환기 초기화
    generator = StrategyGenerator(
        openai_api_key=config.openai_api_key,
        output_dir=output_dir
    )

    converted = []
    for i, strategy in enumerate(to_convert, 1):
        title = strategy.get("title", f"Strategy {i}")
        pine_code = strategy["pine_code"]
        score = strategy["analysis"]["total_score"]

        print(f"[{i}/{len(to_convert)}] {title} (점수: {score:.1f}) 변환 중...")

        try:
            output_path = await generator.generate(
                pine_code=pine_code,
                strategy_name=title,
                meta=strategy
            )

            print(f"  ✓ 변환 완료: {output_path}")
            converted.append({
                "title": title,
                "score": score,
                "output_path": str(output_path)
            })

        except Exception as e:
            print(f"  ✗ 변환 실패: {e}")

    # 결과 요약
    print("\n" + "=" * 60)
    print("변환 완료")
    print("=" * 60)
    print(f"성공: {len(converted)}/{len(to_convert)}개")
    print(f"출력 디렉토리: {output_dir}")

    if converted:
        print("\n변환된 전략:")
        for c in converted:
            print(f"  - {c['title']} ({c['score']:.1f}점)")


if __name__ == "__main__":
    asyncio.run(main())
