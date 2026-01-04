"""
Enhanced Strategy: Power Hour Trendlines [LuxAlgo]
Original Pine Script: ibJoSrFp-Power-Hour-Trendlines-LuxAlgo.pine
Enhanced with Risk Management

Converted: 2026-01-04

Strategy Logic:
- Collects price data during "Power Hour" (3PM-4PM NY time, 15:00-16:00 UTC-5)
- Fits linear regression trendlines (upper, middle, lower) across multiple sessions
- Uses trendline breakouts for entry signals
- Buy Signal: Price crosses above middle trendline
- Sell Signal: Price crosses below middle trendline
- Note: Time-based filtering simplified for 24/7 crypto markets
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for risk_management_patterns
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from risk_management_patterns import EnhancedRiskManagementMixin


class PowerHourTrendlinesEnhanced(Strategy, EnhancedRiskManagementMixin):
    """
    Power Hour Trendlines Strategy with Enhanced Risk Management

    Indicators:
    - Linear regression trendlines (simplified for crypto)
    - Moving average for trend direction
    - Volume confirmation

    Entry Signals:
    - Long: Price crosses above middle trendline with volume
    - Short: Price crosses below middle trendline with volume

    Note: Original strategy uses NYSE Power Hour (3-4PM ET).
    For 24/7 crypto, we use a simplified trend-following approach.
    """

    # Simplified Parameters (crypto markets are 24/7)
    lookback_period = 100  # Bars to calculate trend
    ma_period = 50

    # Risk Management Parameters
    use_fixed_sl = False
    use_atr_sl = True
    use_rr_tp = True
    use_trailing_stop = True

    sl_percent = 5.0
    atr_sl_multiplier = 2.0
    rr_ratio = 2.0
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

        # Moving averages for trend
        self.ma_fast = self.I(lambda x: pd.Series(x).rolling(20).mean(), close)
        self.ma_slow = self.I(lambda x: pd.Series(x).rolling(50).mean(), close)

        # Volume analysis
        self.avg_volume = self.I(lambda x: pd.Series(x).rolling(20).mean(), volume)

        # Linear regression trendline
        self.middle_line = self.I(self._calc_linear_regression, close, self.lookback_period)

    def next(self):
        """Execute strategy logic"""
        min_bars = max(self.lookback_period, self.ma_period) + 10
        if len(self.data) < min_bars:
            return

        # Current values
        close = self.data.Close[-1]
        prev_close = self.data.Close[-2]
        middle = self.middle_line[-1]
        prev_middle = self.middle_line[-2]
        volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[-1]

        # Skip if invalid values
        if np.isnan(middle) or np.isnan(prev_middle):
            self.manage_risk()
            return

        # Volume confirmation
        has_volume = volume > avg_vol if not np.isnan(avg_vol) else True

        # Trend confirmation from MAs
        is_uptrend = self.ma_fast[-1] > self.ma_slow[-1]
        is_downtrend = self.ma_fast[-1] < self.ma_slow[-1]

        # Entry Logic
        if not self.position:
            # Bullish: Cross above middle line with volume and uptrend
            if (prev_close <= prev_middle and
                close > middle and
                has_volume and
                is_uptrend):
                self.buy()

            # Bearish: Cross below middle line with volume and downtrend
            elif (prev_close >= prev_middle and
                  close < middle and
                  has_volume and
                  is_downtrend):
                self.sell()

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
    def _calc_linear_regression(close, period):
        """Calculate linear regression trendline (middle line)"""
        close_series = pd.Series(close)
        result = np.full(len(close), np.nan)

        for i in range(period, len(close)):
            # Get data window
            y = close_series.iloc[i - period + 1:i + 1].values
            x = np.arange(len(y))

            # Calculate linear regression
            if len(y) > 0 and not np.all(np.isnan(y)):
                # y = ax + b
                x_mean = x.mean()
                y_mean = np.nanmean(y)

                numerator = np.sum((x - x_mean) * (y - y_mean))
                denominator = np.sum((x - x_mean) ** 2)

                if denominator != 0:
                    a = numerator / denominator
                    b = y_mean - a * x_mean

                    # Current value (last point in regression)
                    result[i] = a * (len(y) - 1) + b

        return result


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
        PowerHourTrendlinesEnhanced,
        cash=100000,
        commission=0.001,
        exclusive_orders=True
    )

    print("\nRunning backtest...")
    stats = bt.run()

    print("\n" + "="*80)
    print("STRATEGY: Power Hour Trendlines Enhanced")
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
