#!/usr/bin/env python3
"""
TradingView Strategy Research Lab - Main Entry Point

전체 파이프라인 실행:
1. TradingView에서 전략 수집 (Collector)
2. Pine Script 코드 가져오기 (Pine Fetcher)
3. 전략 분석 및 점수화 (Analyzer)
4. Python 코드로 변환 (Converter)
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.collector import TVScriptsScraper, PineCodeFetcher, StrategyMeta
from src.analyzer import StrategyScorer
from src.converter import StrategyGenerator
from src.storage import StrategyDatabase
from scripts.generate_report import generate_html_report


def setup_logging(debug: bool = False, logs_dir: str = "logs") -> logging.Logger:
    """로깅 설정."""
    log_level = logging.DEBUG if debug else logging.INFO

    # 로그 디렉토리 생성
    Path(logs_dir).mkdir(parents=True, exist_ok=True)

    # 로그 파일명 (날짜 포함)
    log_filename = Path(logs_dir) / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # 포매터 설정
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 파일 핸들러
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # 루트 로거 설정
    logger = logging.getLogger("strategy_lab")
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


async def run_collector(
    config: Config,
    max_strategies: int,
    min_likes: int,
    sort_by: str,
    logger: logging.Logger
) -> List[StrategyMeta]:
    """1단계: TradingView에서 전략 메타데이터 수집."""
    logger.info("=" * 60)
    logger.info("1단계: 전략 수집 시작")
    logger.info("=" * 60)

    async with TVScriptsScraper(headless=config.headless) as scraper:
        strategies = await scraper.scrape_strategies(
            max_count=max_strategies,
            min_likes=min_likes,
            sort_by="popularity" if sort_by == "popular" else sort_by
        )
        logger.info(f"수집 완료: {len(strategies)}개 전략")
        return strategies


async def run_pine_fetcher(
    strategies: List[StrategyMeta],
    config: Config,
    logger: logging.Logger
) -> List[dict]:
    """2단계: Pine Script 소스 코드 가져오기."""
    logger.info("=" * 60)
    logger.info("2단계: Pine Script 코드 수집 시작")
    logger.info("=" * 60)

    fetcher = PineCodeFetcher(headless=config.headless)

    results = []
    for i, strategy in enumerate(strategies, 1):
        logger.info(f"[{i}/{len(strategies)}] {strategy.title} 코드 가져오기...")

        pine_data = await fetcher.fetch_pine_code(strategy.script_url)

        if pine_data and pine_data.pine_code:
            results.append({
                "meta": strategy,
                "pine_code": pine_data.pine_code,
                "version": pine_data.pine_version
            })
            logger.info(f"  ✓ 코드 수집 성공 (v{pine_data.pine_version})")
        else:
            logger.warning(f"  ✗ 코드 수집 실패")

        # Rate limiting
        await asyncio.sleep(config.rate_limit_delay)

    logger.info(f"코드 수집 완료: {len(results)}/{len(strategies)}개")
    return results


async def run_analyzer(
    strategies_with_code: List[dict],
    config: Config,
    analyze_limit: Optional[int],
    skip_llm: bool,
    logger: logging.Logger,
    db: StrategyDatabase
) -> List[dict]:
    """3단계: 전략 분석 및 점수화."""
    logger.info("=" * 60)
    logger.info("3단계: 전략 분석 시작")
    logger.info("=" * 60)

    scorer = StrategyScorer(
        llm_api_key=config.openai_api_key,
        llm_model=config.llm_model
    )

    # 분석할 전략 수 제한
    to_analyze = strategies_with_code[:analyze_limit] if analyze_limit else strategies_with_code

    results = []
    for i, item in enumerate(to_analyze, 1):
        meta = item["meta"]
        pine_code = item["pine_code"]

        logger.info(f"[{i}/{len(to_analyze)}] {meta.title} 분석 중...")

        try:
            # 전략 점수 계산
            score = await scorer.score_strategy(
                pine_code=pine_code,
                skip_llm=skip_llm
            )

            logger.info(f"  총점: {score.total_score:.1f}/100")
            logger.info(f"  등급: {score.grade} / 상태: {score.status}")
            logger.info(f"  리페인팅: {score.repainting_score:.1f} / 오버피팅: {score.overfitting_score:.1f}")

            # 데이터베이스에 저장
            await db.save_strategy(
                meta=meta,
                pine_code=pine_code,
                analysis=score
            )

            results.append({
                **item,
                "score": score
            })
        except Exception as e:
            logger.error(f"  분석 실패: {e}")

    logger.info(f"분석 완료: {len(results)}개 전략")
    return results


async def run_converter(
    analyzed_strategies: List[dict],
    config: Config,
    convert_limit: Optional[int],
    logger: logging.Logger,
    db: StrategyDatabase
) -> int:
    """4단계: Python 코드로 변환."""
    logger.info("=" * 60)
    logger.info("4단계: Python 변환 시작")
    logger.info("=" * 60)

    generator = StrategyGenerator()
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 변환할 전략 선택 (점수 높은 순)
    sorted_strategies = sorted(
        analyzed_strategies,
        key=lambda x: x["score"].total_score,
        reverse=True
    )

    to_convert = sorted_strategies[:convert_limit] if convert_limit else sorted_strategies

    converted_count = 0
    for i, item in enumerate(to_convert, 1):
        meta = item["meta"]
        pine_code = item["pine_code"]
        score = item["score"]

        # 점수가 낮은 전략은 스킵
        if score.total_score < 50:
            logger.info(f"[{i}] {meta.title} - 점수 부족 ({score.total_score:.1f}), 스킵")
            continue

        logger.info(f"[{i}/{len(to_convert)}] {meta.title} 변환 중...")

        try:
            # 분석 결과를 딕셔너리로 변환
            analysis_dict = {
                "total_score": score.total_score,
                "grade": score.grade,
                "status": score.status,
                "repainting_analysis": score.repainting_analysis,
                "overfitting_analysis": score.overfitting_analysis,
            }

            result = generator.generate_strategy(
                strategy_code=meta.script_id,
                strategy_name=meta.title,
                strategy_type="basic",
                pine_code=pine_code,
                analysis_result=analysis_dict
            )

            # 파일 저장
            filename = f"{meta.script_id}_strategy.py"
            output_path = output_dir / filename
            output_path.write_text(result["strategy_file"], encoding="utf-8")

            logger.info(f"  ✓ 변환 완료: {output_path}")

            # 데이터베이스 업데이트
            await db.update_converted_path(
                script_id=meta.script_id,
                converted_path=str(output_path)
            )

            converted_count += 1
        except Exception as e:
            logger.error(f"  변환 실패: {e}")

    logger.info(f"변환 완료: {converted_count}개 전략")
    return converted_count


async def main():
    """메인 파이프라인 실행."""
    parser = argparse.ArgumentParser(
        description="TradingView Strategy Research Lab",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 실행 (전체 파이프라인)
  python main.py

  # 최대 50개 전략, 좋아요 1000개 이상
  python main.py --max-strategies 50 --min-likes 1000

  # LLM 분석 스킵 (빠른 실행)
  python main.py --skip-llm

  # 디버그 모드
  python main.py --debug
        """
    )

    # 수집 옵션
    parser.add_argument(
        "--max-strategies", "-m",
        type=int,
        default=100,
        help="최대 수집 전략 수 (기본: 100)"
    )
    parser.add_argument(
        "--min-likes", "-l",
        type=int,
        default=500,
        help="최소 좋아요 수 (기본: 500)"
    )
    parser.add_argument(
        "--sort-by", "-s",
        choices=["popular", "recent", "trending"],
        default="popular",
        help="정렬 기준 (기본: popular)"
    )

    # 분석 옵션
    parser.add_argument(
        "--analyze-limit", "-a",
        type=int,
        default=None,
        help="분석할 전략 수 제한"
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="LLM 딥 분석 스킵"
    )

    # 변환 옵션
    parser.add_argument(
        "--convert-limit", "-c",
        type=int,
        default=None,
        help="변환할 전략 수 제한"
    )

    # 일반 옵션
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="디버그 모드 활성화"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="브라우저 UI 표시 (디버깅용)"
    )

    args = parser.parse_args()

    # 설정 로드
    config = Config.load()
    config.headless = not args.no_headless
    config.skip_llm = args.skip_llm
    config.ensure_directories()

    # 로깅 설정
    logger = setup_logging(debug=args.debug, logs_dir=config.logs_dir)

    logger.info("=" * 60)
    logger.info("TradingView Strategy Research Lab 시작")
    logger.info("=" * 60)
    logger.info(f"설정:")
    logger.info(f"  - 최대 전략 수: {args.max_strategies}")
    logger.info(f"  - 최소 좋아요: {args.min_likes}")
    logger.info(f"  - 정렬: {args.sort_by}")
    logger.info(f"  - LLM 스킵: {args.skip_llm}")
    logger.info(f"  - 디버그: {args.debug}")

    # 데이터베이스 초기화
    db = StrategyDatabase(config.db_path)
    await db.init_db()

    try:
        # 1단계: 전략 수집
        strategies = await run_collector(
            config=config,
            max_strategies=args.max_strategies,
            min_likes=args.min_likes,
            sort_by=args.sort_by,
            logger=logger
        )

        if not strategies:
            logger.warning("수집된 전략이 없습니다.")
            return

        # 2단계: Pine Script 코드 가져오기
        strategies_with_code = await run_pine_fetcher(
            strategies=strategies,
            config=config,
            logger=logger
        )

        if not strategies_with_code:
            logger.warning("코드를 가져온 전략이 없습니다.")
            return

        # 3단계: 분석
        analyzed = await run_analyzer(
            strategies_with_code=strategies_with_code,
            config=config,
            analyze_limit=args.analyze_limit,
            skip_llm=args.skip_llm,
            logger=logger,
            db=db
        )

        if not analyzed:
            logger.warning("분석된 전략이 없습니다.")
            return

        # 4단계: 변환
        converted = await run_converter(
            analyzed_strategies=analyzed,
            config=config,
            convert_limit=args.convert_limit,
            logger=logger,
            db=db
        )

        # 결과 요약
        logger.info("=" * 60)
        logger.info("파이프라인 완료")
        logger.info("=" * 60)
        logger.info(f"수집: {len(strategies)}개")
        logger.info(f"코드 가져오기: {len(strategies_with_code)}개")
        logger.info(f"분석: {len(analyzed)}개")
        logger.info(f"변환: {converted}개")

        # 데이터베이스 통계
        stats = await db.get_stats()
        logger.info(f"\n데이터베이스 통계:")
        logger.info(f"  - 총 전략: {stats.total_strategies}")
        logger.info(f"  - 분석 완료: {stats.analyzed_count}")
        logger.info(f"  - 통과: {stats.passed_count} / 검토: {stats.review_count} / 거부: {stats.rejected_count}")

        # HTML 리포트 생성
        logger.info("=" * 60)
        logger.info("HTML 리포트 생성 시작")
        logger.info("=" * 60)
        try:
            report_path = await generate_html_report(
                db_path=config.db_path,
                output_path="data/report.html"
            )
            logger.info(f"HTML 리포트 생성 완료: {report_path}")
            logger.info(f"브라우저에서 열기: open {report_path}")
        except Exception as e:
            logger.error(f"HTML 리포트 생성 실패: {e}")

    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단됨")
    except Exception as e:
        logger.exception(f"파이프라인 오류: {e}")
        raise
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
