"""
Enhanced Strategy: Structure Lite - Smart Volume & Break of Structure
Original Pine Script: ETN2PyhG-Structure-Lite-Automatic-Major-Trend-Lines.pine
Enhanced with Risk Management

Converted: 2026-01-04

Strategy Logic:
- Detects Pivot Highs and Pivot Lows (Major Support/Resistance)
- Tracks Break of Structure (BOS) with high volume confirmation
- Uses RSI overlay for momentum confirmation
- Buy Signal: Bullish BOS (price crosses above pivot high with high volume)
- Sell Signal: Bearish BOS (price crosses below pivot low with high volume)
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for risk_management_patterns
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from risk_management_patterns import EnhancedRiskManagementMixin


class StructureLiteEnhanced(Strategy, EnhancedRiskManagementMixin):
    """
    Structure Lite Strategy with Enhanced Risk Management

    Indicators:
    - Pivot High/Low detection (20-bar lookback)
    - Volume spike detection (1.5x average)
    - RSI (14 periods)

    Entry Signals:
    - Long: Price breaks above last pivot high with high volume
    - Short: Price breaks below last pivot low with high volume
    """

    # Pine Script Parameters
    pivot_lookback = 20
    volume_threshold = 1.5
    rsi_period = 14

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

        # Volume analysis
        self.avg_volume = self.I(lambda x: pd.Series(x).rolling(20).mean(), volume)

        # RSI
        self.rsi = self.I(self._calc_rsi, close, self.rsi_period)

        # Pivot detection
        self.pivot_high = self.I(self._detect_pivot_high, high,
                                  self.pivot_lookback, self.pivot_lookback)
        self.pivot_low = self.I(self._detect_pivot_low, low,
                                 self.pivot_lookback, self.pivot_lookback)

        # Last known pivots (forward fill)
        self.last_pivot_high = self.I(self._forward_fill, self.pivot_high)
        self.last_pivot_low = self.I(self._forward_fill, self.pivot_low)

    def next(self):
        """Execute strategy logic"""
        min_bars = self.pivot_lookback * 2 + 20
        if len(self.data) < min_bars:
            return

        # Current values
        close = self.data.Close[-1]
        volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[-1]

        # Check for high volume
        is_high_volume = volume > (avg_vol * self.volume_threshold) if not np.isnan(avg_vol) else False

        # Get last pivot levels
        last_ph = self.last_pivot_high[-1]
        last_pl = self.last_pivot_low[-1]
        prev_close = self.data.Close[-2]

        # Entry Logic
        if not self.position:
            # Bullish BOS: Close crosses above last pivot high with high volume
            if (not np.isnan(last_ph) and
                prev_close <= last_ph and
                close > last_ph and
                is_high_volume and
                self.rsi[-1] > 50):  # RSI momentum confirmation
                self.buy()

            # Bearish BOS: Close crosses below last pivot low with high volume
            elif (not np.isnan(last_pl) and
                  prev_close >= last_pl and
                  close < last_pl and
                  is_high_volume and
                  self.rsi[-1] < 50):  # RSI momentum confirmation
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
    def _calc_rsi(close, period):
        """Calculate RSI"""
        close = pd.Series(close)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return (100 - (100 / (1 + rs))).values

    @staticmethod
    def _detect_pivot_high(high, left_bars, right_bars):
        """Detect pivot highs"""
        high_series = pd.Series(high)
        result = np.full(len(high), np.nan)

        for i in range(left_bars, len(high) - right_bars):
            center_val = high_series.iloc[i]
            left_max = high_series.iloc[i - left_bars:i].max()
            right_max = high_series.iloc[i + 1:i + right_bars + 1].max()

            if center_val > left_max and center_val > right_max:
                result[i] = center_val

        return result

    @staticmethod
    def _detect_pivot_low(low, left_bars, right_bars):
        """Detect pivot lows"""
        low_series = pd.Series(low)
        result = np.full(len(low), np.nan)

        for i in range(left_bars, len(low) - right_bars):
            center_val = low_series.iloc[i]
            left_min = low_series.iloc[i - left_bars:i].min()
            right_min = low_series.iloc[i + 1:i + right_bars + 1].min()

            if center_val < left_min and center_val < right_min:
                result[i] = center_val

        return result

    @staticmethod
    def _forward_fill(series):
        """Forward fill NaN values with last valid value"""
        return pd.Series(series).ffill().values


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
        StructureLiteEnhanced,
        cash=100000,
        commission=0.001,
        exclusive_orders=True
    )

    print("\nRunning backtest...")
    stats = bt.run()

    print("\n" + "="*80)
    print("STRATEGY: Structure Lite Enhanced")
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
