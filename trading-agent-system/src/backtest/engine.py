"""
Backtest Engine

backtesting.py 래퍼 - 전략 실행 및 결과 수집
임시 파일 기반 동적 전략 로딩 지원
"""

import json
import importlib.util
import tempfile
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from backtesting import Backtest


@dataclass
class BacktestMetrics:
    """백테스트 결과 메트릭"""
    strategy_name: str
    symbol: str
    interval: str
    start_date: str
    end_date: str
    total_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_return: float
    exposure_time: float
    buy_hold_return: float
    equity_final: float
    equity_peak: float


class BacktestEngine:
    """백테스트 실행 엔진"""

    def __init__(
        self,
        initial_cash: float = 100_000,
        commission: float = 0.001,
        exclusive_orders: bool = True,
        results_dir: str = "results"
    ):
        """
        Args:
            initial_cash: 초기 자본금
            commission: 수수료 비율 (0.001 = 0.1%)
            exclusive_orders: 동시 주문 비허용
            results_dir: 결과 저장 디렉토리
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.exclusive_orders = exclusive_orders
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        strategy_class: type,
        data: pd.DataFrame,
        symbol: str = "UNKNOWN",
        interval: str = "1h",
        optimize: bool = False,
        **optimize_params
    ) -> BacktestMetrics:
        """
        백테스트 실행

        Args:
            strategy_class: backtesting.py Strategy 클래스
            data: OHLCV DataFrame (columns: Open, High, Low, Close, Volume)
            symbol: 심볼명
            interval: 타임프레임
            optimize: 최적화 실행 여부
            **optimize_params: 최적화 파라미터

        Returns:
            BacktestMetrics
        """
        # 데이터 검증
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        for col in required_columns:
            if col not in data.columns:
                raise ValueError(f"Missing required column: {col}")

        # Backtest 인스턴스 생성
        bt = Backtest(
            data,
            strategy_class,
            cash=self.initial_cash,
            commission=self.commission,
            exclusive_orders=self.exclusive_orders
        )

        # 실행
        if optimize and optimize_params:
            stats = bt.optimize(**optimize_params)
        else:
            stats = bt.run()

        # 메트릭 추출
        metrics = self._extract_metrics(
            stats=stats,
            strategy_name=strategy_class.__name__,
            symbol=symbol,
            interval=interval,
            data=data
        )

        return metrics

    def run_from_file(
        self,
        strategy_file: str,
        data: pd.DataFrame,
        symbol: str = "UNKNOWN",
        interval: str = "1h",
        strategy_class_name: str | None = None
    ) -> BacktestMetrics:
        """
        파일에서 전략 로드 후 백테스트 실행

        Args:
            strategy_file: 전략 파일 경로 (.py)
            data: OHLCV DataFrame
            symbol: 심볼명
            interval: 타임프레임
            strategy_class_name: Strategy 클래스 이름 (None이면 자동 탐지)

        Returns:
            BacktestMetrics
        """
        strategy_path = Path(strategy_file)
        if not strategy_path.exists():
            raise FileNotFoundError(f"Strategy file not found: {strategy_file}")

        # 모듈 로드
        spec = importlib.util.spec_from_file_location(
            f"strategy_{strategy_path.stem}",
            strategy_path
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load strategy from: {strategy_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Strategy 클래스 찾기
        strategy_class = self._find_strategy_class(module, strategy_class_name)

        return self.run(
            strategy_class=strategy_class,
            data=data,
            symbol=symbol,
            interval=interval
        )

    def run_from_code(
        self,
        strategy_code: str,
        data: pd.DataFrame,
        symbol: str = "UNKNOWN",
        interval: str = "1h",
        strategy_class_name: str | None = None
    ) -> BacktestMetrics:
        """
        코드 문자열에서 전략 로드 후 백테스트 실행
        임시 파일을 생성하여 안전하게 모듈 로드

        Args:
            strategy_code: Python 전략 코드 문자열
            data: OHLCV DataFrame
            symbol: 심볼명
            interval: 타임프레임
            strategy_class_name: Strategy 클래스 이름 (None이면 자동 탐지)

        Returns:
            BacktestMetrics
        """
        # 임시 파일에 코드 저장
        temp_dir = Path(tempfile.gettempdir())
        temp_file = temp_dir / f"strategy_{uuid.uuid4().hex}.py"

        try:
            # 코드를 임시 파일로 저장
            temp_file.write_text(strategy_code, encoding="utf-8")

            # 파일 기반 로드 사용
            return self.run_from_file(
                strategy_file=str(temp_file),
                data=data,
                symbol=symbol,
                interval=interval,
                strategy_class_name=strategy_class_name
            )
        finally:
            # 임시 파일 정리
            if temp_file.exists():
                temp_file.unlink()

    def _find_strategy_class(
        self,
        module: Any,
        class_name: str | None = None
    ) -> type:
        """모듈에서 Strategy 클래스 찾기"""
        from backtesting import Strategy

        if class_name:
            # 명시된 클래스 찾기
            if hasattr(module, class_name):
                cls = getattr(module, class_name)
                if isinstance(cls, type) and issubclass(cls, Strategy):
                    return cls
            raise ValueError(f"Strategy class not found: {class_name}")

        # 자동 탐지: Strategy 서브클래스 찾기
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and
                issubclass(obj, Strategy) and
                obj is not Strategy):
                return obj

        raise ValueError("No Strategy subclass found in module")

    def _extract_metrics(
        self,
        stats: pd.Series,
        strategy_name: str,
        symbol: str,
        interval: str,
        data: pd.DataFrame
    ) -> BacktestMetrics:
        """백테스트 결과에서 메트릭 추출"""

        # 안전하게 값 추출 (없으면 0 또는 기본값)
        def safe_get(key: str, default: float = 0.0) -> float:
            value = stats.get(key, default)
            if pd.isna(value):
                return default
            return float(value)

        return BacktestMetrics(
            strategy_name=strategy_name,
            symbol=symbol,
            interval=interval,
            start_date=str(data.index.min()),
            end_date=str(data.index.max()),
            total_return=safe_get("Return [%]"),
            sharpe_ratio=safe_get("Sharpe Ratio"),
            sortino_ratio=safe_get("Sortino Ratio"),
            max_drawdown=abs(safe_get("Max. Drawdown [%]")),
            win_rate=safe_get("Win Rate [%]"),
            profit_factor=safe_get("Profit Factor", 1.0),
            total_trades=int(safe_get("# Trades")),
            avg_trade_return=safe_get("Avg. Trade [%]"),
            exposure_time=safe_get("Exposure Time [%]"),
            buy_hold_return=safe_get("Buy & Hold Return [%]"),
            equity_final=safe_get("Equity Final [$]", self.initial_cash),
            equity_peak=safe_get("Equity Peak [$]", self.initial_cash),
        )

    def save_results(
        self,
        metrics: BacktestMetrics,
        prefix: str = ""
    ) -> str:
        """결과를 JSON 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{metrics.strategy_name}_{metrics.symbol}_{timestamp}.json"
        file_path = self.results_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(metrics), f, indent=2, ensure_ascii=False)

        return str(file_path)

    def load_results(self, file_path: str) -> BacktestMetrics:
        """저장된 결과 로드"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return BacktestMetrics(**data)

    def aggregate_results(
        self,
        metrics_list: list[BacktestMetrics]
    ) -> dict[str, Any]:
        """여러 백테스트 결과 집계"""
        if not metrics_list:
            return {}

        import numpy as np

        returns = [m.total_return for m in metrics_list]
        sharpes = [m.sharpe_ratio for m in metrics_list]
        drawdowns = [m.max_drawdown for m in metrics_list]
        win_rates = [m.win_rate for m in metrics_list]

        return {
            "total_tests": len(metrics_list),
            "avg_return": float(np.mean(returns)),
            "std_return": float(np.std(returns)),
            "avg_sharpe": float(np.mean(sharpes)),
            "avg_max_drawdown": float(np.mean(drawdowns)),
            "avg_win_rate": float(np.mean(win_rates)),
            "positive_returns": sum(1 for r in returns if r > 0),
            "consistency_rate": sum(1 for r in returns if r > 0) / len(returns) * 100,
            "best_return": float(max(returns)),
            "worst_return": float(min(returns)),
        }
