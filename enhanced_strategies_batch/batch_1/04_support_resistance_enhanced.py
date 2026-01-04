"""
Enhanced Strategy: Support and Resistance
Original Pine Script: x0pgNaRA-Support-and-Resistance.pine
Enhanced with Risk Management

Converted: 2026-01-04

Strategy Logic:
- Identifies support and resistance zones using pivot points
- Groups pivots within ATR-based threshold into zones
- Detects breakouts when price crosses zones
- Buy Signal: Price breaks above resistance zone
- Sell Signal: Price breaks below support zone
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for risk_management_patterns
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from risk_management_patterns import EnhancedRiskManagementMixin


class SupportResistanceEnhanced(Strategy, EnhancedRiskManagementMixin):
    """
    Support & Resistance Strategy with Enhanced Risk Management

    Indicators:
    - Pivot High/Low detection (10-bar strength)
    - ATR-based zone clustering
    - Zone tracking with state management

    Entry Signals:
    - Long: Price closes above resistance zone (from below)
    - Short: Price closes below support zone (from above)
    """

    # Pine Script Parameters
    back_bars = 300
    pivot_strength = 10
    min_touches = 2

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

        # ATR for zone threshold
        self.atr = self.I(self._calc_atr, high, low, close, 14)

        # Pivot detection
        self.pivot_high = self.I(self._detect_pivot_high, high,
                                  self.pivot_strength, self.pivot_strength)
        self.pivot_low = self.I(self._detect_pivot_low, low,
                                 self.pivot_strength, self.pivot_strength)

        # Zone arrays (will be populated in next())
        self.zones = []
        self.last_position_side = 0  # 1: above, -1: below, 0: neutral

    def next(self):
        """Execute strategy logic"""
        min_bars = max(self.pivot_strength * 2, 50)
        if len(self.data) < min_bars:
            return

        current_idx = len(self.data) - 1
        threshold = self.atr[-1] if not np.isnan(self.atr[-1]) else 0

        # Update zones with new pivots
        if not np.isnan(self.pivot_high[-1]):
            self._add_to_zones(self.pivot_high[-1], threshold)

        if not np.isnan(self.pivot_low[-1]):
            self._add_to_zones(self.pivot_low[-1], threshold)

        # Check for valid zones (min_touches met)
        valid_zones = [z for z in self.zones if z['count'] >= self.min_touches]

        if not valid_zones:
            self.manage_risk()
            return

        close = self.data.Close[-1]

        # Entry Logic - Check each zone
        for zone in valid_zones:
            top = zone['top']
            bot = zone['bottom']
            prev_state = zone.get('state', 0)

            # Determine current position relative to zone
            if close > top:
                current_state = 1  # Above
            elif close < bot:
                current_state = -1  # Below
            else:
                current_state = 0  # Inside (keep previous state)

            # Update state if not inside
            if current_state != 0:
                zone['state'] = current_state

            # Entry signals - only if crossing from one side to another
            if not self.position:
                # Bullish breakout: was below, now above
                if prev_state == -1 and current_state == 1:
                    self.buy()
                    break

                # Bearish breakdown: was above, now below
                elif prev_state == 1 and current_state == -1:
                    self.sell()
                    break

        # Risk management
        self.manage_risk()

    def _add_to_zones(self, price, threshold):
        """Add pivot to existing zone or create new zone"""
        if threshold <= 0:
            return

        # Try to merge with existing zone
        for zone in self.zones:
            potential_top = max(zone['top'], price)
            potential_bot = min(zone['bottom'], price)

            # If within threshold, merge
            if (potential_top - potential_bot) <= threshold:
                zone['top'] = potential_top
                zone['bottom'] = potential_bot
                zone['count'] += 1
                return

        # Create new zone
        self.zones.append({
            'top': price,
            'bottom': price,
            'count': 1,
            'state': 0  # neutral initially
        })

        # Limit number of zones
        if len(self.zones) > 20:
            self.zones = self.zones[-20:]

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
        SupportResistanceEnhanced,
        cash=100000,
        commission=0.001,
        exclusive_orders=True
    )

    print("\nRunning backtest...")
    stats = bt.run()

    print("\n" + "="*80)
    print("STRATEGY: Support & Resistance Enhanced")
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
