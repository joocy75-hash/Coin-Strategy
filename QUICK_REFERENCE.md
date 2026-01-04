# Pine Script to Python Converter - Quick Reference

**Last Updated**: January 4, 2026
**Current Status**: Phase 1 ✅ + Phase 2 ✅ Complete

---

## Installation & Testing

```bash
# Navigate to project
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab

# Run Phase 1 tests (Lexer + Indicator Mapper)
python test_phase1.py

# Run Phase 2 tests (Parser + AST Builder)
python test_phase2.py
```

---

## Phase 1: Pine Lexer + Indicator Mapper

### Pine Lexer - Quick Start

```python
from converter import PineLexer

lexer = PineLexer()
tokens = lexer.tokenize(pine_script_code)

# Get clean token stream (no whitespace/comments)
clean_tokens = lexer.get_token_stream(include_whitespace=False)

# Print tokens for debugging
lexer.print_tokens()
```

### Indicator Mapper - Quick Start

```python
from converter import IndicatorMapper
import pandas as pd

mapper = IndicatorMapper()

# Single indicators
sma = mapper.calculate('ta.sma', df['close'], length=20)
ema = mapper.calculate('ta.ema', df['close'], length=9)
rsi = mapper.calculate('ta.rsi', df['close'], length=14)

# Multiple return values
macd, signal, histogram = mapper.calculate('ta.macd', df['close'])
upper, basis, lower = mapper.calculate('ta.bb', df['close'], length=20, mult=2.0)

# Crossover detection
crossover = mapper.calculate('ta.crossover', fast, slow)
```

### Supported Indicators (45+)

**Trend**: SMA, EMA, WMA, RMA, VWMA, HMA, ALMA, TEMA, DEMA
**Momentum**: RSI, MACD, Stoch, CCI, MFI, ROC, WPR, MOM
**Volatility**: ATR, TR, BB, KC, StdDev, Variance, Range
**Volume**: VWAP, OBV, AccDist
**Crossover**: Crossover, Crossunder, Cross
**Math**: Highest, Lowest, Change, Cum, Correlation, etc.
**Pivot**: PivotHigh, PivotLow
**Directional**: ADX, DMI
**Advanced**: Supertrend, SAR

---

## Phase 2: Pine Parser + AST Builder ✨ NEW

### Basic Parsing

```python
from converter import parse_pine_script, print_ast_summary

# One-step parsing
ast = parse_pine_script(pine_code)

# Print summary with complexity visualization
print_ast_summary(ast)
```

### Complexity-Based Decision Making

```python
ast = parse_pine_script(pine_code)

if ast.complexity_score < 0.3:
    print("LOW complexity - Use rule-based conversion")
    # TODO: Phase 3 implementation
elif ast.complexity_score < 0.7:
    print("MEDIUM complexity - Use hybrid approach")
    # TODO: Phase 4 implementation
else:
    print("HIGH complexity - Use LLM conversion")
    # TODO: Phase 4 implementation
```

### Accessing AST Components

```python
ast = parse_pine_script(pine_code)

# Basic info
print(f"Script: {ast.script_name}")
print(f"Type: {ast.script_type}")
print(f"Version: {ast.version}")
print(f"Complexity: {ast.complexity_score:.2f}")

# Inputs
for inp in ast.inputs:
    print(f"Input: {inp.name} ({inp.input_type}) = {inp.default_value}")

# Variables
for var in ast.variables:
    print(f"Variable: {var.name} = {var.value_expr}")

# Functions
for func in ast.functions:
    print(f"Function: {func.name}({len(func.parameters)} params)")

# Strategy calls
for call in ast.strategy_calls:
    print(f"Strategy: {call.call_type}('{call.id_value}')")
    if call.when:
        print(f"  Condition: {call.when}")

# Indicators
print(f"Indicators: {', '.join(ast.indicators_used)}")

# Complexity factors
for factor, value in ast.complexity_factors.items():
    print(f"{factor}: {value:.2f}")
```

### Advanced Parsing

```python
from converter import PineLexer, PineParser, PineAST

# Step-by-step parsing
lexer = PineLexer()
tokens = lexer.tokenize(pine_code)

parser = PineParser(tokens, raw_code=pine_code)
ast = parser.parse()

# Access parsed components
inputs = ast.inputs
variables = ast.variables
functions = ast.functions
strategy_calls = ast.strategy_calls
plots = ast.plots

# Complexity analysis
score = ast.complexity_score
factors = ast.complexity_factors
```

---

## Complexity Scoring Reference

### Factors (8 Total)

| Factor | Weight | Description | Threshold |
|--------|--------|-------------|-----------|
| Lines | 25% | Code line count | 150 lines = 1.0 |
| Functions | 20% | Custom functions | 3 functions = 1.0 |
| Custom Types | 15% | User-defined types | 2 types = 1.0 |
| Arrays/Matrices | 10% | Array operations | 8 operations = 1.0 |
| Drawing | 5% | Visual indicators | 3 drawings = 1.0 |
| Nesting | 10% | Conditional depth | 3 levels = 1.0 |
| Indicators | 10% | ta.* usage | 8 indicators = 1.0 |
| Variables | 5% | Variable count | 20 variables = 1.0 |

### Score Categories

- **0.0-0.3**: LOW complexity
  - Simple scripts
  - Standard indicators only
  - No custom logic
  - **→ Use rule-based conversion**

- **0.3-0.7**: MEDIUM complexity
  - Multiple indicators
  - Some custom logic
  - Moderate nesting
  - **→ Use hybrid approach**

- **0.7-1.0**: HIGH complexity
  - Custom functions
  - Custom types
  - Array operations
  - Deep nesting
  - **→ Use LLM conversion**

---

## Complete Examples

### Example 1: Simple Strategy (Phase 1 + Phase 2)

```python
from converter import (
    PineLexer,
    IndicatorMapper,
    parse_pine_script,
    print_ast_summary
)

pine_code = """
//@version=5
strategy("SMA Cross", overlay=true)

length = input.int(20, "Length")
ma = ta.sma(close, length)

if close > ma
    strategy.entry("Long", strategy.long)
if close < ma
    strategy.close("Long")

plot(ma, color=color.blue)
"""

# Phase 1: Tokenize and get indicator info
lexer = PineLexer()
tokens = lexer.tokenize(pine_code)
print(f"Total tokens: {len(tokens)}")

# Phase 2: Parse and analyze
ast = parse_pine_script(pine_code)
print_ast_summary(ast)

# Decision making
if ast.complexity_score < 0.3:
    print("\n→ Use rule-based conversion (Phase 3)")
```

### Example 2: Extract All Components

```python
ast = parse_pine_script(pine_code)

# Extract inputs with defaults
input_params = {}
for inp in ast.inputs:
    input_params[inp.name] = {
        'type': inp.input_type,
        'default': inp.default_value,
        'title': inp.title,
        'min': inp.min_value,
        'max': inp.max_value
    }

# Extract indicators for calculation
indicators_needed = []
for var in ast.variables:
    for indicator in ast.indicators_used:
        if indicator in var.value_expr:
            indicators_needed.append({
                'name': indicator,
                'variable': var.name,
                'expression': var.value_expr
            })

# Extract strategy logic
strategy_logic = []
for call in ast.strategy_calls:
    strategy_logic.append({
        'type': call.call_type,
        'id': call.id_value,
        'direction': call.direction,
        'condition': call.when
    })

print(f"Inputs: {len(input_params)}")
print(f"Indicators: {len(indicators_needed)}")
print(f"Strategy calls: {len(strategy_logic)}")
```

### Example 3: Complexity Analysis

```python
ast = parse_pine_script(pine_code)

# Detailed complexity breakdown
print(f"\nComplexity Analysis for: {ast.script_name}")
print(f"Overall Score: {ast.complexity_score:.3f}")
print("\nFactor Breakdown:")

for factor, value in sorted(ast.complexity_factors.items(), key=lambda x: x[1], reverse=True):
    # Visual bar (20 chars max)
    bar = "█" * int(value * 20)
    # Category based on value
    category = "HIGH" if value > 0.7 else "MED" if value > 0.3 else "LOW"
    print(f"  {factor:15s}: {value:.2f} {bar:20s} [{category}]")

# Recommendation
if ast.complexity_score < 0.3:
    recommendation = "RULE-BASED (Fast, reliable)"
elif ast.complexity_score < 0.7:
    recommendation = "HYBRID (Balanced approach)"
else:
    recommendation = "LLM (Most accurate)"

print(f"\nRecommendation: {recommendation}")

# Detailed stats
print(f"\nStatistics:")
print(f"  Total lines:     {ast.total_lines}")
print(f"  Code lines:      {ast.code_lines}")
print(f"  Inputs:          {len(ast.inputs)}")
print(f"  Variables:       {len(ast.variables)}")
print(f"  Functions:       {len(ast.functions)}")
print(f"  Indicators:      {len(ast.indicators_used)}")
print(f"  Strategy calls:  {len(ast.strategy_calls)}")
```

---

## Common Patterns

### Pattern 1: EMA Crossover with RSI Filter

```python
# Using Phase 1 (Indicator Mapper)
mapper = IndicatorMapper()

fast = mapper.calculate('ta.ema', df['close'], length=9)
slow = mapper.calculate('ta.ema', df['close'], length=21)
rsi = mapper.calculate('ta.rsi', df['close'], length=14)

bullish = mapper.calculate('ta.crossover', fast, slow) & (rsi < 70)
bearish = mapper.calculate('ta.crossunder', fast, slow) & (rsi > 30)
```

### Pattern 2: Bollinger Bands Breakout

```python
upper, basis, lower = mapper.calculate('ta.bb', df['close'], length=20, mult=2.0)

breakout_up = df['close'] > upper
breakout_down = df['close'] < lower
squeeze = (upper - lower) / basis < 0.1  # Low volatility
```

### Pattern 3: Multi-Indicator Confluence

```python
ema = mapper.calculate('ta.ema', df['close'], length=20)
rsi = mapper.calculate('ta.rsi', df['close'], length=14)
macd, signal, _ = mapper.calculate('ta.macd', df['close'])

# Buy when all align
strong_buy = (df['close'] > ema) & (rsi < 70) & (macd > signal)

# Sell when all reverse
strong_sell = (df['close'] < ema) & (rsi > 30) & (macd < signal)
```

---

## Performance Tips

1. **Parse once, use multiple times**: Store the AST object
   ```python
   ast = parse_pine_script(pine_code)  # Do once
   # Use ast.inputs, ast.variables, etc. multiple times
   ```

2. **Calculate indicators once**: Reuse calculated series
   ```python
   ema = mapper.calculate('ta.ema', df['close'], length=20)  # Once
   signal1 = ema > df['close']  # Reuse
   signal2 = ema.shift(1) < df['close'].shift(1)  # Reuse
   ```

3. **Use vectorized operations**: All indicators are already vectorized

4. **Filter data first**: Apply date/symbol filters before calculation

---

## Error Handling

```python
# Parsing errors
try:
    ast = parse_pine_script(pine_code)
except Exception as e:
    print(f"Parsing error: {e}")

# Indicator calculation errors
try:
    result = mapper.calculate('ta.unknown', df['close'])
except ValueError as e:
    print(f"Unknown indicator: {e}")

# Check for required data
if ast.code_lines == 0:
    print("Warning: No code lines detected")

if len(ast.indicators_used) == 0:
    print("Warning: No indicators detected")
```

---

## Documentation Files

| File | Description | Lines |
|------|-------------|-------|
| `PHASE1_README.md` | Phase 1 complete guide | 350+ |
| `PHASE1_SUMMARY.md` | Phase 1 implementation summary | 360+ |
| `PHASE2_README.md` | Phase 2 complete guide | 1,000+ |
| `PHASE2_SUMMARY.md` | Phase 2 implementation summary | 650+ |
| `test_phase1.py` | Phase 1 test suite | 400+ |
| `test_phase2.py` | Phase 2 test suite | 400+ |
| `QUICK_REFERENCE.md` | This file | 350+ |

---

## Import Reference

```python
# Phase 1 + Phase 2 - Complete import
from converter import (
    # Phase 1: Lexer
    PineLexer,
    Token,
    TokenType,

    # Phase 1: Indicator Mapper
    IndicatorMapper,
    IndicatorMapping,

    # Phase 2: Parser
    PineParser,
    PineAST,

    # Phase 2: AST Nodes
    InputNode,
    VariableNode,
    FunctionNode,
    StrategyCallNode,
    PlotNode,
    ConditionNode,
    ExpressionNode,

    # Phase 2: Utilities
    parse_pine_script,
    print_ast_summary,
)
```

---

## Quick Commands

```bash
# Test everything
python test_phase1.py && python test_phase2.py

# Verify installation
python -c "from converter import parse_pine_script; print('✓ Ready')"

# Check version
python -c "from converter import PineParser; print('Phase 2 installed')"

# Run example
python examples/phase1_usage.py
```

---

## Status Summary

| Phase | Status | Tests | Lines | Features |
|-------|--------|-------|-------|----------|
| **Phase 1** | ✅ Complete | 12/12 ✅ | 1,500+ | Lexer + 45 Indicators |
| **Phase 2** | ✅ Complete | 7/7 ✅ | 1,300+ | Parser + AST + Complexity |
| **Phase 3** | 🔜 Pending | - | - | Expression Transformer |
| **Phase 4** | 🔜 Pending | - | - | LLM Converter |
| **Phase 5** | 🔜 Pending | - | - | Top 5 Testing |

**Current Capabilities**:
- ✅ Full Pine Script tokenization
- ✅ 45+ technical indicators with pandas/numpy
- ✅ Complete AST parsing
- ✅ Intelligent complexity scoring (0.0-1.0)
- ✅ Indicator detection and extraction
- ✅ Input/variable/function parsing
- ✅ Strategy call extraction
- ⏳ Python code generation (Phase 3)
- ⏳ LLM-based conversion (Phase 4)

---

**Need Help?**
- Run `python test_phase1.py` for Phase 1 verification
- Run `python test_phase2.py` for Phase 2 verification
- Check `PHASE1_README.md` for Phase 1 detailed documentation
- Check `PHASE2_README.md` for Phase 2 detailed documentation
- See `examples/phase1_usage.py` for working examples

---

*Last Updated: January 4, 2026*
*Total Implementation: Phase 1 + Phase 2 Complete*
*Next: Phase 3 - Expression Transformer and Python Generator*
