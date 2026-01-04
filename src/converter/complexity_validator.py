"""
Complexity Validator for Rule-Based Conversion

Validates that Pine Script strategies meet complexity requirements
for rule-based (non-LLM) conversion.
"""

from dataclasses import dataclass, field
from typing import List
import logging
import re

from .pine_parser import PineAST

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of complexity validation.

    Attributes:
        is_valid: Whether AST passes validation for rule-based conversion
        complexity_score: Actual complexity score
        errors: List of validation errors (blocking issues)
        warnings: List of warnings (non-blocking issues)
    """
    is_valid: bool
    complexity_score: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        return f"ValidationResult({status}, score={self.complexity_score:.3f}, {len(self.errors)} errors)"


class ComplexityValidator:
    """
    Validate Pine Script AST for rule-based conversion.

    Checks complexity score and detects unsupported features that would
    require LLM-based conversion instead.

    Validation Rules:
    - Complexity score < 0.3 (LOW complexity)
    - No custom functions
    - No advanced array/matrix operations
    - No custom type definitions
    - Simple conditional logic only (depth ≤ 1)

    Example:
        >>> validator = ComplexityValidator()
        >>> # Assume ast is from parse_pine_script()
        >>> result = validator.validate(ast)
        >>> if result.is_valid:
        ...     print("Can use rule-based conversion")
        ... else:
        ...     print("Need LLM conversion:", result.errors)
    """

    # Complexity threshold for rule-based conversion
    MAX_COMPLEXITY = 0.3

    # Maximum conditional nesting depth
    MAX_NESTING_DEPTH = 1

    def __init__(self, max_complexity: float = MAX_COMPLEXITY):
        """
        Initialize validator.

        Args:
            max_complexity: Maximum allowed complexity score (default: 0.3)
        """
        self.max_complexity = max_complexity

    def validate(self, ast: PineAST) -> ValidationResult:
        """
        Validate AST for rule-based conversion.

        Args:
            ast: Pine Script AST from PineParser

        Returns:
            ValidationResult with validation status and details

        Example:
            >>> validator = ComplexityValidator()
            >>> result = validator.validate(ast)
            >>> result.is_valid
            True
        """
        errors = []
        warnings = []

        logger.info(f"Validating '{ast.script_name}' (complexity: {ast.complexity_score:.3f})")

        # Check 1: Complexity score
        if ast.complexity_score >= self.max_complexity:
            errors.append(
                f"Complexity score {ast.complexity_score:.3f} exceeds threshold "
                f"{self.max_complexity:.3f}. Use LLM-based conversion instead."
            )

        # Check 2: No custom functions
        if ast.functions:
            errors.append(
                f"Found {len(ast.functions)} custom function(s). "
                f"Custom functions require LLM-based conversion."
            )

        # Check 3: No unsupported features in code
        unsupported = self._check_unsupported_features(ast)
        if unsupported:
            errors.extend(unsupported)

        # Check 4: Simple conditionals only
        if ast.complexity_factors.get('nesting', 0) > self.MAX_NESTING_DEPTH:
            errors.append(
                f"Conditional nesting depth {ast.complexity_factors['nesting']} "
                f"exceeds maximum {self.MAX_NESTING_DEPTH}. Use LLM-based conversion."
            )

        # Warnings (non-blocking)
        if len(ast.indicators_used) > 5:
            warnings.append(
                f"Strategy uses {len(ast.indicators_used)} indicators. "
                f"Verify all are supported by IndicatorMapper."
            )

        # Determine if valid
        is_valid = len(errors) == 0

        result = ValidationResult(
            is_valid=is_valid,
            complexity_score=ast.complexity_score,
            errors=errors,
            warnings=warnings
        )

        if is_valid:
            logger.info(f"Validation passed for '{ast.script_name}'")
        else:
            logger.warning(f"Validation failed for '{ast.script_name}': {len(errors)} errors")

        return result

    def _check_unsupported_features(self, ast: PineAST) -> List[str]:
        """
        Check for unsupported Pine Script features in the code.

        Args:
            ast: Pine AST

        Returns:
            List of error messages for unsupported features
        """
        errors = []

        # Check complexity factors for advanced features
        factors = ast.complexity_factors

        # Array/matrix operations
        if factors.get('array_matrix', 0) > 0:
            errors.append(
                "Advanced array/matrix operations detected. "
                "These require LLM-based conversion."
            )

        # Custom types
        if factors.get('custom_types', 0) > 0:
            errors.append(
                "Custom type definitions detected. "
                "These require LLM-based conversion."
            )

        # Drawing objects
        if factors.get('drawing', 0) > 3:
            warnings = []  # Drawing is not blocking, but note it
            warnings.append(
                f"Multiple drawing objects ({factors['drawing']}) detected. "
                f"These will be converted to comments."
            )

        return errors

    def get_recommendation(self, ast: PineAST) -> str:
        """
        Get conversion strategy recommendation.

        Args:
            ast: Pine AST

        Returns:
            Recommendation string

        Example:
            >>> validator = ComplexityValidator()
            >>> recommendation = validator.get_recommendation(ast)
            >>> print(recommendation)
            'Rule-based conversion recommended (complexity: 0.14)'
        """
        result = self.validate(ast)

        if result.is_valid:
            return (
                f"Rule-based conversion recommended "
                f"(complexity: {ast.complexity_score:.2f})"
            )
        elif ast.complexity_score < 0.7:
            return (
                f"Hybrid conversion recommended "
                f"(complexity: {ast.complexity_score:.2f}). "
                f"Issues: {', '.join(result.errors[:2])}"
            )
        else:
            return (
                f"LLM-based conversion required "
                f"(complexity: {ast.complexity_score:.2f}). "
                f"Too complex for rule-based conversion."
            )
