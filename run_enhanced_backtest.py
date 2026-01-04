#!/usr/bin/env python3
"""
백테스트 비교: Original vs Enhanced 전략
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import importlib.util

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "trading-agent-system"))

from backtesting import Backtest

# Paths
ENHANCED_DIR = BASE_DIR / "enhanced_strategies"
DATA_DIR = BASE_DIR / "trading-agent-system/data/datasets"

# Moon Dev Criteria
MOON_DEV = {
    'sharpe_ratio': 1.5,
    'profit_factor': 1.5,
    'max_drawdown': -30.0,
    'win_rate': 40.0
}


def load_strategy_module(file_path, class_name):
    """동적으로 전략 모듈 로드"""
    spec = importlib.util.spec_from_file_location("strategy_module", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


def run_single_backtest(strategy_class, data):
    """단일 백테스트 실행"""
    try:
        bt = Backtest(data, strategy_class, cash=10000, commission=0.0003, exclusive_orders=True)
        stats = bt.run()
        
        return {
            'total_return': float(stats.get('Return [%]', 0)),
            'sharpe_ratio': float(stats.get('Sharpe Ratio', 0)),
            'sortino_ratio': float(stats.get('Sortino Ratio', 0)),
            'max_drawdown': float(stats.get('Max. Drawdown [%]', 0)),
            'win_rate': float(stats.get('Win Rate [%]', 0)),
            'profit_factor': float(stats.get('Profit Factor', 0)),
            'total_trades': int(stats.get('# Trades', 0)),
            'avg_trade': float(stats.get('Avg. Trade [%]', 0)),
        }
    except Exception as e:
        return {'error': str(e)}


def load_datasets(limit=10):
    """데이터셋 로드"""
    datasets = []
    parquet_files = sorted(DATA_DIR.glob("*_1h.parquet"))[:limit]
    
    for file_path in parquet_files:
        try:
            df = pd.read_parquet(file_path)
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            datasets.append((file_path.stem, df))
        except Exception as e:
            print(f"  Failed to load {file_path.name}: {e}")
    
    return datasets


def main():
    print("=" * 80)
    print("백테스트 비교: Original vs Enhanced")
    print("=" * 80)
    
    # 전략 정의
    strategies = [
        {
            'name': 'SuperTrend Divergence',
            'original_file': '1_supertrend_divergence_original.py',
            'enhanced_file': '1_supertrend_divergence_enhanced.py',
            'original_class': 'SuperTrendDivergence',
            'enhanced_class': 'SuperTrendDivergenceEnhanced',
        },
        {
            'name': 'ATR VWMA Deviation',
            'original_file': '2_atr_vwma_deviation_original.py',
            'enhanced_file': '2_atr_vwma_deviation_enhanced.py',
            'original_class': 'ATRVWMADeviation',
            'enhanced_class': 'ATRVWMADeviationEnhanced',
        },
    ]
    
    # 데이터셋 로드
    print("\n[1] 데이터셋 로드...")
    datasets = load_datasets(limit=10)
    print(f"로드 완료: {len(datasets)}개 데이터셋")
    
    # 백테스트 실행
    print("\n[2] 백테스트 실행...")
    
    all_results = []
    
    for strat in strategies:
        print(f"\n{'=' * 80}")
        print(f"전략: {strat['name']}")
        print(f"{'=' * 80}")
        
        # Load strategy classes
        try:
            original_cls = load_strategy_module(
                ENHANCED_DIR / strat['original_file'],
                strat['original_class']
            )
            enhanced_cls = load_strategy_module(
                ENHANCED_DIR / strat['enhanced_file'],
                strat['enhanced_class']
            )
        except Exception as e:
            print(f"Error loading strategy: {e}")
            continue
        
        original_results = []
        enhanced_results = []
        
        for symbol, data in datasets:
            print(f"  Testing: {symbol}...", end=" ")
            
            # Original
            orig_res = run_single_backtest(original_cls, data)
            original_results.append(orig_res)
            
            # Enhanced
            enh_res = run_single_backtest(enhanced_cls, data)
            enhanced_results.append(enh_res)
            
            print("Done")
        
        # Calculate averages
        def calc_avg(results, key):
            valid = [r[key] for r in results if key in r and 'error' not in r]
            return np.mean(valid) if valid else 0
        
        avg_orig = {
            'sharpe_ratio': calc_avg(original_results, 'sharpe_ratio'),
            'profit_factor': calc_avg(original_results, 'profit_factor'),
            'max_drawdown': calc_avg(original_results, 'max_drawdown'),
            'win_rate': calc_avg(original_results, 'win_rate'),
            'total_return': calc_avg(original_results, 'total_return'),
        }
        
        avg_enh = {
            'sharpe_ratio': calc_avg(enhanced_results, 'sharpe_ratio'),
            'profit_factor': calc_avg(enhanced_results, 'profit_factor'),
            'max_drawdown': calc_avg(enhanced_results, 'max_drawdown'),
            'win_rate': calc_avg(enhanced_results, 'win_rate'),
            'total_return': calc_avg(enhanced_results, 'total_return'),
        }
        
        # Moon Dev evaluation
        moon_orig = all([
            avg_orig['sharpe_ratio'] >= MOON_DEV['sharpe_ratio'],
            avg_orig['profit_factor'] >= MOON_DEV['profit_factor'],
            avg_orig['max_drawdown'] >= MOON_DEV['max_drawdown'],
            avg_orig['win_rate'] >= MOON_DEV['win_rate'],
        ])
        
        moon_enh = all([
            avg_enh['sharpe_ratio'] >= MOON_DEV['sharpe_ratio'],
            avg_enh['profit_factor'] >= MOON_DEV['profit_factor'],
            avg_enh['max_drawdown'] >= MOON_DEV['max_drawdown'],
            avg_enh['win_rate'] >= MOON_DEV['win_rate'],
        ])
        
        # Display results
        print(f"\n  Original:")
        print(f"    Sharpe Ratio: {avg_orig['sharpe_ratio']:.2f}")
        print(f"    Profit Factor: {avg_orig['profit_factor']:.2f}")
        print(f"    Max Drawdown: {avg_orig['max_drawdown']:.2f}%")
        print(f"    Win Rate: {avg_orig['win_rate']:.2f}%")
        print(f"    Moon Dev: {'PASS' if moon_orig else 'FAIL'}")
        
        print(f"\n  Enhanced:")
        print(f"    Sharpe Ratio: {avg_enh['sharpe_ratio']:.2f} ({avg_enh['sharpe_ratio'] - avg_orig['sharpe_ratio']:+.2f})")
        print(f"    Profit Factor: {avg_enh['profit_factor']:.2f} ({avg_enh['profit_factor'] - avg_orig['profit_factor']:+.2f})")
        print(f"    Max Drawdown: {avg_enh['max_drawdown']:.2f}% ({avg_enh['max_drawdown'] - avg_orig['max_drawdown']:+.2f}%)")
        print(f"    Win Rate: {avg_enh['win_rate']:.2f}% ({avg_enh['win_rate'] - avg_orig['win_rate']:+.2f}%)")
        print(f"    Moon Dev: {'PASS' if moon_enh else 'FAIL'}")
        
        all_results.append({
            'strategy': strat['name'],
            'orig_sharpe': avg_orig['sharpe_ratio'],
            'enh_sharpe': avg_enh['sharpe_ratio'],
            'sharpe_improvement': avg_enh['sharpe_ratio'] - avg_orig['sharpe_ratio'],
            'orig_pf': avg_orig['profit_factor'],
            'enh_pf': avg_enh['profit_factor'],
            'pf_improvement': avg_enh['profit_factor'] - avg_orig['profit_factor'],
            'orig_dd': avg_orig['max_drawdown'],
            'enh_dd': avg_enh['max_drawdown'],
            'dd_improvement': avg_enh['max_drawdown'] - avg_orig['max_drawdown'],
            'orig_wr': avg_orig['win_rate'],
            'enh_wr': avg_enh['win_rate'],
            'wr_improvement': avg_enh['win_rate'] - avg_orig['win_rate'],
            'orig_moon_dev': moon_orig,
            'enh_moon_dev': moon_enh,
        })
    
    # Save results
    print(f"\n{'=' * 80}")
    print("[3] 결과 저장")
    print(f"{'=' * 80}")
    
    df = pd.DataFrame(all_results)
    csv_path = BASE_DIR / "c_grade_enhancement_results.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"\nCSV 저장: {csv_path}")
    
    # Summary
    print(f"\n{'=' * 80}")
    print("요약")
    print(f"{'=' * 80}")
    
    orig_pass = sum(1 for r in all_results if r['orig_moon_dev'])
    enh_pass = sum(1 for r in all_results if r['enh_moon_dev'])
    
    print(f"\nMoon Dev 통과:")
    print(f"  Original: {orig_pass}/{len(all_results)}")
    print(f"  Enhanced: {enh_pass}/{len(all_results)}")
    
    avg_sharpe_imp = np.mean([r['sharpe_improvement'] for r in all_results])
    avg_pf_imp = np.mean([r['pf_improvement'] for r in all_results])
    avg_dd_imp = np.mean([r['dd_improvement'] for r in all_results])
    avg_wr_imp = np.mean([r['wr_improvement'] for r in all_results])
    
    print(f"\n평균 개선도:")
    print(f"  Sharpe Ratio: {avg_sharpe_imp:+.2f}")
    print(f"  Profit Factor: {avg_pf_imp:+.2f}")
    print(f"  Max Drawdown: {avg_dd_imp:+.2f}%")
    print(f"  Win Rate: {avg_wr_imp:+.2f}%")
    
    print(f"\n완료!")


if __name__ == "__main__":
    main()
