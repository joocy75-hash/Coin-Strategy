#!/usr/bin/env python3
"""
Debug PMax strategy to check indicator calculations
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "trading-agent-system"))

import pandas as pd
import numpy as np
from strategies.pmax_asymmetric import PMaxAsymmetric

# Load data
data_file = Path(__file__).parent / "trading-agent-system/data/datasets/BTCUSDT_1h.parquet"
df = pd.read_parquet(data_file)

# Calculate indicators manually
close = df['Close'].values
high = df['High'].values
low = df['Low'].values

# Calculate ATR
atr = PMaxAsymmetric._calculate_atr(high, low, close, 10)

# Calculate MA (EMA)
ma = PMaxAsymmetric._calculate_ma(close, 10, "EMA")

# Calculate PMax
pmax = PMaxAsymmetric._calculate_pmax(ma, atr, 1.5, 3.0)

# Create result DataFrame
result = pd.DataFrame({
    'Close': close,
    'MA': ma,
    'ATR': atr,
    'PMax': pmax,
}, index=df.index)

# Check for crossovers
result['MA_prev'] = result['MA'].shift(1)
result['PMax_prev'] = result['PMax'].shift(1)

result['Buy_Signal'] = (result['MA_prev'] <= result['PMax_prev']) & (result['MA'] > result['PMax'])
result['Sell_Signal'] = (result['MA_prev'] >= result['PMax_prev']) & (result['MA'] < result['PMax'])

# Count signals
buy_count = result['Buy_Signal'].sum()
sell_count = result['Sell_Signal'].sum()

print("=" * 70)
print("PMax Strategy Debug Analysis")
print("=" * 70)
print(f"Total bars: {len(result)}")
print(f"Buy signals: {buy_count}")
print(f"Sell signals: {sell_count}")
print(f"Total signals: {buy_count + sell_count}")
print()

# Show first 50 rows with non-null values
print("First 50 rows (after indicators warm up):")
print(result.iloc[20:70][['Close', 'MA', 'ATR', 'PMax', 'Buy_Signal', 'Sell_Signal']].to_string())
print()

# Show all buy signals
if buy_count > 0:
    print(f"\nAll {buy_count} BUY signals:")
    buy_signals = result[result['Buy_Signal']]
    print(buy_signals[['Close', 'MA', 'PMax']].head(20).to_string())
print()

# Show all sell signals
if sell_count > 0:
    print(f"\nAll {sell_count} SELL signals:")
    sell_signals = result[result['Sell_Signal']]
    print(sell_signals[['Close', 'MA', 'PMax']].head(20).to_string())
