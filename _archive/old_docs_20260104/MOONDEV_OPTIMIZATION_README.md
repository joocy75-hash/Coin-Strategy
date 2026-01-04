# Moon Dev Optimization System
## Advanced Parameter Optimization for Adaptive ML Trailing Stop Strategy

**Created**: 2026-01-04
**Goal**: Achieve Moon Dev criteria through systematic Bayesian optimization
**Status**: Ready for execution

---

## Quick Start

### 1. Install Dependencies

```bash
cd "/Users/mr.joo/Desktop/전략연구소"
pip install -r requirements_moondev.txt
```

This will install:
- **Optuna**: Bayesian optimization framework
- **Pandas/Numpy**: Data processing
- **Backtesting.py**: Backtesting framework
- Supporting libraries

### 2. Quick Validation (Optional but Recommended)

Before running the full optimization (which can take hours), do a quick validation:

```bash
python quick_validate_moondev.py
```

This will:
- Test current parameters on 5 new datasets
- Validate data integrity
- Give baseline performance snapshot
- Takes ~2-5 minutes

### 3. Run Full Optimization

```bash
python optimize_adaptive_ml_moon_dev.py
```

This will:
- Test 100 parameter combinations
- Across 25 diverse datasets
- Using Bayesian optimization (Optuna)
- Takes ~2-4 hours (depending on hardware)

---

## What Gets Created

After running optimization, you'll have:

### 1. `optimization_results_moondev.csv`
Complete trial history with all tested parameters and their scores.

**Columns:**
- `trial_number`: Sequential trial ID
- `score`: Composite Moon Dev score (0-1)
- `avg_sharpe`, `avg_win_rate`, `avg_return`, etc.
- All tested parameters

**Use for:**
- Analyzing parameter sensitivity
- Finding correlation patterns
- Plotting optimization progress

### 2. `best_params_moondev.json`
Best parameters found during optimization.

**Structure:**
```json
{
  "best_score": 0.7234,
  "best_params": {
    "kama_length": 25,
    "atr_period": 28,
    "base_multiplier": 3.0,
    ...
  },
  "optimization_date": "2026-01-04T...",
  "n_trials": 100,
  "n_datasets": 25
}
```

**Use for:**
- Directly updating strategy parameters
- Comparing with baseline configuration
- Production deployment

### 3. `MOONDEV_OPTIMIZATION_REPORT.md`
Comprehensive markdown report with:
- Executive summary (current vs optimized)
- Best parameters found
- Per-dataset performance breakdown
- Top 10 trials
- Parameter impact analysis
- Actionable recommendations
- Next steps to achieve full Moon Dev

**Use for:**
- Understanding optimization results
- Presenting findings
- Planning next optimization phase

---

## Understanding the Optimization

### What is Being Optimized?

The system tests different combinations of these parameters:

| Parameter | Range | Impact |
|-----------|-------|--------|
| `kama_length` | 15-30 | KAMA period - affects trend responsiveness |
| `atr_period` | 21-35 | ATR period - affects stop distance calculation |
| `base_multiplier` | 2.0-3.5 | ATR multiplier - wider or tighter stops |
| `adaptive_strength` | 0.5-2.0 | How much stops adapt to market conditions |
| `knn_weight` | 0.0-0.3 | Influence of ML predictions |
| `stop_loss_percent` | 3.0-7.0 | Fixed stop loss percentage |

### How is Performance Measured?

Each parameter combination gets a **Moon Dev Score** (0 to 1):

```python
score = (
    (sharpe_ratio / 1.5) * 0.40 +      # 40% weight on Sharpe
    (win_rate / 40) * 0.30 +           # 30% weight on Win Rate
    (profit_factor / 1.5) * 0.20 +     # 20% weight on Profit Factor
    (1 - abs(max_dd) / 30) * 0.10      # 10% weight on Drawdown
)
```

**Score Interpretation:**
- `1.0` = Perfect Moon Dev (all criteria met)
- `0.75` = Strong performance (close to Moon Dev)
- `0.50` = Moderate performance (needs improvement)
- `0.25` = Weak performance (major issues)

### What is Bayesian Optimization?

Unlike grid search (testing every combination), Bayesian optimization:
1. Starts with random trials
2. Learns which parameters work well
3. Intelligently suggests promising parameter combinations
4. Converges faster to optimal solution

**Advantages:**
- Finds better parameters in fewer trials
- Handles complex parameter interactions
- Provides uncertainty estimates

---

## Dataset Coverage

### 25 Diverse Datasets Tested

**Major Pairs** (5):
- BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT

**Altcoins** (9):
- AVAXUSDT, DOTUSDT, LINKUSDT, ATOMUSDT, MATICUSDT
- ADAUSDT, UNIUSDT, LTCUSDT, NEARUSDT

**Layer 2 / New Coins** (4):
- ARBUSDT, OPUSDT, APTUSDT, SUIUSDT

**Meme Coins** (3):
- DOGEUSDT, SHIBUSDT, PEPEUSDT

**Others** (4):
- FETUSDT, INJUSDT, WLDUSDT, THETAUSDT

**Why this mix?**
- **Diversity**: Different market behaviors, volatilities, trends
- **Robustness**: Good parameters should work across asset types
- **Statistical Validity**: 25+ datasets = statistically significant results

---

## Moon Dev Criteria

### Current Status (Baseline)

From previous testing on 10 datasets:

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Sharpe Ratio | 0.30 | > 1.5 | ❌ FAIL |
| Win Rate | 26.2% | > 40% | ❌ FAIL |
| Profit Factor | 2.83 | > 1.5 | ✅ PASS |
| Max Drawdown | TBD | < -30% | ⚠️ TBD |

**Challenge**: Need to 5x Sharpe and 1.5x Win Rate

### What Success Looks Like

**Minimum Viable Moon Dev (MVMD)**:
- Sharpe Ratio: > 1.0 (halfway to target)
- Win Rate: > 35% (approaching target)
- Profit Factor: > 1.5 (maintain)
- Max Drawdown: < -35% (slightly relaxed)

**Full Moon Dev**:
- All criteria met exactly as specified
- Consistent across 80%+ of datasets
- Validated on out-of-sample data

---

## Interpreting Results

### After Optimization Completes

1. **Check the Report**
   - Open `MOONDEV_OPTIMIZATION_REPORT.md`
   - Review "Executive Summary" table
   - Look for ✓ PASS indicators

2. **Analyze Best Parameters**
   - Open `best_params_moondev.json`
   - Compare with current parameters
   - Understand what changed and why

3. **Review Trial Data**
   - Open `optimization_results_moondev.csv` in Excel/Pandas
   - Plot score vs trial_number (see optimization progress)
   - Check correlation between parameters and score

### What If Results Are Not Moon Dev?

The report includes **Recommendations** section with:

1. **If Sharpe < 1.5**:
   - Add trend filter (ADX)
   - Implement market regime detection
   - Test longer timeframes (4h)
   - Add volatility filter

2. **If Win Rate < 40%**:
   - Add confirmation filters
   - Use volume analysis
   - Implement stricter entry conditions
   - Add support/resistance levels

3. **Advanced Techniques**:
   - Multi-timeframe analysis
   - Enhanced ML (full KNN, Random Forest)
   - Dynamic position sizing
   - Portfolio approach (focus on best assets)

---

## Customization

### Adjusting Number of Trials

In `optimize_adaptive_ml_moon_dev.py`, line 578:

```python
optimizer = MoonDevOptimizer(
    n_trials=100,  # Change this (more = better but slower)
    n_jobs=1       # Parallel jobs (use CPU count for speed)
)
```

**Recommendations:**
- Quick test: 20 trials (~30 min)
- Standard: 100 trials (~2-4 hours)
- Thorough: 200 trials (~4-8 hours)
- Exhaustive: 500 trials (~10-20 hours)

### Changing Datasets

In `optimize_adaptive_ml_moon_dev.py`, lines 36-50:

```python
DATASETS = [
    'BTCUSDT_1h', 'ETHUSDT_1h',  # Edit this list
    ...
]
```

**Tips:**
- Focus on higher volume pairs for reliability
- Mix timeframes for robustness
- Avoid too many correlated pairs (BTC/ETH/BNB all move together)

### Adjusting Parameter Ranges

In `optimize_adaptive_ml_moon_dev.py`, `objective()` function:

```python
params = {
    'kama_length': trial.suggest_int('kama_length', 15, 30, step=5),
    # Change ranges here: (min, max, step)
}
```

### Changing Optimization Weights

In `optimize_adaptive_ml_moon_dev.py`, lines 32-37:

```python
MOON_DEV_WEIGHTS = {
    'sharpe': 0.40,       # Increase to prioritize Sharpe
    'win_rate': 0.30,     # Increase to prioritize Win Rate
    'profit_factor': 0.20,
    'max_drawdown': 0.10,
}
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'optuna'"

```bash
pip install optuna
```

### "FileNotFoundError: [dataset].parquet"

Check that datasets exist:
```bash
ls "/Users/mr.joo/Desktop/전략연구소/trading-agent-system/data/datasets/"
```

### "All trials failing"

Run quick validation first:
```bash
python quick_validate_moondev.py
```

Check for data issues or strategy bugs.

### Optimization is slow

1. Reduce number of datasets (test on 10 instead of 25)
2. Reduce trials (50 instead of 100)
3. Use parallel jobs: `n_jobs=4`

### Results are worse than baseline

This can happen! Optimization can overfit or explore bad parameter space.

**Solutions:**
1. Check if baseline params were in search space
2. Run more trials (100 → 200)
3. Adjust parameter ranges
4. Verify data quality

---

## Advanced Usage

### Running Multiple Optimization Rounds

```bash
# Round 1: Broad search
python optimize_adaptive_ml_moon_dev.py

# Analyze results, narrow parameter ranges

# Round 2: Fine-tuning
# Edit parameter ranges in script
python optimize_adaptive_ml_moon_dev.py
```

### Combining with Manual Analysis

```python
import pandas as pd

# Load results
df = pd.read_csv('optimization_results_moondev.csv')

# Find best Sharpe configurations
best_sharpe = df.nlargest(10, 'avg_sharpe')

# Find best Win Rate configurations
best_wr = df.nlargest(10, 'avg_win_rate')

# Find configurations good at both
balanced = df[(df['avg_sharpe'] > 1.0) & (df['avg_win_rate'] > 35)]
```

### Exporting for Production

After finding best parameters:

```python
import json

# Load best params
with open('best_params_moondev.json', 'r') as f:
    best = json.load(f)

# Update strategy file
# Edit: trading-agent-system/strategies/adaptive_ml_trailing_stop.py
# Copy values from best['best_params']
```

---

## Files Reference

### Input Files
- `/Users/mr.joo/Desktop/전략연구소/trading-agent-system/strategies/adaptive_ml_trailing_stop.py`
  - Strategy implementation
- `/Users/mr.joo/Desktop/전략연구소/trading-agent-system/data/datasets/*.parquet`
  - Historical data (25 symbols × 3 timeframes)

### Scripts
- `optimize_adaptive_ml_moon_dev.py`
  - Main optimization script
- `quick_validate_moondev.py`
  - Quick validation script

### Output Files
- `optimization_results_moondev.csv`
  - All trials data
- `best_params_moondev.json`
  - Best parameters
- `MOONDEV_OPTIMIZATION_REPORT.md`
  - Detailed report

### Documentation
- `MOONDEV_PROGRESS_TRACKER.md`
  - Progress tracking document
- `MOONDEV_OPTIMIZATION_README.md`
  - This file

---

## Expected Timeline

| Phase | Duration | Activity |
|-------|----------|----------|
| Setup | 10 min | Install dependencies |
| Quick Validation | 5 min | Test on 5 datasets |
| Full Optimization | 2-4 hours | 100 trials × 25 datasets |
| Analysis | 30 min | Review results, read report |
| Implementation | 1 hour | Update strategy with best params |
| Validation | 1 hour | Out-of-sample testing |
| **Total** | **~5-7 hours** | End-to-end process |

---

## Next Steps After Optimization

### 1. If Moon Dev Achieved (Score > 0.8)
- ✅ Update strategy parameters
- ✅ Run out-of-sample validation
- ✅ Begin paper trading
- ✅ Document configuration
- ✅ Set up monitoring

### 2. If Close to Moon Dev (Score 0.6-0.8)
- 📊 Analyze which criteria are failing
- 🔧 Implement targeted improvements
- 🔄 Run second optimization round
- 📈 Consider ensemble approaches

### 3. If Far from Moon Dev (Score < 0.6)
- 🤔 Reconsider strategy fundamentals
- 💡 Implement Phase 2 advanced features:
  - Trend filters (ADX)
  - Market regime detection
  - Multi-timeframe analysis
  - Volume confirmation
- 🧪 Test on different asset subset
- 🔬 Analyze failure modes

---

## Support & Resources

### Documentation
- **Optuna Docs**: https://optuna.readthedocs.io/
- **Backtesting.py Docs**: https://kernc.github.io/backtesting.py/
- **Strategy Source**: Pine Script "Adaptive ML Trailing Stop [BOSWaves]"

### Internal Files
- `MOONDEV_PROGRESS_TRACKER.md` - Track progress
- Strategy implementation for technical details
- Backtest runner agent for reference

### Common Questions

**Q: Can I run this overnight?**
A: Yes! Optimization is fully automated. Start it and check results in the morning.

**Q: Will this guarantee Moon Dev?**
A: No guarantee. It finds the best parameters within the search space. You may need advanced features (Phase 2) to achieve full criteria.

**Q: How do I know if I'm overfitting?**
A: Reserve some data for out-of-sample testing. If out-of-sample performance drops significantly, you've overfit.

**Q: Can I optimize on my best-performing assets only?**
A: Yes, but ensure diversity. Don't optimize on only BTC/ETH/BNB (too correlated).

**Q: Should I use 1h or 4h data?**
A: Current uses 1h. Try 4h for potentially higher Sharpe (smoother, fewer trades).

---

## Conclusion

This optimization system provides a **systematic, data-driven approach** to achieving Moon Dev criteria.

**Key Features:**
- ✅ Bayesian optimization (intelligent search)
- ✅ 25+ diverse datasets (robust)
- ✅ Multi-objective scoring (balanced)
- ✅ Comprehensive reporting (actionable)
- ✅ Extensible framework (iterative improvement)

**Success depends on:**
1. Data quality (✅ have good datasets)
2. Parameter ranges (✅ well-chosen)
3. Scoring function (✅ aligned with Moon Dev)
4. Patience (optimization takes time)
5. Iteration (may need multiple rounds)

Good luck achieving Moon Dev! 🚀

---

*Strategy Research Lab - Moon Dev Initiative 2026*
*"From 0.30 Sharpe to 1.5+ through systematic optimization"*
