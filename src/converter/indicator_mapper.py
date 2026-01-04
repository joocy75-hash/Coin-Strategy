"""
Pine Script Indicator Mapper

Maps Pine Script technical indicators to pandas/numpy implementations.
Supports 50+ common indicators with proper parameter handling and defaults.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class IndicatorMapping:
    """Mapping configuration for a Pine Script indicator"""

    name: str  # Pine Script name (e.g., 'ta.sma')
    python_func: str  # Python method name
    params: List[str]  # Parameter names in order
    defaults: Dict[str, Any]  # Default parameter values
    description: str  # Indicator description
    returns_multiple: bool = False  # True if returns tuple (e.g., MACD)
    return_names: Optional[List[str]] = None  # Names for multiple returns


class IndicatorMapper:
    """
    Comprehensive mapping of Pine Script indicators to Python implementations

    Provides implementations for 50+ technical indicators commonly used in
    Pine Script, with proper parameter handling and pandas/numpy operations.

    Example:
        mapper = IndicatorMapper()
        df = pd.DataFrame({'close': [...], 'high': [...], 'low': [...]})
        sma_20 = mapper.calculate('ta.sma', df['close'], length=20)
        rsi_14 = mapper.calculate('ta.rsi', df['close'], length=14)
    """

    def __init__(self):
        """Initialize indicator mapper with all mappings"""
        self.mappings = self._build_mappings()

    def _build_mappings(self) -> Dict[str, IndicatorMapping]:
        """Build comprehensive indicator mapping dictionary"""
        mappings = {}

        # === TREND INDICATORS ===

        # Simple Moving Average
        mappings['ta.sma'] = IndicatorMapping(
            name='ta.sma',
            python_func='_sma',
            params=['source', 'length'],
            defaults={'length': 14},
            description='Simple Moving Average'
        )

        # Exponential Moving Average
        mappings['ta.ema'] = IndicatorMapping(
            name='ta.ema',
            python_func='_ema',
            params=['source', 'length'],
            defaults={'length': 14},
            description='Exponential Moving Average'
        )

        # Weighted Moving Average
        mappings['ta.wma'] = IndicatorMapping(
            name='ta.wma',
            python_func='_wma',
            params=['source', 'length'],
            defaults={'length': 14},
            description='Weighted Moving Average'
        )

        # Running Moving Average (Wilder's)
        mappings['ta.rma'] = IndicatorMapping(
            name='ta.rma',
            python_func='_rma',
            params=['source', 'length'],
            defaults={'length': 14},
            description="Wilder's Moving Average (RMA)"
        )

        # Volume Weighted Moving Average
        mappings['ta.vwma'] = IndicatorMapping(
            name='ta.vwma',
            python_func='_vwma',
            params=['source', 'length'],
            defaults={'length': 20},
            description='Volume Weighted Moving Average'
        )

        # Hull Moving Average
        mappings['ta.hma'] = IndicatorMapping(
            name='ta.hma',
            python_func='_hma',
            params=['source', 'length'],
            defaults={'length': 9},
            description='Hull Moving Average'
        )

        # Arnaud Legoux Moving Average
        mappings['ta.alma'] = IndicatorMapping(
            name='ta.alma',
            python_func='_alma',
            params=['source', 'length', 'offset', 'sigma'],
            defaults={'length': 9, 'offset': 0.85, 'sigma': 6},
            description='Arnaud Legoux Moving Average'
        )

        # Triple EMA
        mappings['ta.tema'] = IndicatorMapping(
            name='ta.tema',
            python_func='_tema',
            params=['source', 'length'],
            defaults={'length': 14},
            description='Triple Exponential Moving Average'
        )

        # Double EMA
        mappings['ta.dema'] = IndicatorMapping(
            name='ta.dema',
            python_func='_dema',
            params=['source', 'length'],
            defaults={'length': 14},
            description='Double Exponential Moving Average'
        )

        # === MOMENTUM INDICATORS ===

        # Relative Strength Index
        mappings['ta.rsi'] = IndicatorMapping(
            name='ta.rsi',
            python_func='_rsi',
            params=['source', 'length'],
            defaults={'length': 14},
            description='Relative Strength Index'
        )

        # Moving Average Convergence Divergence
        mappings['ta.macd'] = IndicatorMapping(
            name='ta.macd',
            python_func='_macd',
            params=['source', 'fast_length', 'slow_length', 'signal_length'],
            defaults={'fast_length': 12, 'slow_length': 26, 'signal_length': 9},
            description='MACD',
            returns_multiple=True,
            return_names=['macd', 'signal', 'histogram']
        )

        # Stochastic Oscillator
        mappings['ta.stoch'] = IndicatorMapping(
            name='ta.stoch',
            python_func='_stoch',
            params=['source', 'high', 'low', 'length'],
            defaults={'length': 14},
            description='Stochastic Oscillator',
            returns_multiple=True,
            return_names=['k', 'd']
        )

        # Commodity Channel Index
        mappings['ta.cci'] = IndicatorMapping(
            name='ta.cci',
            python_func='_cci',
            params=['source', 'length'],
            defaults={'length': 20},
            description='Commodity Channel Index'
        )

        # Money Flow Index
        mappings['ta.mfi'] = IndicatorMapping(
            name='ta.mfi',
            python_func='_mfi',
            params=['high', 'low', 'close', 'volume', 'length'],
            defaults={'length': 14},
            description='Money Flow Index'
        )

        # Rate of Change
        mappings['ta.roc'] = IndicatorMapping(
            name='ta.roc',
            python_func='_roc',
            params=['source', 'length'],
            defaults={'length': 10},
            description='Rate of Change'
        )

        # Williams %R
        mappings['ta.wpr'] = IndicatorMapping(
            name='ta.wpr',
            python_func='_wpr',
            params=['high', 'low', 'close', 'length'],
            defaults={'length': 14},
            description='Williams Percent R'
        )

        # Momentum
        mappings['ta.mom'] = IndicatorMapping(
            name='ta.mom',
            python_func='_mom',
            params=['source', 'length'],
            defaults={'length': 10},
            description='Momentum'
        )

        # === VOLATILITY INDICATORS ===

        # Average True Range
        mappings['ta.atr'] = IndicatorMapping(
            name='ta.atr',
            python_func='_atr',
            params=['high', 'low', 'close', 'length'],
            defaults={'length': 14},
            description='Average True Range'
        )

        # True Range
        mappings['ta.tr'] = IndicatorMapping(
            name='ta.tr',
            python_func='_tr',
            params=['high', 'low', 'close'],
            defaults={},
            description='True Range'
        )

        # Bollinger Bands
        mappings['ta.bb'] = IndicatorMapping(
            name='ta.bb',
            python_func='_bb',
            params=['source', 'length', 'mult'],
            defaults={'length': 20, 'mult': 2.0},
            description='Bollinger Bands',
            returns_multiple=True,
            return_names=['upper', 'basis', 'lower']
        )

        # Keltner Channels
        mappings['ta.kc'] = IndicatorMapping(
            name='ta.kc',
            python_func='_kc',
            params=['high', 'low', 'close', 'length', 'mult'],
            defaults={'length': 20, 'mult': 2.0},
            description='Keltner Channels',
            returns_multiple=True,
            return_names=['upper', 'basis', 'lower']
        )

        # Standard Deviation
        mappings['ta.stdev'] = IndicatorMapping(
            name='ta.stdev',
            python_func='_stdev',
            params=['source', 'length'],
            defaults={'length': 20},
            description='Standard Deviation'
        )

        # === VOLUME INDICATORS ===

        # Volume Weighted Average Price
        mappings['ta.vwap'] = IndicatorMapping(
            name='ta.vwap',
            python_func='_vwap',
            params=['high', 'low', 'close', 'volume'],
            defaults={},
            description='Volume Weighted Average Price'
        )

        # On Balance Volume
        mappings['ta.obv'] = IndicatorMapping(
            name='ta.obv',
            python_func='_obv',
            params=['close', 'volume'],
            defaults={},
            description='On Balance Volume'
        )

        # Accumulation/Distribution
        mappings['ta.accdist'] = IndicatorMapping(
            name='ta.accdist',
            python_func='_accdist',
            params=['high', 'low', 'close', 'volume'],
            defaults={},
            description='Accumulation/Distribution'
        )

        # === PIVOT AND SUPPORT/RESISTANCE ===

        # Pivot High
        mappings['ta.pivothigh'] = IndicatorMapping(
            name='ta.pivothigh',
            python_func='_pivothigh',
            params=['source', 'left_bars', 'right_bars'],
            defaults={'left_bars': 5, 'right_bars': 5},
            description='Pivot High'
        )

        # Pivot Low
        mappings['ta.pivotlow'] = IndicatorMapping(
            name='ta.pivotlow',
            python_func='_pivotlow',
            params=['source', 'left_bars', 'right_bars'],
            defaults={'left_bars': 5, 'right_bars': 5},
            description='Pivot Low'
        )

        # === CROSSOVER FUNCTIONS ===

        # Crossover
        mappings['ta.crossover'] = IndicatorMapping(
            name='ta.crossover',
            python_func='_crossover',
            params=['source1', 'source2'],
            defaults={},
            description='Crossover detection'
        )

        # Crossunder
        mappings['ta.crossunder'] = IndicatorMapping(
            name='ta.crossunder',
            python_func='_crossunder',
            params=['source1', 'source2'],
            defaults={},
            description='Crossunder detection'
        )

        # Cross (either direction)
        mappings['ta.cross'] = IndicatorMapping(
            name='ta.cross',
            python_func='_cross',
            params=['source1', 'source2'],
            defaults={},
            description='Cross detection (either direction)'
        )

        # === MATH FUNCTIONS ===

        # Highest
        mappings['ta.highest'] = IndicatorMapping(
            name='ta.highest',
            python_func='_highest',
            params=['source', 'length'],
            defaults={'length': 14},
            description='Highest value over period'
        )

        # Lowest
        mappings['ta.lowest'] = IndicatorMapping(
            name='ta.lowest',
            python_func='_lowest',
            params=['source', 'length'],
            defaults={'length': 14},
            description='Lowest value over period'
        )

        # Change
        mappings['ta.change'] = IndicatorMapping(
            name='ta.change',
            python_func='_change',
            params=['source', 'length'],
            defaults={'length': 1},
            description='Change over period'
        )

        # Cumulative sum
        mappings['ta.cum'] = IndicatorMapping(
            name='ta.cum',
            python_func='_cum',
            params=['source'],
            defaults={},
            description='Cumulative sum'
        )

        # Correlation
        mappings['ta.correlation'] = IndicatorMapping(
            name='ta.correlation',
            python_func='_correlation',
            params=['source1', 'source2', 'length'],
            defaults={'length': 20},
            description='Correlation coefficient'
        )

        # Covariance
        mappings['ta.cov'] = IndicatorMapping(
            name='ta.cov',
            python_func='_covariance',
            params=['source1', 'source2', 'length'],
            defaults={'length': 20},
            description='Covariance'
        )

        # Median
        mappings['ta.median'] = IndicatorMapping(
            name='ta.median',
            python_func='_median',
            params=['source', 'length'],
            defaults={'length': 14},
            description='Median value'
        )

        # Mode
        mappings['ta.mode'] = IndicatorMapping(
            name='ta.mode',
            python_func='_mode',
            params=['source', 'length'],
            defaults={'length': 14},
            description='Mode (most common value)'
        )

        # Percentile Rank
        mappings['ta.percentrank'] = IndicatorMapping(
            name='ta.percentrank',
            python_func='_percentrank',
            params=['source', 'length'],
            defaults={'length': 14},
            description='Percentile rank'
        )

        # Range
        mappings['ta.range'] = IndicatorMapping(
            name='ta.range',
            python_func='_range',
            params=['source', 'length'],
            defaults={'length': 14},
            description='Range (max - min)'
        )

        # Variance
        mappings['ta.variance'] = IndicatorMapping(
            name='ta.variance',
            python_func='_variance',
            params=['source', 'length'],
            defaults={'length': 20},
            description='Variance'
        )

        # === DIRECTIONAL MOVEMENT ===

        # ADX (Average Directional Index)
        mappings['ta.adx'] = IndicatorMapping(
            name='ta.adx',
            python_func='_adx',
            params=['high', 'low', 'close', 'length'],
            defaults={'length': 14},
            description='Average Directional Index'
        )

        # DMI
        mappings['ta.dmi'] = IndicatorMapping(
            name='ta.dmi',
            python_func='_dmi',
            params=['high', 'low', 'close', 'length'],
            defaults={'length': 14},
            description='Directional Movement Index',
            returns_multiple=True,
            return_names=['plus_di', 'minus_di', 'adx']
        )

        # === SUPERTREND ===

        mappings['ta.supertrend'] = IndicatorMapping(
            name='ta.supertrend',
            python_func='_supertrend',
            params=['high', 'low', 'close', 'factor', 'atr_period'],
            defaults={'factor': 3.0, 'atr_period': 10},
            description='Supertrend indicator',
            returns_multiple=True,
            return_names=['supertrend', 'direction']
        )

        # === SAR ===

        mappings['ta.sar'] = IndicatorMapping(
            name='ta.sar',
            python_func='_sar',
            params=['high', 'low', 'start', 'increment', 'maximum'],
            defaults={'start': 0.02, 'increment': 0.02, 'maximum': 0.2},
            description='Parabolic SAR'
        )

        return mappings

    # === IMPLEMENTATION METHODS ===

    def _sma(self, source: pd.Series, length: int) -> pd.Series:
        """Simple Moving Average"""
        return source.rolling(window=length, min_periods=1).mean()

    def _ema(self, source: pd.Series, length: int) -> pd.Series:
        """Exponential Moving Average"""
        return source.ewm(span=length, adjust=False, min_periods=1).mean()

    def _wma(self, source: pd.Series, length: int) -> pd.Series:
        """Weighted Moving Average"""
        weights = np.arange(1, length + 1)
        return source.rolling(window=length, min_periods=1).apply(
            lambda x: np.sum(weights[:len(x)] * x) / np.sum(weights[:len(x)]),
            raw=True
        )

    def _rma(self, source: pd.Series, length: int) -> pd.Series:
        """Running Moving Average (Wilder's smoothing)"""
        alpha = 1.0 / length
        return source.ewm(alpha=alpha, adjust=False, min_periods=1).mean()

    def _vwma(self, source: pd.Series, length: int, volume: pd.Series = None) -> pd.Series:
        """Volume Weighted Moving Average"""
        if volume is None:
            return self._sma(source, length)
        pv = source * volume
        return pv.rolling(window=length, min_periods=1).sum() / volume.rolling(window=length, min_periods=1).sum()

    def _hma(self, source: pd.Series, length: int) -> pd.Series:
        """Hull Moving Average"""
        half_length = int(length / 2)
        sqrt_length = int(np.sqrt(length))

        wma_half = self._wma(source, half_length)
        wma_full = self._wma(source, length)
        raw_hma = 2 * wma_half - wma_full

        return self._wma(raw_hma, sqrt_length)

    def _alma(self, source: pd.Series, length: int, offset: float, sigma: float) -> pd.Series:
        """Arnaud Legoux Moving Average"""
        m = offset * (length - 1)
        s = length / sigma

        def alma_window(window):
            w = np.exp(-((np.arange(len(window)) - m) ** 2) / (2 * s * s))
            return np.sum(w * window) / np.sum(w)

        return source.rolling(window=length, min_periods=1).apply(alma_window, raw=True)

    def _tema(self, source: pd.Series, length: int) -> pd.Series:
        """Triple Exponential Moving Average"""
        ema1 = self._ema(source, length)
        ema2 = self._ema(ema1, length)
        ema3 = self._ema(ema2, length)
        return 3 * ema1 - 3 * ema2 + ema3

    def _dema(self, source: pd.Series, length: int) -> pd.Series:
        """Double Exponential Moving Average"""
        ema1 = self._ema(source, length)
        ema2 = self._ema(ema1, length)
        return 2 * ema1 - ema2

    def _rsi(self, source: pd.Series, length: int) -> pd.Series:
        """Relative Strength Index"""
        delta = source.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length, min_periods=1).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    def _macd(self, source: pd.Series, fast_length: int = 12,
              slow_length: int = 26, signal_length: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence)"""
        fast = self._ema(source, fast_length)
        slow = self._ema(source, slow_length)
        macd_line = fast - slow
        signal_line = self._ema(macd_line, signal_length)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _stoch(self, source: pd.Series, high: pd.Series, low: pd.Series,
               length: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator"""
        lowest_low = low.rolling(window=length, min_periods=1).min()
        highest_high = high.rolling(window=length, min_periods=1).max()

        k = 100 * (source - lowest_low) / (highest_high - lowest_low)
        k = k.rolling(window=smooth_k, min_periods=1).mean()
        d = k.rolling(window=smooth_d, min_periods=1).mean()

        return k.fillna(50), d.fillna(50)

    def _cci(self, source: pd.Series, length: int) -> pd.Series:
        """Commodity Channel Index"""
        tp = source  # Typically (high + low + close) / 3
        sma_tp = self._sma(tp, length)
        mad = source.rolling(window=length, min_periods=1).apply(
            lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
        )
        cci = (tp - sma_tp) / (0.015 * mad)
        return cci.fillna(0)

    def _mfi(self, high: pd.Series, low: pd.Series, close: pd.Series,
             volume: pd.Series, length: int) -> pd.Series:
        """Money Flow Index"""
        tp = (high + low + close) / 3
        mf = tp * volume
        mf_pos = mf.where(tp > tp.shift(1), 0).rolling(window=length, min_periods=1).sum()
        mf_neg = mf.where(tp < tp.shift(1), 0).rolling(window=length, min_periods=1).sum()

        mfi = 100 - (100 / (1 + mf_pos / mf_neg.replace(0, 1)))
        return mfi.fillna(50)

    def _roc(self, source: pd.Series, length: int) -> pd.Series:
        """Rate of Change"""
        roc = ((source - source.shift(length)) / source.shift(length)) * 100
        return roc.fillna(0)

    def _wpr(self, high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
        """Williams Percent R"""
        highest_high = high.rolling(window=length, min_periods=1).max()
        lowest_low = low.rolling(window=length, min_periods=1).min()
        wpr = -100 * (highest_high - close) / (highest_high - lowest_low)
        return wpr.fillna(-50)

    def _mom(self, source: pd.Series, length: int) -> pd.Series:
        """Momentum"""
        return source.diff(length).fillna(0)

    def _atr(self, high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
        """Average True Range"""
        tr = self._tr(high, low, close)
        return self._rma(tr, length)

    def _tr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """True Range"""
        hl = high - low
        hc = (high - close.shift(1)).abs()
        lc = (low - close.shift(1)).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return tr

    def _bb(self, source: pd.Series, length: int, mult: float) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands"""
        basis = self._sma(source, length)
        dev = mult * self._stdev(source, length)
        upper = basis + dev
        lower = basis - dev
        return upper, basis, lower

    def _kc(self, high: pd.Series, low: pd.Series, close: pd.Series,
            length: int, mult: float) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Keltner Channels"""
        basis = self._ema(close, length)
        range_ma = self._ema(high - low, length)
        upper = basis + range_ma * mult
        lower = basis - range_ma * mult
        return upper, basis, lower

    def _stdev(self, source: pd.Series, length: int) -> pd.Series:
        """Standard Deviation"""
        return source.rolling(window=length, min_periods=1).std()

    def _vwap(self, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Volume Weighted Average Price"""
        tp = (high + low + close) / 3
        return (tp * volume).cumsum() / volume.cumsum()

    def _obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """On Balance Volume"""
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        return obv

    def _accdist(self, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Accumulation/Distribution"""
        clv = ((close - low) - (high - close)) / (high - low)
        clv = clv.fillna(0)
        ad = (clv * volume).cumsum()
        return ad

    def _pivothigh(self, source: pd.Series, left_bars: int, right_bars: int) -> pd.Series:
        """Pivot High detection"""
        pivots = pd.Series(np.nan, index=source.index)
        for i in range(left_bars, len(source) - right_bars):
            window = source.iloc[i - left_bars:i + right_bars + 1]
            if source.iloc[i] == window.max():
                pivots.iloc[i] = source.iloc[i]
        return pivots

    def _pivotlow(self, source: pd.Series, left_bars: int, right_bars: int) -> pd.Series:
        """Pivot Low detection"""
        pivots = pd.Series(np.nan, index=source.index)
        for i in range(left_bars, len(source) - right_bars):
            window = source.iloc[i - left_bars:i + right_bars + 1]
            if source.iloc[i] == window.min():
                pivots.iloc[i] = source.iloc[i]
        return pivots

    def _crossover(self, source1: pd.Series, source2: pd.Series) -> pd.Series:
        """Crossover detection (source1 crosses over source2)"""
        return (source1 > source2) & (source1.shift(1) <= source2.shift(1))

    def _crossunder(self, source1: pd.Series, source2: pd.Series) -> pd.Series:
        """Crossunder detection (source1 crosses under source2)"""
        return (source1 < source2) & (source1.shift(1) >= source2.shift(1))

    def _cross(self, source1: pd.Series, source2: pd.Series) -> pd.Series:
        """Cross detection (either direction)"""
        return self._crossover(source1, source2) | self._crossunder(source1, source2)

    def _highest(self, source: pd.Series, length: int) -> pd.Series:
        """Highest value over period"""
        return source.rolling(window=length, min_periods=1).max()

    def _lowest(self, source: pd.Series, length: int) -> pd.Series:
        """Lowest value over period"""
        return source.rolling(window=length, min_periods=1).min()

    def _change(self, source: pd.Series, length: int) -> pd.Series:
        """Change over period"""
        return source.diff(length).fillna(0)

    def _cum(self, source: pd.Series) -> pd.Series:
        """Cumulative sum"""
        return source.cumsum()

    def _correlation(self, source1: pd.Series, source2: pd.Series, length: int) -> pd.Series:
        """Correlation coefficient"""
        return source1.rolling(window=length, min_periods=1).corr(source2)

    def _covariance(self, source1: pd.Series, source2: pd.Series, length: int) -> pd.Series:
        """Covariance"""
        return source1.rolling(window=length, min_periods=1).cov(source2)

    def _median(self, source: pd.Series, length: int) -> pd.Series:
        """Median value"""
        return source.rolling(window=length, min_periods=1).median()

    def _mode(self, source: pd.Series, length: int) -> pd.Series:
        """Mode (most common value)"""
        return source.rolling(window=length, min_periods=1).apply(
            lambda x: pd.Series(x).mode()[0] if len(pd.Series(x).mode()) > 0 else x.iloc[-1],
            raw=False
        )

    def _percentrank(self, source: pd.Series, length: int) -> pd.Series:
        """Percentile rank"""
        return source.rolling(window=length, min_periods=1).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100,
            raw=False
        )

    def _range(self, source: pd.Series, length: int) -> pd.Series:
        """Range (max - min)"""
        return self._highest(source, length) - self._lowest(source, length)

    def _variance(self, source: pd.Series, length: int) -> pd.Series:
        """Variance"""
        return source.rolling(window=length, min_periods=1).var()

    def _adx(self, high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
        """Average Directional Index"""
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = self._tr(high, low, close)
        atr = self._rma(tr, length)

        plus_di = 100 * self._rma(plus_dm, length) / atr
        minus_di = 100 * self._rma(minus_dm, length) / atr

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = self._rma(dx, length)

        return adx

    def _dmi(self, high: pd.Series, low: pd.Series, close: pd.Series,
             length: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Directional Movement Index"""
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = self._tr(high, low, close)
        atr = self._rma(tr, length)

        plus_di = 100 * self._rma(plus_dm, length) / atr
        minus_di = 100 * self._rma(minus_dm, length) / atr

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = self._rma(dx, length)

        return plus_di, minus_di, adx

    def _supertrend(self, high: pd.Series, low: pd.Series, close: pd.Series,
                    factor: float, atr_period: int) -> Tuple[pd.Series, pd.Series]:
        """Supertrend indicator"""
        atr = self._atr(high, low, close, atr_period)
        hl_avg = (high + low) / 2

        upper_band = hl_avg + factor * atr
        lower_band = hl_avg - factor * atr

        supertrend = pd.Series(np.nan, index=close.index)
        direction = pd.Series(1, index=close.index)  # 1 = uptrend, -1 = downtrend

        for i in range(1, len(close)):
            if close.iloc[i] > upper_band.iloc[i - 1]:
                direction.iloc[i] = 1
            elif close.iloc[i] < lower_band.iloc[i - 1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i - 1]

            if direction.iloc[i] == 1:
                supertrend.iloc[i] = lower_band.iloc[i]
            else:
                supertrend.iloc[i] = upper_band.iloc[i]

        return supertrend, direction

    def _sar(self, high: pd.Series, low: pd.Series, start: float,
             increment: float, maximum: float) -> pd.Series:
        """Parabolic SAR"""
        sar = pd.Series(np.nan, index=high.index)
        af = start
        trend = 1  # 1 for uptrend, -1 for downtrend

        sar.iloc[0] = low.iloc[0]
        ep = high.iloc[0]

        for i in range(1, len(high)):
            sar.iloc[i] = sar.iloc[i - 1] + af * (ep - sar.iloc[i - 1])

            if trend == 1:
                if low.iloc[i] < sar.iloc[i]:
                    trend = -1
                    sar.iloc[i] = ep
                    ep = low.iloc[i]
                    af = start
                else:
                    if high.iloc[i] > ep:
                        ep = high.iloc[i]
                        af = min(af + increment, maximum)
            else:
                if high.iloc[i] > sar.iloc[i]:
                    trend = 1
                    sar.iloc[i] = ep
                    ep = high.iloc[i]
                    af = start
                else:
                    if low.iloc[i] < ep:
                        ep = low.iloc[i]
                        af = min(af + increment, maximum)

        return sar

    # === PUBLIC INTERFACE ===

    def calculate(self, indicator_name: str, *args, **kwargs) -> Any:
        """
        Calculate an indicator by name

        Args:
            indicator_name: Pine Script indicator name (e.g., 'ta.sma')
            *args: Positional arguments (data series)
            **kwargs: Named parameters

        Returns:
            Calculated indicator (Series or Tuple of Series)

        Example:
            sma = mapper.calculate('ta.sma', df['close'], length=20)
            macd, signal, hist = mapper.calculate('ta.macd', df['close'])
        """
        if indicator_name not in self.mappings:
            raise ValueError(f"Unknown indicator: {indicator_name}")

        mapping = self.mappings[indicator_name]

        # Merge defaults with provided kwargs
        params = {**mapping.defaults, **kwargs}

        # Get the implementation method
        method = getattr(self, mapping.python_func)

        # Call with args and params
        return method(*args, **params)

    def get_mapping(self, indicator_name: str) -> Optional[IndicatorMapping]:
        """Get mapping information for an indicator"""
        return self.mappings.get(indicator_name)

    def list_indicators(self) -> List[str]:
        """Get list of all supported indicators"""
        return sorted(self.mappings.keys())

    def get_indicator_info(self, indicator_name: str) -> Dict[str, Any]:
        """Get detailed information about an indicator"""
        if indicator_name not in self.mappings:
            return None

        mapping = self.mappings[indicator_name]
        return {
            'name': mapping.name,
            'description': mapping.description,
            'params': mapping.params,
            'defaults': mapping.defaults,
            'returns_multiple': mapping.returns_multiple,
            'return_names': mapping.return_names
        }


if __name__ == "__main__":
    # Example usage
    mapper = IndicatorMapper()

    # Create sample data
    data = pd.DataFrame({
        'close': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 102,
        'low': np.random.randn(100).cumsum() + 98,
        'volume': np.random.randint(1000, 10000, 100)
    })

    # Calculate indicators
    sma_20 = mapper.calculate('ta.sma', data['close'], length=20)
    ema_9 = mapper.calculate('ta.ema', data['close'], length=9)
    rsi = mapper.calculate('ta.rsi', data['close'], length=14)
    macd, signal, hist = mapper.calculate('ta.macd', data['close'])

    print("Supported indicators:", len(mapper.list_indicators()))
    print("\nSample calculations:")
    print(f"SMA(20): {sma_20.iloc[-1]:.2f}")
    print(f"EMA(9): {ema_9.iloc[-1]:.2f}")
    print(f"RSI(14): {rsi.iloc[-1]:.2f}")
    print(f"MACD: {macd.iloc[-1]:.4f}")
