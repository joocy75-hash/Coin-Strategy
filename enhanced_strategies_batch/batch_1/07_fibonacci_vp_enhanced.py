"""
Enhanced Strategy: Fibonacci Volume Profile
Original Pine Script: z8gaWHWQ-Auto-Anchored-Fibonacci-Volume-Profile-Custom-Array-Engine.pine
Enhanced with Risk Management

Converted: 2026-01-04

Strategy Logic:
- Finds swing high/low over lookback period
- Calculates Fibonacci retracement levels (0.236, 0.382, 0.5, 0.618, 0.786)
- Identifies Point of Control (POC) - price level with highest volume
- Simplified: Uses VWAP instead of full volume profile for efficiency
- Buy Signal: Price bounces from key Fibonacci support (0.618, 0.786) near POC
- Sell Signal: Price rejects from key Fibonacci resistance (0.236, 0.382) near POC
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for risk_management_patterns
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from risk_management_patterns import EnhancedRiskManagementMixin


class FibonacciVPEnhanced(Strategy, EnhancedRiskManagementMixin):
    """
    Fibonacci Volume Profile Strategy with Enhanced Risk Management

    Indicators:
    - Fibonacci retracement levels
    - VWAP (simplified volume profile)
    - ATR for volatility

    Entry Signals:
    - Long: Price bounces from 0.618 or 0.786 Fib level with volume
    - Short: Price rejects from 0.236 or 0.382 Fib level with volume

    Note: Simplified from original - uses VWAP instead of full volume profile
    """

    # Pine Script Parameters
    lookback_period = 200
    fib_levels = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]

    # Risk Management Parameters
    use_fixed_sl = False
    use_atr_sl = True
    use_rr_tp = True
    use_trailing_stop = True

    sl_percent = 5.0
    atr_sl_multiplier = 2.5
    rr_ratio = 2.5
    trailing_activation = 5.0
    trailing_percent = 3.0

    def init(self):
        """Initialize indicators and risk management"""
        self.init_risk_management()

        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        volume = self.data.Volume

        # ATR for risk management
        self.atr = self.I(self._calc_atr, high, low, close, 14)

        # VWAP as simplified volume profile
        self.vwap = self.I(self._calc_vwap, high, low, close, volume, 50)

        # Moving average for trend
        self.ma = self.I(lambda x: pd.Series(x).rolling(50).mean(), close)

        # Volume analysis
        self.avg_volume = self.I(lambda x: pd.Series(x).rolling(20).mean(), volume)

        # Fibonacci levels (calculated in next())
        self.fib_cache = {}

    def next(self):
        """Execute strategy logic"""
        min_bars = self.lookback_period + 50
        if len(self.data) < min_bars:
            return

        # Find swing high/low
        lookback_data = self.data.Close[-self.lookback_period:]
        swing_high = max(self.data.High[-self.lookback_period:])
        swing_low = min(self.data.Low[-self.lookback_period:])

        if swing_high == swing_low:
            self.manage_risk()
            return

        # Calculate Fibonacci levels
        swing_range = swing_high - swing_low
        fib_prices = {
            'f0': swing_low,
            'f236': swing_low + swing_range * 0.236,
            'f382': swing_low + swing_range * 0.382,
            'f500': swing_low + swing_range * 0.5,
            'f618': swing_low + swing_range * 0.618,
            'f786': swing_low + swing_range * 0.786,
            'f100': swing_high
        }

        # Current values
        close = self.data.Close[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        prev_close = self.data.Close[-2]
        prev_low = self.data.Low[-2]
        prev_high = self.data.High[-2]
        volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[-1]
        vwap = self.vwap[-1]

        # Volume confirmation
        has_volume = volume > avg_vol if not np.isnan(avg_vol) else True

        # Trend from MA
        is_uptrend = close > self.ma[-1] if not np.isnan(self.ma[-1]) else True
        is_downtrend = close < self.ma[-1] if not np.isnan(self.ma[-1]) else True

        # Entry Logic - Golden ratios (0.618, 0.786) for support
        # and (0.236, 0.382) for resistance

        if not self.position:
            # Buy Signal: Bounce from 0.618 or 0.786 level
            # Price drops to level then bounces back
            for level_name in ['f618', 'f786']:
                level_price = fib_prices[level_name]

                # Check if previous bar touched/went below level
                # and current bar is back above with volume
                if (prev_low <= level_price and
                    close > level_price and
                    has_volume and
                    is_uptrend and
                    close > vwap):  # Above VWAP for confirmation
                    self.buy()
                    break

            # Sell Signal: Rejection from 0.236 or 0.382 level
            # Price rises to level then gets rejected
            for level_name in ['f236', 'f382']:
                level_price = fib_prices[level_name]

                # Check if previous bar touched/went above level
                # and current bar is back below with volume
                if (prev_high >= level_price and
                    close < level_price and
                    has_volume and
                    is_downtrend and
                    close < vwap):  # Below VWAP for confirmation
                    self.sell()
                    break

        # Risk management
        self.manage_risk()

    @staticmethod
    def _calc_atr(high, low, close, period):
        """Calculate ATR"""
        high, low, close = pd.Series(high), pd.Series(low), pd.Series(close)
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean().values

    @staticmethod
    def _calc_vwap(high, low, close, volume, period):
        """Calculate VWAP (Volume Weighted Average Price)"""
        typical_price = (high + low + close) / 3
        tp_series = pd.Series(typical_price)
        vol_series = pd.Series(volume)

        # Rolling VWAP
        return (tp_series * vol_series).rolling(period).sum() / vol_series.rolling(period).sum()


def run_backtest():
    """Run backtest with BTCUSDT data"""
    print("Loading BTCUSDT 1h data...")

    data_path = Path(__file__).parent.parent.parent / "data" / "BTCUSDT_1h.csv"
    df = pd.read_csv(data_path, parse_dates=['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

    print(f"Data loaded: {len(df)} bars from {df.index[0]} to {df.index[-1]}")

    # Run backtest
    bt = Backtest(
        df,
        FibonacciVPEnhanced,
        cash=100000,
        commission=0.001,
        exclusive_orders=True
    )

    print("\nRunning backtest...")
    stats = bt.run()

    print("\n" + "="*80)
    print("STRATEGY: Fibonacci Volume Profile Enhanced")
    print("="*80)
    print(stats)
    print("="*80)

    return bt, stats


if __name__ == "__main__":
    bt, stats = run_backtest()

    # Optional: Plot results
    try:
        bt.plot()
    except Exception as e:
        print(f"\nNote: Could not generate plot: {e}")
