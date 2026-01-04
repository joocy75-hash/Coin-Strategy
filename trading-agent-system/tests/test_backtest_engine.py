"""
Backtest Engine Tests

백테스트 엔진 단위 테스트
"""

import numpy as np
import pandas as pd
import pytest
from pathlib import Path
import tempfile

from backtesting import Strategy

from src.backtest import BacktestEngine, BacktestMetrics


@pytest.fixture
def sample_ohlcv_data():
    """테스트용 OHLCV 데이터 생성"""
    np.random.seed(42)
    n = 500  # 충분한 데이터 포인트

    dates = pd.date_range(start="2023-01-01", periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_price = low + np.random.rand(n) * (high - low)
    volume = np.abs(np.random.randn(n) * 1000000 + 5000000)

    df = pd.DataFrame({
        "Open": open_price,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    }, index=dates)

    return df


class SimpleSMAStrategy(Strategy):
    """테스트용 단순 SMA 크로스오버 전략"""

    n1 = 10  # 빠른 SMA 기간
    n2 = 20  # 느린 SMA 기간

    def init(self):
        close = self.data.Close
        self.sma1 = self.I(lambda x: pd.Series(x).rolling(self.n1).mean(), close)
        self.sma2 = self.I(lambda x: pd.Series(x).rolling(self.n2).mean(), close)

    def next(self):
        if self.sma1[-1] > self.sma2[-1]:
            if not self.position:
                self.buy()
        elif self.sma1[-1] < self.sma2[-1]:
            if self.position:
                self.position.close()


class TestBacktestEngine:
    """BacktestEngine 테스트"""

    def test_engine_initialization(self):
        """엔진 초기화 테스트"""
        engine = BacktestEngine(
            initial_cash=100_000,
            commission=0.001,
            exclusive_orders=True,
        )

        assert engine.initial_cash == 100_000
        assert engine.commission == 0.001
        assert engine.exclusive_orders is True

    def test_run_with_strategy_class(self, sample_ohlcv_data):
        """전략 클래스로 백테스트 실행"""
        engine = BacktestEngine()
        metrics = engine.run(
            strategy_class=SimpleSMAStrategy,
            data=sample_ohlcv_data,
            symbol="TEST",
            interval="1h",
        )

        assert isinstance(metrics, BacktestMetrics)
        assert metrics.strategy_name == "SimpleSMAStrategy"
        assert metrics.symbol == "TEST"
        assert metrics.interval == "1h"

    def test_metrics_values(self, sample_ohlcv_data):
        """메트릭 값 검증"""
        engine = BacktestEngine()
        metrics = engine.run(
            strategy_class=SimpleSMAStrategy,
            data=sample_ohlcv_data,
        )

        # 기본 메트릭 존재 확인
        assert hasattr(metrics, "total_return")
        assert hasattr(metrics, "sharpe_ratio")
        assert hasattr(metrics, "max_drawdown")
        assert hasattr(metrics, "win_rate")
        assert hasattr(metrics, "total_trades")

        # 값 범위 검증
        assert metrics.max_drawdown >= 0
        assert 0 <= metrics.win_rate <= 100

    def test_run_from_file(self, sample_ohlcv_data, tmp_path):
        """파일에서 전략 로드 후 백테스트"""
        strategy_code = '''
from backtesting import Strategy
import pandas as pd

class TestFileStrategy(Strategy):
    n = 15

    def init(self):
        close = self.data.Close
        self.sma = self.I(lambda x: pd.Series(x).rolling(self.n).mean(), close)

    def next(self):
        if self.data.Close[-1] > self.sma[-1]:
            if not self.position:
                self.buy()
        else:
            if self.position:
                self.position.close()
'''
        strategy_file = tmp_path / "test_strategy.py"
        strategy_file.write_text(strategy_code)

        engine = BacktestEngine()
        metrics = engine.run_from_file(
            strategy_file=str(strategy_file),
            data=sample_ohlcv_data,
            symbol="BTCUSDT",
        )

        assert isinstance(metrics, BacktestMetrics)
        assert metrics.strategy_name == "TestFileStrategy"

    def test_run_from_code(self, sample_ohlcv_data):
        """코드 문자열에서 전략 로드 후 백테스트"""
        strategy_code = '''
from backtesting import Strategy
import pandas as pd

class DynamicStrategy(Strategy):
    def init(self):
        close = self.data.Close
        self.ema = self.I(
            lambda x: pd.Series(x).ewm(span=12, adjust=False).mean(),
            close
        )

    def next(self):
        if self.data.Close[-1] > self.ema[-1]:
            if not self.position:
                self.buy()
        else:
            if self.position:
                self.position.close()
'''
        engine = BacktestEngine()
        metrics = engine.run_from_code(
            strategy_code=strategy_code,
            data=sample_ohlcv_data,
            symbol="ETHUSDT",
        )

        assert isinstance(metrics, BacktestMetrics)
        assert metrics.strategy_name == "DynamicStrategy"
        assert metrics.symbol == "ETHUSDT"

    def test_save_and_load_results(self, sample_ohlcv_data, tmp_path):
        """결과 저장 및 로드 테스트"""
        engine = BacktestEngine(results_dir=str(tmp_path))
        metrics = engine.run(
            strategy_class=SimpleSMAStrategy,
            data=sample_ohlcv_data,
        )

        # 저장
        file_path = engine.save_results(metrics, prefix="test")
        assert Path(file_path).exists()

        # 로드
        loaded_metrics = engine.load_results(file_path)
        assert loaded_metrics.strategy_name == metrics.strategy_name
        assert loaded_metrics.total_return == metrics.total_return

    def test_aggregate_results(self, sample_ohlcv_data):
        """여러 결과 집계 테스트"""
        engine = BacktestEngine()

        # 여러 백테스트 실행
        metrics_list = []
        for _ in range(3):
            metrics = engine.run(
                strategy_class=SimpleSMAStrategy,
                data=sample_ohlcv_data,
            )
            metrics_list.append(metrics)

        # 집계
        aggregated = engine.aggregate_results(metrics_list)

        assert aggregated["total_tests"] == 3
        assert "avg_return" in aggregated
        assert "avg_sharpe" in aggregated
        assert "consistency_rate" in aggregated


class TestBacktestMetrics:
    """BacktestMetrics 테스트"""

    def test_metrics_dataclass(self):
        """메트릭 데이터클래스 테스트"""
        metrics = BacktestMetrics(
            strategy_name="TestStrategy",
            symbol="BTCUSDT",
            interval="1h",
            start_date="2023-01-01",
            end_date="2023-12-31",
            total_return=25.5,
            sharpe_ratio=1.8,
            sortino_ratio=2.1,
            max_drawdown=15.3,
            win_rate=55.0,
            profit_factor=1.7,
            total_trades=150,
            avg_trade_return=0.17,
            exposure_time=60.0,
            buy_hold_return=30.0,
            equity_final=125500.0,
            equity_peak=130000.0,
        )

        assert metrics.strategy_name == "TestStrategy"
        assert metrics.total_return == 25.5
        assert metrics.sharpe_ratio == 1.8


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_missing_columns(self):
        """필수 컬럼 누락 시 에러"""
        engine = BacktestEngine()
        incomplete_df = pd.DataFrame({
            "Open": [100],
            "Close": [101],
        })

        with pytest.raises(ValueError, match="Missing required column"):
            engine.run(
                strategy_class=SimpleSMAStrategy,
                data=incomplete_df,
            )

    def test_file_not_found(self, sample_ohlcv_data):
        """존재하지 않는 파일"""
        engine = BacktestEngine()

        with pytest.raises(FileNotFoundError):
            engine.run_from_file(
                strategy_file="/nonexistent/path/strategy.py",
                data=sample_ohlcv_data,
            )

    def test_invalid_strategy_code(self, sample_ohlcv_data):
        """잘못된 전략 코드"""
        engine = BacktestEngine()
        invalid_code = "this is not valid python code {"

        with pytest.raises(SyntaxError):
            engine.run_from_code(
                strategy_code=invalid_code,
                data=sample_ohlcv_data,
            )

    def test_no_strategy_class_in_code(self, sample_ohlcv_data):
        """Strategy 클래스가 없는 코드"""
        engine = BacktestEngine()
        no_strategy_code = '''
def some_function():
    pass

class NotAStrategy:
    pass
'''
        with pytest.raises(ValueError, match="No Strategy subclass found"):
            engine.run_from_code(
                strategy_code=no_strategy_code,
                data=sample_ohlcv_data,
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
