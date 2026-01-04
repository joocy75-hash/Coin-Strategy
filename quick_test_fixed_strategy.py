#!/usr/bin/env python3
"""
Quick Test: Verify Fixed Adaptive ML Strategy
Tests that the bug fix allows trades to execute and metrics to be calculated.
"""

import sys
sys.path.append('/Users/mr.joo/Desktop/전략연구소/trading-agent-system')

import pandas as pd
from backtesting import Backtest
from strategies.adaptive_ml_trailing_stop import AdaptiveMLTrailingStop

def main():
    print("=" * 80)
    print("QUICK TEST: Fixed Adaptive ML Trailing Stop Strategy")
    print("=" * 80)

    # Load sample dataset
    print("\n1. Loading dataset...")
    data_path = '/Users/mr.joo/Desktop/전략연구소/trading-agent-system/data/datasets/BTCUSDT_1h.parquet'
    data = pd.read_parquet(data_path)
    print(f"   ✓ Loaded {len(data)} rows (BTCUSDT 1h)")

    # Run backtest
    print("\n2. Running backtest...")

    # BUGFIX: Validate cash vs asset price
    first_price = data.iloc[0]['Close']
    required_cash = first_price * 2  # Need 2x price minimum
    initial_cash = max(100000, required_cash)  # Use at least $100k
    print(f"   Asset price: ${first_price:,.2f}, Using cash: ${initial_cash:,.2f}")

    bt = Backtest(
        data,
        AdaptiveMLTrailingStop,
        cash=initial_cash,
        commission=0.0003
    )

    stats = bt.run()

    # Display results
    print("\n3. Results:")
    print("=" * 80)

    # Critical metrics
    num_trades = stats['# Trades']
    sharpe = stats['Sharpe Ratio']
    win_rate = stats['Win Rate [%]']
    profit_factor = stats.get('Profit Factor', 'N/A')
    total_return = stats['Return [%]']
    max_dd = stats['Max. Drawdown [%]']

    print(f"# Trades:        {num_trades}")
    print(f"Sharpe Ratio:    {sharpe:.4f}" if pd.notna(sharpe) else f"Sharpe Ratio:    NaN")
    print(f"Win Rate:        {win_rate:.2f}%" if pd.notna(win_rate) else f"Win Rate:        NaN%")
    print(f"Profit Factor:   {profit_factor}")
    print(f"Return:          {total_return:.2f}%")
    print(f"Max Drawdown:    {max_dd:.2f}%")

    # Verification
    print("\n4. Verification:")
    print("=" * 80)

    success = True

    if num_trades == 0:
        print("❌ FAILED: No trades executed (bug still present)")
        success = False
    else:
        print(f"✅ PASSED: {num_trades} trades executed")

    if pd.isna(sharpe):
        print("❌ FAILED: Sharpe Ratio is NaN")
        success = False
    else:
        print(f"✅ PASSED: Sharpe Ratio calculated ({sharpe:.4f})")

    if pd.isna(win_rate):
        print("❌ FAILED: Win Rate is NaN")
        success = False
    else:
        print(f"✅ PASSED: Win Rate calculated ({win_rate:.2f}%)")

    print("\n" + "=" * 80)
    if success:
        print("🎉 SUCCESS: Bug fix verified! Strategy now executes trades.")
        print("\nReady to proceed with Moon Dev optimization.")
    else:
        print("⚠️  WARNING: Some issues remain. Review strategy code.")
    print("=" * 80)

    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
