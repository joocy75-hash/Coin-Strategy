"""
LLM Response Parser

Extracts and validates Python code from Claude's responses.
Handles various response formats and code block syntaxes.
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from ..pine_parser import PineAST
from ..ast_code_generator import GeneratedCode

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ParseResult:
    """Result of parsing LLM response"""
    success: bool
    python_code: str
    generated_code: Optional[GeneratedCode] = None
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


# ============================================================================
# Response Parser
# ============================================================================

class LLMResponseParser:
    """
    Parse Python code from LLM responses.

    Handles:
    - Markdown code blocks (```python ... ```)
    - Raw Python code
    - Mixed text and code responses
    - Error messages from LLM

    Example:
        >>> parser = LLMResponseParser()
        >>> result = parser.parse_python_code(response_text, ast)
        >>> if result.success:
        ...     print(result.python_code)
    """

    # Regex patterns for code extraction
    PYTHON_CODE_BLOCK = re.compile(
        r'```(?:python|py)?\s*\n(.*?)\n```',
        re.DOTALL | re.IGNORECASE
    )

    CLASS_PATTERN = re.compile(
        r'class\s+(\w+)\s*\(',
        re.MULTILINE
    )

    IMPORT_PATTERN = re.compile(
        r'^(from|import)\s+',
        re.MULTILINE
    )

    def __init__(self):
        """Initialize response parser"""
        logger.debug("Initialized LLMResponseParser")

    def parse_python_code(
        self,
        llm_response: str,
        ast: PineAST,
    ) -> ParseResult:
        """
        Extract Python code from LLM response.

        Args:
            llm_response: Raw text response from Claude
            ast: Original Pine Script AST (for validation)

        Returns:
            ParseResult with extracted code and metadata

        Example:
            >>> response = '''Here's the code:
            ... ```python
            ... class MyStrategy(Strategy):
            ...     pass
            ... ```
            ... '''
            >>> result = parser.parse_python_code(response, ast)
            >>> result.success
            True
        """
        logger.debug("Parsing LLM response")

        errors = []
        warnings = []

        # Step 1: Extract code blocks
        code_blocks = self._extract_code_blocks(llm_response)

        if not code_blocks:
            # No explicit code blocks, try to extract raw code
            logger.debug("No code blocks found, attempting raw code extraction")
            python_code = self._extract_raw_code(llm_response)

            if not python_code:
                errors.append("No Python code found in LLM response")
                return ParseResult(
                    success=False,
                    python_code="",
                    errors=errors
                )
        else:
            # Use first (or longest) code block
            python_code = max(code_blocks, key=len) if len(code_blocks) > 1 else code_blocks[0]

        # Step 2: Clean and format code
        python_code = self._clean_code(python_code)

        # Step 3: Basic validation
        validation_errors = self._validate_code_structure(python_code, ast)
        errors.extend(validation_errors)

        # Step 4: Extract metadata
        class_name = self._extract_class_name(python_code)
        imports = self._extract_imports(python_code)
        indicators = self._extract_indicators_used(python_code)

        # Step 5: Build GeneratedCode object
        generated_code = GeneratedCode(
            full_code=python_code,
            class_name=class_name or "UnknownStrategy",
            imports=imports,
            indicators_used=indicators,
            warnings=warnings,
            errors=errors,
        )

        success = len(errors) == 0

        logger.debug(
            f"Parsing {'succeeded' if success else 'failed'} "
            f"({len(python_code)} chars, {len(errors)} errors)"
        )

        return ParseResult(
            success=success,
            python_code=python_code,
            generated_code=generated_code,
            errors=errors,
            warnings=warnings,
        )

    # ------------------------------------------------------------------------
    # Private Helper Methods
    # ------------------------------------------------------------------------

    def _extract_code_blocks(self, text: str) -> List[str]:
        """
        Extract all Python code blocks from markdown.

        Args:
            text: Response text

        Returns:
            List of code blocks
        """
        matches = self.PYTHON_CODE_BLOCK.findall(text)
        return [match.strip() for match in matches]

    def _extract_raw_code(self, text: str) -> str:
        """
        Attempt to extract Python code when no code blocks present.

        Looks for class definitions and imports.

        Args:
            text: Response text

        Returns:
            Extracted code or empty string
        """
        lines = text.split('\n')
        code_lines = []
        in_code = False

        for line in lines:
            # Start collecting when we see import or class
            if re.match(r'^(from |import |class )', line):
                in_code = True

            if in_code:
                code_lines.append(line)

        return '\n'.join(code_lines).strip()

    def _clean_code(self, code: str) -> str:
        """
        Clean and format extracted code.

        Removes:
        - Leading/trailing whitespace
        - Explanatory comments before/after code
        - Excess blank lines

        Args:
            code: Raw extracted code

        Returns:
            Cleaned code
        """
        lines = code.split('\n')
        cleaned_lines = []

        for line in lines:
            # Skip lines that look like explanations
            if line.strip().startswith('#') and any(
                keyword in line.lower()
                for keyword in ['note:', 'explanation:', 'here', 'this code']
            ):
                continue

            cleaned_lines.append(line)

        # Remove excess blank lines
        result = []
        prev_blank = False

        for line in cleaned_lines:
            is_blank = not line.strip()

            if is_blank and prev_blank:
                continue  # Skip consecutive blank lines

            result.append(line)
            prev_blank = is_blank

        return '\n'.join(result).strip()

    def _validate_code_structure(
        self,
        code: str,
        ast: PineAST,
    ) -> List[str]:
        """
        Perform basic structural validation.

        Checks:
        - Presence of Strategy class
        - Presence of init() and next() methods
        - Basic Python syntax

        Args:
            code: Python code to validate
            ast: Original Pine AST

        Returns:
            List of validation errors
        """
        errors = []

        # Check for Strategy class
        if 'class ' not in code:
            errors.append("No class definition found")
            return errors

        if 'Strategy' not in code:
            errors.append("Class does not inherit from Strategy")

        # Check for required methods
        if 'def init(self' not in code:
            errors.append("Missing init() method")

        if 'def next(self' not in code:
            errors.append("Missing next() method")

        # Try to parse Python syntax
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            errors.append(f"Python syntax error: {e}")

        return errors

    def _extract_class_name(self, code: str) -> Optional[str]:
        """
        Extract Strategy class name from code.

        Args:
            code: Python code

        Returns:
            Class name or None
        """
        match = self.CLASS_PATTERN.search(code)
        return match.group(1) if match else None

    def _extract_imports(self, code: str) -> str:
        """
        Extract import statements from code.

        Args:
            code: Python code

        Returns:
            Imports section as string
        """
        lines = code.split('\n')
        import_lines = [
            line for line in lines
            if self.IMPORT_PATTERN.match(line.strip())
        ]

        return '\n'.join(import_lines)

    def _extract_indicators_used(self, code: str) -> List[str]:
        """
        Extract list of technical indicators used in code.

        Args:
            code: Python code

        Returns:
            List of indicator names
        """
        indicators = []

        # Common indicator patterns
        patterns = [
            r'ta\.(\w+)\(',       # pandas_ta functions
            r'self\.I\(ta\.(\w+)', # backtesting.py indicator wrapper
        ]

        for pattern in patterns:
            matches = re.findall(pattern, code)
            indicators.extend(matches)

        return sorted(set(indicators))
