#!/usr/bin/env python3
"""
Compare PMax strategy with and without stop loss
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "trading-agent-system"))

from backtesting import Backtest
import pandas as pd

from strategies.pmax_asymmetric import PMaxAsymmetric
from strategies.pmax_asymmetric_no_sl import PMaxAsymmetricNoSL


def run_backtest(strategy_class, strategy_name, df):
    """Run backtest and return stats"""
    bt = Backtest(
        df,
        strategy_class,
        cash=10_000_000,
        commission=0.0003,
        exclusive_orders=True
    )
    stats = bt.run()

    print(f"\n{'='*70}")
    print(f"{strategy_name}")
    print(f"{'='*70}")
    print(f"Return [%]:           {stats['Return [%]']:.2f}%")
    print(f"Sharpe Ratio:         {stats['Sharpe Ratio']:.2f}")
    print(f"Sortino Ratio:        {stats['Sortino Ratio']:.2f}")
    print(f"Max Drawdown [%]:     {stats['Max. Drawdown [%]']:.2f}%")
    print(f"Win Rate [%]:         {stats['Win Rate [%]']:.2f}%")
    print(f"Profit Factor:        {stats.get('Profit Factor', 0):.2f}")
    print(f"# Trades:             {stats['# Trades']}")
    print(f"Avg Trade [%]:        {stats['Avg. Trade [%]']:.2f}%")
    print(f"Avg Trade Duration:   {stats['Avg. Trade Duration']}")
    print(f"-"*70)

    # Moon Dev criteria
    sharpe_pass = '✅' if stats['Sharpe Ratio'] > 1.5 else '❌'
    dd_pass = '✅' if stats['Max. Drawdown [%]'] < 30 else '❌'
    wr_pass = '✅' if stats['Win Rate [%]'] > 40 else '❌'
    pf_pass = '✅' if stats.get('Profit Factor', 0) > 1.5 else '❌'

    print(f"Moon Dev Criteria:")
    print(f"  {sharpe_pass} Sharpe > 1.5:     {stats['Sharpe Ratio']:.2f}")
    print(f"  {dd_pass} MaxDD < 30%:      {stats['Max. Drawdown [%]']:.2f}%")
    print(f"  {wr_pass} WinRate > 40%:    {stats['Win Rate [%]']:.2f}%")
    print(f"  {pf_pass} PF > 1.5:         {stats.get('Profit Factor', 0):.2f}")

    passed = all([
        stats['Sharpe Ratio'] > 1.5,
        stats['Max. Drawdown [%]'] < 30,
        stats['Win Rate [%]'] > 40,
        stats.get('Profit Factor', 0) > 1.5
    ])

    if passed:
        print(f"\n🎯 PASSES ALL MOON DEV CRITERIA!")

    return stats


def main():
    # Load data
    data_file = Path(__file__).parent / "trading-agent-system/data/datasets/BTCUSDT_1h.parquet"
    df = pd.read_parquet(data_file)

    print("="*70)
    print("PMax Strategy Comparison: With vs Without Stop Loss")
    print("="*70)
    print(f"Symbol: BTCUSDT")
    print(f"Timeframe: 1h")
    print(f"Period: {df.index[0]} to {df.index[-1]}")
    print(f"Bars: {len(df):,}")

    # Test both versions
    stats_with_sl = run_backtest(PMaxAsymmetric, "PMax with 5% Stop Loss", df)
    stats_no_sl = run_backtest(PMaxAsymmetricNoSL, "PMax without Stop Loss", df)

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY COMPARISON")
    print(f"{'='*70}")
    print(f"{'Metric':<25} {'With 5% SL':<20} {'No SL':<20}")
    print(f"{'-'*70}")
    print(f"{'Return':<25} {stats_with_sl['Return [%]']:>19.2f}% {stats_no_sl['Return [%]']:>19.2f}%")
    print(f"{'Sharpe Ratio':<25} {stats_with_sl['Sharpe Ratio']:>20.2f} {stats_no_sl['Sharpe Ratio']:>20.2f}")
    print(f"{'Max Drawdown':<25} {stats_with_sl['Max. Drawdown [%]']:>19.2f}% {stats_no_sl['Max. Drawdown [%]']:>19.2f}%")
    print(f"{'Win Rate':<25} {stats_with_sl['Win Rate [%]']:>19.2f}% {stats_no_sl['Win Rate [%]']:>19.2f}%")
    print(f"{'Profit Factor':<25} {stats_with_sl.get('Profit Factor', 0):>20.2f} {stats_no_sl.get('Profit Factor', 0):>20.2f}")
    print(f"{'# Trades':<25} {stats_with_sl['# Trades']:>20} {stats_no_sl['# Trades']:>20}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
