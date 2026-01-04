"""
ATR-Normalized VWMA Deviation
Converted from Pine Script

Indicators: SMA, ATR
"""

from backtesting import Strategy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from risk_management_patterns import EnhancedRiskManagementMixin
import pandas as pd
import numpy as np


class ATRVWMADeviationEnhanced(Strategy, EnhancedRiskManagementMixin):
    """ATR-normalized VWMA deviation strategy"""
    
    # Parameters
    vwma_period = 20
    atr_period = 14
    deviation_threshold = 1.5
    
    def init(self):
        """Initialize indicators and risk management"""
        self.init_risk_management()
        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        volume = self.data.Volume
        
        self.atr = self.I(self._calc_atr, high, low, close, self.atr_period)
        self.vwma = self.I(self._calc_vwma, close, volume, self.vwma_period)
        self.sma = self.I(lambda x: pd.Series(x).rolling(self.vwma_period).mean(), close)
    
    def next(self):
        """Trading logic"""
        if len(self.data) < self.vwma_period + 1:
            return
        
        # Calculate deviation
        price = self.data.Close[-1]
        deviation = (price - self.vwma[-1]) / self.atr[-1] if self.atr[-1] > 0 else 0
        
        if not self.position:
            # Buy on oversold (price below VWMA)
            if deviation < -self.deviation_threshold:
                self.buy()
        else:
            # Sell on mean reversion or overbought
            if deviation > 0 or deviation > self.deviation_threshold:
                self.position.close()
        
        # Risk management
        self.manage_risk()
    
    @staticmethod
    def _calc_atr(high, low, close, period):
        """Calculate ATR"""
        high, low, close = pd.Series(high), pd.Series(low), pd.Series(close)
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(period).mean().values
    
    @staticmethod
    def _calc_vwma(close, volume, period):
        """Calculate Volume-Weighted Moving Average"""
        close = pd.Series(close)
        volume = pd.Series(volume)
        return (close * volume).rolling(period).sum() / volume.rolling(period).sum()
