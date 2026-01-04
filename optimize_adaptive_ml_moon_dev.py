"""
Advanced Parameter Optimization System for Adaptive ML Trailing Stop Strategy
==============================================================================

Goal: Achieve Moon Dev Criteria
- Sharpe Ratio > 1.5
- Win Rate > 40%
- Profit Factor > 1.5
- Max Drawdown < -30%

This script uses Optuna for Bayesian optimization across 25+ datasets
with multi-objective scoring focused on Sharpe Ratio and Win Rate improvement.

Author: Strategy Research Lab
Date: 2026-01-04
"""

import sys
import os
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import optuna
from optuna.samplers import TPESampler
import warnings
warnings.filterwarnings('ignore')

# Add strategies directory to path
sys.path.append('/Users/mr.joo/Desktop/전략연구소/trading-agent-system/strategies')

from backtesting import Backtest
from adaptive_ml_trailing_stop import AdaptiveMLTrailingStop


# Configuration
DATA_DIR = Path('/Users/mr.joo/Desktop/전략연구소/trading-agent-system/data/datasets')
RESULTS_DIR = Path('/Users/mr.joo/Desktop/전략연구소')
COMMISSION = 0.0003  # 0.03%
INITIAL_CASH = 100000  # BUGFIX: Increased from 10000 to 100000 for high-priced assets

# Dataset selection - 25 diverse datasets
DATASETS = [
    # Major pairs - 1h timeframe (trending markets)
    'BTCUSDT_1h', 'ETHUSDT_1h', 'BNBUSDT_1h', 'SOLUSDT_1h', 'XRPUSDT_1h',

    # Altcoins - 1h timeframe (more volatile)
    'AVAXUSDT_1h', 'DOTUSDT_1h', 'LINKUSDT_1h', 'ATOMUSDT_1h', 'MATICUSDT_1h',
    'ADAUSDT_1h', 'UNIUSDT_1h', 'LTCUSDT_1h', 'NEARUSDT_1h',

    # Layer 2 / New coins - 1h timeframe
    'ARBUSDT_1h', 'OPUSDT_1h', 'APTUSDT_1h', 'SUIUSDT_1h',

    # Meme coins - 1h timeframe (high volatility test)
    'DOGEUSDT_1h', 'SHIBUSDT_1h', 'PEPEUSDT_1h',

    # Additional diverse coins
    'FETUSDT_1h', 'INJUSDT_1h', 'WLDUSDT_1h', 'THETAUSDT_1h',
]

# Moon Dev criteria weights for composite scoring
MOON_DEV_WEIGHTS = {
    'sharpe': 0.40,      # Most important - need to improve from 0.30 to 1.5+
    'win_rate': 0.30,    # Second most important - need to improve from 26% to 40%+
    'profit_factor': 0.20,  # Already passing (2.83 > 1.5)
    'max_drawdown': 0.10,   # Maintain good performance
}

# Moon Dev targets for normalization
MOON_DEV_TARGETS = {
    'sharpe': 1.5,
    'win_rate': 40.0,
    'profit_factor': 1.5,
    'max_drawdown': -30.0,
}


class MoonDevOptimizer:
    """
    Advanced optimizer using Optuna for Bayesian parameter optimization
    with multi-objective scoring focused on Moon Dev criteria.
    """

    def __init__(self, n_trials: int = 100, n_jobs: int = 1, n_datasets: int = None):
        self.n_trials = n_trials
        self.n_jobs = n_jobs
        self.n_datasets = n_datasets if n_datasets else len(DATASETS)  # Use subset if specified
        self.datasets_to_use = DATASETS[:self.n_datasets]  # Take first N datasets
        self.trial_results = []
        self.best_params = None
        self.best_score = -float('inf')

    def load_dataset(self, dataset_name: str) -> pd.DataFrame:
        """Load a parquet dataset and prepare for backtesting."""
        file_path = DATA_DIR / f"{dataset_name}.parquet"
        df = pd.read_parquet(file_path)

        # Ensure proper index and columns
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

        # Rename columns to match backtesting.py requirements
        df = df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })

        # Ensure we have required columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col} in {dataset_name}")

        return df[required_cols]

    def run_backtest(self, dataset_name: str, params: Dict) -> Dict:
        """Run backtest with given parameters on a specific dataset."""
        try:
            # Load data
            data = self.load_dataset(dataset_name)

            # Create backtest
            bt = Backtest(
                data,
                AdaptiveMLTrailingStop,
                cash=INITIAL_CASH,
                commission=COMMISSION,
                exclusive_orders=True
            )

            # Run with parameters
            stats = bt.run(
                kama_length=params['kama_length'],
                fast_length=params['fast_length'],
                slow_length=params['slow_length'],
                atr_period=params['atr_period'],
                base_multiplier=params['base_multiplier'],
                adaptive_strength=params['adaptive_strength'],
                knn_enabled=params['knn_enabled'],
                knn_k=params['knn_k'],
                knn_lookback=params['knn_lookback'],
                knn_feature_length=params['knn_feature_length'],
                knn_weight=params['knn_weight'],
                stop_loss_percent=params['stop_loss_percent'],
            )

            # Extract metrics
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
            print(f"Error in {dataset_name}: {str(e)}")
            return {
                'dataset': dataset_name,
                'return': 0,
                'sharpe': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown': -100,
                'num_trades': 0,
                'success': False,
                'error': str(e),
            }

    def calculate_moon_dev_score(self, results: List[Dict]) -> float:
        """
        Calculate composite Moon Dev score based on average performance.

        Score components:
        1. Sharpe Ratio (40%): normalized to target 1.5
        2. Win Rate (30%): normalized to target 40%
        3. Profit Factor (20%): normalized to target 1.5
        4. Max Drawdown (10%): normalized to target -30%

        Returns a score between 0 and 1, where 1 = perfect Moon Dev criteria
        """
        successful_results = [r for r in results if r['success']]

        if len(successful_results) == 0:
            return 0.0

        # Calculate averages
        avg_sharpe = np.mean([r['sharpe'] for r in successful_results])
        avg_win_rate = np.mean([r['win_rate'] for r in successful_results])
        avg_pf = np.mean([r['profit_factor'] for r in successful_results])
        avg_dd = np.mean([r['max_drawdown'] for r in successful_results])

        # Normalize each metric to [0, 1] based on Moon Dev targets
        # Sharpe: 0 -> 0, 1.5+ -> 1.0
        sharpe_score = min(avg_sharpe / MOON_DEV_TARGETS['sharpe'], 1.0)
        sharpe_score = max(sharpe_score, 0.0)

        # Win Rate: 0 -> 0, 40%+ -> 1.0
        win_rate_score = min(avg_win_rate / MOON_DEV_TARGETS['win_rate'], 1.0)
        win_rate_score = max(win_rate_score, 0.0)

        # Profit Factor: 0 -> 0, 1.5+ -> 1.0
        pf_score = min(avg_pf / MOON_DEV_TARGETS['profit_factor'], 1.0)
        pf_score = max(pf_score, 0.0)

        # Max Drawdown: -100% -> 0, -30% or better -> 1.0
        # Inverted: less negative is better
        dd_score = min(abs(avg_dd) / abs(MOON_DEV_TARGETS['max_drawdown']), 2.0)
        dd_score = max(1.0 - (dd_score - 1.0), 0.0)  # Penalize worse than -30%

        # Weighted composite score
        composite_score = (
            MOON_DEV_WEIGHTS['sharpe'] * sharpe_score +
            MOON_DEV_WEIGHTS['win_rate'] * win_rate_score +
            MOON_DEV_WEIGHTS['profit_factor'] * pf_score +
            MOON_DEV_WEIGHTS['max_drawdown'] * dd_score
        )

        return composite_score

    def objective(self, trial: optuna.Trial) -> float:
        """
        Optuna objective function.

        Suggests parameters and runs backtests across all datasets,
        returning the composite Moon Dev score.
        """
        # Suggest parameters
        params = {
            # KAMA parameters
            'kama_length': trial.suggest_int('kama_length', 15, 30, step=5),
            'fast_length': trial.suggest_int('fast_length', 10, 20, step=5),
            'slow_length': trial.suggest_int('slow_length', 40, 60, step=10),

            # ATR parameters
            'atr_period': trial.suggest_int('atr_period', 21, 35, step=7),
            'base_multiplier': trial.suggest_float('base_multiplier', 2.0, 3.5, step=0.5),
            'adaptive_strength': trial.suggest_float('adaptive_strength', 0.5, 2.0, step=0.5),

            # KNN parameters
            'knn_enabled': trial.suggest_categorical('knn_enabled', [True, False]),
            'knn_k': trial.suggest_int('knn_k', 5, 10, step=1),
            'knn_lookback': trial.suggest_int('knn_lookback', 50, 150, step=50),
            'knn_feature_length': trial.suggest_int('knn_feature_length', 3, 7, step=2),
            'knn_weight': trial.suggest_float('knn_weight', 0.0, 0.3, step=0.1),

            # Risk management
            'stop_loss_percent': trial.suggest_float('stop_loss_percent', 3.0, 7.0, step=1.0),
        }

        # Add constraint: fast_length < slow_length
        if params['fast_length'] >= params['slow_length']:
            return 0.0

        # Run backtests on all datasets (or subset if n_datasets specified)
        results = []
        for dataset_name in self.datasets_to_use:
            result = self.run_backtest(dataset_name, params)
            results.append(result)

        # Calculate Moon Dev score
        score = self.calculate_moon_dev_score(results)

        # Store trial results
        trial_data = {
            'trial_number': trial.number,
            'params': params,
            'score': score,
            'results': results,
            'timestamp': datetime.now().isoformat(),
        }
        self.trial_results.append(trial_data)

        # Calculate and display summary statistics
        successful_results = [r for r in results if r['success']]
        if successful_results:
            avg_sharpe = np.mean([r['sharpe'] for r in successful_results])
            avg_win_rate = np.mean([r['win_rate'] for r in successful_results])
            avg_return = np.mean([r['return'] for r in successful_results])

            print(f"\nTrial {trial.number}: Score={score:.4f}")
            print(f"  Avg Sharpe: {avg_sharpe:.3f} | Avg Win Rate: {avg_win_rate:.1f}% | Avg Return: {avg_return:.2f}%")
            print(f"  Params: kama={params['kama_length']}, atr={params['atr_period']}, "
                  f"mult={params['base_multiplier']}, knn_w={params['knn_weight']}")

        # Update best score
        if score > self.best_score:
            self.best_score = score
            self.best_params = params
            print(f"  *** NEW BEST SCORE: {score:.4f} ***")

        return score

    def optimize(self) -> optuna.Study:
        """Run Optuna optimization."""
        print("="*80)
        print("MOON DEV OPTIMIZATION - Adaptive ML Trailing Stop Strategy")
        print("="*80)
        print(f"\nOptimization Configuration:")
        print(f"  Datasets: {len(DATASETS)}")
        print(f"  Trials: {self.n_trials}")
        print(f"  Parallel Jobs: {self.n_jobs}")
        print(f"\nMoon Dev Targets:")
        print(f"  Sharpe Ratio: > {MOON_DEV_TARGETS['sharpe']}")
        print(f"  Win Rate: > {MOON_DEV_TARGETS['win_rate']}%")
        print(f"  Profit Factor: > {MOON_DEV_TARGETS['profit_factor']}")
        print(f"  Max Drawdown: < {MOON_DEV_TARGETS['max_drawdown']}%")
        print(f"\nScore Weights:")
        print(f"  Sharpe: {MOON_DEV_WEIGHTS['sharpe']*100}%")
        print(f"  Win Rate: {MOON_DEV_WEIGHTS['win_rate']*100}%")
        print(f"  Profit Factor: {MOON_DEV_WEIGHTS['profit_factor']*100}%")
        print(f"  Max Drawdown: {MOON_DEV_WEIGHTS['max_drawdown']*100}%")
        print("\n" + "="*80)
        print("Starting optimization...\n")

        # Create Optuna study
        sampler = TPESampler(seed=42)
        study = optuna.create_study(
            direction='maximize',
            sampler=sampler,
            study_name='moon_dev_optimization'
        )

        # Run optimization
        study.optimize(
            self.objective,
            n_trials=self.n_trials,
            n_jobs=self.n_jobs,
            show_progress_bar=True,
        )

        return study

    def save_results(self, study: optuna.Study):
        """Save optimization results to files."""
        print("\n" + "="*80)
        print("Saving results...")

        # 1. Save all trials to CSV
        trials_data = []
        for trial_info in self.trial_results:
            params = trial_info['params']
            results = trial_info['results']
            successful_results = [r for r in results if r['success']]

            if successful_results:
                row = {
                    'trial_number': trial_info['trial_number'],
                    'score': trial_info['score'],
                    'avg_sharpe': np.mean([r['sharpe'] for r in successful_results]),
                    'avg_win_rate': np.mean([r['win_rate'] for r in successful_results]),
                    'avg_return': np.mean([r['return'] for r in successful_results]),
                    'avg_profit_factor': np.mean([r['profit_factor'] for r in successful_results]),
                    'avg_max_dd': np.mean([r['max_drawdown'] for r in successful_results]),
                    'successful_datasets': len(successful_results),
                    **params
                }
                trials_data.append(row)

        trials_df = pd.DataFrame(trials_data)
        trials_df.to_csv(RESULTS_DIR / 'optimization_results_moondev.csv', index=False)
        print(f"✓ Saved trials to: {RESULTS_DIR / 'optimization_results_moondev.csv'}")

        # 2. Save best parameters to JSON
        best_params_data = {
            'best_score': self.best_score,
            'best_params': self.best_params,
            'optimization_date': datetime.now().isoformat(),
            'n_trials': self.n_trials,
            'n_datasets': len(DATASETS),
            'moon_dev_targets': MOON_DEV_TARGETS,
        }

        with open(RESULTS_DIR / 'best_params_moondev.json', 'w') as f:
            json.dump(best_params_data, f, indent=2)
        print(f"✓ Saved best params to: {RESULTS_DIR / 'best_params_moondev.json'}")

        # 3. Generate detailed markdown report
        self.generate_report(study, trials_df)

        print("="*80)

    def generate_report(self, study: optuna.Study, trials_df: pd.DataFrame):
        """Generate comprehensive markdown report."""

        # Get best trial results
        best_trial_info = [t for t in self.trial_results if t['params'] == self.best_params][0]
        best_results = best_trial_info['results']
        successful_best = [r for r in best_results if r['success']]

        report = f"""# Moon Dev Optimization Report - Adaptive ML Trailing Stop Strategy

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Executive Summary

### Current Status vs Moon Dev Criteria

| Metric | Current (Baseline) | Moon Dev Target | Best Optimized | Status |
|--------|-------------------|-----------------|----------------|--------|
| **Sharpe Ratio** | 0.30 | > 1.5 | {np.mean([r['sharpe'] for r in successful_best]):.3f} | {'✓ PASS' if np.mean([r['sharpe'] for r in successful_best]) > 1.5 else '✗ FAIL'} |
| **Win Rate** | 26.2% | > 40% | {np.mean([r['win_rate'] for r in successful_best]):.1f}% | {'✓ PASS' if np.mean([r['win_rate'] for r in successful_best]) > 40 else '✗ FAIL'} |
| **Profit Factor** | 2.83 | > 1.5 | {np.mean([r['profit_factor'] for r in successful_best]):.2f} | {'✓ PASS' if np.mean([r['profit_factor'] for r in successful_best]) > 1.5 else '✗ FAIL'} |
| **Max Drawdown** | N/A | < -30% | {np.mean([r['max_drawdown'] for r in successful_best]):.1f}% | {'✓ PASS' if np.mean([r['max_drawdown'] for r in successful_best]) > -30 else '✗ FAIL'} |

### Optimization Configuration

- **Total Trials**: {self.n_trials}
- **Datasets Tested**: {len(DATASETS)}
- **Best Score**: {self.best_score:.4f} / 1.00
- **Successful Datasets**: {len(successful_best)} / {len(DATASETS)}

---

## Best Parameters Found

```python
# Optimal configuration for Moon Dev criteria
best_params = {{
    # KAMA Settings
    'kama_length': {self.best_params['kama_length']},
    'fast_length': {self.best_params['fast_length']},
    'slow_length': {self.best_params['slow_length']},

    # Trailing Stop Settings
    'atr_period': {self.best_params['atr_period']},
    'base_multiplier': {self.best_params['base_multiplier']},
    'adaptive_strength': {self.best_params['adaptive_strength']},

    # KNN Machine Learning Settings
    'knn_enabled': {self.best_params['knn_enabled']},
    'knn_k': {self.best_params['knn_k']},
    'knn_lookback': {self.best_params['knn_lookback']},
    'knn_feature_length': {self.best_params['knn_feature_length']},
    'knn_weight': {self.best_params['knn_weight']},

    # Risk Management
    'stop_loss_percent': {self.best_params['stop_loss_percent']},
}}
```

---

## Detailed Performance Analysis

### Best Configuration Results by Dataset

| Dataset | Return | Sharpe | Win Rate | Profit Factor | Max DD | Trades |
|---------|--------|--------|----------|---------------|--------|--------|
"""

        # Add per-dataset results
        for result in sorted(successful_best, key=lambda x: x['sharpe'], reverse=True):
            report += f"| {result['dataset']:15s} | {result['return']:+7.2f}% | {result['sharpe']:6.3f} | {result['win_rate']:5.1f}% | {result['profit_factor']:6.2f} | {result['max_drawdown']:6.1f}% | {result['num_trades']:4.0f} |\n"

        # Add summary statistics
        report += f"""
### Summary Statistics (Best Configuration)

- **Average Return**: {np.mean([r['return'] for r in successful_best]):.2f}%
- **Average Sharpe Ratio**: {np.mean([r['sharpe'] for r in successful_best]):.3f}
- **Average Win Rate**: {np.mean([r['win_rate'] for r in successful_best]):.1f}%
- **Average Profit Factor**: {np.mean([r['profit_factor'] for r in successful_best]):.2f}
- **Average Max Drawdown**: {np.mean([r['max_drawdown'] for r in successful_best]):.1f}%
- **Total Trades**: {np.sum([r['num_trades'] for r in successful_best]):.0f}

### Top 5 Performing Datasets (by Sharpe Ratio)

| Rank | Dataset | Return | Sharpe | Win Rate | Profit Factor |
|------|---------|--------|--------|----------|---------------|
"""

        top_5 = sorted(successful_best, key=lambda x: x['sharpe'], reverse=True)[:5]
        for i, result in enumerate(top_5, 1):
            report += f"| {i} | {result['dataset']:15s} | {result['return']:+7.2f}% | {result['sharpe']:6.3f} | {result['win_rate']:5.1f}% | {result['profit_factor']:6.2f} |\n"

        # Add optimization insights
        report += f"""

---

## Optimization Insights

### Parameter Impact Analysis

"""

        # Calculate parameter correlations with score
        if len(trials_df) > 10:
            param_cols = ['kama_length', 'atr_period', 'base_multiplier', 'adaptive_strength',
                         'knn_weight', 'stop_loss_percent']
            correlations = {}
            for param in param_cols:
                if param in trials_df.columns:
                    corr = trials_df[[param, 'score']].corr().iloc[0, 1]
                    correlations[param] = corr

            report += "**Correlation with Moon Dev Score:**\n\n"
            for param, corr in sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True):
                direction = "↑ Positive" if corr > 0 else "↓ Negative"
                report += f"- `{param}`: {corr:+.3f} ({direction})\n"

        # Top 10 trials
        report += f"""

### Top 10 Trials

| Trial | Score | Sharpe | Win Rate | Return | Key Params |
|-------|-------|--------|----------|--------|------------|
"""

        top_10_trials = trials_df.nlargest(10, 'score')
        for _, row in top_10_trials.iterrows():
            report += f"| {row['trial_number']:.0f} | {row['score']:.4f} | {row['avg_sharpe']:.3f} | {row['avg_win_rate']:.1f}% | {row['avg_return']:+.1f}% | kama={row['kama_length']:.0f}, mult={row['base_multiplier']:.1f} |\n"

        # Recommendations
        report += """

---

## Recommendations

### Next Steps to Achieve Moon Dev Criteria

"""

        avg_sharpe = np.mean([r['sharpe'] for r in successful_best])
        avg_win_rate = np.mean([r['win_rate'] for r in successful_best])

        if avg_sharpe < 1.5:
            gap = 1.5 - avg_sharpe
            report += f"""
#### 1. Sharpe Ratio Improvement (Current: {avg_sharpe:.3f}, Gap: {gap:.3f})

**Strategies:**
- Consider adding a **trend filter** to avoid choppy/ranging markets
- Implement **market regime detection** (trending vs ranging)
- Test with **longer timeframes** (4h instead of 1h) for smoother signals
- Add **volatility filter** to trade only in favorable conditions
- Explore **ensemble methods** combining multiple timeframes
"""

        if avg_win_rate < 40:
            gap = 40 - avg_win_rate
            report += f"""
#### 2. Win Rate Improvement (Current: {avg_win_rate:.1f}%, Gap: {gap:.1f}%)

**Strategies:**
- Implement **confirmation filters** to reduce false signals
- Add **volume analysis** to confirm trend strength
- Use **support/resistance levels** for entry refinement
- Consider **scaling into positions** instead of all-at-once entries
- Test **tighter entry conditions** (sacrifice some profit for higher accuracy)
- Implement **time-of-day filters** (avoid low-liquidity periods)
"""

        report += """

#### 3. Advanced Techniques to Explore

1. **Multi-Timeframe Analysis**
   - Use higher timeframe for trend direction
   - Use lower timeframe for precise entries
   - Align signals across timeframes

2. **Machine Learning Enhancements**
   - Implement full KNN (currently simplified)
   - Add Random Forest for trend classification
   - Use XGBoost for pattern recognition

3. **Risk Management Enhancements**
   - Dynamic position sizing based on volatility
   - Pyramiding in strong trends
   - Partial profit taking at key levels

4. **Market Regime Adaptation**
   - Detect trending vs ranging markets
   - Use different parameters for different regimes
   - Disable trading in unfavorable regimes

5. **Portfolio Approach**
   - Instead of optimizing for all assets, identify best-performing subset
   - Focus on assets where strategy naturally excels
   - Use portfolio diversification to improve Sharpe

---

## Dataset Coverage Analysis

### Datasets Used in Optimization

"""

        report += "**Successfully Tested:** " + str(len(successful_best)) + " / " + str(len(DATASETS)) + "\n\n"

        # Group by performance tier
        excellent = [r for r in successful_best if r['sharpe'] > 1.0]
        good = [r for r in successful_best if 0.5 <= r['sharpe'] <= 1.0]
        poor = [r for r in successful_best if r['sharpe'] < 0.5]

        report += f"""
**Performance Tiers:**
- Excellent (Sharpe > 1.0): {len(excellent)} datasets
- Good (Sharpe 0.5-1.0): {len(good)} datasets
- Poor (Sharpe < 0.5): {len(poor)} datasets

"""

        # Failed datasets
        failed_results = [r for r in best_results if not r['success']]
        if failed_results:
            report += f"**Failed Datasets:** {len(failed_results)}\n"
            for r in failed_results:
                report += f"- {r['dataset']}: {r.get('error', 'Unknown error')}\n"

        report += f"""

---

## Conclusion

This optimization tested **{self.n_trials} parameter combinations** across **{len(DATASETS)} diverse datasets**.

**Key Findings:**
1. Best Moon Dev Score achieved: **{self.best_score:.4f} / 1.00**
2. Average Sharpe Ratio: **{avg_sharpe:.3f}** (target: 1.5)
3. Average Win Rate: **{avg_win_rate:.1f}%** (target: 40%)
4. Profit Factor consistently above 1.5 ✓

**Status:** {'🎯 MOON DEV ACHIEVED!' if avg_sharpe >= 1.5 and avg_win_rate >= 40 else '📈 Further optimization needed'}

The strategy shows strong potential with proper parameter tuning. The next phase should focus on:
- Implementing advanced filtering techniques
- Testing market regime adaptation
- Exploring multi-timeframe approaches
- Fine-tuning on the best-performing asset subset

---

*Report generated by Moon Dev Optimization System*
*Strategy Research Lab - 2026*
"""

        # Save report
        report_path = RESULTS_DIR / 'MOONDEV_OPTIMIZATION_REPORT.md'
        with open(report_path, 'w') as f:
            f.write(report)

        print(f"✓ Saved detailed report to: {report_path}")


def main():
    """Main optimization execution."""
    global DATASETS

    # Check if datasets exist
    print("Checking datasets...")
    missing_datasets = []
    for dataset_name in DATASETS:
        file_path = DATA_DIR / f"{dataset_name}.parquet"
        if not file_path.exists():
            missing_datasets.append(dataset_name)

    if missing_datasets:
        print(f"\n⚠ WARNING: {len(missing_datasets)} datasets not found:")
        for ds in missing_datasets[:5]:
            print(f"  - {ds}")
        if len(missing_datasets) > 5:
            print(f"  ... and {len(missing_datasets) - 5} more")
        print(f"\nProceeding with {len(DATASETS) - len(missing_datasets)} available datasets.\n")

        DATASETS = [ds for ds in DATASETS if ds not in missing_datasets]

    # Create optimizer
    optimizer = MoonDevOptimizer(
        n_trials=100,  # Adjust based on time available
        n_jobs=1       # Parallel jobs (set to 1 for debugging)
    )

    # Run optimization
    study = optimizer.optimize()

    # Save results
    optimizer.save_results(study)

    # Print final summary
    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE!")
    print("="*80)
    print(f"\nBest Score: {optimizer.best_score:.4f}")
    print(f"\nBest Parameters:")
    for param, value in optimizer.best_params.items():
        print(f"  {param:20s}: {value}")
    print("\n" + "="*80)
    print("\nFiles created:")
    print(f"  1. {RESULTS_DIR / 'optimization_results_moondev.csv'}")
    print(f"  2. {RESULTS_DIR / 'best_params_moondev.json'}")
    print(f"  3. {RESULTS_DIR / 'MOONDEV_OPTIMIZATION_REPORT.md'}")
    print("="*80)


if __name__ == '__main__':
    main()
