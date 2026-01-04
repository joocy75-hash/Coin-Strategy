"""
Expression Transformer - Main Module

Transforms Pine Script expressions to Python code using AST-based parsing
and context-aware code generation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import logging

from .expression_parser import ExpressionParser, ParseError
from .python_code_builder import PythonCodeBuilder
from .transformation_context import TransformationContext
from .indicator_mapper import IndicatorMapper

logger = logging.getLogger(__name__)


@dataclass
class TransformationResult:
    """
    Result of expression transformation.

    Attributes:
        success: Whether transformation succeeded
        python_code: Generated Python code
        indicators_used: List of indicator names used (e.g., ['ta.sma', 'ta.ema'])
        variables_referenced: List of variables referenced
        builtins_used: List of built-in variables used (e.g., ['close', 'open'])
        warnings: Non-fatal issues encountered
        errors: Fatal errors that prevented transformation
    """
    success: bool
    python_code: str
    indicators_used: List[str] = field(default_factory=list)
    variables_referenced: List[str] = field(default_factory=list)
    builtins_used: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ExpressionTransformer:
    """
    Transform Pine Script expressions to Python code.

    Main entry point for expression transformation. Coordinates parsing,
    code building, and context management.

    Example:
        >>> transformer = ExpressionTransformer()
        >>> result = transformer.transform_expression("ta.ema(close, 9)")
        >>> result.success
        True
        >>> result.python_code
        "self.indicator_mapper.calculate('ta.ema', self.close, 9)"
    """

    def __init__(self, indicator_mapper: Optional[IndicatorMapper] = None):
        """
        Initialize expression transformer.

        Args:
            indicator_mapper: IndicatorMapper instance for ta.* functions.
                            If None, creates a new instance.
        """
        self.indicator_mapper = indicator_mapper or IndicatorMapper()
        self.parser = ExpressionParser()
        self.builder = PythonCodeBuilder(self.indicator_mapper)

        # Error accumulation (non-throwing pattern)
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def transform_expression(
        self,
        pine_expr: str,
        context: Optional[TransformationContext] = None
    ) -> TransformationResult:
        """
        Transform a Pine Script expression to Python code.

        Args:
            pine_expr: Pine Script expression string
            context: Transformation context. If None, creates a fresh context.

        Returns:
            TransformationResult with Python code and metadata

        Example:
            >>> transformer = ExpressionTransformer()
            >>> result = transformer.transform_expression("close > 100")
            >>> result.python_code
            'self.close > 100'
            >>> result.builtins_used
            ['close']
        """
        # Create context if not provided
        if context is None:
            context = TransformationContext()

        # Reset error state
        self.warnings = []
        self.errors = []

        try:
            # Parse expression to AST
            logger.debug(f"Parsing expression: {pine_expr}")
            ast = self.parser.parse(pine_expr)

            # Build Python code from AST
            logger.debug(f"Building Python code from AST")
            python_code = self.builder.build(ast, context)

            # Extract metadata
            indicators_used = list(context.indicators_used)
            builtins_used = self._extract_builtins_used(pine_expr, context)

            return TransformationResult(
                success=True,
                python_code=python_code,
                indicators_used=indicators_used,
                builtins_used=builtins_used,
                warnings=self.warnings.copy(),
                errors=self.errors.copy()
            )

        except ParseError as e:
            # Parsing failed
            error_msg = f"Parse error: {e}"
            self.errors.append(error_msg)
            logger.error(error_msg)

            return TransformationResult(
                success=False,
                python_code=f"# PARSE_ERROR: {pine_expr}",
                errors=self.errors.copy()
            )

        except Exception as e:
            # Unexpected error
            error_msg = f"Transformation error: {e}"
            self.errors.append(error_msg)
            logger.error(error_msg, exc_info=True)

            return TransformationResult(
                success=False,
                python_code=f"# ERROR: {pine_expr}",
                errors=self.errors.copy()
            )

    def transform_assignment(
        self,
        var_name: str,
        pine_expr: str,
        modifier: str = "",
        context: Optional[TransformationContext] = None
    ) -> str:
        """
        Transform a variable assignment.

        Handles Pine variable declarations with modifiers (var, varip).

        Args:
            var_name: Variable name
            pine_expr: Right-hand side expression
            modifier: Variable modifier ('var', 'varip', or '')
            context: Transformation context

        Returns:
            Python assignment statement

        Example:
            >>> transformer = ExpressionTransformer()
            >>> transformer.transform_assignment("fast", "ta.ema(close, 9)", "var")
            'self.fast = self.indicator_mapper.calculate(\\'ta.ema\\', self.close, 9)'
        """
        if context is None:
            context = TransformationContext()

        # Transform the expression
        result = self.transform_expression(pine_expr, context)

        if not result.success:
            # Return error as comment
            return f"# ERROR transforming {var_name}: {pine_expr}"

        # Build assignment
        # 'var' and 'varip' create persistent state variables
        if modifier in ['var', 'varip']:
            # State variable - use self. prefix
            python_var = f"self.{var_name}"
        else:
            # Local variable - no prefix in method context
            python_var = var_name

        # Register variable in context for future references
        context.add_variable(var_name, python_var)

        # Return assignment statement
        return f"{python_var} = {result.python_code}"

    def transform_condition(
        self,
        pine_expr: str,
        context: Optional[TransformationContext] = None
    ) -> str:
        """
        Transform a boolean condition expression.

        Used for if statements, while loops, strategy conditions, etc.

        Args:
            pine_expr: Pine Script boolean expression
            context: Transformation context

        Returns:
            Python boolean expression

        Example:
            >>> transformer = ExpressionTransformer()
            >>> transformer.transform_condition("rsi < 30 and close > ema_21")
            'rsi < 30 and self.close > ema_21'
        """
        result = self.transform_expression(pine_expr, context)

        if not result.success:
            logger.warning(f"Failed to transform condition: {pine_expr}")
            return f"False  # ERROR: {pine_expr}"

        return result.python_code

    def transform_function_body(
        self,
        pine_body: str,
        context: Optional[TransformationContext] = None
    ) -> List[str]:
        """
        Transform a function body (multi-line Pine code).

        Splits by newlines and transforms each expression.

        Args:
            pine_body: Pine Script function body (may be multi-line)
            context: Transformation context

        Returns:
            List of Python code lines

        Example:
            >>> transformer = ExpressionTransformer()
            >>> body = "fast = ta.ema(close, 9)\\nslow = ta.sma(close, 21)\\nfast > slow"
            >>> lines = transformer.transform_function_body(body)
            >>> len(lines)
            3
        """
        if context is None:
            context = TransformationContext()

        python_lines = []

        # Split by newlines
        pine_lines = pine_body.strip().split('\n')

        for line in pine_lines:
            line = line.strip()
            if not line or line.startswith('//'):
                # Skip empty lines and comments
                continue

            # Check if this is an assignment
            if '=' in line and not any(op in line for op in ['==', '!=', '<=', '>=']):
                # Assignment statement
                if ':=' in line:
                    var_name, expr = line.split(':=', 1)
                elif '=' in line:
                    var_name, expr = line.split('=', 1)
                else:
                    # Just transform as expression
                    result = self.transform_expression(line, context)
                    python_lines.append(result.python_code)
                    continue

                var_name = var_name.strip()
                expr = expr.strip()

                # Transform assignment
                python_line = self.transform_assignment(var_name, expr, '', context)
                python_lines.append(python_line)

            else:
                # Regular expression
                result = self.transform_expression(line, context)
                python_lines.append(result.python_code)

        return python_lines

    def _extract_builtins_used(
        self,
        pine_expr: str,
        context: TransformationContext
    ) -> List[str]:
        """
        Extract list of built-in variables used in expression.

        Args:
            pine_expr: Pine Script expression
            context: Transformation context

        Returns:
            List of built-in variable names
        """
        builtins = []

        # Check for common built-ins
        common_builtins = [
            'close', 'open', 'high', 'low', 'volume',
            'hl2', 'hlc3', 'ohlc4',
            'bar_index'
        ]

        for builtin in common_builtins:
            if builtin in pine_expr:
                builtins.append(builtin)

        return builtins

    def _add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
        logger.warning(message)

    def _add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        logger.error(message)


# Convenience function
def transform_pine_expression(pine_expr: str) -> str:
    """
    Quick transformation of a Pine expression to Python.

    Args:
        pine_expr: Pine Script expression

    Returns:
        Python code string

    Example:
        >>> transform_pine_expression("ta.ema(close, 9)")
        "self.indicator_mapper.calculate('ta.ema', self.close, 9)"
    """
    transformer = ExpressionTransformer()
    result = transformer.transform_expression(pine_expr)

    if not result.success:
        raise ValueError(f"Transformation failed: {result.errors}")

    return result.python_code
