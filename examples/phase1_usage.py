"""
Phase 1 Usage Examples

Demonstrates practical usage of the Pine Lexer and Indicator Mapper
for Pine Script analysis and conversion.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from converter import PineLexer, IndicatorMapper, TokenType


def example1_basic_lexer():
    """Example 1: Basic lexer usage"""
    print("\n" + "="*60)
    print("Example 1: Basic Pine Script Tokenization")
    print("="*60)

    pine_code = """
//@version=5
indicator("Moving Average Cross", overlay=true)

fastLength = input.int(9, "Fast Length")
slowLength = input.int(21, "Slow Length")

fast = ta.ema(close, fastLength)
slow = ta.sma(close, slowLength)

plot(fast, color=color.blue)
plot(slow, color=color.red)
"""

    lexer = PineLexer()
    tokens = lexer.tokenize(pine_code)

    print(f"\nPine Script Code:\n{pine_code}")
    print(f"\nTotal tokens: {len(tokens)}")

    # Get statistics
    keywords = lexer.get_tokens_by_type(TokenType.KEYWORD)
    namespaces = lexer.get_tokens_by_type(TokenType.NAMESPACE)
    builtins = lexer.get_tokens_by_type(TokenType.BUILTIN)

    print(f"\nToken Statistics:")
    print(f"  Keywords:   {len(keywords)}")
    print(f"  Namespaces: {len(namespaces)}")
    print(f"  Builtins:   {len(builtins)}")

    print(f"\nKeywords found: {[t.value for t in keywords]}")
    print(f"Namespaces: {set([t.value for t in namespaces])}")
    print(f"Builtins: {set([t.value for t in builtins])}")


def example2_detect_indicators():
    """Example 2: Detect indicators in Pine Script"""
    print("\n" + "="*60)
    print("Example 2: Detect Technical Indicators")
    print("="*60)

    pine_code = """
//@version=5
strategy("RSI Strategy")

// Indicators
rsi = ta.rsi(close, 14)
macdLine, signalLine, hist = ta.macd(close, 12, 26, 9)
atr = ta.atr(14)
[upperBB, basis, lowerBB] = ta.bb(close, 20, 2)

// Entry conditions
longCondition = ta.crossover(rsi, 30)
shortCondition = ta.crossunder(rsi, 70)
"""

    lexer = PineLexer()
    tokens = lexer.tokenize(pine_code)

    # Extract all ta.* calls
    clean_tokens = lexer.get_token_stream(include_whitespace=False)

    indicators_found = []
    for i, token in enumerate(clean_tokens):
        if token.type == TokenType.NAMESPACE and token.value == 'ta':
            if i + 2 < len(clean_tokens) and clean_tokens[i+1].type == TokenType.DOT:
                indicator_name = clean_tokens[i+2].value
                indicators_found.append(f"ta.{indicator_name}")

    print(f"\nIndicators detected in code:")
    for ind in set(indicators_found):
        print(f"  • {ind}")

    # Check if all are supported
    mapper = IndicatorMapper()
    supported = mapper.list_indicators()

    print(f"\nSupport status:")
    for ind in set(indicators_found):
        status = "✓" if ind in supported else "✗"
        print(f"  {status} {ind}")


def example3_calculate_indicators():
    """Example 3: Calculate indicators with real data"""
    print("\n" + "="*60)
    print("Example 3: Calculate Technical Indicators")
    print("="*60)

    # Generate realistic price data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')

    base_price = 50000
    returns = np.random.randn(100) * 0.02
    close = base_price * (1 + returns).cumprod()

    df = pd.DataFrame({
        'close': close,
        'high': close * (1 + np.abs(np.random.randn(100) * 0.01)),
        'low': close * (1 - np.abs(np.random.randn(100) * 0.01)),
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)

    mapper = IndicatorMapper()

    # Calculate various indicators
    print("\nCalculating indicators on sample BTC data...")

    sma_20 = mapper.calculate('ta.sma', df['close'], length=20)
    ema_9 = mapper.calculate('ta.ema', df['close'], length=9)
    rsi = mapper.calculate('ta.rsi', df['close'], length=14)
    macd, signal, hist = mapper.calculate('ta.macd', df['close'])
    upper, basis, lower = mapper.calculate('ta.bb', df['close'], length=20, mult=2.0)

    print(f"\nLatest values:")
    print(f"  Close:       ${df['close'].iloc[-1]:,.2f}")
    print(f"  SMA(20):     ${sma_20.iloc[-1]:,.2f}")
    print(f"  EMA(9):      ${ema_9.iloc[-1]:,.2f}")
    print(f"  RSI(14):     {rsi.iloc[-1]:.2f}")
    print(f"  MACD:        {macd.iloc[-1]:,.2f}")
    print(f"  BB Upper:    ${upper.iloc[-1]:,.2f}")
    print(f"  BB Lower:    ${lower.iloc[-1]:,.2f}")

    # Generate trading signal
    print(f"\nTrading Analysis:")
    trend = "BULLISH" if ema_9.iloc[-1] > sma_20.iloc[-1] else "BEARISH"
    print(f"  Trend:       {trend}")

    if rsi.iloc[-1] > 70:
        print(f"  RSI Signal:  OVERBOUGHT (Sell)")
    elif rsi.iloc[-1] < 30:
        print(f"  RSI Signal:  OVERSOLD (Buy)")
    else:
        print(f"  RSI Signal:  NEUTRAL")

    if hist.iloc[-1] > 0:
        print(f"  MACD Signal: BULLISH")
    else:
        print(f"  MACD Signal: BEARISH")


def example4_strategy_backtest():
    """Example 4: Build a complete strategy"""
    print("\n" + "="*60)
    print("Example 4: Complete Strategy with Signal Generation")
    print("="*60)

    # Generate data
    np.random.seed(123)
    n = 200
    dates = pd.date_range('2024-01-01', periods=n, freq='1h')

    base_price = 45000
    returns = np.random.randn(n) * 0.015
    close = base_price * (1 + returns).cumprod()

    df = pd.DataFrame({
        'close': close,
        'high': close * (1 + np.abs(np.random.randn(n) * 0.008)),
        'low': close * (1 - np.abs(np.random.randn(n) * 0.008)),
        'volume': np.random.randint(1000, 10000, n)
    }, index=dates)

    mapper = IndicatorMapper()

    print("\nStrategy: EMA Crossover with RSI Filter")
    print("-" * 40)

    # Calculate indicators
    ema_fast = mapper.calculate('ta.ema', df['close'], length=9)
    ema_slow = mapper.calculate('ta.ema', df['close'], length=21)
    rsi = mapper.calculate('ta.rsi', df['close'], length=14)

    # Detect crossovers
    bullish_cross = mapper.calculate('ta.crossover', ema_fast, ema_slow)
    bearish_cross = mapper.calculate('ta.crossunder', ema_fast, ema_slow)

    # Generate signals with RSI filter
    df['signal'] = 0
    df.loc[bullish_cross & (rsi < 70), 'signal'] = 1  # Buy
    df.loc[bearish_cross & (rsi > 30), 'signal'] = -1  # Sell

    # Count signals
    buy_signals = (df['signal'] == 1).sum()
    sell_signals = (df['signal'] == -1).sum()

    print(f"\nBacktest Results:")
    print(f"  Period:       {df.index[0]} to {df.index[-1]}")
    print(f"  Total bars:   {len(df)}")
    print(f"  Buy signals:  {buy_signals}")
    print(f"  Sell signals: {sell_signals}")
    print(f"  Total trades: {buy_signals + sell_signals}")

    # Show latest signals
    recent_signals = df[df['signal'] != 0].tail(5)
    if len(recent_signals) > 0:
        print(f"\nRecent signals:")
        for idx, row in recent_signals.iterrows():
            action = "BUY" if row['signal'] == 1 else "SELL"
            print(f"  {idx}: {action} at ${row['close']:,.2f}")

    # Current position
    print(f"\nCurrent Status:")
    print(f"  Price:        ${df['close'].iloc[-1]:,.2f}")
    print(f"  EMA Fast:     ${ema_fast.iloc[-1]:,.2f}")
    print(f"  EMA Slow:     ${ema_slow.iloc[-1]:,.2f}")
    print(f"  RSI:          {rsi.iloc[-1]:.2f}")

    if ema_fast.iloc[-1] > ema_slow.iloc[-1]:
        print(f"  Trend:        BULLISH (Fast > Slow)")
    else:
        print(f"  Trend:        BEARISH (Fast < Slow)")


def example5_multi_timeframe():
    """Example 5: Multi-timeframe analysis"""
    print("\n" + "="*60)
    print("Example 5: Multi-Timeframe Indicator Analysis")
    print("="*60)

    # Generate data for different timeframes
    np.random.seed(456)
    base_price = 48000

    # 5-minute data
    n_5min = 288  # 24 hours
    returns_5min = np.random.randn(n_5min) * 0.01
    close_5min = base_price * (1 + returns_5min).cumprod()

    # 1-hour data (aggregate from 5min)
    close_1h = close_5min.reshape(-1, 12).mean(axis=1)

    mapper = IndicatorMapper()

    print("\nAnalyzing multiple timeframes...")

    # 5-minute timeframe
    df_5min = pd.Series(close_5min)
    ema_9_5min = mapper.calculate('ta.ema', df_5min, length=9)
    rsi_5min = mapper.calculate('ta.rsi', df_5min, length=14)

    # 1-hour timeframe
    df_1h = pd.Series(close_1h)
    ema_9_1h = mapper.calculate('ta.ema', df_1h, length=9)
    rsi_1h = mapper.calculate('ta.rsi', df_1h, length=14)

    print(f"\n5-Minute Timeframe:")
    print(f"  Current price: ${df_5min.iloc[-1]:,.2f}")
    print(f"  EMA(9):        ${ema_9_5min.iloc[-1]:,.2f}")
    print(f"  RSI(14):       {rsi_5min.iloc[-1]:.2f}")

    print(f"\n1-Hour Timeframe:")
    print(f"  Current price: ${df_1h.iloc[-1]:,.2f}")
    print(f"  EMA(9):        ${ema_9_1h.iloc[-1]:,.2f}")
    print(f"  RSI(14):       {rsi_1h.iloc[-1]:.2f}")

    # Multi-timeframe alignment
    print(f"\nMulti-Timeframe Alignment:")

    if rsi_5min.iloc[-1] < 30 and rsi_1h.iloc[-1] < 40:
        print(f"  ✓ Both timeframes oversold - Strong BUY signal")
    elif rsi_5min.iloc[-1] > 70 and rsi_1h.iloc[-1] > 60:
        print(f"  ✓ Both timeframes overbought - Strong SELL signal")
    else:
        print(f"  ⚠ Timeframes diverging - Wait for confirmation")


def example6_indicator_info():
    """Example 6: Explore available indicators"""
    print("\n" + "="*60)
    print("Example 6: Indicator Information & Discovery")
    print("="*60)

    mapper = IndicatorMapper()

    # List all indicators
    all_indicators = mapper.list_indicators()
    print(f"\nTotal indicators available: {len(all_indicators)}")

    # Group by category
    categories = {
        'Trend': ['sma', 'ema', 'wma', 'rma', 'vwma', 'hma', 'alma', 'tema', 'dema'],
        'Momentum': ['rsi', 'macd', 'stoch', 'cci', 'mfi', 'roc', 'wpr', 'mom'],
        'Volatility': ['atr', 'tr', 'bb', 'kc', 'stdev'],
        'Volume': ['vwap', 'obv', 'accdist'],
        'Crossover': ['crossover', 'crossunder', 'cross'],
    }

    print("\nIndicators by category:")
    for category, keywords in categories.items():
        count = sum(1 for ind in all_indicators if any(k in ind for k in keywords))
        print(f"  {category:12s}: {count:2d} indicators")

    # Show detailed info for specific indicators
    print("\nDetailed Information:")
    print("-" * 40)

    examples = ['ta.sma', 'ta.rsi', 'ta.macd', 'ta.bb']
    for ind_name in examples:
        info = mapper.get_indicator_info(ind_name)
        if info:
            print(f"\n{info['name']}:")
            print(f"  Description: {info['description']}")
            print(f"  Parameters:  {', '.join(info['params'])}")
            print(f"  Defaults:    {info['defaults']}")
            if info['returns_multiple']:
                print(f"  Returns:     {', '.join(info['return_names'])}")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("PHASE 1 USAGE EXAMPLES")
    print("Pine Script Lexer & Indicator Mapper")
    print("="*70)

    try:
        example1_basic_lexer()
        example2_detect_indicators()
        example3_calculate_indicators()
        example4_strategy_backtest()
        example5_multi_timeframe()
        example6_indicator_info()

        print("\n" + "="*70)
        print("✅ All examples completed successfully!")
        print("="*70)
        print("\nThese examples demonstrate:")
        print("  • Pine Script tokenization and analysis")
        print("  • Indicator detection from code")
        print("  • Technical indicator calculations")
        print("  • Strategy signal generation")
        print("  • Multi-timeframe analysis")
        print("  • Indicator discovery and information")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
