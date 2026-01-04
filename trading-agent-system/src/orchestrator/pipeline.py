"""
Trading Pipeline Orchestrator

strategy-research-lab과 trading-agent-system을 통합하여
전체 워크플로우를 자동화하는 파이프라인 오케스트레이터
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

# strategy-research-lab imports
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "strategy-research-lab" / "src"))

from collector import TVScriptsScraper, PineCodeFetcher, StrategyMeta, PineCodeData
from analyzer import (
    RepaintingDetector,
    OverfittingDetector,
    RiskChecker,
    LLMDeepAnalyzer,
    StrategyScorer,
    FinalScore,
)
from converter import PineScriptConverter, StrategyGenerator

# trading-agent-system imports
from agents import (
    StrategyArchitectAgent,
    VariationGeneratorAgent,
    BacktestRunnerAgent,
    ResultAnalyzerAgent,
)
from backtest import BacktestEngine, BacktestMetrics


logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """파이프라인 단계"""
    COLLECT = "collect"          # 전략 수집
    ANALYZE = "analyze"          # 품질 분석
    CONVERT = "convert"          # Pine→Python 변환
    OPTIMIZE = "optimize"        # AI 최적화/변형
    BACKTEST = "backtest"        # 백테스트 실행
    REPORT = "report"            # 결과 리포트 생성


@dataclass
class PipelineConfig:
    """파이프라인 설정"""
    # 수집 단계
    max_strategies: int = 20
    min_likes: int = 50
    min_plays: int = 100

    # 분석 단계
    skip_llm_analysis: bool = False
    min_quality_score: float = 60.0

    # 변환 단계
    converter_model: str = "gemini-2.0-flash-exp"

    # 백테스트 단계
    symbols: list[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    intervals: list[str] = field(default_factory=lambda: ["1h", "4h"])
    initial_cash: float = 100_000.0
    commission: float = 0.001

    # 최적화 단계
    variation_count: int = 3
    parallel_backtests: int = 4

    # 출력 설정
    output_dir: str = "pipeline_output"
    save_intermediate: bool = True

    # 이벤트 콜백
    on_stage_complete: Optional[Callable[[str, Any], None]] = None
    on_error: Optional[Callable[[str, Exception], None]] = None


@dataclass
class PipelineResult:
    """파이프라인 단계 결과"""
    stage: PipelineStage
    success: bool
    data: Any
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "stage": self.stage.value,
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
            "duration": self.duration,
            "timestamp": self.timestamp,
        }


class TradingPipeline:
    """트레이딩 파이프라인 오케스트레이터"""

    def __init__(self, config: PipelineConfig):
        """
        Args:
            config: 파이프라인 설정
        """
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 상태 관리
        self._is_running = False
        self._is_paused = False
        self._is_cancelled = False
        self._current_stage: Optional[PipelineStage] = None
        self._results: list[PipelineResult] = []

        # 컴포넌트 초기화
        self._init_components()

        logger.info(f"TradingPipeline initialized with output_dir: {self.output_dir}")

    def _init_components(self) -> None:
        """파이프라인 컴포넌트 초기화"""
        # strategy-research-lab 컴포넌트
        self.scraper = TVScriptsScraper()
        self.fetcher = PineCodeFetcher()
        self.repainting_detector = RepaintingDetector()
        self.overfitting_detector = OverfittingDetector()
        self.risk_checker = RiskChecker()
        self.llm_analyzer = LLMDeepAnalyzer()
        self.scorer = StrategyScorer()
        self.converter = PineScriptConverter(model_name=self.config.converter_model)
        self.strategy_generator = StrategyGenerator()

        # trading-agent-system 컴포넌트
        self.architect_agent = StrategyArchitectAgent()
        self.variation_agent = VariationGeneratorAgent()
        self.backtest_runner = BacktestRunnerAgent()
        self.result_analyzer = ResultAnalyzerAgent()
        self.backtest_engine = BacktestEngine(
            initial_cash=self.config.initial_cash,
            commission=self.config.commission,
            results_dir=str(self.output_dir / "backtest_results")
        )

    async def run_full_pipeline(self) -> list[PipelineResult]:
        """
        전체 파이프라인 실행

        Returns:
            각 단계의 PipelineResult 리스트
        """
        if self._is_running:
            raise RuntimeError("Pipeline is already running")

        self._is_running = True
        self._is_cancelled = False
        self._results = []

        try:
            logger.info("=" * 60)
            logger.info("Trading Pipeline Started")
            logger.info("=" * 60)

            # 1. 전략 수집
            collect_result = await self.run_stage(PipelineStage.COLLECT)
            if not collect_result.success or not collect_result.data:
                logger.error("Collection stage failed, aborting pipeline")
                return self._results

            # 2. 품질 분석
            analyze_result = await self.run_stage(PipelineStage.ANALYZE)
            if not analyze_result.success or not analyze_result.data:
                logger.error("Analysis stage failed, aborting pipeline")
                return self._results

            # 3. Pine → Python 변환
            convert_result = await self.run_stage(PipelineStage.CONVERT)
            if not convert_result.success or not convert_result.data:
                logger.error("Conversion stage failed, aborting pipeline")
                return self._results

            # 4. AI 최적화/변형 생성
            optimize_result = await self.run_stage(PipelineStage.OPTIMIZE)
            if not optimize_result.success or not optimize_result.data:
                logger.warning("Optimization stage failed, continuing with base strategies")

            # 5. 백테스트 실행
            backtest_result = await self.run_stage(PipelineStage.BACKTEST)
            if not backtest_result.success:
                logger.error("Backtest stage failed, aborting pipeline")
                return self._results

            # 6. 결과 리포트 생성
            report_result = await self.run_stage(PipelineStage.REPORT)

            logger.info("=" * 60)
            logger.info("Trading Pipeline Completed Successfully")
            logger.info("=" * 60)

            return self._results

        except Exception as e:
            logger.exception("Pipeline execution failed")
            if self.config.on_error:
                self.config.on_error("pipeline", e)
            raise
        finally:
            self._is_running = False
            self._current_stage = None

    async def run_stage(self, stage: PipelineStage) -> PipelineResult:
        """
        특정 단계 실행

        Args:
            stage: 실행할 파이프라인 단계

        Returns:
            PipelineResult
        """
        self._check_cancellation()
        await self._wait_if_paused()

        self._current_stage = stage
        start_time = time.time()

        logger.info(f"Starting stage: {stage.value}")

        try:
            # 단계별 실행
            if stage == PipelineStage.COLLECT:
                result = await self._collect_strategies()
            elif stage == PipelineStage.ANALYZE:
                result = await self._analyze_strategies(self._get_previous_data(PipelineStage.COLLECT))
            elif stage == PipelineStage.CONVERT:
                result = await self._convert_strategies(self._get_previous_data(PipelineStage.ANALYZE))
            elif stage == PipelineStage.OPTIMIZE:
                result = await self._optimize_strategies(self._get_previous_data(PipelineStage.CONVERT))
            elif stage == PipelineStage.BACKTEST:
                result = await self._run_backtests(self._get_previous_data(PipelineStage.OPTIMIZE))
            elif stage == PipelineStage.REPORT:
                result = await self._generate_report(self._get_previous_data(PipelineStage.BACKTEST))
            else:
                raise ValueError(f"Unknown stage: {stage}")

            # 실행 시간 기록
            result.duration = time.time() - start_time

            # 결과 저장
            self._results.append(result)

            # 중간 결과 저장
            if self.config.save_intermediate:
                self._save_stage_result(result)

            # 콜백 호출
            if self.config.on_stage_complete:
                self.config.on_stage_complete(stage.value, result.data)

            logger.info(f"Stage {stage.value} completed in {result.duration:.2f}s")

            return result

        except Exception as e:
            logger.exception(f"Stage {stage.value} failed")

            error_result = PipelineResult(
                stage=stage,
                success=False,
                data=None,
                errors=[str(e)],
                duration=time.time() - start_time
            )

            self._results.append(error_result)

            if self.config.on_error:
                self.config.on_error(stage.value, e)

            return error_result

    async def _collect_strategies(self) -> PipelineResult:
        """
        1단계: TradingView에서 전략 수집

        Returns:
            PipelineResult with list[dict] containing strategy metadata and pine code
        """
        logger.info(f"Collecting up to {self.config.max_strategies} strategies...")

        collected_strategies = []
        errors = []
        warnings = []

        try:
            # 전략 메타데이터 수집
            strategy_metas = await asyncio.to_thread(
                self.scraper.scrape_strategies,
                max_strategies=self.config.max_strategies,
                min_likes=self.config.min_likes
            )

            logger.info(f"Found {len(strategy_metas)} strategy metadata entries")

            # Pine 코드 수집
            for meta in strategy_metas:
                try:
                    pine_data = await asyncio.to_thread(
                        self.fetcher.fetch_pine_code,
                        meta.url
                    )

                    if pine_data and pine_data.code:
                        collected_strategies.append({
                            "meta": meta,
                            "pine_code": pine_data.code,
                            "url": meta.url
                        })
                    else:
                        warnings.append(f"Failed to fetch Pine code for {meta.title}")

                except Exception as e:
                    errors.append(f"Error fetching {meta.title}: {str(e)}")
                    logger.error(f"Error fetching strategy {meta.url}: {e}")

            logger.info(f"Successfully collected {len(collected_strategies)} strategies")

            return PipelineResult(
                stage=PipelineStage.COLLECT,
                success=len(collected_strategies) > 0,
                data=collected_strategies,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            logger.exception("Strategy collection failed")
            return PipelineResult(
                stage=PipelineStage.COLLECT,
                success=False,
                data=[],
                errors=[str(e)]
            )

    async def _analyze_strategies(self, strategies: list[dict]) -> PipelineResult:
        """
        2단계: 전략 품질 분석

        Args:
            strategies: _collect_strategies의 결과

        Returns:
            PipelineResult with list[dict] containing analyzed strategies
        """
        logger.info(f"Analyzing {len(strategies)} strategies...")

        analyzed_strategies = []
        errors = []
        warnings = []

        for strategy in strategies:
            try:
                pine_code = strategy["pine_code"]
                meta = strategy["meta"]

                # 1. Repainting 검사
                repainting_result = await asyncio.to_thread(
                    self.repainting_detector.detect,
                    pine_code
                )

                # 2. Overfitting 검사
                overfitting_result = await asyncio.to_thread(
                    self.overfitting_detector.detect,
                    pine_code
                )

                # 3. 리스크 검사
                risk_result = await asyncio.to_thread(
                    self.risk_checker.check,
                    pine_code
                )

                # 4. LLM 심층 분석 (옵션)
                llm_result = None
                if not self.config.skip_llm_analysis:
                    try:
                        llm_result = await asyncio.to_thread(
                            self.llm_analyzer.analyze,
                            pine_code
                        )
                    except Exception as e:
                        warnings.append(f"LLM analysis failed for {meta.title}: {str(e)}")

                # 5. 최종 스코어 계산
                final_score = await asyncio.to_thread(
                    self.scorer.calculate_final_score,
                    repainting_result,
                    overfitting_result,
                    risk_result,
                    llm_result
                )

                # 품질 스코어 필터링
                if final_score.total_score >= self.config.min_quality_score:
                    analyzed_strategies.append({
                        **strategy,
                        "analysis": {
                            "repainting": repainting_result,
                            "overfitting": overfitting_result,
                            "risk": risk_result,
                            "llm": llm_result,
                            "final_score": final_score
                        }
                    })
                    logger.info(f"✓ {meta.title}: score={final_score.total_score:.1f}")
                else:
                    warnings.append(
                        f"Strategy {meta.title} filtered out (score={final_score.total_score:.1f})"
                    )
                    logger.info(f"✗ {meta.title}: score={final_score.total_score:.1f} (filtered)")

            except Exception as e:
                errors.append(f"Analysis failed for {strategy.get('meta', {}).get('title', 'Unknown')}: {str(e)}")
                logger.error(f"Strategy analysis error: {e}")

        logger.info(f"Analysis complete: {len(analyzed_strategies)}/{len(strategies)} passed quality filter")

        return PipelineResult(
            stage=PipelineStage.ANALYZE,
            success=len(analyzed_strategies) > 0,
            data=analyzed_strategies,
            errors=errors,
            warnings=warnings
        )

    async def _convert_strategies(self, analyzed_strategies: list[dict]) -> PipelineResult:
        """
        3단계: Pine Script → Python 변환

        Args:
            analyzed_strategies: _analyze_strategies의 결과

        Returns:
            PipelineResult with list[dict] containing converted strategies
        """
        logger.info(f"Converting {len(analyzed_strategies)} strategies to Python...")

        converted_strategies = []
        errors = []
        warnings = []

        for strategy in analyzed_strategies:
            try:
                pine_code = strategy["pine_code"]
                meta = strategy["meta"]

                # Pine → Python 변환
                python_code = await asyncio.to_thread(
                    self.converter.convert,
                    pine_code,
                    strategy_name=meta.title
                )

                if python_code:
                    # Strategy 클래스 생성
                    strategy_class_code = await asyncio.to_thread(
                        self.strategy_generator.generate,
                        python_code,
                        strategy_name=meta.title
                    )

                    # 파일로 저장
                    if self.config.save_intermediate:
                        strategy_file = self.output_dir / "converted" / f"{self._sanitize_filename(meta.title)}.py"
                        strategy_file.parent.mkdir(parents=True, exist_ok=True)
                        strategy_file.write_text(strategy_class_code, encoding="utf-8")

                    converted_strategies.append({
                        **strategy,
                        "python_code": strategy_class_code,
                        "strategy_file": str(strategy_file) if self.config.save_intermediate else None
                    })

                    logger.info(f"✓ Converted: {meta.title}")
                else:
                    warnings.append(f"Conversion returned empty code for {meta.title}")
                    logger.warning(f"✗ Conversion failed: {meta.title}")

            except Exception as e:
                errors.append(f"Conversion failed for {strategy.get('meta', {}).get('title', 'Unknown')}: {str(e)}")
                logger.error(f"Conversion error: {e}")

        logger.info(f"Conversion complete: {len(converted_strategies)}/{len(analyzed_strategies)} successful")

        return PipelineResult(
            stage=PipelineStage.CONVERT,
            success=len(converted_strategies) > 0,
            data=converted_strategies,
            errors=errors,
            warnings=warnings
        )

    async def _optimize_strategies(self, converted_strategies: list[dict]) -> PipelineResult:
        """
        4단계: AI 기반 전략 최적화 및 변형 생성

        Args:
            converted_strategies: _convert_strategies의 결과

        Returns:
            PipelineResult with list[dict] containing optimized strategies
        """
        logger.info(f"Optimizing {len(converted_strategies)} strategies...")

        optimized_strategies = []
        errors = []
        warnings = []

        for strategy in converted_strategies:
            try:
                python_code = strategy["python_code"]
                meta = strategy["meta"]

                # 기본 전략 추가
                optimized_strategies.append({
                    **strategy,
                    "variation_type": "original",
                    "variation_index": 0
                })

                # 변형 생성 (옵션)
                if self.config.variation_count > 0:
                    # VariationGenerator 에이전트 사용
                    # 실제 구현은 에이전트와의 통신이 필요하므로 여기서는 placeholder
                    logger.info(f"Generating {self.config.variation_count} variations for {meta.title}")

                    for i in range(self.config.variation_count):
                        # TODO: 실제 variation generation 로직 구현
                        # variation = await self._generate_variation(python_code, i)
                        warnings.append(f"Variation generation not implemented yet for {meta.title}")
                        break

                logger.info(f"✓ Optimized: {meta.title}")

            except Exception as e:
                errors.append(f"Optimization failed for {strategy.get('meta', {}).get('title', 'Unknown')}: {str(e)}")
                logger.error(f"Optimization error: {e}")

        logger.info(f"Optimization complete: {len(optimized_strategies)} strategies ready")

        return PipelineResult(
            stage=PipelineStage.OPTIMIZE,
            success=len(optimized_strategies) > 0,
            data=optimized_strategies,
            errors=errors,
            warnings=warnings
        )

    async def _run_backtests(self, optimized_strategies: list[dict]) -> PipelineResult:
        """
        5단계: 백테스트 실행

        Args:
            optimized_strategies: _optimize_strategies의 결과

        Returns:
            PipelineResult with list[dict] containing backtest results
        """
        logger.info(f"Running backtests for {len(optimized_strategies)} strategies...")
        logger.info(f"Symbols: {self.config.symbols}, Intervals: {self.config.intervals}")

        backtest_results = []
        errors = []
        warnings = []

        # 백테스트 태스크 생성
        tasks = []
        for strategy in optimized_strategies:
            for symbol in self.config.symbols:
                for interval in self.config.intervals:
                    tasks.append((strategy, symbol, interval))

        logger.info(f"Total backtest tasks: {len(tasks)}")

        # 병렬 실행 (세마포어로 제어)
        semaphore = asyncio.Semaphore(self.config.parallel_backtests)

        async def run_single_backtest(strategy_data: dict, symbol: str, interval: str):
            async with semaphore:
                try:
                    # TODO: 실제 데이터 로드 및 백테스트 실행
                    # data = await self._load_market_data(symbol, interval)
                    # metrics = await asyncio.to_thread(
                    #     self.backtest_engine.run_from_code,
                    #     strategy_data["python_code"],
                    #     data,
                    #     symbol,
                    #     interval
                    # )

                    # Placeholder
                    warnings.append(f"Backtest data loading not implemented for {symbol}/{interval}")
                    return None

                except Exception as e:
                    errors.append(
                        f"Backtest failed for {strategy_data.get('meta', {}).get('title', 'Unknown')} "
                        f"on {symbol}/{interval}: {str(e)}"
                    )
                    logger.error(f"Backtest error: {e}")
                    return None

        # 모든 백테스트 실행
        results = await asyncio.gather(
            *[run_single_backtest(s, sym, intvl) for s, sym, intvl in tasks],
            return_exceptions=True
        )

        # 결과 수집
        for (strategy, symbol, interval), result in zip(tasks, results):
            if result and not isinstance(result, Exception):
                backtest_results.append({
                    "strategy": strategy,
                    "symbol": symbol,
                    "interval": interval,
                    "metrics": result
                })

        logger.info(f"Backtests complete: {len(backtest_results)} successful")

        return PipelineResult(
            stage=PipelineStage.BACKTEST,
            success=True,  # 부분 성공도 허용
            data=backtest_results,
            errors=errors,
            warnings=warnings
        )

    async def _generate_report(self, backtest_results: list[dict]) -> PipelineResult:
        """
        6단계: 결과 리포트 생성

        Args:
            backtest_results: _run_backtests의 결과

        Returns:
            PipelineResult with report data
        """
        logger.info("Generating final report...")

        try:
            # 리포트 데이터 생성
            report_data = {
                "summary": {
                    "total_strategies": len(set(r["strategy"]["meta"].title for r in backtest_results if r.get("metrics"))),
                    "total_backtests": len(backtest_results),
                    "symbols": self.config.symbols,
                    "intervals": self.config.intervals,
                    "timestamp": datetime.now().isoformat()
                },
                "pipeline_results": [r.to_dict() for r in self._results],
                "top_strategies": self._rank_strategies(backtest_results)
            }

            # 리포트 파일 저장
            report_file = self.output_dir / f"pipeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            import json
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"Report saved to {report_file}")

            return PipelineResult(
                stage=PipelineStage.REPORT,
                success=True,
                data={
                    "report_file": str(report_file),
                    "report_data": report_data
                }
            )

        except Exception as e:
            logger.exception("Report generation failed")
            return PipelineResult(
                stage=PipelineStage.REPORT,
                success=False,
                data=None,
                errors=[str(e)]
            )

    def _rank_strategies(self, backtest_results: list[dict]) -> list[dict]:
        """백테스트 결과를 랭킹"""
        # Metrics가 있는 결과만 필터링
        valid_results = [r for r in backtest_results if r.get("metrics")]

        # Sharpe ratio 기준 정렬
        sorted_results = sorted(
            valid_results,
            key=lambda x: x["metrics"].sharpe_ratio if hasattr(x["metrics"], "sharpe_ratio") else 0,
            reverse=True
        )

        return sorted_results[:10]  # Top 10

    def _get_previous_data(self, stage: PipelineStage) -> Any:
        """이전 단계의 결과 데이터 가져오기"""
        for result in reversed(self._results):
            if result.stage == stage and result.success:
                return result.data
        return None

    def _save_stage_result(self, result: PipelineResult) -> None:
        """단계 결과를 파일로 저장"""
        import json

        stage_dir = self.output_dir / "stages"
        stage_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{result.stage.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = stage_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False, default=str)

        logger.debug(f"Stage result saved to {filepath}")

    def _sanitize_filename(self, name: str) -> str:
        """파일명으로 사용 가능한 문자열로 변환"""
        import re
        # 영문, 숫자, 언더스코어, 하이픈만 허용
        sanitized = re.sub(r'[^\w\-]', '_', name)
        # 연속된 언더스코어를 하나로
        sanitized = re.sub(r'_+', '_', sanitized)
        return sanitized.lower()[:100]  # 최대 100자

    def _check_cancellation(self) -> None:
        """취소 요청 확인"""
        if self._is_cancelled:
            raise RuntimeError("Pipeline was cancelled")

    async def _wait_if_paused(self) -> None:
        """일시정지 상태 확인 및 대기"""
        while self._is_paused:
            await asyncio.sleep(0.1)

    # 상태 관리 메서드

    def get_status(self) -> dict[str, Any]:
        """현재 파이프라인 상태 반환"""
        return {
            "is_running": self._is_running,
            "is_paused": self._is_paused,
            "is_cancelled": self._is_cancelled,
            "current_stage": self._current_stage.value if self._current_stage else None,
            "completed_stages": [r.stage.value for r in self._results if r.success],
            "failed_stages": [r.stage.value for r in self._results if not r.success],
            "total_duration": sum(r.duration for r in self._results),
        }

    def pause(self) -> None:
        """파이프라인 일시정지"""
        if self._is_running and not self._is_paused:
            self._is_paused = True
            logger.info("Pipeline paused")

    def resume(self) -> None:
        """파이프라인 재개"""
        if self._is_paused:
            self._is_paused = False
            logger.info("Pipeline resumed")

    def cancel(self) -> None:
        """파이프라인 취소"""
        if self._is_running:
            self._is_cancelled = True
            logger.info("Pipeline cancellation requested")


# 편의 함수

async def run_pipeline(
    max_strategies: int = 20,
    min_quality_score: float = 60.0,
    symbols: list[str] = None,
    intervals: list[str] = None,
    output_dir: str = "pipeline_output"
) -> list[PipelineResult]:
    """
    파이프라인 간단 실행 함수

    Args:
        max_strategies: 수집할 최대 전략 수
        min_quality_score: 최소 품질 점수
        symbols: 백테스트할 심볼 목록
        intervals: 타임프레임 목록
        output_dir: 출력 디렉토리

    Returns:
        PipelineResult 리스트
    """
    config = PipelineConfig(
        max_strategies=max_strategies,
        min_quality_score=min_quality_score,
        symbols=symbols or ["BTCUSDT", "ETHUSDT"],
        intervals=intervals or ["1h", "4h"],
        output_dir=output_dir
    )

    pipeline = TradingPipeline(config)
    return await pipeline.run_full_pipeline()


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # 파이프라인 실행 예제
    async def main():
        results = await run_pipeline(
            max_strategies=10,
            min_quality_score=65.0,
            symbols=["BTCUSDT"],
            intervals=["1h"]
        )

        print("\n" + "=" * 60)
        print("Pipeline Execution Summary")
        print("=" * 60)

        for result in results:
            status = "✓" if result.success else "✗"
            print(f"{status} {result.stage.value}: {result.duration:.2f}s")
            if result.errors:
                for error in result.errors[:3]:
                    print(f"  Error: {error}")

        print("=" * 60)

    asyncio.run(main())
