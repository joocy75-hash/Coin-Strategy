"""
Heikin Ashi Wick Strategy Multi-Dataset Backtest
Tests across 10 different symbol/timeframe combinations
"""

import sys
sys.path.append('/Users/mr.joo/Desktop/전략연구소/trading-agent-system')

from backtesting import Backtest
from strategies.heikin_ashi_wick import HeikinAshiWick
from src.data.binance_collector import BinanceDataCollector
import pandas as pd

def run_multi_dataset_backtest():
    """Run backtest across 10 different datasets."""

    # Initialize data collector
    collector = BinanceDataCollector(data_dir='/Users/mr.joo/Desktop/전략연구소/trading-agent-system/data/datasets')

    # Define 10 test datasets (same as PMax test)
    datasets = [
        ('BTCUSDT', '1h'),
        ('BTCUSDT', '4h'),
        ('ETHUSDT', '1h'),
        ('ETHUSDT', '4h'),
        ('SOLUSDT', '1h'),
        ('SOLUSDT', '4h'),
        ('BNBUSDT', '1h'),
        ('BNBUSDT', '4h'),
        ('ADAUSDT', '4h'),
        ('DOGEUSDT', '4h'),
    ]

    print("=" * 80)
    print("HEIKIN ASHI WICK STRATEGY - MULTI-DATASET BACKTEST")
    print("=" * 80)
    print(f"\nTesting {len(datasets)} different symbol/timeframe combinations")
    print(f"Strategy: Heikin Ashi Wick (5% Stop Loss)")
    print("\n" + "=" * 80 + "\n")

    results = []

    for symbol, timeframe in datasets:
        try:
            # Load data
            df = collector.load_dataset(symbol, timeframe)

            if df is None or len(df) < 100:
                print(f"❌ Skipping {symbol} {timeframe}: Insufficient data")
                continue

            print(f"\n📊 Testing {symbol} {timeframe}")
            print(f"   Data: {len(df)} rows ({df.index[0]} to {df.index[-1]})")

            # Run backtest
            bt = Backtest(
                df,
                HeikinAshiWick,
                cash=100000,
                commission=0.0003,  # 0.03%
                exclusive_orders=True
            )

            stats = bt.run()

            # Store results
            result = {
                'Symbol': symbol,
                'Timeframe': timeframe,
                'Return%': round(stats['Return [%]'], 2),
                'Sharpe': round(stats['Sharpe Ratio'], 2),
                'MaxDD%': round(stats['Max. Drawdown [%]'], 2),
                'WinRate%': round(stats['Win Rate [%]'], 2),
                'PF': round(stats['Profit Factor'], 2),
                '#Trades': stats['# Trades']
            }
            results.append(result)

            # Print summary
            print(f"   ✅ Return: {result['Return%']:.2f}% | Sharpe: {result['Sharpe']:.2f} | "
                  f"MaxDD: {result['MaxDD%']:.2f}% | Trades: {result['#Trades']}")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            continue

    # Print summary table
    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)

    if results:
        df_results = pd.DataFrame(results)

        # Print table
        print("\n" + df_results.to_string(index=False))

        # Print aggregated statistics
        print("\n" + "=" * 80)
        print("AGGREGATED STATISTICS")
        print("=" * 80)

        avg_return = df_results['Return%'].mean()
        avg_sharpe = df_results['Sharpe'].mean()
        avg_winrate = df_results['WinRate%'].mean()
        avg_pf = df_results['PF'].mean()
        total_trades = df_results['#Trades'].sum()

        print(f"\nAverage Return:    {avg_return:.2f}%")
        print(f"Average Sharpe:    {avg_sharpe:.2f}")
        print(f"Average Win Rate:  {avg_winrate:.2f}%")
        print(f"Average PF:        {avg_pf:.2f}")
        print(f"Total Trades:      {total_trades}")

        # Moon Dev criteria check
        print("\n" + "=" * 80)
        print("MOON DEV CRITERIA CHECK")
        print("=" * 80)

        criteria = {
            'Sharpe Ratio > 1.5': avg_sharpe > 1.5,
            'Win Rate > 40%': avg_winrate > 40,
            'Profit Factor > 1.5': avg_pf > 1.5,
            'Total Trades > 100': total_trades > 100
        }

        for criterion, passed in criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{criterion:.<50} {status}")

        passed_all = all(criteria.values())
        print("\n" + "=" * 80)
        if passed_all:
            print("🎉 STRATEGY PASSES ALL MOON DEV CRITERIA!")
        else:
            print("⚠️  STRATEGY DOES NOT MEET MOON DEV CRITERIA")
        print("=" * 80)

        # Save results to CSV
        csv_path = '/Users/mr.joo/Desktop/전략연구소/heikin_ashi_results.csv'
        df_results.to_csv(csv_path, index=False)
        print(f"\n📁 Results saved to: {csv_path}")

    else:
        print("\n❌ No successful backtests completed")


if __name__ == "__main__":
    run_multi_dataset_backtest()
