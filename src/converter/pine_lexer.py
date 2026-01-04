"""
Pine Script Lexer

Tokenizes Pine Script code into structured tokens for parsing and conversion.
Handles Pine-specific syntax including operators (:=, =>), keywords, and identifiers.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Token types for Pine Script lexical analysis"""

    # Keywords
    KEYWORD = auto()

    # Operators
    OPERATOR = auto()

    # Identifiers and literals
    IDENTIFIER = auto()
    LITERAL = auto()
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()

    # Namespaces and builtins
    NAMESPACE = auto()
    BUILTIN = auto()

    # Comments
    COMMENT = auto()

    # Whitespace and structure
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    WHITESPACE = auto()

    # Punctuation
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    DOT = auto()

    # Special
    EOF = auto()
    UNKNOWN = auto()


@dataclass
class Token:
    """Represents a single token in Pine Script"""

    type: TokenType
    value: str
    line: int
    column: int
    raw_value: Optional[str] = None  # Original value before normalization

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {repr(self.value)}, {self.line}:{self.column})"


class PineLexer:
    """
    Lexical analyzer for Pine Script

    Converts Pine Script source code into a stream of tokens for parsing.
    Handles all Pine Script v5 syntax including special operators and keywords.

    Example:
        lexer = PineLexer()
        tokens = lexer.tokenize(pine_script_code)
        for token in tokens:
            print(f"{token.type}: {token.value}")
    """

    # Pine Script keywords
    KEYWORDS = {
        'var', 'varip', 'if', 'else', 'for', 'while', 'switch', 'break', 'continue',
        'export', 'import', 'as', 'return', 'true', 'false', 'na', 'and', 'or', 'not',
        'type', 'method', 'int', 'float', 'bool', 'color', 'string', 'line', 'label',
        'box', 'table', 'array', 'matrix', 'map', 'void'
    }

    # Pine Script built-in functions/declarations
    DECLARATIONS = {
        'strategy', 'indicator', 'library'
    }

    # Pine Script namespaces
    NAMESPACES = {
        'ta', 'math', 'strategy', 'array', 'matrix', 'map', 'line', 'label', 'box',
        'table', 'color', 'request', 'timeframe', 'ticker', 'input', 'plot', 'plotshape',
        'plotchar', 'barcolor', 'bgcolor', 'fill', 'hline', 'str', 'runtime', 'session'
    }

    # Pine Script built-in variables
    BUILTINS = {
        'close', 'open', 'high', 'low', 'volume', 'time', 'hl2', 'hlc3', 'ohlc4',
        'bar_index', 'barstate', 'syminfo', 'timenow', 'year', 'month', 'weekofyear',
        'dayofmonth', 'dayofweek', 'hour', 'minute', 'second'
    }

    # Operators (ordered by length for proper matching)
    OPERATORS = [
        # Assignment and special
        ':=', '=>', '?:',
        # Comparison
        '==', '!=', '<=', '>=', '<', '>',
        # Arithmetic
        '+=', '-=', '*=', '/=', '%=',
        '+', '-', '*', '/', '%',
        # Logical (handled as keywords)
        # Other
        '=', '?', ':'
    ]

    def __init__(self):
        """Initialize the Pine Script lexer"""
        self.source = ""
        self.tokens: List[Token] = []
        self.current_pos = 0
        self.current_line = 1
        self.current_column = 1
        self.indent_stack = [0]  # Track indentation levels

    def tokenize(self, source: str) -> List[Token]:
        """
        Tokenize Pine Script source code

        Args:
            source: Pine Script source code string

        Returns:
            List of Token objects
        """
        self.source = source
        self.tokens = []
        self.current_pos = 0
        self.current_line = 1
        self.current_column = 1
        self.indent_stack = [0]

        while self.current_pos < len(self.source):
            # Try to match different token types
            if self._match_whitespace():
                continue
            elif self._match_newline():
                continue
            elif self._match_comment():
                continue
            elif self._match_string():
                continue
            elif self._match_number():
                continue
            elif self._match_operator():
                continue
            elif self._match_punctuation():
                continue
            elif self._match_keyword_or_identifier():
                continue
            else:
                # Unknown character
                char = self.source[self.current_pos]
                self._add_token(TokenType.UNKNOWN, char)
                self._advance()

        # Add final DEDENT tokens if needed
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self._add_token(TokenType.DEDENT, '')

        # Add EOF token
        self._add_token(TokenType.EOF, '')

        return self.tokens

    def _match_whitespace(self) -> bool:
        """Match whitespace (excluding newlines)"""
        if self.current_pos >= len(self.source):
            return False

        char = self.source[self.current_pos]
        if char in ' \t\r':
            start_pos = self.current_pos
            while (self.current_pos < len(self.source) and
                   self.source[self.current_pos] in ' \t\r'):
                self._advance()
            return True
        return False

    def _match_newline(self) -> bool:
        """Match newline and handle indentation"""
        if self.current_pos >= len(self.source):
            return False

        char = self.source[self.current_pos]
        if char == '\n':
            self._add_token(TokenType.NEWLINE, '\\n')
            self._advance()

            # Check indentation on next line
            indent_level = 0
            while (self.current_pos < len(self.source) and
                   self.source[self.current_pos] in ' \t'):
                if self.source[self.current_pos] == ' ':
                    indent_level += 1
                elif self.source[self.current_pos] == '\t':
                    indent_level += 4  # Assume 4 spaces per tab
                self._advance()

            # Skip empty lines
            if self.current_pos < len(self.source) and self.source[self.current_pos] == '\n':
                return True

            # Generate INDENT/DEDENT tokens
            current_indent = self.indent_stack[-1]
            if indent_level > current_indent:
                self.indent_stack.append(indent_level)
                self._add_token(TokenType.INDENT, '')
            elif indent_level < current_indent:
                while len(self.indent_stack) > 1 and self.indent_stack[-1] > indent_level:
                    self.indent_stack.pop()
                    self._add_token(TokenType.DEDENT, '')

            return True
        return False

    def _match_comment(self) -> bool:
        """Match single-line or multi-line comments"""
        if self.current_pos >= len(self.source) - 1:
            return False

        # Single-line comment
        if self.source[self.current_pos:self.current_pos+2] == '//':
            start_pos = self.current_pos
            while (self.current_pos < len(self.source) and
                   self.source[self.current_pos] != '\n'):
                self._advance()
            comment = self.source[start_pos:self.current_pos]
            self._add_token(TokenType.COMMENT, comment)
            return True

        # Multi-line comment
        if self.source[self.current_pos:self.current_pos+2] == '/*':
            start_pos = self.current_pos
            self._advance()  # Skip '/'
            self._advance()  # Skip '*'

            while self.current_pos < len(self.source) - 1:
                if self.source[self.current_pos:self.current_pos+2] == '*/':
                    self._advance()  # Skip '*'
                    self._advance()  # Skip '/'
                    break
                self._advance()

            comment = self.source[start_pos:self.current_pos]
            self._add_token(TokenType.COMMENT, comment)
            return True

        return False

    def _match_string(self) -> bool:
        """Match string literals (single or double quoted)"""
        if self.current_pos >= len(self.source):
            return False

        char = self.source[self.current_pos]
        if char in '"\'':
            quote_char = char
            start_pos = self.current_pos
            self._advance()  # Skip opening quote

            while self.current_pos < len(self.source):
                current = self.source[self.current_pos]

                # Handle escape sequences
                if current == '\\' and self.current_pos + 1 < len(self.source):
                    self._advance()  # Skip backslash
                    self._advance()  # Skip escaped character
                    continue

                # End of string
                if current == quote_char:
                    self._advance()  # Skip closing quote
                    break

                self._advance()

            string_value = self.source[start_pos:self.current_pos]
            self._add_token(TokenType.STRING, string_value)
            return True

        return False

    def _match_number(self) -> bool:
        """Match numeric literals (int or float)"""
        if self.current_pos >= len(self.source):
            return False

        char = self.source[self.current_pos]
        if char.isdigit() or (char == '.' and self.current_pos + 1 < len(self.source)
                              and self.source[self.current_pos + 1].isdigit()):
            start_pos = self.current_pos
            has_dot = False

            while self.current_pos < len(self.source):
                current = self.source[self.current_pos]

                if current.isdigit():
                    self._advance()
                elif current == '.' and not has_dot:
                    has_dot = True
                    self._advance()
                elif current in 'eE':
                    # Scientific notation
                    self._advance()
                    if (self.current_pos < len(self.source) and
                        self.source[self.current_pos] in '+-'):
                        self._advance()
                else:
                    break

            number = self.source[start_pos:self.current_pos]
            self._add_token(TokenType.NUMBER, number)
            return True

        return False

    def _match_operator(self) -> bool:
        """Match operators"""
        if self.current_pos >= len(self.source):
            return False

        # Try to match operators (longest first)
        for op in self.OPERATORS:
            if self.source[self.current_pos:].startswith(op):
                self._add_token(TokenType.OPERATOR, op)
                for _ in range(len(op)):
                    self._advance()
                return True

        return False

    def _match_punctuation(self) -> bool:
        """Match punctuation characters"""
        if self.current_pos >= len(self.source):
            return False

        char = self.source[self.current_pos]
        token_type = None

        if char == '(':
            token_type = TokenType.LPAREN
        elif char == ')':
            token_type = TokenType.RPAREN
        elif char == '[':
            token_type = TokenType.LBRACKET
        elif char == ']':
            token_type = TokenType.RBRACKET
        elif char == ',':
            token_type = TokenType.COMMA
        elif char == '.':
            # Check if it's a namespace accessor or numeric
            if (self.current_pos + 1 < len(self.source) and
                self.source[self.current_pos + 1].isalpha()):
                token_type = TokenType.DOT
            else:
                return False

        if token_type:
            self._add_token(token_type, char)
            self._advance()
            return True

        return False

    def _match_keyword_or_identifier(self) -> bool:
        """Match keywords, declarations, namespaces, builtins, or identifiers"""
        if self.current_pos >= len(self.source):
            return False

        char = self.source[self.current_pos]
        if char.isalpha() or char == '_':
            start_pos = self.current_pos

            # Read identifier
            while (self.current_pos < len(self.source) and
                   (self.source[self.current_pos].isalnum() or
                    self.source[self.current_pos] == '_')):
                self._advance()

            identifier = self.source[start_pos:self.current_pos]

            # Classify the identifier
            if identifier in self.KEYWORDS or identifier in self.DECLARATIONS:
                self._add_token(TokenType.KEYWORD, identifier)
            elif identifier in ['true', 'false', 'na']:
                self._add_token(TokenType.BOOLEAN, identifier)
            elif identifier in self.NAMESPACES:
                self._add_token(TokenType.NAMESPACE, identifier)
            elif identifier in self.BUILTINS:
                self._add_token(TokenType.BUILTIN, identifier)
            else:
                self._add_token(TokenType.IDENTIFIER, identifier)

            return True

        return False

    def _add_token(self, token_type: TokenType, value: str):
        """Add a token to the token list"""
        token = Token(
            type=token_type,
            value=value,
            line=self.current_line,
            column=self.current_column - len(value)
        )
        self.tokens.append(token)

    def _advance(self):
        """Advance position in source code"""
        if self.current_pos < len(self.source):
            if self.source[self.current_pos] == '\n':
                self.current_line += 1
                self.current_column = 1
            else:
                self.current_column += 1
            self.current_pos += 1

    def get_tokens_by_type(self, token_type: TokenType) -> List[Token]:
        """
        Get all tokens of a specific type

        Args:
            token_type: The token type to filter by

        Returns:
            List of tokens matching the type
        """
        return [t for t in self.tokens if t.type == token_type]

    def get_token_stream(self, include_whitespace: bool = False,
                        include_comments: bool = False) -> List[Token]:
        """
        Get a filtered token stream

        Args:
            include_whitespace: Include whitespace tokens
            include_comments: Include comment tokens

        Returns:
            Filtered list of tokens
        """
        excluded_types = set()
        if not include_whitespace:
            excluded_types.update({TokenType.WHITESPACE, TokenType.NEWLINE,
                                  TokenType.INDENT, TokenType.DEDENT})
        if not include_comments:
            excluded_types.add(TokenType.COMMENT)

        return [t for t in self.tokens if t.type not in excluded_types]

    def print_tokens(self, include_whitespace: bool = False):
        """
        Print all tokens for debugging

        Args:
            include_whitespace: Include whitespace tokens in output
        """
        tokens = self.get_token_stream(include_whitespace=include_whitespace)
        for token in tokens:
            print(f"{token.line:3d}:{token.column:3d} {token.type.name:15s} {repr(token.value)}")


def tokenize_pine_script(source: str) -> List[Token]:
    """
    Convenience function to tokenize Pine Script source code

    Args:
        source: Pine Script source code

    Returns:
        List of Token objects
    """
    lexer = PineLexer()
    return lexer.tokenize(source)


if __name__ == "__main__":
    # Example usage
    sample_code = """
//@version=5
indicator("Test", overlay=true)

// Calculate moving averages
fast = ta.ema(close, 9)
slow = ta.sma(close, 21)

// Check crossover
signal = ta.crossover(fast, slow)

// Plot
plot(fast, color=color.blue)
"""

    lexer = PineLexer()
    tokens = lexer.tokenize(sample_code)
    lexer.print_tokens()
