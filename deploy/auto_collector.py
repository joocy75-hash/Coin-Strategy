#!/usr/bin/env python3
"""
자동 전략 수집 및 검증 스크립트
cron 또는 systemd timer로 주기적으로 실행됩니다.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import Config
from src.collector.scripts_scraper import TVScriptsScraper
from src.collector.pine_fetcher import PineCodeFetcher
from src.analyzer.scorer import StrategyScorer
from src.storage.database import StrategyDatabase
from src.converter.strategy_generator import StrategyGenerator
from src.converter.pine_to_python import PineScriptConverter
from scripts.generate_beginner_report import generate_beginner_report

# 로깅 설정
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"auto_collect_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutoCollector:
    """자동화된 전략 수집 및 검증 시스템"""

    def __init__(self, config: Config):
        self.config = config
        self.db = StrategyDatabase(config.db_path)
        self.scorer = StrategyScorer(
            llm_api_key=config.anthropic_api_key,
            llm_model=config.llm_model
        )
        # 템플릿 디렉토리 경로 설정
        templates_dir = PROJECT_ROOT / "src" / "converter" / "templates"
        self.generator = StrategyGenerator(str(templates_dir) if templates_dir.exists() else None)
        self.converter = PineScriptConverter()
        self.output_dir = PROJECT_ROOT / "data" / "converted"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def run_collection_cycle(
        self,
        max_strategies: int = 20,
        min_likes: int = 500,
        sort_by: str = "popular"
    ):
        """하나의 수집 사이클 실행"""
        cycle_start = datetime.now()
        logger.info(f"=== 수집 사이클 시작: {cycle_start} ===")

        stats = {
            "collected": 0,
            "fetched": 0,
            "analyzed": 0,
            "converted": 0,
            "errors": []
        }

        try:
            # 1. 데이터베이스 초기화
            await self.db.init_db()

            # 2. 전략 메타데이터 수집
            logger.info(f"전략 수집 시작 (max: {max_strategies}, min_likes: {min_likes})")
            strategies = []

            async with TVScriptsScraper(headless=True) as scraper:
                strategies = await scraper.scrape_strategies(
                    max_count=max_strategies,
                    min_likes=min_likes,
                    sort_by="popularity" if sort_by == "popular" else sort_by
                )

            stats["collected"] = len(strategies)
            logger.info(f"수집 완료: {len(strategies)}개 전략")

            if not strategies:
                logger.warning("수집된 전략이 없습니다.")
                return stats

            # 3. Pine 코드 추출
            logger.info("Pine Script 코드 추출 시작")
            fetcher = PineCodeFetcher(headless=True)
            pine_data_list = []

            for strategy in strategies:
                try:
                    # strategy.script_url을 전달 (URL 문자열)
                    pine_data = await fetcher.fetch_pine_code(strategy.script_url)
                    if pine_data and pine_data.pine_code:
                        pine_data_list.append((strategy, pine_data))
                        stats["fetched"] += 1
                        logger.info(f"코드 추출 성공: {strategy.title}")
                    await asyncio.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.error(f"코드 추출 실패 ({strategy.title}): {e}")
                    stats["errors"].append(f"fetch:{strategy.script_id}:{str(e)[:50]}")

            logger.info(f"코드 추출 완료: {stats['fetched']}개")

            # 4. 품질 분석 및 저장
            logger.info("품질 분석 시작")
            for strategy, pine_data in pine_data_list:
                try:
                    # 분석 실행
                    score_result = await self.scorer.score_strategy(
                        pine_code=pine_data.pine_code,
                        title=strategy.title,
                        description=strategy.description,
                        performance=pine_data.performance
                    )

                    # 데이터베이스 저장
                    await self.db.save_strategy(
                        meta=strategy,
                        pine_code=pine_data.pine_code,
                        analysis=score_result
                    )
                    stats["analyzed"] += 1

                    # 고득점 전략 Python 변환 (점수 >= 50)
                    if score_result.total_score >= 50:
                        try:
                            # Pine Script를 Python으로 변환
                            conversion_result = self.converter.convert(pine_data.pine_code)

                            # 생성기로 전략 파일 생성
                            strategy_code = strategy.script_id.replace("-", "_")
                            files = self.generator.generate_strategy(
                                strategy_code=strategy_code,
                                strategy_name=strategy.title,
                                strategy_type="basic",
                                pine_code=pine_data.pine_code,
                                analysis_result={
                                    "total_score": score_result.total_score,
                                    "grade": score_result.grade,
                                    "repainting_risk": score_result.repainting_analysis.get("risk_level", "unknown")
                                },
                                llm_converted_code=conversion_result.python_code if conversion_result else None
                            )

                            # 파일 저장
                            output_path = self.output_dir / f"{strategy_code}_strategy.py"
                            if "strategy_file" in files:
                                output_path.write_text(files["strategy_file"])
                                await self.db.update_converted_path(
                                    strategy.script_id,
                                    str(output_path)
                                )
                                stats["converted"] += 1
                                logger.info(f"전략 변환 완료: {output_path}")
                        except Exception as e:
                            logger.error(f"변환 실패 ({strategy.title}): {e}")

                except Exception as e:
                    logger.error(f"분석 실패 ({strategy.title}): {e}")
                    stats["errors"].append(f"analyze:{strategy.script_id}:{str(e)[:50]}")

            logger.info(f"분석 완료: {stats['analyzed']}개, 변환: {stats['converted']}개")

            # 5. HTML 리포트 자동 생성
            logger.info("HTML 리포트 생성 시작")
            try:
                report_path = await generate_beginner_report(
                    db_path=str(PROJECT_ROOT / "data" / "strategies.db"),
                    output_path=str(PROJECT_ROOT / "data" / "beginner_report.html")
                )
                logger.info(f"HTML 리포트 생성 완료: {report_path}")
            except Exception as e:
                logger.error(f"HTML 리포트 생성 실패: {e}")
                stats["errors"].append(f"report:{str(e)[:50]}")

        except Exception as e:
            logger.error(f"수집 사이클 오류: {e}")
            stats["errors"].append(f"cycle:{str(e)[:100]}")

        finally:
            cycle_end = datetime.now()
            duration = (cycle_end - cycle_start).total_seconds()
            logger.info(f"=== 수집 사이클 종료: {cycle_end} (소요: {duration:.1f}초) ===")
            logger.info(f"결과: 수집={stats['collected']}, 추출={stats['fetched']}, "
                       f"분석={stats['analyzed']}, 변환={stats['converted']}, "
                       f"오류={len(stats['errors'])}")

        return stats


async def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="자동 전략 수집기")
    parser.add_argument("--max-strategies", "-m", type=int, default=20,
                       help="수집할 최대 전략 수 (기본: 20)")
    parser.add_argument("--min-likes", "-l", type=int, default=500,
                       help="최소 좋아요 수 (기본: 500)")
    parser.add_argument("--sort-by", "-s", choices=["popular", "recent", "trending"],
                       default="popular", help="정렬 기준 (기본: popular)")
    parser.add_argument("--continuous", "-c", action="store_true",
                       help="연속 실행 모드 (6시간마다)")

    args = parser.parse_args()

    config = Config()
    collector = AutoCollector(config)

    if args.continuous:
        # 연속 실행 모드
        while True:
            try:
                await collector.run_collection_cycle(
                    max_strategies=args.max_strategies,
                    min_likes=args.min_likes,
                    sort_by=args.sort_by
                )
            except Exception as e:
                logger.error(f"사이클 실행 오류: {e}")

            # 6시간 대기
            logger.info("다음 수집까지 6시간 대기...")
            await asyncio.sleep(6 * 60 * 60)
    else:
        # 단일 실행
        await collector.run_collection_cycle(
            max_strategies=args.max_strategies,
            min_likes=args.min_likes,
            sort_by=args.sort_by
        )


if __name__ == "__main__":
    asyncio.run(main())
