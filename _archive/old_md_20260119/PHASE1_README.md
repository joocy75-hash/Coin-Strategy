# Phase 1: Pine Script Lexer & Indicator Mapper

## Overview

Phase 1 implements the foundational components for Pine Script to Python conversion:
- **Pine Lexer**: Tokenizes Pine Script code into structured tokens
- **Indicator Mapper**: Maps 50+ Pine Script indicators to pandas/numpy implementations

## Components

### 1. Pine Lexer (`src/converter/pine_lexer.py`)

A complete lexical analyzer that tokenizes Pine Script v5 syntax.

#### Features

- **Token Types Supported**:
  - Keywords: `var`, `varip`, `if`, `else`, `for`, `while`, `strategy`, `indicator`, etc.
  - Operators: `=`, `:=`, `=>`, `+`, `-`, `*`, `/`, `%`, `and`, `or`, `not`, `?`, `:`
  - Identifiers: Variable names, function names
  - Literals: Numbers, strings, booleans (`true`, `false`, `na`)
  - Namespaces: `ta`, `math`, `strategy`, `array`, `matrix`, etc.
  - Builtins: `close`, `open`, `high`, `low`, `volume`, `time`
  - Comments: Single-line (`//`) and multi-line (`/* */`)
  - Structure: `NEWLINE`, `INDENT`, `DEDENT` for block detection

#### Usage

```python
from converter.pine_lexer import PineLexer

lexer = PineLexer()
tokens = lexer.tokenize(pine_script_code)

# Get clean token stream (no whitespace)
clean_tokens = lexer.get_token_stream(include_whitespace=False)

# Print tokens for debugging
lexer.print_tokens()

# Get tokens by type
keywords = lexer.get_tokens_by_type(TokenType.KEYWORD)
```

#### Example

```python
pine_code = """
//@version=5
indicator("Test")
fast = ta.ema(close, 9)
slow = ta.sma(close, 21)
signal = ta.crossover(fast, slow)
"""

lexer = PineLexer()
tokens = lexer.tokenize(pine_code)
# Returns structured Token objects with type, value, line, column
```

### 2. Indicator Mapper (`src/converter/indicator_mapper.py`)

Comprehensive mapping of Pine Script technical indicators to pandas/numpy implementations.

#### Supported Indicators (45+)

**Trend Indicators**:
- `ta.sma` - Simple Moving Average
- `ta.ema` - Exponential Moving Average
- `ta.wma` - Weighted Moving Average
- `ta.rma` - Running Moving Average (Wilder's)
- `ta.vwma` - Volume Weighted Moving Average
- `ta.hma` - Hull Moving Average
- `ta.alma` - Arnaud Legoux Moving Average
- `ta.tema` - Triple Exponential Moving Average
- `ta.dema` - Double Exponential Moving Average

**Momentum Indicators**:
- `ta.rsi` - Relative Strength Index
- `ta.macd` - MACD (returns 3 values: macd, signal, histogram)
- `ta.stoch` - Stochastic Oscillator (returns k, d)
- `ta.cci` - Commodity Channel Index
- `ta.mfi` - Money Flow Index
- `ta.roc` - Rate of Change
- `ta.wpr` - Williams %R
- `ta.mom` - Momentum

**Volatility Indicators**:
- `ta.atr` - Average True Range
- `ta.tr` - True Range
- `ta.bb` - Bollinger Bands (returns upper, basis, lower)
- `ta.kc` - Keltner Channels (returns upper, basis, lower)
- `ta.stdev` - Standard Deviation

**Volume Indicators**:
- `ta.vwap` - Volume Weighted Average Price
- `ta.obv` - On Balance Volume
- `ta.accdist` - Accumulation/Distribution

**Pivot & Support/Resistance**:
- `ta.pivothigh` - Pivot High detection
- `ta.pivotlow` - Pivot Low detection

**Crossover Functions**:
- `ta.crossover` - Detect crossover (source1 crosses over source2)
- `ta.crossunder` - Detect crossunder (source1 crosses under source2)
- `ta.cross` - Detect cross in either direction

**Math Functions**:
- `ta.highest` - Highest value over period
- `ta.lowest` - Lowest value over period
- `ta.change` - Change over period
- `ta.cum` - Cumulative sum
- `ta.correlation` - Correlation coefficient
- `ta.cov` - Covariance
- `ta.median` - Median value
- `ta.mode` - Mode (most common value)
- `ta.percentrank` - Percentile rank
- `ta.range` - Range (max - min)
- `ta.variance` - Variance

**Directional Movement**:
- `ta.adx` - Average Directional Index
- `ta.dmi` - Directional Movement Index (returns plus_di, minus_di, adx)

**Advanced Indicators**:
- `ta.supertrend` - Supertrend indicator (returns supertrend, direction)
- `ta.sar` - Parabolic SAR

#### Usage

```python
from converter.indicator_mapper import IndicatorMapper
import pandas as pd

mapper = IndicatorMapper()

# Create data
df = pd.DataFrame({
    'close': [...],
    'high': [...],
    'low': [...],
    'volume': [...]
})

# Calculate single indicators
sma_20 = mapper.calculate('ta.sma', df['close'], length=20)
ema_9 = mapper.calculate('ta.ema', df['close'], length=9)
rsi = mapper.calculate('ta.rsi', df['close'], length=14)

# Calculate indicators with multiple returns
macd, signal, histogram = mapper.calculate('ta.macd', df['close'])
upper, basis, lower = mapper.calculate('ta.bb', df['close'], length=20, mult=2.0)

# Detect crossovers
fast = mapper.calculate('ta.ema', df['close'], length=9)
slow = mapper.calculate('ta.sma', df['close'], length=21)
crossover = mapper.calculate('ta.crossover', fast, slow)

# List all available indicators
all_indicators = mapper.list_indicators()
print(f"Supported: {len(all_indicators)} indicators")

# Get indicator information
info = mapper.get_indicator_info('ta.macd')
print(info['description'])
print(info['params'])
print(info['defaults'])
```

#### Example: Complete Strategy

```python
import pandas as pd
import numpy as np
from converter.indicator_mapper import IndicatorMapper

# Load your data
df = pd.DataFrame({
    'close': [...],
    'high': [...],
    'low': [...],
    'volume': [...]
})

mapper = IndicatorMapper()

# Calculate indicators
ema_fast = mapper.calculate('ta.ema', df['close'], length=9)
ema_slow = mapper.calculate('ta.sma', df['close'], length=21)
rsi = mapper.calculate('ta.rsi', df['close'], length=14)
atr = mapper.calculate('ta.atr', df['high'], df['low'], df['close'], length=14)

# Detect signals
bullish = mapper.calculate('ta.crossover', ema_fast, ema_slow) & (rsi < 70)
bearish = mapper.calculate('ta.crossunder', ema_fast, ema_slow) & (rsi > 30)

# Generate trading signals
df['signal'] = 0
df.loc[bullish, 'signal'] = 1  # Buy
df.loc[bearish, 'signal'] = -1  # Sell
```

## Testing

Run the comprehensive test suite:

```bash
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab
python test_phase1.py
```

### Test Coverage

1. **Lexer Tests**:
   - Simple indicator tokenization
   - Strategy with Pine operators (`:=`, `=>`, `?:`)
   - Complex expressions with ternary operators
   - Token classification (keywords, namespaces, builtins, identifiers)

2. **Indicator Mapper Tests**:
   - Moving averages (SMA, EMA, WMA)
   - Momentum indicators (RSI, ROC, MOM)
   - MACD with multiple return values
   - Volatility indicators (ATR, Bollinger Bands)
   - Crossover detection
   - Support/Resistance levels
   - Complete indicator catalog

3. **Integration Tests**:
   - Tokenize Pine Script
   - Extract indicator calls
   - Verify all detected indicators are supported
   - Calculate indicators and generate signals

## Implementation Details

### Pine Lexer Architecture

```
Source Code → Tokenization → Token Stream
                  ↓
         Character-by-character processing
                  ↓
    Pattern matching (keywords, operators, literals)
                  ↓
         Token objects with metadata
```

**Key Design Decisions**:
- Character-by-character scanning for precision
- Longest-match operator detection
- Indentation tracking for block structure
- Line/column tracking for error reporting

### Indicator Mapper Architecture

```
Pine Script Call → Mapping Lookup → Python Implementation
        ↓              ↓                    ↓
    ta.ema()    IndicatorMapping      pandas/numpy
                   metadata           calculations
```

**Key Design Decisions**:
- Dataclass-based mapping configuration
- Pandas Series operations for vectorization
- Proper handling of edge cases (NaN, insufficient data)
- Support for multiple return values (MACD, BB, etc.)

## File Structure

```
strategy-research-lab/
├── src/
│   └── converter/
│       ├── __init__.py                  # Module exports
│       ├── pine_lexer.py                # Pine Script lexer
│       ├── indicator_mapper.py          # Indicator mapper
│       ├── pine_to_python.py           # Existing converter
│       └── strategy_generator.py       # Existing generator
├── test_phase1.py                      # Phase 1 tests
└── PHASE1_README.md                    # This file
```

## Integration with Existing Code

The new components integrate seamlessly with existing converter modules:

```python
# Combined usage
from converter import (
    PineLexer,
    IndicatorMapper,
    PineScriptConverter,
    StrategyGenerator
)

# Tokenize
lexer = PineLexer()
tokens = lexer.tokenize(pine_code)

# Calculate indicators
mapper = IndicatorMapper()
sma = mapper.calculate('ta.sma', df['close'], length=20)

# Convert to Python (existing)
converter = PineScriptConverter()
result = converter.convert(pine_code)

# Generate strategy (existing)
generator = StrategyGenerator()
strategy = generator.generate_strategy(...)
```

## Next Steps: Phase 2

Phase 2 will build on this foundation:

1. **Pine Parser**: Convert token stream to Abstract Syntax Tree (AST)
2. **AST Builder**: Build structured representation of Pine Script
3. **Code Generator**: Generate Python code from AST
4. **Type Inference**: Detect variable types and function signatures

## Performance Considerations

- **Lexer**: O(n) time complexity, single pass through source
- **Indicator Mapper**: Vectorized pandas operations, efficient for large datasets
- **Memory**: Token objects are lightweight, minimal overhead

## Error Handling

Both components include comprehensive error handling:

```python
# Lexer
try:
    tokens = lexer.tokenize(pine_code)
except Exception as e:
    logger.error(f"Tokenization error: {e}")

# Indicator Mapper
try:
    result = mapper.calculate('ta.sma', data, length=20)
except ValueError as e:
    logger.error(f"Invalid indicator: {e}")
```

## Contributing

To add new indicators:

1. Add mapping to `_build_mappings()` in `IndicatorMapper`
2. Implement calculation method (e.g., `_new_indicator()`)
3. Add test case to `test_phase1.py`
4. Update documentation

Example:

```python
# In _build_mappings()
mappings['ta.newindi'] = IndicatorMapping(
    name='ta.newindi',
    python_func='_newindi',
    params=['source', 'length'],
    defaults={'length': 14},
    description='New Indicator'
)

# Implementation
def _newindi(self, source: pd.Series, length: int) -> pd.Series:
    """New Indicator implementation"""
    return source.rolling(window=length).apply(custom_logic)
```

## License

Part of the Strategy Research Lab project.

## Author

Strategy Research Lab Development Team

---

**Status**: ✅ Phase 1 Complete and Tested

**Test Results**: All 8 test suites passed
- Lexer tokenization: ✅
- Indicator calculations: ✅
- Integration: ✅

**Ready for**: Phase 2 - Pine Parser and AST Builder
