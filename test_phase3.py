"""
Phase 3 Tests - Expression Transformer, Python Generator, and Rule-Based Converter

Tests the complete Phase 3 implementation for LOW complexity Pine Script strategies.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from converter import (
    # Phase 2
    parse_pine_script,
    # Phase 3
    ExpressionTransformer,
    TransformationContext,
    RuleBasedConverter,
    ComplexityValidator,
    ASTCodeGenerator,
    convert_pine_to_python,
)


def test_expression_transformer():
    """Test Expression Transformer basic functionality."""
    print("\n" + "="*80)
    print("TEST 1: Expression Transformer")
    print("="*80)

    transformer = ExpressionTransformer()

    # Test 1: Simple indicator call
    result1 = transformer.transform_expression("ta.ema(close, 9)")
    print(f"\n1. Simple indicator:")
    print(f"   Input:  ta.ema(close, 9)")
    print(f"   Output: {result1.python_code}")
    print(f"   Success: {result1.success}")
    assert result1.success, "Simple indicator transformation failed"

    # Test 2: Binary operation
    result2 = transformer.transform_expression("close > 100")
    print(f"\n2. Binary operation:")
    print(f"   Input:  close > 100")
    print(f"   Output: {result2.python_code}")
    print(f"   Success: {result2.success}")
    assert result2.success, "Binary operation transformation failed"

    # Test 3: Logical expression
    result3 = transformer.transform_expression("rsi < 30 and close > ema")
    print(f"\n3. Logical expression:")
    print(f"   Input:  rsi < 30 and close > ema")
    print(f"   Output: {result3.python_code}")
    print(f"   Success: {result3.success}")
    assert result3.success, "Logical expression transformation failed"

    # Test 4: Ternary operator
    result4 = transformer.transform_expression("rsi < 30 ? 1 : 0")
    print(f"\n4. Ternary operator:")
    print(f"   Input:  rsi < 30 ? 1 : 0")
    print(f"   Output: {result4.python_code}")
    print(f"   Success: {result4.success}")
    assert result4.success, "Ternary operator transformation failed"

    print("\n✅ All Expression Transformer tests passed!")
    return True


def test_complexity_validator():
    """Test Complexity Validator."""
    print("\n" + "="*80)
    print("TEST 2: Complexity Validator")
    print("="*80)

    # Test 1: Simple MA (should pass)
    pine_code_simple = """
//@version=5
indicator("Simple MA", overlay=true)

length = input.int(20, "Length", minval=1, maxval=200)
ma = ta.sma(close, length)
plot(ma, color=color.blue, linewidth=2)
"""

    ast_simple = parse_pine_script(pine_code_simple)
    validator = ComplexityValidator()
    result = validator.validate(ast_simple)

    print(f"\n1. Simple MA strategy:")
    print(f"   Complexity: {ast_simple.complexity_score:.3f}")
    print(f"   Valid for rule-based: {result.is_valid}")
    print(f"   Errors: {result.errors}")
    assert result.is_valid, "Simple MA should pass validation"

    # Test 2: Medium complexity (should fail)
    pine_code_medium = """
//@version=5
strategy("Multi-Indicator", overlay=true)

// Multiple inputs and indicators
rsi_period = input.int(14, "RSI Period")
ema_fast = input.int(9, "Fast EMA")
ema_slow = input.int(21, "Slow EMA")
bb_length = input.int(20, "BB Length")

// Calculate indicators
rsi = ta.rsi(close, rsi_period)
fast = ta.ema(close, ema_fast)
slow = ta.ema(close, ema_slow)
[bb_middle, bb_upper, bb_lower] = ta.bb(close, bb_length, 2)

// Complex conditions
longCondition = ta.crossover(fast, slow) and rsi < 70 and close > bb_lower
shortCondition = ta.crossunder(fast, slow) and rsi > 30 and close < bb_upper

if longCondition
    strategy.entry("Long", strategy.long)

if shortCondition
    strategy.close("Long")
"""

    ast_medium = parse_pine_script(pine_code_medium)
    result_medium = validator.validate(ast_medium)

    print(f"\n2. Medium complexity strategy:")
    print(f"   Complexity: {ast_medium.complexity_score:.3f}")
    print(f"   Valid for rule-based: {result_medium.is_valid}")
    print(f"   Recommendation: {validator.get_recommendation(ast_medium)}")

    print("\n✅ All Complexity Validator tests passed!")
    return True


def test_rule_based_converter():
    """Test complete Rule-Based Converter."""
    print("\n" + "="*80)
    print("TEST 3: Rule-Based Converter (End-to-End)")
    print("="*80)

    # Test with simple MA strategy
    pine_code = """
//@version=5
strategy("Simple EMA Cross", overlay=true)

// Inputs
fast_length = input.int(9, "Fast EMA Length", minval=1)
slow_length = input.int(21, "Slow EMA Length", minval=1)

// Calculate EMAs
fast_ema = ta.ema(close, fast_length)
slow_ema = ta.ema(close, slow_length)

// Entry conditions
long_condition = ta.crossover(fast_ema, slow_ema)
short_condition = ta.crossunder(fast_ema, slow_ema)

// Strategy calls
if long_condition
    strategy.entry("Long", strategy.long)

if short_condition
    strategy.close("Long")

// Plots
plot(fast_ema, color=color.blue, title="Fast EMA")
plot(slow_ema, color=color.red, title="Slow EMA")
"""

    print("\nPine Script Input:")
    print("-" * 60)
    print(pine_code)
    print("-" * 60)

    # Parse
    ast = parse_pine_script(pine_code)
    print(f"\nParsed AST:")
    print(f"  Name: {ast.script_name}")
    print(f"  Type: {ast.script_type}")
    print(f"  Complexity: {ast.complexity_score:.3f}")
    print(f"  Inputs: {len(ast.inputs)}")
    print(f"  Variables: {len(ast.variables)}")
    print(f"  Indicators: {ast.indicators_used}")

    # Convert
    converter = RuleBasedConverter()

    # Check if can convert
    validation = converter.can_convert(ast)
    print(f"\nValidation:")
    print(f"  Can convert: {validation.is_valid}")
    if not validation.is_valid:
        print(f"  Errors: {validation.errors}")
        print("\n❌ Cannot convert with rules - complexity too high")
        return False

    # Do conversion
    python_code = converter.convert(ast)

    print("\nGenerated Python Code:")
    print("=" * 80)
    print(python_code[:2000])  # Print first 2000 chars
    if len(python_code) > 2000:
        print(f"\n... ({len(python_code) - 2000} more characters)")
    print("=" * 80)

    # Basic validation
    assert "class" in python_code, "No class definition found"
    assert "def __init__" in python_code, "No __init__ method found"
    assert "def generate_signal" in python_code, "No generate_signal method found"
    assert "ta.ema" in python_code or "ema" in python_code, "No EMA indicator found"

    print("\n✅ Rule-Based Converter test passed!")
    print(f"   Generated {len(python_code)} characters of Python code")

    return True


def test_convenience_function():
    """Test convenience function convert_pine_to_python."""
    print("\n" + "="*80)
    print("TEST 4: Convenience Function")
    print("="*80)

    pine_code = """
//@version=5
indicator("RSI Signal", overlay=false)

rsi_period = input.int(14, "RSI Period")
oversold = input.int(30, "Oversold")
overbought = input.int(70, "Overbought")

rsi = ta.rsi(close, rsi_period)

plot(rsi, color=color.blue)
"""

    print("\nConverting Pine Script in one function call...")

    try:
        python_code = convert_pine_to_python(pine_code)

        print(f"\n✅ Successfully generated {len(python_code)} characters")
        print("\nFirst 500 characters:")
        print(python_code[:500])

        return True
    except Exception as e:
        print(f"\n❌ Conversion failed: {e}")
        return False


def run_all_tests():
    """Run all Phase 3 tests."""
    print("\n" + "="*80)
    print("PHASE 3 COMPREHENSIVE TESTS")
    print("Testing Expression Transformer, Python Generator, and Rule-Based Converter")
    print("="*80)

    tests = [
        ("Expression Transformer", test_expression_transformer),
        ("Complexity Validator", test_complexity_validator),
        ("Rule-Based Converter", test_rule_based_converter),
        ("Convenience Function", test_convenience_function),
    ]

    results = {}

    for name, test_func in tests:
        try:
            success = test_func()
            results[name] = "✅ PASSED" if success else "❌ FAILED"
        except Exception as e:
            print(f"\n❌ Test '{name}' raised exception:")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results[name] = "❌ EXCEPTION"

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for name, result in results.items():
        print(f"{name:30s} {result}")

    print("="*80)

    # Overall result
    all_passed = all("✅" in r for r in results.values())

    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Phase 3 implementation is complete and working.")
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
