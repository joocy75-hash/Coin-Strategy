"""
Enhanced Strategy: AOTPWbpq-Pivot-Trend-ChartPrime
Original Pine Script ID: AOTPWbpq-Pivot-Trend-ChartPrime
Enhanced with Risk Management

Generated: 2026-01-04 05:40:47
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
from risk_management_patterns import EnhancedRiskManagementMixin


class ChartPrime_Enhanced(Strategy, EnhancedRiskManagementMixin):
    """
    Enhanced version with risk management

    Detected Indicators:
    - ATR: 1 instance(s)
    - PIVOT: 2 instance(s)

    Entry Signals:
    - Crossover signals detected
    - Crossunder signals detected
    - Price comparison logic detected
    """

    # Risk Management Parameters (from analysis)
    use_fixed_sl = False
    use_atr_sl = True
    use_rr_tp = True
    use_trailing_stop = True

    sl_percent = 5.0
    atr_sl_multiplier = 2.5
    rr_ratio = 2.0
    trailing_activation = 5.0
    trailing_percent = 3.0

    # Strategy Parameters (TODO: Extract from Pine Script)
    # Add your strategy-specific parameters here

    def init(self):
        """Initialize indicators and risk management"""
        self.init_risk_management()

        # TODO: Initialize indicators based on Pine Script
        # Detected indicators: ['atr', 'pivot']

        # self.atr = self.I(ta.atr, self.data.High, self.data.Low, self.data.Close, length=14)

    def next(self):
        """Execute strategy logic"""
        # TODO: Implement entry/exit logic from Pine Script

        # Example long entry condition (replace with actual logic)
        # if self.some_indicator[-1] > threshold:
        #     if not self.position:
        #         self.buy()

        # Example short entry condition
        # if self.some_indicator[-1] < threshold:
        #     if not self.position:
        #         self.sell()

        # Risk management (KEEP THIS AT END)
        self.manage_risk()


def run_backtest():
    """Run backtest with BTC data"""
    import sys
    sys.path.append('/Users/mr.joo/Desktop/전략연구소')

    # Load data (adjust path as needed)
    data_path = '/Users/mr.joo/Desktop/전략연구소/trading-agent-system/data/btc_data.csv'
    df = pd.read_csv(data_path, index_col=0, parse_dates=True)

    # Ensure column names are capitalized
    df.columns = [col.capitalize() for col in df.columns]

    # Run backtest
    bt = Backtest(
        df,
        ChartPrime_Enhanced,
        cash=100000,
        commission=0.001,
        exclusive_orders=True
    )

    stats = bt.run()
    print(stats)

    # Plot results
    bt.plot()

    return stats


if __name__ == '__main__':
    stats = run_backtest()
