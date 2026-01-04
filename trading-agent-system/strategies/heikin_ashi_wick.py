"""
Heikin Ashi Wick Strategy
Converted from Pine Script to backtesting.py format

Strategy Logic:
- Entry: Heikin Ashi green candle + upper wick exists
- Exit: No upper wick OR lower wick dominates (lower_wick > upper_wick)

Commission: 0.03%
Stop Loss: 5% (added for risk management)
"""

from backtesting import Strategy
import pandas as pd
import numpy as np


class HeikinAshiWick(Strategy):
    """
    Heikin Ashi Wick Strategy

    Enters long when:
    - HA candle is green (ha_close > ha_open)
    - Upper wick exists (upper_wick > 0)

    Exits when:
    - No upper wick (upper_wick == 0)
    - OR lower wick dominates (lower_wick > upper_wick)
    """

    # Parameters
    stop_loss_percent = 5.0  # Added for risk management

    def init(self):
        """Initialize Heikin Ashi candles and wick calculations."""
        # Calculate Heikin Ashi candles
        ha_data = self.I(self._calculate_heikin_ashi,
                        self.data.Open,
                        self.data.High,
                        self.data.Low,
                        self.data.Close)

        self.ha_open = ha_data[0]
        self.ha_high = ha_data[1]
        self.ha_low = ha_data[2]
        self.ha_close = ha_data[3]

        # Calculate wicks
        wick_data = self.I(self._calculate_wicks,
                          self.ha_open,
                          self.ha_high,
                          self.ha_low,
                          self.ha_close)

        self.upper_wick = wick_data[0]
        self.lower_wick = wick_data[1]

        # Track entry price for stop loss
        self.entry_price = None

    def _calculate_heikin_ashi(self, open_prices, high_prices, low_prices, close_prices):
        """
        Calculate Heikin Ashi candles.

        Returns:
            Tuple of (ha_open, ha_high, ha_low, ha_close) arrays
        """
        n = len(close_prices)
        ha_close = (open_prices + high_prices + low_prices + close_prices) / 4

        ha_open = np.zeros(n)
        ha_open[0] = (open_prices[0] + close_prices[0]) / 2

        for i in range(1, n):
            ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2

        ha_high = np.maximum(high_prices, np.maximum(ha_open, ha_close))
        ha_low = np.minimum(low_prices, np.minimum(ha_open, ha_close))

        return ha_open, ha_high, ha_low, ha_close

    def _calculate_wicks(self, ha_open, ha_high, ha_low, ha_close):
        """
        Calculate upper and lower wicks of Heikin Ashi candles.

        Returns:
            Tuple of (upper_wick, lower_wick) arrays
        """
        # Upper wick = high - max(open, close)
        upper_wick = ha_high - np.maximum(ha_open, ha_close)

        # Lower wick = min(open, close) - low
        lower_wick = np.minimum(ha_open, ha_close) - ha_low

        return upper_wick, lower_wick

    def next(self):
        """Execute trading logic on each bar."""
        # Skip if we don't have enough data
        if len(self.data) < 2:
            return

        current_idx = len(self.data) - 1

        # Get current HA candle data
        ha_open_cur = self.ha_open[current_idx]
        ha_close_cur = self.ha_close[current_idx]
        upper_wick_cur = self.upper_wick[current_idx]
        lower_wick_cur = self.lower_wick[current_idx]

        # Check if HA candle is green
        ha_green = ha_close_cur > ha_open_cur

        # Entry Logic: HA green + upper wick exists + no position
        if not self.position:
            long_entry = ha_green and upper_wick_cur > 0

            if long_entry:
                self.buy()
                self.entry_price = self.data.Close[-1]

        # Exit Logic: Position exists
        else:
            # Calculate stop loss level
            stop_loss_level = self.entry_price * (1 - self.stop_loss_percent / 100)

            # Exit conditions
            exit_no_upper_wick = upper_wick_cur == 0 or upper_wick_cur < 1e-10
            exit_lower_dominates = lower_wick_cur > upper_wick_cur
            exit_stop_loss = self.data.Close[-1] < stop_loss_level

            if exit_no_upper_wick or exit_lower_dominates or exit_stop_loss:
                self.position.close()
                self.entry_price = None


class HeikinAshiWickNoSL(Strategy):
    """
    Heikin Ashi Wick Strategy (No Stop Loss version)

    Same as HeikinAshiWick but without stop loss for comparison testing.
    """

    def init(self):
        """Initialize Heikin Ashi candles and wick calculations."""
        # Calculate Heikin Ashi candles
        ha_data = self.I(self._calculate_heikin_ashi,
                        self.data.Open,
                        self.data.High,
                        self.data.Low,
                        self.data.Close)

        self.ha_open = ha_data[0]
        self.ha_high = ha_data[1]
        self.ha_low = ha_data[2]
        self.ha_close = ha_data[3]

        # Calculate wicks
        wick_data = self.I(self._calculate_wicks,
                          self.ha_open,
                          self.ha_high,
                          self.ha_low,
                          self.ha_close)

        self.upper_wick = wick_data[0]
        self.lower_wick = wick_data[1]

    def _calculate_heikin_ashi(self, open_prices, high_prices, low_prices, close_prices):
        """Calculate Heikin Ashi candles."""
        n = len(close_prices)
        ha_close = (open_prices + high_prices + low_prices + close_prices) / 4

        ha_open = np.zeros(n)
        ha_open[0] = (open_prices[0] + close_prices[0]) / 2

        for i in range(1, n):
            ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2

        ha_high = np.maximum(high_prices, np.maximum(ha_open, ha_close))
        ha_low = np.minimum(low_prices, np.minimum(ha_open, ha_close))

        return ha_open, ha_high, ha_low, ha_close

    def _calculate_wicks(self, ha_open, ha_high, ha_low, ha_close):
        """Calculate upper and lower wicks."""
        upper_wick = ha_high - np.maximum(ha_open, ha_close)
        lower_wick = np.minimum(ha_open, ha_close) - ha_low

        return upper_wick, lower_wick

    def next(self):
        """Execute trading logic on each bar (no stop loss)."""
        if len(self.data) < 2:
            return

        current_idx = len(self.data) - 1

        ha_open_cur = self.ha_open[current_idx]
        ha_close_cur = self.ha_close[current_idx]
        upper_wick_cur = self.upper_wick[current_idx]
        lower_wick_cur = self.lower_wick[current_idx]

        ha_green = ha_close_cur > ha_open_cur

        # Entry
        if not self.position:
            long_entry = ha_green and upper_wick_cur > 0
            if long_entry:
                self.buy()

        # Exit (no stop loss)
        else:
            exit_no_upper_wick = upper_wick_cur == 0 or upper_wick_cur < 1e-10
            exit_lower_dominates = lower_wick_cur > upper_wick_cur

            if exit_no_upper_wick or exit_lower_dominates:
                self.position.close()
