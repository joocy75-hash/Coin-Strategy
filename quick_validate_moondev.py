"""
Quick Validation Script - Test Current Parameters on New Datasets
===================================================================

Before running full optimization, validate that the strategy works
on the expanded dataset and check baseline performance.

This script:
1. Tests current optimized parameters on 5 new datasets
2. Provides quick performance snapshot
3. Validates data integrity
4. Gives confidence before full optimization

Author: Strategy Research Lab
Date: 2026-01-04
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add strategies directory to path
sys.path.append('/Users/mr.joo/Desktop/전략연구소/trading-agent-system/strategies')

from backtesting import Backtest
from adaptive_ml_trailing_stop import AdaptiveMLTrailingStop


# Configuration
DATA_DIR = Path('/Users/mr.joo/Desktop/전략연구소/trading-agent-system/data/datasets')
COMMISSION = 0.0003
INITIAL_CASH = 10000

# Current optimized parameters (baseline)
CURRENT_PARAMS = {
    'kama_length': 20,
    'fast_length': 15,
    'slow_length': 50,
    'atr_period': 28,
    'base_multiplier': 2.5,
    'adaptive_strength': 1.0,
    'knn_enabled': True,
    'knn_k': 7,
    'knn_lookback': 100,
    'knn_feature_length': 5,
    'knn_weight': 0.2,
    'stop_loss_percent': 5.0,
}

# Test datasets - mix of different asset types
TEST_DATASETS = [
    'LINKUSDT_1h',   # DeFi oracle
    'AVAXUSDT_1h',   # Layer 1 alternative
    'ATOMUSDT_1h',   # Cosmos ecosystem
    'ARBUSDT_1h',    # Layer 2 scaling
    'APTUSDT_1h',    # New Layer 1
]


def load_dataset(dataset_name: str) -> pd.DataFrame:
    """Load parquet dataset."""
    file_path = DATA_DIR / f"{dataset_name}.parquet"
    df = pd.read_parquet(file_path)

    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

    df = df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    })

    return df[['Open', 'High', 'Low', 'Close', 'Volume']]


def run_quick_test(dataset_name: str, params: dict) -> dict:
    """Run single backtest."""
    try:
        data = load_dataset(dataset_name)

        bt = Backtest(
            data,
            AdaptiveMLTrailingStop,
            cash=INITIAL_CASH,
            commission=COMMISSION,
            exclusive_orders=True
        )

        stats = bt.run(**params)

        return {
            'dataset': dataset_name,
            'return': stats['Return [%]'],
            'sharpe': stats['Sharpe Ratio'],
            'win_rate': stats['Win Rate [%]'],
            'profit_factor': stats.get('Profit Factor', 0),
            'max_drawdown': stats['Max. Drawdown [%]'],
            'num_trades': stats['# Trades'],
            'success': True,
        }

    except Exception as e:
        return {
            'dataset': dataset_name,
            'error': str(e),
            'success': False,
        }


def main():
    """Run quick validation."""
    print("="*80)
    print("QUICK VALIDATION - Adaptive ML Trailing Stop")
    print("="*80)
    print(f"\nTesting current optimized parameters on {len(TEST_DATASETS)} new datasets...")
    print(f"Commission: {COMMISSION*100}%")
    print(f"Initial Cash: ${INITIAL_CASH:,.0f}\n")

    print("Current Parameters:")
    for key, value in CURRENT_PARAMS.items():
        print(f"  {key:20s}: {value}")
    print("\n" + "="*80)

    # Run tests
    results = []
    for i, dataset in enumerate(TEST_DATASETS, 1):
        print(f"\n[{i}/{len(TEST_DATASETS)}] Testing {dataset}...")
        result = run_quick_test(dataset, CURRENT_PARAMS)
        results.append(result)

        if result['success']:
            print(f"  Return: {result['return']:+.2f}%")
            print(f"  Sharpe: {result['sharpe']:.3f}")
            print(f"  Win Rate: {result['win_rate']:.1f}%")
            print(f"  Profit Factor: {result['profit_factor']:.2f}")
            print(f"  Max DD: {result['max_drawdown']:.1f}%")
            print(f"  Trades: {result['num_trades']:.0f}")
        else:
            print(f"  ERROR: {result['error']}")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    successful = [r for r in results if r['success']]

    if not successful:
        print("\n⚠️ No successful tests. Check data and strategy.")
        return

    print(f"\nSuccessful Tests: {len(successful)}/{len(results)}")
    print(f"\nAverage Performance:")
    print(f"  Return: {np.mean([r['return'] for r in successful]):+.2f}%")
    print(f"  Sharpe: {np.mean([r['sharpe'] for r in successful]):.3f}")
    print(f"  Win Rate: {np.mean([r['win_rate'] for r in successful]):.1f}%")
    print(f"  Profit Factor: {np.mean([r['profit_factor'] for r in successful]):.2f}")
    print(f"  Max Drawdown: {np.mean([r['max_drawdown'] for r in successful]):.1f}%")

    # Moon Dev comparison
    print("\n" + "-"*80)
    print("Moon Dev Criteria Check:")
    print("-"*80)

    avg_sharpe = np.mean([r['sharpe'] for r in successful])
    avg_win_rate = np.mean([r['win_rate'] for r in successful])
    avg_pf = np.mean([r['profit_factor'] for r in successful])
    avg_dd = np.mean([r['max_drawdown'] for r in successful])

    print(f"  Sharpe Ratio:   {avg_sharpe:.3f} {'✓ PASS' if avg_sharpe >= 1.5 else '✗ FAIL'} (target: 1.5)")
    print(f"  Win Rate:       {avg_win_rate:.1f}% {'✓ PASS' if avg_win_rate >= 40 else '✗ FAIL'} (target: 40%)")
    print(f"  Profit Factor:  {avg_pf:.2f} {'✓ PASS' if avg_pf >= 1.5 else '✗ FAIL'} (target: 1.5)")
    print(f"  Max Drawdown:   {avg_dd:.1f}% {'✓ PASS' if avg_dd > -30 else '✗ FAIL'} (target: < -30%)")

    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    passing_criteria = sum([
        avg_sharpe >= 1.5,
        avg_win_rate >= 40,
        avg_pf >= 1.5,
        avg_dd > -30
    ])

    if passing_criteria >= 3:
        print("\n✅ Strategy is performing well! Consider minor fine-tuning.")
    elif passing_criteria >= 2:
        print("\n⚠️ Strategy needs optimization. Run full Moon Dev optimization.")
    else:
        print("\n❌ Strategy needs major improvements. Consider:")
        print("   - Adding trend filters")
        print("   - Implementing market regime detection")
        print("   - Testing different parameter ranges")

    print("\nNext Steps:")
    print("  1. Review these results")
    print("  2. If satisfied, run full optimization:")
    print("     python optimize_adaptive_ml_moon_dev.py")
    print("  3. Compare results with baseline (SOLUSDT 1h: +483%, Sharpe 0.72)")

    print("\n" + "="*80)


if __name__ == '__main__':
    main()
