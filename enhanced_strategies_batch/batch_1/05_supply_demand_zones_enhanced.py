"""
Enhanced Strategy: Supply and Demand Zones [BigBeluga]
Original Pine Script: I0o8N7VW-Supply-and-Demand-Zones-BigBeluga.pine
Enhanced with Risk Management

Converted: 2026-01-04

Strategy Logic:
- Detects supply zones (3 consecutive bear candles + high volume)
- Detects demand zones (3 consecutive bull candles + high volume)
- Zones are drawn from reversal point with ATR-based height
- Buy Signal: Price enters demand zone from above
- Sell Signal: Price enters supply zone from below
- Zones are deleted when broken
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for risk_management_patterns
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from risk_management_patterns import EnhancedRiskManagementMixin


class SupplyDemandZonesEnhanced(Strategy, EnhancedRiskManagementMixin):
    """
    Supply & Demand Zones Strategy with Enhanced Risk Management

    Indicators:
    - Volume spike detection (above average)
    - ATR-based zone sizing (2x ATR 200)
    - Consecutive candle patterns

    Entry Signals:
    - Long: Price enters demand zone (bullish reversal area)
    - Short: Price enters supply zone (bearish reversal area)
    """

    # Pine Script Parameters
    atr_period = 200
    atr_multiplier = 2.0
    volume_window = 1000
    cooldown_bars = 15

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
        open_ = self.data.Open
        volume = self.data.Volume

        # ATR for zone sizing
        self.atr = self.I(self._calc_atr, high, low, close, self.atr_period)

        # Volume analysis
        self.avg_volume = self.I(lambda x: pd.Series(x).rolling(20).mean(), volume)

        # Candle type
        self.is_bull_candle = self.I(lambda c, o: (c > o).astype(int), close, open_)
        self.is_bear_candle = self.I(lambda c, o: (c < o).astype(int), close, open_)

        # Zone tracking
        self.supply_zones = []
        self.demand_zones = []
        self.supply_cooldown = 0
        self.demand_cooldown = 0

    def next(self):
        """Execute strategy logic"""
        min_bars = max(self.atr_period, 50)
        if len(self.data) < min_bars:
            return

        # Current values
        idx = len(self.data) - 1
        close = self.data.Close[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[-1]
        atr = self.atr[-1] * self.atr_multiplier

        # Volume spike check
        extra_vol = volume > avg_vol if not np.isnan(avg_vol) else False

        # Check for 3 consecutive bear candles + volume spike
        if (self.is_bear_candle[-1] and
            self.is_bear_candle[-2] and
            self.is_bear_candle[-3] and
            extra_vol and
            self.supply_cooldown == 0):

            # Look back for bullish reversal candle
            for i in range(1, 6):
                if len(self.data) > i and self.is_bull_candle[-i]:
                    # Create supply zone
                    zone_low = self.data.Low[-i]
                    zone_high = zone_low + atr
                    self.supply_zones.append({
                        'top': zone_high,
                        'bottom': zone_low,
                        'bar': idx - i
                    })
                    self.supply_cooldown = self.cooldown_bars
                    break

        # Check for 3 consecutive bull candles + volume spike
        if (self.is_bull_candle[-1] and
            self.is_bull_candle[-2] and
            self.is_bull_candle[-3] and
            extra_vol and
            self.demand_cooldown == 0):

            # Look back for bearish reversal candle
            for i in range(1, 6):
                if len(self.data) > i and self.is_bear_candle[-i]:
                    # Create demand zone
                    zone_high = self.data.High[-i]
                    zone_low = zone_high - atr
                    self.demand_zones.append({
                        'top': zone_high,
                        'bottom': zone_low,
                        'bar': idx - i
                    })
                    self.demand_cooldown = self.cooldown_bars
                    break

        # Decrement cooldowns
        if self.supply_cooldown > 0:
            self.supply_cooldown -= 1
        if self.demand_cooldown > 0:
            self.demand_cooldown -= 1

        # Clean up broken zones and check for entries
        self._process_zones(close, high, low, idx)

        # Risk management
        self.manage_risk()

    def _process_zones(self, close, high, low, current_bar):
        """Process zones for breakouts and entries"""
        # Process supply zones
        zones_to_remove = []
        for i, zone in enumerate(self.supply_zones):
            # Delete if price closes above zone (broken)
            if close > zone['top']:
                zones_to_remove.append(i)
                continue

            # Entry signal: price enters zone from below
            # Only if zone is "mature" (at least 20 bars old)
            zone_age = current_bar - zone['bar']
            if (zone_age > 20 and
                not self.position and
                low <= zone['top'] and
                high >= zone['bottom']):
                # Price is in supply zone - sell signal
                self.sell()

        # Remove broken zones
        for i in reversed(zones_to_remove):
            self.supply_zones.pop(i)

        # Limit supply zones
        if len(self.supply_zones) > 5:
            self.supply_zones = self.supply_zones[-5:]

        # Process demand zones
        zones_to_remove = []
        for i, zone in enumerate(self.demand_zones):
            # Delete if price closes below zone (broken)
            if close < zone['bottom']:
                zones_to_remove.append(i)
                continue

            # Entry signal: price enters zone from above
            zone_age = current_bar - zone['bar']
            if (zone_age > 20 and
                not self.position and
                high >= zone['bottom'] and
                low <= zone['top']):
                # Price is in demand zone - buy signal
                self.buy()

        # Remove broken zones
        for i in reversed(zones_to_remove):
            self.demand_zones.pop(i)

        # Limit demand zones
        if len(self.demand_zones) > 5:
            self.demand_zones = self.demand_zones[-5:]

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
        SupplyDemandZonesEnhanced,
        cash=100000,
        commission=0.001,
        exclusive_orders=True
    )

    print("\nRunning backtest...")
    stats = bt.run()

    print("\n" + "="*80)
    print("STRATEGY: Supply & Demand Zones Enhanced")
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
