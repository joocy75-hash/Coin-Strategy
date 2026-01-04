"""
B등급 전략 3개 비교 분석
- PMax - Asymmetric Multipliers (72.2점)
- Adaptive ML Trailing Stop (70.2점)
- Heikin Ashi Wick Strategy (70.0점)
"""

import pandas as pd
import numpy as np

# Load results from CSV files
pmax_results = pd.read_csv('/Users/mr.joo/Desktop/전략연구소/pmax_results.csv')
adaptive_results = pd.read_csv('/Users/mr.joo/Desktop/전략연구소/adaptive_ml_results.csv')
heikin_results = pd.read_csv('/Users/mr.joo/Desktop/전략연구소/heikin_ashi_results.csv')

# PMax 결과
pmax_data = {
    'Strategy': 'PMax - Asymmetric Multipliers',
    'TradingView Score': 72.2,
    'Avg Return%': pmax_results['Return%'].mean(),
    'Avg Sharpe': pmax_results['Sharpe'].mean(),
    'Avg Win Rate%': pmax_results['WinRate%'].mean(),
    'Avg PF': pmax_results['PF'].mean(),
    'Total Trades': pmax_results['#Trades'].sum(),
    'Best Performance': f"{pmax_results.loc[pmax_results['Return%'].idxmax(), 'Symbol']} {pmax_results.loc[pmax_results['Return%'].idxmax(), 'Timeframe']} ({pmax_results['Return%'].max():.2f}%, PF {pmax_results.loc[pmax_results['Return%'].idxmax(), 'PF']})"
}

# Adaptive ML 결과
adaptive_summary = {
    'Strategy': 'Adaptive ML Trailing Stop',
    'TradingView Score': 70.2,
    'Avg Return%': adaptive_results['Return%'].mean(),
    'Avg Sharpe': adaptive_results['Sharpe'].mean(),
    'Avg Win Rate%': adaptive_results['WinRate%'].mean(),
    'Avg PF': adaptive_results['PF'].mean(),
    'Total Trades': adaptive_results['#Trades'].sum(),
    'Best Performance': f"{adaptive_results.loc[adaptive_results['Return%'].idxmax(), 'Symbol']} {adaptive_results.loc[adaptive_results['Return%'].idxmax(), 'Timeframe']} ({adaptive_results['Return%'].max():.2f}%, PF {adaptive_results.loc[adaptive_results['Return%'].idxmax(), 'PF']})"
}

# Heikin Ashi 결과
heikin_summary = {
    'Strategy': 'Heikin Ashi Wick',
    'TradingView Score': 70.0,
    'Avg Return%': heikin_results['Return%'].mean(),
    'Avg Sharpe': heikin_results['Sharpe'].mean(),
    'Avg Win Rate%': heikin_results['WinRate%'].mean(),
    'Avg PF': heikin_results['PF'].mean(),
    'Total Trades': heikin_results['#Trades'].sum(),
    'Best Performance': f"{heikin_results.loc[heikin_results['Return%'].idxmax(), 'Symbol']} {heikin_results.loc[heikin_results['Return%'].idxmax(), 'Timeframe']} ({heikin_results['Return%'].max():.2f}%, PF {heikin_results.loc[heikin_results['Return%'].idxmax(), 'PF']})"
}

# Create comparison DataFrame
comparison = pd.DataFrame([pmax_data, adaptive_summary, heikin_summary])

print("=" * 100)
print("B등급 전략 3개 비교 분석")
print("=" * 100)
print("\n")
print(comparison.to_string(index=False))

# Moon Dev 기준 평가
print("\n" + "=" * 100)
print("MOON DEV CRITERIA EVALUATION")
print("=" * 100)

for idx, row in comparison.iterrows():
    print(f"\n{row['Strategy']} (TradingView Score: {row['TradingView Score']})")
    print("-" * 100)

    sharpe_pass = "✅ PASS" if row['Avg Sharpe'] > 1.5 else "❌ FAIL"
    winrate_pass = "✅ PASS" if row['Avg Win Rate%'] > 40 else "❌ FAIL"
    pf_pass = "✅ PASS" if row['Avg PF'] > 1.5 else "❌ FAIL"
    trades_pass = "✅ PASS" if row['Total Trades'] > 100 else "❌ FAIL"

    print(f"  Sharpe Ratio > 1.5:    {row['Avg Sharpe']:.2f}  {sharpe_pass}")
    print(f"  Win Rate > 40%:        {row['Avg Win Rate%']:.2f}%  {winrate_pass}")
    print(f"  Profit Factor > 1.5:   {row['Avg PF']:.2f}  {pf_pass}")
    print(f"  Total Trades > 100:    {row['Total Trades']}  {trades_pass}")

    passed = (row['Avg Sharpe'] > 1.5 and row['Avg Win Rate%'] > 40 and
              row['Avg PF'] > 1.5 and row['Total Trades'] > 100)

    print(f"\n  Overall: {'✅ PASSES ALL CRITERIA' if passed else '❌ DOES NOT MEET CRITERIA'}")

# 최고 성과 전략 선정
print("\n" + "=" * 100)
print("RANKING & RECOMMENDATION")
print("=" * 100)

# Scoring system (weighted)
comparison['Return Score'] = comparison['Avg Return%'] / comparison['Avg Return%'].max() * 30
comparison['Sharpe Score'] = comparison['Avg Sharpe'] / comparison['Avg Sharpe'].max() * 25 if comparison['Avg Sharpe'].max() > 0 else 0
comparison['WinRate Score'] = comparison['Avg Win Rate%'] / comparison['Avg Win Rate%'].max() * 20
comparison['PF Score'] = comparison['Avg PF'] / comparison['Avg PF'].max() * 25

comparison['Total Score'] = (comparison['Return Score'] + comparison['Sharpe Score'] +
                             comparison['WinRate Score'] + comparison['PF Score'])

comparison_sorted = comparison.sort_values('Total Score', ascending=False)

print("\n전략 순위 (종합 점수 기준):")
print("-" * 100)

for rank, (idx, row) in enumerate(comparison_sorted.iterrows(), 1):
    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
    print(f"{medal} #{rank}: {row['Strategy']}")
    print(f"   종합 점수: {row['Total Score']:.2f}/100")
    print(f"   평균 수익률: {row['Avg Return%']:.2f}%")
    print(f"   샤프 비율: {row['Avg Sharpe']:.2f}")
    print(f"   승률: {row['Avg Win Rate%']:.2f}%")
    print(f"   Profit Factor: {row['Avg PF']:.2f}")
    print(f"   최고 성과: {row['Best Performance']}")
    print()

# Final recommendation
winner = comparison_sorted.iloc[0]

print("=" * 100)
print("🏆 최종 추천 전략")
print("=" * 100)
print(f"\n전략명: {winner['Strategy']}")
print(f"TradingView 점수: {winner['TradingView Score']}")
print(f"종합 점수: {winner['Total Score']:.2f}/100")
print(f"\n추천 이유:")
print(f"  - 평균 수익률: {winner['Avg Return%']:.2f}% (3개 전략 중 {'1위' if winner['Avg Return%'] == comparison['Avg Return%'].max() else '2위 이하'})")
print(f"  - 샤프 비율: {winner['Avg Sharpe']:.2f} (위험 대비 수익)")
print(f"  - 승률: {winner['Avg Win Rate%']:.2f}%")
print(f"  - Profit Factor: {winner['Avg PF']:.2f}")
print(f"  - 최고 성과: {winner['Best Performance']}")

print("\n⚠️  주의사항:")
print("  - 모든 B등급 전략이 Moon Dev 기준(Sharpe>1.5, WinRate>40%, PF>1.5)을 미달했습니다.")
print("  - TradingView 점수와 실제 백테스트 성과가 일치하지 않습니다.")
print("  - 실전 운용 전 추가 최적화 및 리스크 관리 강화가 필요합니다.")
print("  - 타임프레임에 따라 성과 차이가 크므로 (1h vs 4h), 적절한 선택이 중요합니다.")

print("\n" + "=" * 100)
