"""
파라미터 최적화 결과 시각화

최적화 결과를 그래프로 시각화하여 파라미터별 성과를 분석합니다.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'  # macOS
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지


def load_optimization_results(results_dir: Path):
    """최적화 결과 CSV 파일 로드"""

    strategies = {
        'AdaptiveMLTrailingStop': 'Adaptive ML',
        'PMaxAsymmetric': 'PMax',
        'HeikinAshiWick': 'Heikin Ashi'
    }

    results = {}

    for strategy_name, short_name in strategies.items():
        csv_file = results_dir / f"optimization_results_{strategy_name}.csv"

        if csv_file.exists():
            df = pd.read_csv(csv_file)
            results[short_name] = df
            print(f"Loaded: {csv_file.name} ({len(df)} rows)")
        else:
            print(f"Warning: {csv_file.name} not found")

    return results


def plot_parameter_performance(results_dir: Path):
    """전략별 파라미터 성과 시각화"""

    results = load_optimization_results(results_dir)

    if not results:
        print("No results to visualize")
        return

    # 1. Adaptive ML - 파라미터별 Sharpe Ratio
    if 'Adaptive ML' in results:
        df = results['Adaptive ML']

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Adaptive ML Trailing Stop - Parameter Performance', fontsize=16, fontweight='bold')

        # kama_length vs Sharpe
        ax = axes[0, 0]
        df_grouped = df.groupby('kama_length')['avg_sharpe'].mean().sort_index()
        ax.bar(df_grouped.index.astype(str), df_grouped.values, color='steelblue', alpha=0.7)
        ax.set_title('KAMA Length vs Sharpe Ratio')
        ax.set_xlabel('KAMA Length')
        ax.set_ylabel('Avg Sharpe Ratio')
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax.grid(axis='y', alpha=0.3)

        # atr_period vs Sharpe
        ax = axes[0, 1]
        df_grouped = df.groupby('atr_period')['avg_sharpe'].mean().sort_index()
        ax.bar(df_grouped.index.astype(str), df_grouped.values, color='darkorange', alpha=0.7)
        ax.set_title('ATR Period vs Sharpe Ratio')
        ax.set_xlabel('ATR Period')
        ax.set_ylabel('Avg Sharpe Ratio')
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax.grid(axis='y', alpha=0.3)

        # base_multiplier vs Sharpe
        ax = axes[1, 0]
        df_grouped = df.groupby('base_multiplier')['avg_sharpe'].mean().sort_index()
        ax.bar(df_grouped.index.astype(str), df_grouped.values, color='forestgreen', alpha=0.7)
        ax.set_title('Base Multiplier vs Sharpe Ratio')
        ax.set_xlabel('Base Multiplier')
        ax.set_ylabel('Avg Sharpe Ratio')
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax.grid(axis='y', alpha=0.3)

        # Return vs Sharpe scatter
        ax = axes[1, 1]
        scatter = ax.scatter(df['avg_return'], df['avg_sharpe'],
                           c=df['avg_win_rate'], cmap='RdYlGn',
                           s=100, alpha=0.6, edgecolors='black', linewidth=0.5)
        ax.set_title('Return vs Sharpe (colored by Win Rate)')
        ax.set_xlabel('Avg Return (%)')
        ax.set_ylabel('Avg Sharpe Ratio')
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax.axvline(x=0, color='red', linestyle='--', alpha=0.5)
        ax.grid(alpha=0.3)

        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Win Rate (%)')

        plt.tight_layout()
        plt.savefig(results_dir / 'adaptive_ml_parameter_analysis.png', dpi=150, bbox_inches='tight')
        print(f"Saved: adaptive_ml_parameter_analysis.png")
        plt.close()

    # 2. PMax - 파라미터별 성과
    if 'PMax' in results:
        df = results['PMax']

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('PMax Asymmetric - Parameter Performance', fontsize=16, fontweight='bold')

        # atr_length vs Return
        ax = axes[0, 0]
        df_grouped = df.groupby('atr_length')['avg_return'].mean().sort_index()
        ax.bar(df_grouped.index.astype(str), df_grouped.values, color='steelblue', alpha=0.7)
        ax.set_title('ATR Length vs Return')
        ax.set_xlabel('ATR Length')
        ax.set_ylabel('Avg Return (%)')
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax.grid(axis='y', alpha=0.3)

        # upper_multiplier vs Return
        ax = axes[0, 1]
        df_grouped = df.groupby('upper_multiplier')['avg_return'].mean().sort_index()
        ax.bar(df_grouped.index.astype(str), df_grouped.values, color='darkorange', alpha=0.7)
        ax.set_title('Upper Multiplier vs Return')
        ax.set_xlabel('Upper Multiplier')
        ax.set_ylabel('Avg Return (%)')
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax.grid(axis='y', alpha=0.3)

        # lower_multiplier vs Return
        ax = axes[1, 0]
        df_grouped = df.groupby('lower_multiplier')['avg_return'].mean().sort_index()
        ax.bar(df_grouped.index.astype(str), df_grouped.values, color='forestgreen', alpha=0.7)
        ax.set_title('Lower Multiplier vs Return')
        ax.set_xlabel('Lower Multiplier')
        ax.set_ylabel('Avg Return (%)')
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax.grid(axis='y', alpha=0.3)

        # Heatmap: upper vs lower multiplier
        ax = axes[1, 1]
        pivot = df.pivot_table(
            values='avg_return',
            index='lower_multiplier',
            columns='upper_multiplier',
            aggfunc='mean'
        )
        sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
                   ax=ax, cbar_kws={'label': 'Avg Return (%)'})
        ax.set_title('Return Heatmap: Upper vs Lower Multiplier')
        ax.set_xlabel('Upper Multiplier')
        ax.set_ylabel('Lower Multiplier')

        plt.tight_layout()
        plt.savefig(results_dir / 'pmax_parameter_analysis.png', dpi=150, bbox_inches='tight')
        print(f"Saved: pmax_parameter_analysis.png")
        plt.close()

    # 3. 전략 비교 대시보드
    plot_strategy_comparison(results, results_dir)


def plot_strategy_comparison(results: dict, results_dir: Path):
    """전략 간 비교 대시보드"""

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('Strategy Optimization Comparison', fontsize=16, fontweight='bold')

    strategies = list(results.keys())
    colors = ['steelblue', 'darkorange', 'forestgreen']

    # Best results for each strategy
    best_results = {}
    for strategy, df in results.items():
        best_idx = df['avg_sharpe'].idxmax()
        best_results[strategy] = df.loc[best_idx]

    # 1. Average Return
    ax = axes[0, 0]
    returns = [best_results[s]['avg_return'] for s in strategies]
    bars = ax.bar(strategies, returns, color=colors, alpha=0.7)
    ax.set_title('Best Avg Return by Strategy')
    ax.set_ylabel('Avg Return (%)')
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.1f}%',
               ha='center', va='bottom' if height > 0 else 'top')

    # 2. Sharpe Ratio
    ax = axes[0, 1]
    sharpes = [best_results[s]['avg_sharpe'] for s in strategies]
    bars = ax.bar(strategies, sharpes, color=colors, alpha=0.7)
    ax.set_title('Best Avg Sharpe Ratio by Strategy')
    ax.set_ylabel('Avg Sharpe Ratio')
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax.axhline(y=1.5, color='green', linestyle='--', alpha=0.5, label='Moon Dev Target')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.2f}',
               ha='center', va='bottom' if height > 0 else 'top')

    # 3. Win Rate
    ax = axes[0, 2]
    win_rates = [best_results[s]['avg_win_rate'] for s in strategies]
    bars = ax.bar(strategies, win_rates, color=colors, alpha=0.7)
    ax.set_title('Best Avg Win Rate by Strategy')
    ax.set_ylabel('Win Rate (%)')
    ax.axhline(y=40, color='green', linestyle='--', alpha=0.5, label='Moon Dev Target')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.1f}%',
               ha='center', va='bottom')

    # 4. Profit Factor
    ax = axes[1, 0]
    profit_factors = [best_results[s]['avg_profit_factor'] for s in strategies]
    bars = ax.bar(strategies, profit_factors, color=colors, alpha=0.7)
    ax.set_title('Best Avg Profit Factor by Strategy')
    ax.set_ylabel('Profit Factor')
    ax.axhline(y=1.5, color='green', linestyle='--', alpha=0.5, label='Moon Dev Target')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.2f}',
               ha='center', va='bottom')

    # 5. Max Drawdown
    ax = axes[1, 1]
    drawdowns = [best_results[s]['avg_max_drawdown'] for s in strategies]
    bars = ax.bar(strategies, drawdowns, color=colors, alpha=0.7)
    ax.set_title('Best Avg Max Drawdown by Strategy')
    ax.set_ylabel('Max Drawdown (%)')
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.1f}%',
               ha='center', va='bottom')

    # 6. Consistency Rate
    ax = axes[1, 2]
    consistency = [best_results[s]['consistency_rate'] for s in strategies]
    bars = ax.bar(strategies, consistency, color=colors, alpha=0.7)
    ax.set_title('Best Consistency Rate by Strategy')
    ax.set_ylabel('Consistency Rate (%)')
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.1f}%',
               ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig(results_dir / 'strategy_comparison_dashboard.png', dpi=150, bbox_inches='tight')
    print(f"Saved: strategy_comparison_dashboard.png")
    plt.close()


def plot_optimization_progress(results_dir: Path):
    """최적화 전후 비교 차트"""

    # Load best parameters
    strategies = ['AdaptiveMLTrailingStop', 'PMaxAsymmetric', 'HeikinAshiWick']
    short_names = ['Adaptive ML', 'PMax', 'Heikin Ashi']

    import json

    baseline_data = {
        'Adaptive ML': {'return': 21.78, 'sharpe': -0.09, 'win_rate': 34.1},
        'PMax': {'return': -1.22, 'sharpe': -0.27, 'win_rate': 34.5},
        'Heikin Ashi': {'return': -82.28, 'sharpe': -2.00, 'win_rate': 33.6}
    }

    optimized_data = {}

    for strategy, short in zip(strategies, short_names):
        json_file = results_dir / f"best_parameters_{strategy}.json"

        if json_file.exists():
            with open(json_file, 'r') as f:
                data = json.load(f)
                optimized_data[short] = {
                    'return': data['avg_return'],
                    'sharpe': data['avg_sharpe'],
                    'win_rate': data['avg_win_rate']
                }

    # Create comparison chart
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle('Optimization Before vs After Comparison', fontsize=16, fontweight='bold')

    x = np.arange(len(short_names))
    width = 0.35

    # 1. Return comparison
    ax = axes[0]
    baseline_returns = [baseline_data[s]['return'] for s in short_names]
    optimized_returns = [optimized_data[s]['return'] for s in short_names]

    ax.bar(x - width/2, baseline_returns, width, label='Before', color='lightcoral', alpha=0.7)
    ax.bar(x + width/2, optimized_returns, width, label='After', color='lightgreen', alpha=0.7)
    ax.set_title('Average Return Comparison')
    ax.set_ylabel('Return (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(short_names)
    ax.legend()
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(axis='y', alpha=0.3)

    # 2. Sharpe comparison
    ax = axes[1]
    baseline_sharpes = [baseline_data[s]['sharpe'] for s in short_names]
    optimized_sharpes = [optimized_data[s]['sharpe'] for s in short_names]

    ax.bar(x - width/2, baseline_sharpes, width, label='Before', color='lightcoral', alpha=0.7)
    ax.bar(x + width/2, optimized_sharpes, width, label='After', color='lightgreen', alpha=0.7)
    ax.set_title('Sharpe Ratio Comparison')
    ax.set_ylabel('Sharpe Ratio')
    ax.set_xticks(x)
    ax.set_xticklabels(short_names)
    ax.legend()
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.axhline(y=1.5, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Moon Dev Target')
    ax.grid(axis='y', alpha=0.3)

    # 3. Win Rate comparison
    ax = axes[2]
    baseline_wins = [baseline_data[s]['win_rate'] for s in short_names]
    optimized_wins = [optimized_data[s]['win_rate'] for s in short_names]

    ax.bar(x - width/2, baseline_wins, width, label='Before', color='lightcoral', alpha=0.7)
    ax.bar(x + width/2, optimized_wins, width, label='After', color='lightgreen', alpha=0.7)
    ax.set_title('Win Rate Comparison')
    ax.set_ylabel('Win Rate (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(short_names)
    ax.legend()
    ax.axhline(y=40, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Moon Dev Target')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(results_dir / 'optimization_before_after.png', dpi=150, bbox_inches='tight')
    print(f"Saved: optimization_before_after.png")
    plt.close()


def main():
    """메인 실행 함수"""

    print("=" * 80)
    print("파라미터 최적화 결과 시각화")
    print("=" * 80)

    results_dir = Path(__file__).parent / "optimization_results"

    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        return

    print(f"\nResults directory: {results_dir}\n")

    # 시각화 생성
    print("Generating visualizations...\n")

    plot_parameter_performance(results_dir)
    plot_optimization_progress(results_dir)

    print("\n" + "=" * 80)
    print("Visualization Complete!")
    print("=" * 80)
    print(f"\nGenerated files in {results_dir}:")
    print("  - adaptive_ml_parameter_analysis.png")
    print("  - pmax_parameter_analysis.png")
    print("  - strategy_comparison_dashboard.png")
    print("  - optimization_before_after.png")


if __name__ == "__main__":
    main()
