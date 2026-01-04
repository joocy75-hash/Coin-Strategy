#!/usr/bin/env python3
"""
Test PMax strategy on multiple datasets (different symbols and timeframes)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "trading-agent-system"))

from backtesting import Backtest
import pandas as pd

from strategies.pmax_asymmetric import PMaxAsymmetric


def run_backtest(data_file):
    """Run backtest on a single dataset"""
    df = pd.read_parquet(data_file)

    bt = Backtest(
        df,
        PMaxAsymmetric,
        cash=10_000_000,
        commission=0.0003,
        exclusive_orders=True
    )

    stats = bt.run()

    # Extract symbol and timeframe from filename
    filename = data_file.stem  # e.g., "BTCUSDT_4h"
    symbol, timeframe = filename.split('_')

    return {
        'Symbol': symbol,
        'Timeframe': timeframe,
        'Return': stats['Return [%]'],
        'Sharpe': stats['Sharpe Ratio'],
        'Sortino': stats['Sortino Ratio'],
        'MaxDD': stats['Max. Drawdown [%]'],
        'WinRate': stats['Win Rate [%]'],
        'ProfitFactor': stats.get('Profit Factor', 0),
        'Trades': stats['# Trades'],
        'AvgTrade': stats['Avg. Trade [%]'],
    }


def main():
    data_dir = Path(__file__).parent / "trading-agent-system/data/datasets"

    # Test on various datasets
    test_files = [
        "BTCUSDT_1h.parquet",
        "BTCUSDT_4h.parquet",
        "ETHUSDT_1h.parquet",
        "ETHUSDT_4h.parquet",
        "SOLUSDT_1h.parquet",
        "SOLUSDT_4h.parquet",
        "BNBUSDT_1h.parquet",
        "BNBUSDT_4h.parquet",
        "ADAUSDT_4h.parquet",
        "DOGEUSDT_4h.parquet",
    ]

    results = []

    print("="*100)
    print("PMax Strategy - Multi-Dataset Backtest")
    print("="*100)
    print()

    for filename in test_files:
        file_path = data_dir / filename

        if not file_path.exists():
            print(f"⚠️  Skipping {filename} (not found)")
            continue

        print(f"Testing: {filename}...", end=" ", flush=True)

        try:
            result = run_backtest(file_path)
            results.append(result)
            print(f"✅ Return: {result['Return']:.2f}%, Sharpe: {result['Sharpe']:.2f}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")

    # Summary table
    if results:
        print()
        print("="*100)
        print("RESULTS SUMMARY")
        print("="*100)

        # Header
        print(f"{'Symbol':<10} {'TF':<6} {'Return%':>10} {'Sharpe':>8} {'MaxDD%':>10} {'WinRate%':>10} {'PF':>8} {'#Trades':>8}")
        print("-"*100)

        # Results
        for r in results:
            print(f"{r['Symbol']:<10} {r['Timeframe']:<6} {r['Return']:>10.2f} {r['Sharpe']:>8.2f} {r['MaxDD']:>10.2f} {r['WinRate']:>10.2f} {r['ProfitFactor']:>8.2f} {r['Trades']:>8}")

        # Statistics
        avg_return = sum(r['Return'] for r in results) / len(results)
        avg_sharpe = sum(r['Sharpe'] for r in results) / len(results)
        avg_winrate = sum(r['WinRate'] for r in results) / len(results)
        avg_pf = sum(r['ProfitFactor'] for r in results) / len(results)

        print("-"*100)
        print(f"{'AVERAGE':<10} {'':<6} {avg_return:>10.2f} {avg_sharpe:>8.2f} {'':<10} {avg_winrate:>10.2f} {avg_pf:>8.2f} {'':<8}")
        print("="*100)

        # Moon Dev criteria check
        print()
        print("Moon Dev Criteria Check on Averages:")
        print(f"  {'✅' if avg_sharpe > 1.5 else '❌'} Sharpe > 1.5:      {avg_sharpe:.2f}")
        print(f"  {'✅' if avg_winrate > 40 else '❌'} Win Rate > 40%:    {avg_winrate:.2f}%")
        print(f"  {'✅' if avg_pf > 1.5 else '❌'} Profit Factor > 1.5: {avg_pf:.2f}")
        print()

        # Best performers
        best_return = max(results, key=lambda x: x['Return'])
        best_sharpe = max(results, key=lambda x: x['Sharpe'])

        print("Best Performers:")
        print(f"  Highest Return:  {best_return['Symbol']} {best_return['Timeframe']} ({best_return['Return']:.2f}%)")
        print(f"  Highest Sharpe:  {best_sharpe['Symbol']} {best_sharpe['Timeframe']} ({best_sharpe['Sharpe']:.2f})")


if __name__ == "__main__":
    main()
