"""
Enhanced Strategy: Pivot Trend [ChartPrime]
Original Pine Script: AOTPWbpq-Pivot-Trend-ChartPrime.pine
Enhanced with Risk Management

Converted: 2026-01-04

Strategy Logic:
- Uses 200-period ATR for volatility measurement
- Detects Pivot Highs and Pivot Lows with ATR offset
- Determines trend based on price position relative to pivot bands
- Buy Signal: Trend crosses above 0 (from -1 to +1)
- Sell Signal: Trend crosses below 0 (from +1 to -1)
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for risk_management_patterns
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from risk_management_patterns import EnhancedRiskManagementMixin


class PivotTrendEnhanced(Strategy, EnhancedRiskManagementMixin):
    """
    Pivot Trend Strategy with Enhanced Risk Management

    Indicators:
    - ATR (200 periods)
    - Pivot High/Low detection with ATR offset

    Entry Signals:
    - Long: Trend crosses above 0 (bearish to bullish)
    - Short: Trend crosses below 0 (bullish to bearish)
    """

    # Pine Script Parameters
    left_bars = 10
    right_bars = 10
    offset = 2.0
    atr_period = 200

    # Risk Management Parameters
    use_fixed_sl = False
    use_atr_sl = True
    use_rr_tp = True
    use_trailing_stop = True

    sl_percent = 5.0
    atr_sl_multiplier = 2.0  # Using offset value
    rr_ratio = 2.0
    trailing_activation = 5.0
    trailing_percent = 3.0

    def init(self):
        """Initialize indicators and risk management"""
        self.init_risk_management()

        close = self.data.Close
        high = self.data.High
        low = self.data.Low

        # ATR calculation
        self.atr = self.I(self._calc_atr, high, low, close, self.atr_period)

        # Pivot High and Low detection
        self.pivot_high = self.I(self._detect_pivot_high, high, self.atr,
                                  self.left_bars, self.right_bars, self.offset)
        self.pivot_low = self.I(self._detect_pivot_low, low, self.atr,
                                 self.left_bars, self.right_bars, self.offset)

        # Upper and Lower Bands (last valid pivot values)
        self.upper_band = self.I(self._forward_fill, self.pivot_high)
        self.lower_band = self.I(self._forward_fill, self.pivot_low)

        # Trend calculation
        self.trend = self.I(self._calc_trend, close, self.upper_band, self.lower_band)

    def next(self):
        """Execute strategy logic"""
        # Need at least enough bars for pivot detection
        min_bars = max(self.left_bars, self.right_bars) + self.atr_period + 1
        if len(self.data) < min_bars:
            return

        # Get current and previous trend
        current_trend = self.trend[-1]
        prev_trend = self.trend[-2] if len(self.trend) > 1 else 0

        # Check for valid trend values
        if np.isnan(current_trend) or np.isnan(prev_trend):
            self.manage_risk()
            return

        # Entry Logic
        if not self.position:
            # Buy Signal: Trend crosses above 0 (from -1 to +1)
            if prev_trend <= 0 and current_trend > 0:
                self.buy()

            # Sell Signal: Trend crosses below 0 (from +1 to -1)
            elif prev_trend >= 0 and current_trend < 0:
                self.sell()

        else:
            # Exit Logic: Opposite trend signal
            if self.position.is_long and current_trend < 0:
                self.position.close()
            elif self.position.is_short and current_trend > 0:
                self.position.close()

        # Risk management (MUST be at end)
        self.manage_risk()

    @staticmethod
    def _calc_atr(high, low, close, period):
        """Calculate Average True Range"""
        high = pd.Series(high, dtype=float)
        low = pd.Series(low, dtype=float)
        close = pd.Series(close, dtype=float)

        # True Range calculation
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR is RMA (Rolling Mean) of TR
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        return atr.values

    @staticmethod
    def _detect_pivot_high(high, atr, left_bars, right_bars, offset):
        """
        Detect Pivot Highs
        Pine Script: ta.pivothigh(high + atr * Offset, left_bars, right_bars)

        Returns the pivot high value at the pivot point, NaN elsewhere
        """
        high = pd.Series(high, dtype=float)
        atr = pd.Series(atr, dtype=float)

        # Adjust high with ATR offset
        adjusted_high = high + atr * offset
        pivot_high = pd.Series(np.nan, index=high.index)

        # Need enough bars on both sides
        total_window = left_bars + right_bars + 1

        for i in range(left_bars, len(adjusted_high) - right_bars):
            center_val = adjusted_high.iloc[i]

            # Check if center is highest in the window
            left_window = adjusted_high.iloc[i - left_bars:i]
            right_window = adjusted_high.iloc[i + 1:i + right_bars + 1]

            is_pivot = True

            # Center must be higher than all left bars
            if len(left_window) > 0 and (left_window >= center_val).any():
                is_pivot = False

            # Center must be higher than all right bars
            if len(right_window) > 0 and (right_window >= center_val).any():
                is_pivot = False

            if is_pivot:
                # Return the original high value (not adjusted)
                pivot_high.iloc[i] = high.iloc[i]

        return pivot_high.values

    @staticmethod
    def _detect_pivot_low(low, atr, left_bars, right_bars, offset):
        """
        Detect Pivot Lows
        Pine Script: ta.pivotlow(low - atr * Offset, left_bars, right_bars)

        Returns the pivot low value at the pivot point, NaN elsewhere
        """
        low = pd.Series(low, dtype=float)
        atr = pd.Series(atr, dtype=float)

        # Adjust low with ATR offset
        adjusted_low = low - atr * offset
        pivot_low = pd.Series(np.nan, index=low.index)

        # Need enough bars on both sides
        total_window = left_bars + right_bars + 1

        for i in range(left_bars, len(adjusted_low) - right_bars):
            center_val = adjusted_low.iloc[i]

            # Check if center is lowest in the window
            left_window = adjusted_low.iloc[i - left_bars:i]
            right_window = adjusted_low.iloc[i + 1:i + right_bars + 1]

            is_pivot = True

            # Center must be lower than all left bars
            if len(left_window) > 0 and (left_window <= center_val).any():
                is_pivot = False

            # Center must be lower than all right bars
            if len(right_window) > 0 and (right_window <= center_val).any():
                is_pivot = False

            if is_pivot:
                # Return the original low value (not adjusted)
                pivot_low.iloc[i] = low.iloc[i]

        return pivot_low.values

    @staticmethod
    def _forward_fill(series):
        """
        Forward fill NaN values (equivalent to Pine Script's var and if bool(p_high))
        """
        s = pd.Series(series, dtype=float)
        return s.ffill().values

    @staticmethod
    def _calc_trend(close, upper_band, lower_band):
        """
        Calculate trend based on Pine Script logic:

        if prevTrend == prevUpperBand:
            trend := close > upperBand ? 1 : -1
        else:
            trend := close < lowerBand ? -1 : 1

        Trend value is set based on the relationship between close and bands
        """
        close = pd.Series(close, dtype=float)
        upper_band = pd.Series(upper_band, dtype=float)
        lower_band = pd.Series(lower_band, dtype=float)

        # Initialize trend series
        trend = pd.Series(np.nan, index=close.index)
        trend_value = pd.Series(np.nan, index=close.index)

        # Start with initial trend
        if len(close) > 0:
            if close.iloc[0] > upper_band.iloc[0]:
                trend.iloc[0] = 1
                trend_value.iloc[0] = lower_band.iloc[0]
            elif close.iloc[0] < lower_band.iloc[0]:
                trend.iloc[0] = -1
                trend_value.iloc[0] = upper_band.iloc[0]
            else:
                trend.iloc[0] = 1
                trend_value.iloc[0] = lower_band.iloc[0]

        # Calculate trend for each bar
        for i in range(1, len(close)):
            prev_trend_val = trend_value.iloc[i - 1]
            prev_upper = upper_band.iloc[i - 1]
            prev_lower = lower_band.iloc[i - 1]

            curr_close = close.iloc[i]
            curr_upper = upper_band.iloc[i]
            curr_lower = lower_band.iloc[i]

            # Pine Script logic
            if np.isnan(prev_trend_val):
                # Default to uptrend if no previous trend
                if curr_close > curr_upper:
                    trend.iloc[i] = 1
                elif curr_close < curr_lower:
                    trend.iloc[i] = -1
                else:
                    trend.iloc[i] = 1
            elif abs(prev_trend_val - prev_upper) < 1e-6:  # prevTrend == prevUpperBand
                # Was in downtrend
                if curr_close > curr_upper:
                    trend.iloc[i] = 1
                else:
                    trend.iloc[i] = -1
            else:  # prevTrend == prevLowerBand
                # Was in uptrend
                if curr_close < curr_lower:
                    trend.iloc[i] = -1
                else:
                    trend.iloc[i] = 1

            # Set trend value
            if trend.iloc[i] == 1:
                trend_value.iloc[i] = curr_lower
            elif trend.iloc[i] == -1:
                trend_value.iloc[i] = curr_upper

        return trend.values


def run_backtest():
    """Run backtest with BTC data"""
    import sys
    sys.path.append('/Users/mr.joo/Desktop/전략연구소')

    # Load data (1h timeframe)
    data_path = '/Users/mr.joo/Desktop/전략연구소/trading-agent-system/data/datasets/BTCUSDT_1h.parquet'
    df = pd.read_parquet(data_path)

    # Ensure column names are capitalized
    df.columns = [col.capitalize() for col in df.columns]

    # Print data info
    print(f"Data shape: {df.shape}")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    print(f"Columns: {df.columns.tolist()}")

    # Run backtest
    bt = Backtest(
        df,
        PivotTrendEnhanced,
        cash=100000,
        commission=0.001,
        exclusive_orders=True
    )

    stats = bt.run()
    print("\n" + "="*50)
    print("BACKTEST RESULTS - Pivot Trend Enhanced")
    print("="*50)
    print(stats)
    print("="*50)

    # Plot results
    try:
        bt.plot()
    except Exception as e:
        print(f"Plotting failed: {e}")

    return stats


if __name__ == '__main__':
    stats = run_backtest()
