"""
LLM Prompt Builder for Pine Script Conversion

Builds optimized prompts for Claude to convert Pine Scripts to Python
with high accuracy and minimal token usage.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..pine_parser import PineAST, InputNode, VariableNode, FunctionNode

logger = logging.getLogger(__name__)


# ============================================================================
# Prompt Templates
# ============================================================================

class PromptTemplate(Enum):
    """Predefined prompt templates"""
    BASIC_CONVERSION = "basic_conversion"
    WITH_INDICATORS = "with_indicators"
    WITH_CUSTOM_FUNCTIONS = "with_custom_functions"
    REFINEMENT = "refinement"


# ============================================================================
# Prompt Builder
# ============================================================================

class LLMPromptBuilder:
    """
    Build optimized prompts for Claude to convert Pine Scripts.

    Prompt engineering optimizations:
    - Clear task description
    - Structured input format
    - Explicit output requirements
    - Examples where helpful
    - Minimal token usage

    Example:
        >>> builder = LLMPromptBuilder()
        >>> prompt = builder.build_conversion_prompt(ast)
        >>> len(prompt)  # Optimized for cost
        2847
    """

    # System-level instructions (prepended to all prompts)
    SYSTEM_INSTRUCTIONS = """You are an expert in converting TradingView Pine Script strategies to Python for backtesting.

Key requirements:
1. Generate a complete Python class inheriting from `backtesting.Strategy`
2. Implement `init()` and `next()` methods following backtesting.py conventions
3. Use pandas-ta for technical indicators (e.g., `ta.sma()`, `ta.rsi()`)
4. Preserve ALL strategy logic, parameters, and conditions from the Pine Script
5. Add proper error handling and type hints
6. Include detailed docstrings

Output ONLY valid Python code without explanations."""

    def __init__(self):
        """Initialize prompt builder"""
        self.template_cache: Dict[str, str] = {}
        logger.debug("Initialized LLMPromptBuilder")

    def build_conversion_prompt(
        self,
        ast: PineAST,
        template: PromptTemplate = PromptTemplate.BASIC_CONVERSION,
        include_examples: bool = False,
    ) -> str:
        """
        Build conversion prompt from Pine Script AST.

        Args:
            ast: Parsed Pine Script AST
            template: Prompt template to use
            include_examples: Include code examples (increases tokens)

        Returns:
            Complete prompt for Claude

        Example:
            >>> prompt = builder.build_conversion_prompt(ast)
            >>> "Convert the following Pine Script" in prompt
            True
        """
        logger.debug(f"Building conversion prompt for '{ast.script_name}'")

        # Build prompt sections
        sections = [
            self.SYSTEM_INSTRUCTIONS,
            "",
            "# Task",
            f"Convert the following Pine Script **{ast.script_type}** to Python for backtesting.",
            "",
            "# Pine Script Code",
            "```pinescript",
            ast.raw_code.strip(),
            "```",
            "",
            "# Strategy Metadata",
            f"- **Name**: {ast.script_name}",
            f"- **Type**: {ast.script_type}",
            f"- **Pine Version**: v{ast.version}",
            f"- **Complexity**: {ast.complexity_score:.3f}",
            "",
        ]

        # Add inputs section if present
        if ast.inputs:
            sections.extend(self._build_inputs_section(ast.inputs))

        # Add indicators section if present
        if ast.indicators_used:
            sections.extend(self._build_indicators_section(ast.indicators_used))

        # Add custom functions section if present
        if ast.functions:
            sections.extend(self._build_functions_section(ast.functions))

        # Add output requirements
        sections.extend(self._build_output_requirements(ast))

        # Optionally add examples
        if include_examples:
            sections.extend(self._build_examples_section())

        # Join all sections
        prompt = "\n".join(sections)

        logger.debug(f"Built prompt ({len(prompt)} chars, ~{len(prompt)//4} tokens)")

        return prompt

    def build_refinement_prompt(
        self,
        ast: PineAST,
        previous_code: str,
        errors: List[str],
    ) -> str:
        """
        Build refinement prompt with validation errors from previous attempt.

        Args:
            ast: Original Pine Script AST
            previous_code: Previously generated code that failed validation
            errors: List of validation errors to fix

        Returns:
            Refinement prompt

        Example:
            >>> prompt = builder.build_refinement_prompt(ast, code, errors)
            >>> "Fix the following validation errors" in prompt
            True
        """
        logger.debug(f"Building refinement prompt with {len(errors)} errors")

        sections = [
            self.SYSTEM_INSTRUCTIONS,
            "",
            "# Task: Fix Validation Errors",
            f"The previous conversion attempt for **{ast.script_name}** failed validation.",
            "Please fix the errors listed below and regenerate the complete Python code.",
            "",
            "# Validation Errors",
        ]

        for i, error in enumerate(errors, 1):
            sections.append(f"{i}. {error}")

        sections.extend([
            "",
            "# Previous Generated Code",
            "```python",
            previous_code.strip(),
            "```",
            "",
            "# Original Pine Script",
            "```pinescript",
            ast.raw_code.strip(),
            "```",
            "",
            "# Requirements",
            "- Fix ALL validation errors listed above",
            "- Preserve all strategy logic from the Pine Script",
            "- Output ONLY the corrected Python code",
            "- Do NOT include explanations or comments about the fixes",
        ])

        prompt = "\n".join(sections)

        logger.debug(f"Built refinement prompt ({len(prompt)} chars)")

        return prompt

    def build_verification_prompt(
        self,
        original_pine: str,
        python_code: str,
    ) -> str:
        """
        Build verification prompt to check code equivalence.

        Args:
            original_pine: Original Pine Script code
            python_code: Generated Python code

        Returns:
            Verification prompt asking Claude to verify correctness

        Example:
            >>> prompt = builder.build_verification_prompt(pine, python)
            >>> "verify" in prompt.lower()
            True
        """
        return f"""Compare the following Pine Script and Python implementations.

# Original Pine Script
```pinescript
{original_pine.strip()}
```

# Generated Python Code
```python
{python_code.strip()}
```

# Task
Verify that the Python code correctly implements the Pine Script strategy.
Report any discrepancies in logic, calculations, or strategy behavior.

Answer with:
- "CORRECT" if implementations match
- "INCORRECT: [specific issue]" if there are problems"""

    # ------------------------------------------------------------------------
    # Private Helper Methods
    # ------------------------------------------------------------------------

    def _build_inputs_section(self, inputs: List[InputNode]) -> List[str]:
        """Build inputs documentation section"""
        section = [
            "# Strategy Parameters (Inputs)",
            "",
            "The following input parameters must be preserved as class attributes:",
            "",
        ]

        for inp in inputs:
            section.append(
                f"- **{inp.name}**: {inp.input_type} = {inp.default_value}"
                + (f" (title: '{inp.title}')" if inp.title else "")
            )

        section.append("")
        return section

    def _build_indicators_section(self, indicators: List[str]) -> List[str]:
        """Build indicators documentation section"""
        section = [
            "# Technical Indicators Used",
            "",
            "Use `pandas-ta` library for the following indicators:",
            "",
        ]

        for indicator in sorted(set(indicators)):
            # Map Pine indicators to pandas-ta
            pandas_ta_name = self._map_indicator_to_pandas_ta(indicator)
            section.append(f"- `{indicator}` → `ta.{pandas_ta_name}()`")

        section.append("")
        return section

    def _build_functions_section(self, functions: List[FunctionNode]) -> List[str]:
        """Build custom functions documentation section"""
        section = [
            "# Custom Functions",
            "",
            "The following user-defined functions must be implemented:",
            "",
        ]

        for func in functions:
            params_str = ", ".join(
                f"{name}: {ptype or 'Any'}" for name, ptype in func.parameters
            )
            return_str = f" -> {func.return_type}" if func.return_type else ""

            section.append(f"- `{func.name}({params_str}){return_str}`")

        section.append("")
        return section

    def _build_output_requirements(self, ast: PineAST) -> List[str]:
        """Build output format requirements"""
        class_name = self._generate_class_name(ast.script_name)

        section = [
            "# Output Requirements",
            "",
            "Generate a complete Python module with:",
            "",
            "```python",
            "from backtesting import Strategy",
            "import pandas as pd",
            "import pandas_ta as ta",
            "",
            f"class {class_name}(Strategy):",
            "    \"\"\"",
            f"    {ast.script_name}",
            "    ",
            "    Converted from Pine Script to Python.",
            "    \"\"\"",
            "    ",
            "    # Parameters (from Pine Script inputs)",
            "    param1 = 20",
            "    param2 = 1.5",
            "    # ... (all input parameters)",
            "    ",
            "    def init(self):",
            "        \"\"\"",
            "        Initialize indicators and state variables.",
            "        Called once at the start of backtesting.",
            "        \"\"\"",
            "        # Calculate indicators using self.I()",
            "        # Example: self.sma = self.I(ta.sma, self.data.Close, self.param1)",
            "        pass",
            "    ",
            "    def next(self):",
            "        \"\"\"",
            "        Strategy logic executed on each bar.",
            "        ",
            "        Use self.buy() and self.sell() for order execution.",
            "        Access indicator values with self.indicator_name[-1]",
            "        \"\"\"",
            "        # Implement Pine Script strategy logic",
            "        pass",
            "```",
            "",
            "**Critical**:",
            "- Use `self.I()` wrapper for ALL indicators in `init()`",
            "- Access current bar data with `self.data.Close[-1]`, etc.",
            "- Access indicator values with `self.indicator[-1]`",
            "- Use `self.buy()` for long entries, `self.sell()` for closes",
            "- Implement proper entry/exit conditions from Pine Script",
            "",
            "Output the complete, runnable Python code now:",
        ]

        return section

    def _build_examples_section(self) -> List[str]:
        """Build examples section (optional, increases token count)"""
        return [
            "",
            "# Example Conversion",
            "",
            "**Pine Script**:",
            "```pinescript",
            "//@version=5",
            "strategy('MA Cross', overlay=true)",
            "fast = input.int(10, 'Fast MA')",
            "slow = input.int(20, 'Slow MA')",
            "fastMA = ta.sma(close, fast)",
            "slowMA = ta.sma(close, slow)",
            "if ta.crossover(fastMA, slowMA)",
            "    strategy.entry('Long', strategy.long)",
            "if ta.crossunder(fastMA, slowMA)",
            "    strategy.close('Long')",
            "```",
            "",
            "**Python Output**:",
            "```python",
            "from backtesting import Strategy",
            "import pandas_ta as ta",
            "",
            "class MACrossStrategy(Strategy):",
            '    """MA Cross strategy converted from Pine Script"""',
            "    fast = 10",
            "    slow = 20",
            "    ",
            "    def init(self):",
            "        close = self.data.Close",
            "        self.fast_ma = self.I(ta.sma, close, self.fast)",
            "        self.slow_ma = self.I(ta.sma, close, self.slow)",
            "    ",
            "    def next(self):",
            "        # Crossover: fast crosses above slow",
            "        if self.fast_ma[-1] > self.slow_ma[-1] and \\",
            "           self.fast_ma[-2] <= self.slow_ma[-2]:",
            "            if not self.position:",
            "                self.buy()",
            "        ",
            "        # Crossunder: fast crosses below slow",
            "        elif self.fast_ma[-1] < self.slow_ma[-1] and \\",
            "             self.fast_ma[-2] >= self.slow_ma[-2]:",
            "            if self.position:",
            "                self.position.close()",
            "```",
            "",
        ]

    def _generate_class_name(self, script_name: str) -> str:
        """
        Generate Python class name from Pine Script name.

        Args:
            script_name: Original Pine Script name

        Returns:
            PascalCase class name

        Example:
            >>> builder._generate_class_name("MA Cross Strategy")
            'MACrossStrategy'
        """
        import re

        # Remove special characters and split on whitespace
        words = re.sub(r'[^a-zA-Z0-9\s]', '', script_name).split()

        # PascalCase
        class_name = ''.join(word.capitalize() for word in words)

        # Ensure it ends with "Strategy"
        if not class_name.endswith("Strategy"):
            class_name += "Strategy"

        return class_name

    def _map_indicator_to_pandas_ta(self, pine_indicator: str) -> str:
        """
        Map Pine Script indicator to pandas-ta equivalent.

        Args:
            pine_indicator: Pine indicator name (e.g., 'ta.sma')

        Returns:
            pandas-ta function name (e.g., 'sma')

        Example:
            >>> builder._map_indicator_to_pandas_ta('ta.sma')
            'sma'
        """
        # Common mappings
        indicator_map = {
            "ta.sma": "sma",
            "ta.ema": "ema",
            "ta.rsi": "rsi",
            "ta.atr": "atr",
            "ta.macd": "macd",
            "ta.bb": "bbands",  # Bollinger Bands
            "ta.stoch": "stoch",
            "ta.adx": "adx",
            "ta.cci": "cci",
            "ta.mfi": "mfi",
            "ta.obv": "obv",
            "ta.vwap": "vwap",
            "ta.supertrend": "supertrend",
            "ta.kc": "kc",  # Keltner Channels
            "ta.dmi": "dmi",
            "ta.willr": "willr",
            "ta.roc": "roc",
            "ta.tsi": "tsi",
        }

        # Strip "ta." prefix if present
        clean_name = pine_indicator.replace("ta.", "")

        return indicator_map.get(pine_indicator, clean_name)
