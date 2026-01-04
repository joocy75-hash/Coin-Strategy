#!/usr/bin/env python3
"""
Test PMax Asymmetric strategy on a single dataset
"""
import sys
from pathlib import Path

# Add trading-agent-system to path
sys.path.insert(0, str(Path(__file__).parent / "trading-agent-system"))

from backtesting import Backtest
import pandas as pd

# Import the converted strategy
from strategies.pmax_asymmetric import PMaxAsymmetric


def main():
    # Load BTCUSDT 1h dataset
    data_file = Path(__file__).parent / "trading-agent-system/data/datasets/BTCUSDT_1h.parquet"

    print(f"Loading data: {data_file}")
    df = pd.read_parquet(data_file)

    print(f"Dataset shape: {df.shape}")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    print(f"\nFirst few rows:")
    print(df.head())

    # Initialize backtest
    bt = Backtest(
        df,
        PMaxAsymmetric,
        cash=10_000_000,  # 10M to avoid fractional trading
        commission=0.0003,  # 0.03%
        exclusive_orders=True
    )

    print("\n" + "=" * 70)
    print("Running PMax Asymmetric Strategy Backtest")
    print("=" * 70)

    # Run backtest
    stats = bt.run()

    print("\n" + "=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)
    print(f"Strategy: PMax - Asymmetric Multipliers")
    print(f"Symbol: BTCUSDT")
    print(f"Timeframe: 1h")
    print(f"Period: {df.index[0]} to {df.index[-1]}")
    print("-" * 70)
    print(f"Return [%]:           {stats['Return [%]']:.2f}%")
    print(f"Sharpe Ratio:         {stats['Sharpe Ratio']:.2f}")
    print(f"Sortino Ratio:        {stats['Sortino Ratio']:.2f}")
    print(f"Max Drawdown [%]:     {stats['Max. Drawdown [%]']:.2f}%")
    print(f"Win Rate [%]:         {stats['Win Rate [%]']:.2f}%")
    print(f"# Trades:             {stats['# Trades']}")
    print(f"Avg Trade [%]:        {stats['Avg. Trade [%]']:.2f}%")
    print(f"Max Trade Duration:   {stats['Max. Trade Duration']}")
    print(f"Avg Trade Duration:   {stats['Avg. Trade Duration']}")
    print("-" * 70)

    # Moon Dev criteria check
    print("\nMoon Dev Criteria Check:")
    print(f"✓ Sharpe Ratio > 1.5:       {'✅ PASS' if stats['Sharpe Ratio'] > 1.5 else '❌ FAIL'} ({stats['Sharpe Ratio']:.2f})")
    print(f"✓ Max Drawdown < 30%:       {'✅ PASS' if stats['Max. Drawdown [%]'] < 30 else '❌ FAIL'} ({stats['Max. Drawdown [%]']:.2f}%)")
    print(f"✓ Win Rate > 40%:           {'✅ PASS' if stats['Win Rate [%]'] > 40 else '❌ FAIL'} ({stats['Win Rate [%]']:.2f}%)")

    print("=" * 70)

    # Generate and save HTML report
    output_file = Path(__file__).parent / "pmax_backtest_result.html"
    print(f"\nGenerating HTML report: {output_file}")
    bt.plot(filename=str(output_file), open_browser=False)
    print(f"✅ Report saved!")


if __name__ == "__main__":
    main()
