"""
PMax - Asymmetric Multipliers Strategy (No Stop Loss Version)
Converted from Pine Script to backtesting.py format

Commission: 0.03% (same as Pine Script)
"""

from backtesting import Strategy
import pandas as pd
import numpy as np


class PMaxAsymmetricNoSL(Strategy):
    """
    PMax strategy with asymmetric ATR multipliers.

    - Upper multiplier (1.5x) for short positions
    - Lower multiplier (3.0x) for long positions
    - Configurable moving average type (SMA, EMA, WMA, RMA, HULL, VAR)
    - NO STOP LOSS - exits only on signal reversal
    """

    # Parameters
    atr_length = 10
    upper_multiplier = 1.5  # ATR multiplier for upper band (short)
    lower_multiplier = 3.0  # ATR multiplier for lower band (long)
    ma_length = 10
    ma_type = "EMA"  # Options: SMA, EMA, WMA, RMA, HULL, VAR

    def init(self):
        """Initialize indicators and state variables."""
        close = self.data.Close
        high = self.data.High
        low = self.data.Low

        # Calculate ATR
        self.atr = self.I(self._calculate_atr, high, low, close, self.atr_length)

        # Calculate Moving Average
        self.ma = self.I(self._calculate_ma, close, self.ma_length, self.ma_type)

        # Calculate PMax
        pmax_data = self.I(self._calculate_pmax, self.ma, self.atr,
                          self.upper_multiplier, self.lower_multiplier)
        self.pmax = pmax_data

    def next(self):
        """Execute trading logic on each bar."""
        # Skip if we don't have enough data
        if len(self.data) < max(self.atr_length, self.ma_length) + 1:
            return

        ma_current = self.ma[-1]
        ma_prev = self.ma[-2]
        pmax_current = self.pmax[-1]
        pmax_prev = self.pmax[-2]

        # Check for crossover (Long signal: MA crosses above PMax)
        buy_signal = ma_prev <= pmax_prev and ma_current > pmax_current

        # Check for crossunder (Short signal: MA crosses below PMax)
        sell_signal = ma_prev >= pmax_prev and ma_current < pmax_current

        # Entry logic (position flipping allowed)
        if buy_signal:
            # Close any short position and go long
            if self.position.is_short:
                self.position.close()
            if not self.position:
                self.buy()

        elif sell_signal:
            # Close any long position and go short
            if self.position.is_long:
                self.position.close()
            if not self.position:
                self.sell()

    @staticmethod
    def _calculate_atr(high, low, close, length):
        """Calculate Average True Range."""
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=length).mean()

        return atr.values

    @staticmethod
    def _calculate_ma(source, length, ma_type):
        """Calculate moving average based on type."""
        series = pd.Series(source)

        if ma_type == "SMA":
            return series.rolling(window=length).mean().values

        elif ma_type == "EMA":
            return series.ewm(span=length, adjust=False).mean().values

        elif ma_type == "WMA":
            weights = np.arange(1, length + 1)
            def wma(x):
                if len(x) < length:
                    return np.nan
                return np.sum(weights * x[-length:]) / weights.sum()
            return series.rolling(window=length).apply(wma, raw=True).values

        elif ma_type == "RMA":
            # RMA is similar to EMA with alpha = 1/length
            alpha = 1.0 / length
            return series.ewm(alpha=alpha, adjust=False).mean().values

        elif ma_type == "HULL":
            # Hull Moving Average: HMA = WMA(2*WMA(n/2) - WMA(n), sqrt(n))
            half_length = int(length / 2)
            sqrt_length = int(np.sqrt(length))

            weights_half = np.arange(1, half_length + 1)
            weights_full = np.arange(1, length + 1)
            weights_sqrt = np.arange(1, sqrt_length + 1)

            def wma_half(x):
                if len(x) < half_length:
                    return np.nan
                return np.sum(weights_half * x[-half_length:]) / weights_half.sum()

            def wma_full(x):
                if len(x) < length:
                    return np.nan
                return np.sum(weights_full * x[-length:]) / weights_full.sum()

            wma1 = series.rolling(window=half_length).apply(wma_half, raw=True)
            wma2 = series.rolling(window=length).apply(wma_full, raw=True)
            raw_hma = 2 * wma1 - wma2

            def wma_sqrt(x):
                if len(x) < sqrt_length:
                    return np.nan
                return np.sum(weights_sqrt * x[-sqrt_length:]) / weights_sqrt.sum()

            hma = raw_hma.rolling(window=sqrt_length).apply(wma_sqrt, raw=True)
            return hma.values

        elif ma_type == "VAR":
            # Variable Adaptive Moving Average
            return PMaxAsymmetricNoSL._calculate_var(series, length)

        else:
            # Default to EMA
            return series.ewm(span=length, adjust=False).mean().values

    @staticmethod
    def _calculate_var(source, length):
        """Calculate Variable Adaptive Moving Average (VAR)."""
        valpha = 2 / (length + 1)

        # Calculate absolute difference
        vud1 = abs(source - source.shift(1))

        # EMA of absolute difference
        vud2 = vud1.ewm(span=length, adjust=False).mean()

        # EMA of difference (with sign)
        vud3 = (source - source.shift(1)).ewm(span=length, adjust=False).mean()

        # Momentum oscillator
        vmo = np.where(vud2 == 0, 0, vud3 / vud2)

        # Volatility-adjusted weight
        vhui = valpha * abs(vmo)

        # Calculate VAR iteratively
        vma = np.zeros(len(source))
        vma[0] = source.iloc[0] if not pd.isna(source.iloc[0]) else 0

        for i in range(1, len(source)):
            if pd.isna(vhui.iloc[i]) or pd.isna(source.iloc[i]):
                vma[i] = vma[i-1]
            else:
                vma[i] = (source.iloc[i] * vhui.iloc[i]) + (vma[i-1] * (1 - vhui.iloc[i]))

        return vma

    @staticmethod
    def _calculate_pmax(ma, atr, upper_mult, lower_mult):
        """
        Calculate PMax with asymmetric multipliers.

        Pine Script logic:
        - basicUpperBand = ma + (upper_mult * atr)
        - basicLowerBand = ma - (lower_mult * atr)
        - Track trend and adjust bands
        - Return pmax based on trend
        """
        ma = pd.Series(ma)
        atr = pd.Series(atr)

        n = len(ma)

        # Initialize arrays
        basic_upper = ma + (upper_mult * atr)
        basic_lower = ma - (lower_mult * atr)

        final_upper = np.zeros(n)
        final_lower = np.zeros(n)
        trend = np.zeros(n, dtype=int)
        pmax = np.zeros(n)

        # Initialize first values
        final_upper[0] = basic_upper.iloc[0] if not pd.isna(basic_upper.iloc[0]) else 0
        final_lower[0] = basic_lower.iloc[0] if not pd.isna(basic_lower.iloc[0]) else 0
        trend[0] = 1
        pmax[0] = final_lower[0]

        # Calculate iteratively (following Pine Script logic)
        for i in range(1, n):
            # Update final upper band
            if basic_upper.iloc[i] < final_upper[i-1] or ma.iloc[i-1] > final_upper[i-1]:
                final_upper[i] = basic_upper.iloc[i]
            else:
                final_upper[i] = final_upper[i-1]

            # Update final lower band
            if basic_lower.iloc[i] > final_lower[i-1] or ma.iloc[i-1] < final_lower[i-1]:
                final_lower[i] = basic_lower.iloc[i]
            else:
                final_lower[i] = final_lower[i-1]

            # Determine trend
            prev_trend = trend[i-1]

            if prev_trend == 1 and ma.iloc[i] < final_lower[i-1]:
                trend[i] = -1
                final_upper[i] = basic_upper.iloc[i]
            elif prev_trend == -1 and ma.iloc[i] > final_upper[i-1]:
                trend[i] = 1
                final_lower[i] = basic_lower.iloc[i]
            else:
                trend[i] = prev_trend

            # Set pmax based on trend
            if trend[i] == 1:
                pmax[i] = final_lower[i]
            else:
                pmax[i] = final_upper[i]

            # Handle NA or zero values
            if pd.isna(pmax[i]) or pmax[i] == 0:
                pmax[i] = ma.iloc[i]

        return pmax
