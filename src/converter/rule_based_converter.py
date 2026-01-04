"""
Rule-Based Converter for LOW Complexity Pine Scripts

Converts simple Pine Script strategies (complexity < 0.3) to Python
using deterministic rules without LLM assistance.
"""

import logging
from typing import Optional

from .pine_parser import PineAST
from .complexity_validator import ComplexityValidator, ValidationResult
from .ast_code_generator import ASTCodeGenerator, GeneratedCode
from .expression_transformer import ExpressionTransformer

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Base exception for conversion errors."""
    pass


class ComplexityError(ConversionError):
    """Raised when script complexity exceeds rule-based threshold."""
    pass


class UnsupportedFeatureError(ConversionError):
    """Raised when unsupported Pine feature is detected."""
    pass


class RuleBasedConverter:
    """
    Convert LOW complexity Pine Script strategies to Python.

    Uses deterministic rules and AST-based transformation for simple
    strategies (complexity score < 0.3). For higher complexity,
    raises ComplexityError and recommends LLM-based conversion.

    Pipeline:
    1. Validate complexity (ComplexityValidator)
    2. Transform expressions (ExpressionTransformer)
    3. Generate Python code (ASTCodeGenerator)
    4. Format and return

    Example:
        >>> from converter import parse_pine_script
        >>> pine_code = '''
        ... //@version=5
        ... indicator("Simple MA", overlay=true)
        ... length = input.int(20, "Length")
        ... ma = ta.sma(close, length)
        ... plot(ma, color=color.blue)
        ... '''
        >>> ast = parse_pine_script(pine_code)
        >>> converter = RuleBasedConverter()
        >>> python_code = converter.convert(ast)
        >>> 'class SimpleMAStrategy' in python_code
        True
    """

    def __init__(self):
        """Initialize rule-based converter."""
        self.validator = ComplexityValidator()
        self.expression_transformer = ExpressionTransformer()
        self.code_generator = ASTCodeGenerator()

    def convert(self, ast: PineAST) -> str:
        """
        Convert Pine Script AST to Python code.

        Args:
            ast: Pine Script AST from PineParser

        Returns:
            Complete Python strategy code

        Raises:
            ComplexityError: If complexity score too high
            UnsupportedFeatureError: If unsupported feature detected
            ConversionError: For other conversion failures

        Example:
            >>> converter = RuleBasedConverter()
            >>> python_code = converter.convert(ast)
            >>> 'def generate_signal' in python_code
            True
        """
        logger.info(f"Starting rule-based conversion for '{ast.script_name}'")

        try:
            # Stage 1: Validate complexity
            logger.debug("Stage 1: Validating complexity")
            validation = self.validator.validate(ast)

            if not validation.is_valid:
                # Build detailed error message
                error_msg = (
                    f"Strategy '{ast.script_name}' cannot be converted using rules. "
                    f"Complexity: {validation.complexity_score:.3f} "
                    f"(max: {self.validator.max_complexity:.3f}). "
                    f"Errors: {'; '.join(validation.errors)}"
                )

                logger.warning(error_msg)
                logger.info(f"Recommendation: {self.validator.get_recommendation(ast)}")

                raise ComplexityError(error_msg)

            # Log warnings if any
            if validation.warnings:
                for warning in validation.warnings:
                    logger.warning(f"Validation warning: {warning}")

            # Stage 2: Generate Python code
            logger.debug("Stage 2: Generating Python code from AST")
            result = self.code_generator.generate(ast)

            if result.errors:
                error_msg = f"Code generation failed: {'; '.join(result.errors)}"
                logger.error(error_msg)
                raise ConversionError(error_msg)

            # Log generation warnings
            if result.warnings:
                for warning in result.warnings:
                    logger.warning(f"Generation warning: {warning}")

            # Stage 3: Success
            logger.info(
                f"Successfully converted '{ast.script_name}' "
                f"({len(result.full_code)} chars, "
                f"{len(result.indicators_used)} indicators)"
            )

            return result.full_code

        except ComplexityError:
            # Re-raise complexity errors for caller to handle
            raise

        except UnsupportedFeatureError:
            # Re-raise unsupported feature errors
            raise

        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = f"Unexpected error during conversion: {e}"
            logger.error(error_msg, exc_info=True)
            raise ConversionError(error_msg) from e

    def can_convert(self, ast: PineAST) -> ValidationResult:
        """
        Check if AST can be converted using rules (without actually converting).

        Args:
            ast: Pine Script AST

        Returns:
            ValidationResult with details

        Example:
            >>> converter = RuleBasedConverter()
            >>> result = converter.can_convert(ast)
            >>> if result.is_valid:
            ...     python_code = converter.convert(ast)
        """
        return self.validator.validate(ast)

    def get_conversion_strategy(self, ast: PineAST) -> str:
        """
        Get recommended conversion strategy for AST.

        Args:
            ast: Pine Script AST

        Returns:
            Strategy recommendation string

        Example:
            >>> converter = RuleBasedConverter()
            >>> strategy = converter.get_conversion_strategy(ast)
            >>> print(strategy)
            'Rule-based conversion recommended (complexity: 0.14)'
        """
        return self.validator.get_recommendation(ast)


# Convenience function
def convert_pine_to_python(pine_code: str) -> str:
    """
    Convert Pine Script code to Python (convenience function).

    Parses Pine Script and converts using rule-based converter.

    Args:
        pine_code: Pine Script source code

    Returns:
        Python strategy code

    Raises:
        ComplexityError: If too complex for rule-based conversion
        ConversionError: If conversion fails

    Example:
        >>> pine_code = '''
        ... //@version=5
        ... indicator("MA", overlay=true)
        ... ma = ta.sma(close, 20)
        ... plot(ma)
        ... '''
        >>> python_code = convert_pine_to_python(pine_code)
        >>> 'class MAStrategy' in python_code
        True
    """
    from .pine_parser import parse_pine_script

    # Parse to AST
    ast = parse_pine_script(pine_code)

    # Convert
    converter = RuleBasedConverter()
    return converter.convert(ast)
