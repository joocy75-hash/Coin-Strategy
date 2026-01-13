#!/usr/bin/env python3
"""
VectorBT 고속 백테스팅 엔진

벡터화된 연산으로 10-100배 빠른 백테스트를 수행합니다.
대량 전략 테스트 및 파라미터 최적화에 최적화되어 있습니다.

GitHub: https://github.com/polakowo/vectorbt
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import warnings

# VectorBT 임포트 시도
try:
    import vectorbt as vbt
    VECTORBT_AVAILABLE = True
except ImportError:
    VECTORBT_AVAILABLE = False
    vbt = None

# 기본 지표 라이브러리
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    talib = None


class SignalType(Enum):
    """신호 유형"""
    LONG_ENTRY = "long_entry"
    LONG_EXIT = "long_exit"
    SHORT_ENTRY = "short_entry"
    SHORT_EXIT = "short_exit"


@dataclass
class BacktestConfig:
    """백테스트 설정"""
    initial_capital: float = 10000.0
    commission: float = 0.001  # 0.1%
    slippage: float = 0.0005  # 0.05%
    size_type: str = "percent"  # "percent" or "fixed"
    size: float = 0.95  # 95% of capital
    allow_shorting: bool = False
    freq: str = "1h"  # 시간프레임


@dataclass
class BacktestResult:
    """백테스트 결과"""
    success: bool
    
    # 수익률 지표
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # 위험 지표
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    volatility: float = 0.0
    
    # 거래 지표
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_trade_return: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # 기타
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: int = 0
    
    # 에러
    error: Optional[str] = None
    
    # 상세 데이터
    equity_curve: Optional[List[float]] = None
    trades: Optional[List[Dict]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "returns": {
                "total_return": round(self.total_return, 4),
                "annual_return": round(self.annual_return, 4),
                "sharpe_ratio": round(self.sharpe_ratio, 2),
                "sortino_ratio": round(self.sortino_ratio, 2),
                "calmar_ratio": round(self.calmar_ratio, 2),
            },
            "risk": {
                "max_drawdown": round(self.max_drawdown, 4),
                "max_drawdown_duration": self.max_drawdown_duration,
                "volatility": round(self.volatility, 4),
            },
            "trades": {
                "total_trades": self.total_trades,
                "win_rate": round(self.win_rate, 4),
                "profit_factor": round(self.profit_factor, 2),
                "avg_trade_return": round(self.avg_trade_return, 4),
                "avg_win": round(self.avg_win, 4),
                "avg_loss": round(self.avg_loss, 4),
            },
            "period": {
                "start_date": self.start_date,
                "end_date": self.end_date,
                "duration_days": self.duration_days,
            },
            "error": self.error,
        }


@dataclass
class OptimizationResult:
    """파라미터 최적화 결과"""
    success: bool
    best_params: Dict[str, Any] = field(default_factory=dict)
    best_sharpe: float = 0.0
    best_return: float = 0.0
    
    # 모든 조합 결과
    all_results: List[Dict[str, Any]] = field(default_factory=list)
    total_combinations: int = 0
    
    # 시간
    elapsed_seconds: float = 0.0
    
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "best_params": self.best_params,
            "best_sharpe": round(self.best_sharpe, 2),
            "best_return": round(self.best_return, 4),
            "total_combinations": self.total_combinations,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "top_results": self.all_results[:10],
            "error": self.error,
        }


class VectorBTEngine:
    """
    VectorBT 기반 고속 백테스팅 엔진
    
    Features:
    - 벡터화된 연산으로 10-100배 빠른 백테스트
    - 대량 파라미터 최적화
    - 다양한 성과 지표 계산
    - 포트폴리오 분석
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        """
        Args:
            config: 백테스트 설정
        """
        self.config = config or BacktestConfig()
        
        if not VECTORBT_AVAILABLE:
            warnings.warn("VectorBT not installed. Install with: pip install vectorbt")
    
    def run_backtest(
        self,
        data: pd.DataFrame,
        entries: pd.Series,
        exits: pd.Series,
        short_entries: Optional[pd.Series] = None,
        short_exits: Optional[pd.Series] = None,
    ) -> BacktestResult:
        """
        백테스트 실행
        
        Args:
            data: OHLCV 데이터 (columns: open, high, low, close, volume)
            entries: 롱 진입 신호 (boolean Series)
            exits: 롱 청산 신호 (boolean Series)
            short_entries: 숏 진입 신호 (optional)
            short_exits: 숏 청산 신호 (optional)
            
        Returns:
            BacktestResult: 백테스트 결과
        """
        if not VECTORBT_AVAILABLE:
            return BacktestResult(
                success=False,
                error="VectorBT not installed"
            )
        
        try:
            close = data['close']
            
            # 포트폴리오 생성
            if self.config.allow_shorting and short_entries is not None:
                # 롱/숏 모두 지원
                pf = vbt.Portfolio.from_signals(
                    close=close,
                    entries=entries,
                    exits=exits,
                    short_entries=short_entries,
                    short_exits=short_exits,
                    init_cash=self.config.initial_capital,
                    fees=self.config.commission,
                    slippage=self.config.slippage,
                    freq=self.config.freq,
                )
            else:
                # 롱만
                pf = vbt.Portfolio.from_signals(
                    close=close,
                    entries=entries,
                    exits=exits,
                    init_cash=self.config.initial_capital,
                    fees=self.config.commission,
                    slippage=self.config.slippage,
                    freq=self.config.freq,
                )
            
            # 결과 추출
            result = self._extract_results(pf, data)
            return result
            
        except Exception as e:
            return BacktestResult(
                success=False,
                error=str(e)
            )
    
    def run_strategy(
        self,
        data: pd.DataFrame,
        strategy_func: Callable[[pd.DataFrame, Dict], Tuple[pd.Series, pd.Series]],
        params: Dict[str, Any] = None,
    ) -> BacktestResult:
        """
        전략 함수로 백테스트 실행
        
        Args:
            data: OHLCV 데이터
            strategy_func: 전략 함수 (data, params) -> (entries, exits)
            params: 전략 파라미터
            
        Returns:
            BacktestResult: 백테스트 결과
        """
        params = params or {}
        
        try:
            entries, exits = strategy_func(data, params)
            return self.run_backtest(data, entries, exits)
        except Exception as e:
            return BacktestResult(
                success=False,
                error=str(e)
            )
    
    def optimize_parameters(
        self,
        data: pd.DataFrame,
        strategy_func: Callable[[pd.DataFrame, Dict], Tuple[pd.Series, pd.Series]],
        param_ranges: Dict[str, List[Any]],
        metric: str = "sharpe_ratio",
        n_jobs: int = -1,
    ) -> OptimizationResult:
        """
        파라미터 최적화
        
        Args:
            data: OHLCV 데이터
            strategy_func: 전략 함수
            param_ranges: 파라미터 범위 {"param_name": [values]}
            metric: 최적화 기준 ("sharpe_ratio", "total_return", "calmar_ratio")
            n_jobs: 병렬 처리 수 (-1: 모든 코어)
            
        Returns:
            OptimizationResult: 최적화 결과
        """
        import itertools
        import time
        
        start_time = time.time()
        
        # 모든 파라미터 조합 생성
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        combinations = list(itertools.product(*param_values))
        
        results = []
        
        for combo in combinations:
            params = dict(zip(param_names, combo))
            
            try:
                bt_result = self.run_strategy(data, strategy_func, params)
                
                if bt_result.success:
                    metric_value = getattr(bt_result, metric, 0)
                    results.append({
                        "params": params,
                        "metric": metric_value,
                        "total_return": bt_result.total_return,
                        "sharpe_ratio": bt_result.sharpe_ratio,
                        "max_drawdown": bt_result.max_drawdown,
                        "win_rate": bt_result.win_rate,
                        "total_trades": bt_result.total_trades,
                    })
            except Exception:
                continue
        
        elapsed = time.time() - start_time
        
        if not results:
            return OptimizationResult(
                success=False,
                error="No valid results",
                elapsed_seconds=elapsed,
            )
        
        # 최적 결과 찾기
        results.sort(key=lambda x: x["metric"], reverse=True)
        best = results[0]
        
        return OptimizationResult(
            success=True,
            best_params=best["params"],
            best_sharpe=best["sharpe_ratio"],
            best_return=best["total_return"],
            all_results=results,
            total_combinations=len(combinations),
            elapsed_seconds=elapsed,
        )
    
    def _extract_results(self, pf, data: pd.DataFrame) -> BacktestResult:
        """포트폴리오에서 결과 추출"""
        try:
            stats = pf.stats()
            trades = pf.trades.records_readable if hasattr(pf, 'trades') else None
            
            # 거래 통계
            total_trades = int(stats.get('Total Trades', 0))
            win_rate = float(stats.get('Win Rate [%]', 0)) / 100 if total_trades > 0 else 0
            
            # 수익률
            total_return = float(stats.get('Total Return [%]', 0)) / 100
            
            # Sharpe Ratio
            sharpe = float(stats.get('Sharpe Ratio', 0))
            if np.isnan(sharpe) or np.isinf(sharpe):
                sharpe = 0.0
            
            # Sortino Ratio
            sortino = float(stats.get('Sortino Ratio', 0))
            if np.isnan(sortino) or np.isinf(sortino):
                sortino = 0.0
            
            # Calmar Ratio
            calmar = float(stats.get('Calmar Ratio', 0))
            if np.isnan(calmar) or np.isinf(calmar):
                calmar = 0.0
            
            # Max Drawdown
            max_dd = float(stats.get('Max Drawdown [%]', 0)) / 100
            
            # Profit Factor
            profit_factor = float(stats.get('Profit Factor', 0))
            if np.isnan(profit_factor) or np.isinf(profit_factor):
                profit_factor = 0.0
            
            # 평균 거래
            avg_trade = float(stats.get('Avg Trade [%]', 0)) / 100 if total_trades > 0 else 0
            avg_win = float(stats.get('Avg Winning Trade [%]', 0)) / 100 if total_trades > 0 else 0
            avg_loss = float(stats.get('Avg Losing Trade [%]', 0)) / 100 if total_trades > 0 else 0
            
            # 기간
            start_date = data.index[0].strftime('%Y-%m-%d') if hasattr(data.index[0], 'strftime') else str(data.index[0])
            end_date = data.index[-1].strftime('%Y-%m-%d') if hasattr(data.index[-1], 'strftime') else str(data.index[-1])
            duration = (data.index[-1] - data.index[0]).days if hasattr(data.index[-1] - data.index[0], 'days') else 0
            
            # 연간 수익률
            annual_return = total_return * (365 / max(duration, 1)) if duration > 0 else 0
            
            # 변동성
            volatility = float(stats.get('Annualized Volatility', 0))
            if np.isnan(volatility):
                volatility = 0.0
            
            return BacktestResult(
                success=True,
                total_return=total_return,
                annual_return=annual_return,
                sharpe_ratio=sharpe,
                sortino_ratio=sortino,
                calmar_ratio=calmar,
                max_drawdown=max_dd,
                volatility=volatility,
                total_trades=total_trades,
                win_rate=win_rate,
                profit_factor=profit_factor,
                avg_trade_return=avg_trade,
                avg_win=avg_win,
                avg_loss=avg_loss,
                start_date=start_date,
                end_date=end_date,
                duration_days=duration,
            )
            
        except Exception as e:
            return BacktestResult(
                success=False,
                error=str(e)
            )


# ============================================================
# 내장 전략 함수들
# ============================================================

def sma_crossover_strategy(
    data: pd.DataFrame,
    params: Dict[str, Any],
) -> Tuple[pd.Series, pd.Series]:
    """
    SMA 크로스오버 전략
    
    Args:
        data: OHLCV 데이터
        params: {"fast_period": int, "slow_period": int}
    """
    fast = params.get("fast_period", 10)
    slow = params.get("slow_period", 30)
    
    close = data['close']
    fast_sma = close.rolling(fast).mean()
    slow_sma = close.rolling(slow).mean()
    
    entries = (fast_sma > slow_sma) & (fast_sma.shift(1) <= slow_sma.shift(1))
    exits = (fast_sma < slow_sma) & (fast_sma.shift(1) >= slow_sma.shift(1))
    
    return entries, exits


def rsi_strategy(
    data: pd.DataFrame,
    params: Dict[str, Any],
) -> Tuple[pd.Series, pd.Series]:
    """
    RSI 전략
    
    Args:
        data: OHLCV 데이터
        params: {"period": int, "oversold": int, "overbought": int}
    """
    period = params.get("period", 14)
    oversold = params.get("oversold", 30)
    overbought = params.get("overbought", 70)
    
    close = data['close']
    
    # RSI 계산
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    entries = (rsi < oversold) & (rsi.shift(1) >= oversold)
    exits = (rsi > overbought) & (rsi.shift(1) <= overbought)
    
    return entries, exits


def bollinger_bands_strategy(
    data: pd.DataFrame,
    params: Dict[str, Any],
) -> Tuple[pd.Series, pd.Series]:
    """
    볼린저 밴드 전략
    
    Args:
        data: OHLCV 데이터
        params: {"period": int, "std_dev": float}
    """
    period = params.get("period", 20)
    std_dev = params.get("std_dev", 2.0)
    
    close = data['close']
    
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    
    entries = close < lower
    exits = close > upper
    
    return entries, exits


# ============================================================
# 편의 함수
# ============================================================

def quick_backtest(
    data: pd.DataFrame,
    strategy: str = "sma_crossover",
    params: Dict[str, Any] = None,
    config: BacktestConfig = None,
) -> Dict[str, Any]:
    """
    빠른 백테스트 실행
    
    Args:
        data: OHLCV 데이터
        strategy: 전략 이름 ("sma_crossover", "rsi", "bollinger")
        params: 전략 파라미터
        config: 백테스트 설정
        
    Returns:
        백테스트 결과 딕셔너리
    """
    strategies = {
        "sma_crossover": sma_crossover_strategy,
        "rsi": rsi_strategy,
        "bollinger": bollinger_bands_strategy,
    }
    
    if strategy not in strategies:
        return {"success": False, "error": f"Unknown strategy: {strategy}"}
    
    engine = VectorBTEngine(config)
    result = engine.run_strategy(data, strategies[strategy], params or {})
    return result.to_dict()


def optimize_strategy(
    data: pd.DataFrame,
    strategy: str = "sma_crossover",
    param_ranges: Dict[str, List[Any]] = None,
    config: BacktestConfig = None,
) -> Dict[str, Any]:
    """
    전략 파라미터 최적화
    
    Args:
        data: OHLCV 데이터
        strategy: 전략 이름
        param_ranges: 파라미터 범위
        config: 백테스트 설정
        
    Returns:
        최적화 결과 딕셔너리
    """
    strategies = {
        "sma_crossover": sma_crossover_strategy,
        "rsi": rsi_strategy,
        "bollinger": bollinger_bands_strategy,
    }
    
    default_ranges = {
        "sma_crossover": {"fast_period": [5, 10, 15, 20], "slow_period": [20, 30, 50, 100]},
        "rsi": {"period": [7, 14, 21], "oversold": [20, 30], "overbought": [70, 80]},
        "bollinger": {"period": [10, 20, 30], "std_dev": [1.5, 2.0, 2.5]},
    }
    
    if strategy not in strategies:
        return {"success": False, "error": f"Unknown strategy: {strategy}"}
    
    engine = VectorBTEngine(config)
    result = engine.optimize_parameters(
        data,
        strategies[strategy],
        param_ranges or default_ranges.get(strategy, {}),
    )
    return result.to_dict()


if __name__ == "__main__":
    print("VectorBT 백테스팅 엔진 테스트")
    print("=" * 50)
    print(f"VectorBT 사용 가능: {VECTORBT_AVAILABLE}")
    
    if VECTORBT_AVAILABLE:
        # 테스트 데이터 생성
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=500, freq='1h')
        
        # 랜덤 워크 + 트렌드
        returns = np.random.randn(500) * 0.02 + 0.0001
        close = 100 * np.exp(np.cumsum(returns))
        
        data = pd.DataFrame({
            'open': close * (1 + np.random.randn(500) * 0.001),
            'high': close * (1 + np.abs(np.random.randn(500)) * 0.01),
            'low': close * (1 - np.abs(np.random.randn(500)) * 0.01),
            'close': close,
            'volume': np.random.randint(1000, 10000, 500),
        }, index=dates)
        
        print("\n1. SMA 크로스오버 백테스트")
        result = quick_backtest(data, "sma_crossover", {"fast_period": 10, "slow_period": 30})
        print(f"   총 수익률: {result['returns']['total_return']:.2%}")
        print(f"   Sharpe Ratio: {result['returns']['sharpe_ratio']:.2f}")
        print(f"   최대 낙폭: {result['risk']['max_drawdown']:.2%}")
        print(f"   총 거래: {result['trades']['total_trades']}회")
        
        print("\n2. 파라미터 최적화")
        opt_result = optimize_strategy(
            data, 
            "sma_crossover",
            {"fast_period": [5, 10, 15], "slow_period": [20, 30, 50]},
        )
        print(f"   최적 파라미터: {opt_result['best_params']}")
        print(f"   최적 Sharpe: {opt_result['best_sharpe']:.2f}")
        print(f"   테스트 조합: {opt_result['total_combinations']}개")
        print(f"   소요 시간: {opt_result['elapsed_seconds']:.2f}초")
    else:
        print("\nVectorBT를 설치하세요: pip install vectorbt")
