#!/usr/bin/env python3
"""
Phase 4 LLM Converter - Usage Examples

Demonstrates how to use the new LLM-based converter for complex Pine Scripts.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.converter.pine_parser import parse_pine_script
from src.converter.llm import UnifiedConverter, ConversionStrategy


# ============================================================================
# Example Pine Scripts
# ============================================================================

SIMPLE_MA_CROSSOVER = """
//@version=5
strategy("MA Crossover", overlay=true)

// Inputs
fastLength = input.int(10, "Fast MA Period")
slowLength = input.int(20, "Slow MA Period")

// Calculate MAs
fastMA = ta.sma(close, fastLength)
slowMA = ta.sma(close, slowLength)

// Strategy logic
if ta.crossover(fastMA, slowMA)
    strategy.entry("Long", strategy.long)

if ta.crossunder(fastMA, slowMA)
    strategy.close("Long")

// Plot
plot(fastMA, "Fast MA", color=color.blue)
plot(slowMA, "Slow MA", color=color.red)
"""

COMPLEX_STRATEGY = """
//@version=5
strategy("Advanced RSI + MACD", overlay=false)

// Inputs
rsiLength = input.int(14, "RSI Length")
rsiOverbought = input.float(70.0, "RSI Overbought")
rsiOversold = input.float(30.0, "RSI Oversold")
macdFast = input.int(12, "MACD Fast")
macdSlow = input.int(26, "MACD Slow")
macdSignal = input.int(9, "MACD Signal")

// Custom function
calcCustomRSI(src, length) =>
    up = ta.rma(math.max(ta.change(src), 0), length)
    down = ta.rma(-math.min(ta.change(src), 0), length)
    rs = up / down
    100 - (100 / (1 + rs))

// Indicators
rsi = calcCustomRSI(close, rsiLength)
[macdLine, signalLine, histLine] = ta.macd(close, macdFast, macdSlow, macdSignal)

// Complex conditions
longCondition = rsi < rsiOversold and ta.crossover(macdLine, signalLine)
shortCondition = rsi > rsiOverbought and ta.crossunder(macdLine, signalLine)

// Strategy execution
if longCondition
    strategy.entry("Long", strategy.long)

if shortCondition
    strategy.entry("Short", strategy.short)

// Plots
plot(rsi, "RSI", color=color.purple)
hline(rsiOverbought, "Overbought", color=color.red)
hline(rsiOversold, "Oversold", color=color.green)
plot(macdLine, "MACD", color=color.blue)
plot(signalLine, "Signal", color=color.orange)
"""


# ============================================================================
# Example Functions
# ============================================================================

async def example_1_simple_conversion():
    """Example 1: Simple conversion with auto-strategy selection"""
    print("\n" + "=" * 60)
    print("Example 1: Simple MA Crossover (Auto-Strategy)")
    print("=" * 60)

    # Initialize converter (no API key needed for simple strategies)
    converter = UnifiedConverter()

    # Convert
    result = await converter.convert_from_code(SIMPLE_MA_CROSSOVER)

    # Display results
    print(f"\nStrategy Used: {result.strategy_used}")
    print(f"Complexity: {result.complexity_score:.3f}")
    print(f"Cost: ${result.cost_usd:.4f}")
    print(f"Time: {result.time_seconds:.2f}s")
    print(f"\nGenerated Python Code:")
    print("-" * 60)
    print(result.python_code[:500] + "...")  # First 500 chars


async def example_2_llm_conversion():
    """Example 2: Complex strategy with LLM conversion"""
    print("\n" + "=" * 60)
    print("Example 2: Complex Strategy (LLM Required)")
    print("=" * 60)

    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not set. Skipping LLM example.")
        print("    Set with: export ANTHROPIC_API_KEY='sk-ant-...'")
        return

    # Initialize converter with API key
    converter = UnifiedConverter(api_key=api_key)

    # Parse first to show complexity
    ast = parse_pine_script(COMPLEX_STRATEGY)
    print(f"\nParsed Strategy:")
    print(f"  - Name: {ast.script_name}")
    print(f"  - Complexity: {ast.complexity_score:.3f}")
    print(f"  - Indicators: {', '.join(ast.indicators_used)}")
    print(f"  - Custom Functions: {len(ast.functions)}")

    # Estimate cost first
    estimated_cost = converter.estimate_cost(ast)
    print(f"\nEstimated Cost: ${estimated_cost:.4f}")

    # Convert
    print("\nConverting with LLM (this may take 20-30 seconds)...")
    result = await converter.convert(ast)

    # Display results
    print(f"\nStrategy Used: {result.strategy_used}")
    print(f"Actual Cost: ${result.cost_usd:.4f}")
    print(f"Tokens Used: {result.tokens_used}")
    print(f"Time: {result.time_seconds:.1f}s")
    print(f"Validation: {'✓ PASSED' if result.validation_passed else '✗ FAILED'}")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for warning in result.warnings[:3]:  # Show first 3
            print(f"  - {warning}")

    print(f"\nGenerated Python Code ({len(result.python_code)} chars):")
    print("-" * 60)
    print(result.python_code[:800] + "...")


async def example_3_strategy_comparison():
    """Example 3: Compare different conversion strategies"""
    print("\n" + "=" * 60)
    print("Example 3: Strategy Comparison")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not set. Skipping comparison.")
        return

    converter = UnifiedConverter(api_key=api_key)
    ast = parse_pine_script(SIMPLE_MA_CROSSOVER)

    strategies = [
        ConversionStrategy.RULE_BASED,
        ConversionStrategy.HYBRID,
        # ConversionStrategy.LLM_ONLY,  # Expensive, commented out
    ]

    print(f"\nComparing strategies for: {ast.script_name}")
    print(f"Complexity: {ast.complexity_score:.3f}\n")

    for strategy in strategies:
        print(f"\n{strategy.value.upper()}:")
        print("-" * 40)

        result = await converter.convert(ast, force_strategy=strategy)

        print(f"  Cost: ${result.cost_usd:.4f}")
        print(f"  Time: {result.time_seconds:.2f}s")
        print(f"  Code Length: {len(result.python_code)} chars")
        print(f"  Validation: {'✓' if result.validation_passed else '✗'}")


async def example_4_batch_conversion():
    """Example 4: Batch convert multiple strategies"""
    print("\n" + "=" * 60)
    print("Example 4: Batch Conversion")
    print("=" * 60)

    strategies = {
        "Simple MA": SIMPLE_MA_CROSSOVER,
        "Complex RSI+MACD": COMPLEX_STRATEGY,
    }

    api_key = os.getenv("ANTHROPIC_API_KEY")
    converter = UnifiedConverter(api_key=api_key) if api_key else UnifiedConverter()

    total_cost = 0.0
    total_time = 0.0

    for name, code in strategies.items():
        print(f"\n{'Converting'}: {name}")
        try:
            result = await converter.convert_from_code(code)

            print(f"  ✓ {result.strategy_used} (${result.cost_usd:.4f})")

            total_cost += result.cost_usd
            total_time += result.time_seconds

        except Exception as e:
            print(f"  ✗ Failed: {e}")

    print(f"\nBatch Summary:")
    print(f"  Total Cost: ${total_cost:.4f}")
    print(f"  Total Time: {total_time:.1f}s")


# ============================================================================
# Main
# ============================================================================

async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("Phase 4 LLM Converter - Examples")
    print("=" * 60)

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n⚠️  WARNING: ANTHROPIC_API_KEY not set")
        print("    Some examples will be skipped.")
        print("    Set with: export ANTHROPIC_API_KEY='sk-ant-...'")

    # Run examples
    await example_1_simple_conversion()
    await example_2_llm_conversion()
    await example_3_strategy_comparison()
    await example_4_batch_conversion()

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
