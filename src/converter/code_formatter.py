"""
Code Formatter for Generated Python Code

Provides code formatting, syntax validation, and optimization utilities.
"""

import ast
import re
from typing import Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of code validation."""
    is_valid: bool
    error_message: str = ""
    line_number: int = 0


class CodeFormatter:
    """
    Format and validate generated Python code.

    Provides syntax validation, basic formatting, and optimization.
    For production use, consider integrating black or autopep8.

    Example:
        >>> formatter = CodeFormatter()
        >>> code = "def foo():  return 42"
        >>> formatted = formatter.format_code(code)
        >>> result = formatter.validate_syntax(formatted)
        >>> result.is_valid
        True
    """

    def __init__(self):
        """Initialize code formatter."""
        pass

    def format_code(self, code: str) -> str:
        """
        Format Python code with basic styling.

        Args:
            code: Python code string

        Returns:
            Formatted code

        Example:
            >>> formatter = CodeFormatter()
            >>> code = "x=1+2"
            >>> formatter.format_code(code)
            'x = 1 + 2'
        """
        # Basic formatting rules
        formatted = code

        # Ensure proper spacing around operators
        formatted = self._fix_operator_spacing(formatted)

        # Fix indentation (basic)
        formatted = self._fix_indentation(formatted)

        # Remove trailing whitespace
        lines = [line.rstrip() for line in formatted.split('\n')]
        formatted = '\n'.join(lines)

        # Ensure file ends with newline
        if formatted and not formatted.endswith('\n'):
            formatted += '\n'

        return formatted

    def validate_syntax(self, code: str) -> ValidationResult:
        """
        Validate Python code syntax.

        Args:
            code: Python code string

        Returns:
            ValidationResult with validation status

        Example:
            >>> formatter = CodeFormatter()
            >>> result = formatter.validate_syntax("def foo(): pass")
            >>> result.is_valid
            True
            >>> result = formatter.validate_syntax("def foo(")
            >>> result.is_valid
            False
        """
        try:
            ast.parse(code)
            return ValidationResult(is_valid=True)

        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                error_message=str(e),
                line_number=e.lineno or 0
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Unexpected error: {e}"
            )

    def optimize_imports(self, code: str) -> str:
        """
        Optimize import statements (remove duplicates, sort).

        Args:
            code: Python code string

        Returns:
            Code with optimized imports

        Example:
            >>> formatter = CodeFormatter()
            >>> code = "import os\\nimport sys\\nimport os"
            >>> optimized = formatter.optimize_imports(code)
            >>> optimized.count('import os')
            1
        """
        lines = code.split('\n')

        # Separate imports from rest of code
        imports = []
        other_lines = []
        in_imports = True

        for line in lines:
            stripped = line.strip()

            if in_imports and (stripped.startswith('import ') or stripped.startswith('from ')):
                if stripped not in imports:  # Remove duplicates
                    imports.append(stripped)
            else:
                if stripped and not stripped.startswith('#'):
                    in_imports = False
                other_lines.append(line)

        # Sort imports (from imports first, then regular imports)
        from_imports = sorted([imp for imp in imports if imp.startswith('from ')])
        regular_imports = sorted([imp for imp in imports if imp.startswith('import ')])

        # Reconstruct code
        optimized_lines = from_imports + regular_imports + [''] + other_lines

        return '\n'.join(optimized_lines)

    def _fix_operator_spacing(self, code: str) -> str:
        """
        Fix spacing around operators.

        Args:
            code: Python code

        Returns:
            Code with fixed spacing
        """
        # Add spaces around binary operators
        # Be careful not to break strings or comments

        # This is a simplified implementation
        # For production, use black or autopep8

        # Fix common cases
        code = re.sub(r'([a-zA-Z0-9_])=([a-zA-Z0-9_])', r'\1 = \2', code)  # x=y → x = y
        code = re.sub(r'([a-zA-Z0-9_])\+([a-zA-Z0-9_])', r'\1 + \2', code)  # x+y → x + y
        code = re.sub(r'([a-zA-Z0-9_])-([a-zA-Z0-9_])', r'\1 - \2', code)  # x-y → x - y

        return code

    def _fix_indentation(self, code: str) -> str:
        """
        Fix indentation to use 4 spaces.

        Args:
            code: Python code

        Returns:
            Code with fixed indentation
        """
        lines = code.split('\n')
        fixed_lines = []

        for line in lines:
            # Count leading spaces
            leading_spaces = len(line) - len(line.lstrip())

            # Convert to indentation level (assume 4 spaces per level)
            if leading_spaces > 0:
                indent_level = leading_spaces // 4
                fixed_line = '    ' * indent_level + line.lstrip()
            else:
                fixed_line = line

            fixed_lines.append(fixed_line)

        return '\n'.join(fixed_lines)

    def add_type_hints(self, code: str) -> str:
        """
        Add basic type hints where missing.

        This is a basic implementation. For production, use tools like
        MonkeyType or PyAnnotate.

        Args:
            code: Python code

        Returns:
            Code with added type hints

        Note:
            Currently a placeholder - full implementation would require
            AST analysis and inference.
        """
        # Placeholder - would require more sophisticated analysis
        logger.debug("Type hint addition not fully implemented")
        return code

    def remove_duplicate_blank_lines(self, code: str) -> str:
        """
        Remove excessive blank lines (more than 2 consecutive).

        Args:
            code: Python code

        Returns:
            Code with reduced blank lines
        """
        # Replace 3+ consecutive newlines with 2
        while '\n\n\n' in code:
            code = code.replace('\n\n\n', '\n\n')

        return code

    def format_docstrings(self, code: str) -> str:
        """
        Ensure docstrings follow PEP 257.

        Args:
            code: Python code

        Returns:
            Code with formatted docstrings

        Note:
            Basic implementation - full compliance would require AST analysis.
        """
        # Placeholder
        logger.debug("Docstring formatting not fully implemented")
        return code
