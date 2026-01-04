"""
SuperTrend Weighted by Divergence
Converted from Pine Script

Indicators: EMA, SMA, ATR
"""

from backtesting import Strategy
import pandas as pd
import numpy as np


class SuperTrendDivergence(Strategy):
    """SuperTrend strategy with EMA/SMA crossover signals"""
    
    # Parameters
    atr_period = 14
    atr_multiplier = 2.0
    fast_period = 10
    slow_period = 30
    
    def init(self):
        """Initialize indicators"""
        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        
        self.atr = self.I(self._calc_atr, high, low, close, self.atr_period)
        self.fast_ema = self.I(lambda x: pd.Series(x).ewm(span=self.fast_period).mean(), close)
        self.slow_ema = self.I(lambda x: pd.Series(x).ewm(span=self.slow_period).mean(), close)
        self.supertrend = self.I(self._calc_supertrend, close, high, low, self.atr, self.atr_multiplier)
    
    def next(self):
        """Trading logic"""
        if len(self.data) < self.slow_period + 1:
            return
            
        # EMA crossover with SuperTrend confirmation
        fast_cross_above = self.fast_ema[-2] <= self.slow_ema[-2] and self.fast_ema[-1] > self.slow_ema[-1]
        fast_cross_below = self.fast_ema[-2] >= self.slow_ema[-2] and self.fast_ema[-1] < self.slow_ema[-1]
        
        price_above_st = self.data.Close[-1] > self.supertrend[-1]
        price_below_st = self.data.Close[-1] < self.supertrend[-1]
        
        if not self.position:
            if fast_cross_above and price_above_st:
                self.buy()
        else:
            if fast_cross_below or price_below_st:
                self.position.close()
    
    @staticmethod
    def _calc_atr(high, low, close, period):
        """Calculate ATR"""
        high, low, close = pd.Series(high), pd.Series(low), pd.Series(close)
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(period).mean().values
    
    @staticmethod
    def _calc_supertrend(close, high, low, atr, multiplier):
        """Calculate SuperTrend"""
        close = pd.Series(close)
        high = pd.Series(high)
        low = pd.Series(low)
        atr = pd.Series(atr)
        
        hl_avg = (high + low) / 2
        upper_band = hl_avg + multiplier * atr
        lower_band = hl_avg - multiplier * atr
        
        supertrend = pd.Series(index=close.index, dtype=float)
        direction = pd.Series(index=close.index, dtype=int)
        
        supertrend.iloc[0] = lower_band.iloc[0]
        direction.iloc[0] = 1
        
        for i in range(1, len(close)):
            if close.iloc[i] > supertrend.iloc[i-1]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lower_band.iloc[i]
            elif close.iloc[i] < supertrend.iloc[i-1]:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upper_band.iloc[i]
            else:
                direction.iloc[i] = direction.iloc[i-1]
                if direction.iloc[i] == 1:
                    supertrend.iloc[i] = lower_band.iloc[i]
                else:
                    supertrend.iloc[i] = upper_band.iloc[i]
        
        return supertrend.values
