"""
Expression Parser for Pine Script

Implements a recursive descent parser to convert Pine Script expressions
into an Abstract Syntax Tree (AST) suitable for Python code generation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Union
from enum import Enum, auto
import logging

from .pine_lexer import PineLexer, Token, TokenType

logger = logging.getLogger(__name__)


class ExprNodeType(Enum):
    """Types of expression AST nodes."""
    LITERAL = auto()          # Numbers, strings, booleans
    IDENTIFIER = auto()       # Variable names
    BINARY_OP = auto()        # Binary operators: +, -, *, /, ==, etc.
    UNARY_OP = auto()         # Unary operators: -, +, not
    CALL = auto()             # Function calls: func(args)
    TERNARY = auto()          # Ternary operator: condition ? true : false
    ARRAY_ACCESS = auto()     # Array indexing: arr[index]
    MEMBER_ACCESS = auto()    # Member access: obj.member


@dataclass
class ExprNode:
    """
    Expression AST Node.

    Represents a parsed Pine Script expression as a tree structure.

    Attributes:
        node_type: Type of expression node
        value: Node value (literal value, operator symbol, identifier name)
        left: Left operand (for binary operators)
        right: Right operand (for binary operators)
        operand: Operand (for unary operators)
        args: Function call arguments (for CALL nodes)
        condition: Condition expression (for TERNARY)
        true_expr: True branch (for TERNARY)
        false_expr: False branch (for TERNARY)
        member: Member name (for MEMBER_ACCESS)
        index: Index expression (for ARRAY_ACCESS)
    """
    node_type: ExprNodeType
    value: Any = None
    left: Optional['ExprNode'] = None
    right: Optional['ExprNode'] = None
    operand: Optional['ExprNode'] = None
    args: List['ExprNode'] = field(default_factory=list)
    condition: Optional['ExprNode'] = None
    true_expr: Optional['ExprNode'] = None
    false_expr: Optional['ExprNode'] = None
    member: Optional[str] = None
    index: Optional['ExprNode'] = None

    def __repr__(self) -> str:
        """Compact representation for debugging."""
        if self.node_type == ExprNodeType.LITERAL:
            return f"Literal({self.value})"
        elif self.node_type == ExprNodeType.IDENTIFIER:
            return f"Id({self.value})"
        elif self.node_type == ExprNodeType.BINARY_OP:
            return f"BinOp({self.value}: {self.left!r}, {self.right!r})"
        elif self.node_type == ExprNodeType.UNARY_OP:
            return f"UnaryOp({self.value}: {self.operand!r})"
        elif self.node_type == ExprNodeType.CALL:
            return f"Call({self.value}, {len(self.args)} args)"
        elif self.node_type == ExprNodeType.TERNARY:
            return f"Ternary(? :)"
        elif self.node_type == ExprNodeType.MEMBER_ACCESS:
            return f"Member({self.value}.{self.member})"
        elif self.node_type == ExprNodeType.ARRAY_ACCESS:
            return f"ArrayAccess({self.value}[...])"
        return f"ExprNode({self.node_type})"


class ParseError(Exception):
    """Raised when expression parsing fails."""
    pass


class ExpressionParser:
    """
    Recursive descent parser for Pine Script expressions.

    Parses expressions according to this grammar (from highest to lowest precedence):

        expression     → ternary
        ternary        → logical_or ( "?" expression ":" expression )?
        logical_or     → logical_and ( "or" logical_and )*
        logical_and    → comparison ( "and" comparison )*
        comparison     → addition ( ("==" | "!=" | "<=" | ">=" | "<" | ">") addition )*
        addition       → multiplication ( ("+" | "-") multiplication )*
        multiplication → unary ( ("*" | "/" | "%") unary )*
        unary          → ("not" | "-" | "+") unary | call
        call           → primary ( "(" arguments? ")" | "[" expression "]" | "." IDENTIFIER )*
        primary        → NUMBER | STRING | BOOLEAN | IDENTIFIER | "(" expression ")"
        arguments      → expression ( "," expression )*

    Example:
        >>> parser = ExpressionParser()
        >>> ast = parser.parse("ta.ema(close, 9)")
        >>> ast.node_type
        <ExprNodeType.CALL: ...>
        >>> ast.value
        'ta.ema'
    """

    def __init__(self):
        """Initialize parser."""
        self.lexer = PineLexer()
        self.tokens: List[Token] = []
        self.current = 0

    def parse(self, pine_expr: str) -> ExprNode:
        """
        Parse a Pine Script expression into an AST.

        Args:
            pine_expr: Pine Script expression string

        Returns:
            ExprNode representing the parsed expression

        Raises:
            ParseError: If expression has invalid syntax

        Example:
            >>> parser = ExpressionParser()
            >>> ast = parser.parse("close > 100")
            >>> ast.node_type == ExprNodeType.BINARY_OP
            True
            >>> ast.value
            '>'
        """
        # Tokenize the expression
        self.tokens = self.lexer.tokenize(pine_expr.strip())
        self.current = 0

        if not self.tokens:
            raise ParseError(f"Empty expression: {pine_expr}")

        # Parse according to grammar
        try:
            node = self.expression()

            # Ensure all tokens consumed
            if not self.is_at_end():
                raise ParseError(
                    f"Unexpected token after expression: {self.peek().value}"
                )

            return node

        except Exception as e:
            logger.error(f"Parse error in '{pine_expr}': {e}")
            raise ParseError(f"Failed to parse expression '{pine_expr}': {e}")

    # Grammar rule implementations (from lowest to highest precedence)

    def expression(self) -> ExprNode:
        """Parse expression → ternary"""
        return self.ternary()

    def ternary(self) -> ExprNode:
        """Parse ternary → logical_or ( "?" expression ":" expression )?"""
        expr = self.logical_or()

        # Check for ternary operator: condition ? true_expr : false_expr
        if self.match(TokenType.OPERATOR, '?'):
            true_expr = self.expression()

            if not self.match(TokenType.OPERATOR, ':'):
                raise ParseError("Expected ':' in ternary operator")

            false_expr = self.expression()

            return ExprNode(
                node_type=ExprNodeType.TERNARY,
                condition=expr,
                true_expr=true_expr,
                false_expr=false_expr
            )

        return expr

    def logical_or(self) -> ExprNode:
        """Parse logical_or → logical_and ( "or" logical_and )*"""
        expr = self.logical_and()

        while self.match(TokenType.KEYWORD, 'or'):
            operator = 'or'
            right = self.logical_and()
            expr = ExprNode(
                node_type=ExprNodeType.BINARY_OP,
                value=operator,
                left=expr,
                right=right
            )

        return expr

    def logical_and(self) -> ExprNode:
        """Parse logical_and → comparison ( "and" comparison )*"""
        expr = self.comparison()

        while self.match(TokenType.KEYWORD, 'and'):
            operator = 'and'
            right = self.comparison()
            expr = ExprNode(
                node_type=ExprNodeType.BINARY_OP,
                value=operator,
                left=expr,
                right=right
            )

        return expr

    def comparison(self) -> ExprNode:
        """Parse comparison → addition ( ("==" | "!=" | "<=" | ">=" | "<" | ">") addition )*"""
        expr = self.addition()

        while self.check_operator(['==', '!=', '<=', '>=', '<', '>']):
            operator = self.advance().value
            right = self.addition()
            expr = ExprNode(
                node_type=ExprNodeType.BINARY_OP,
                value=operator,
                left=expr,
                right=right
            )

        return expr

    def addition(self) -> ExprNode:
        """Parse addition → multiplication ( ("+" | "-") multiplication )*"""
        expr = self.multiplication()

        while self.check_operator(['+', '-']):
            operator = self.advance().value
            right = self.multiplication()
            expr = ExprNode(
                node_type=ExprNodeType.BINARY_OP,
                value=operator,
                left=expr,
                right=right
            )

        return expr

    def multiplication(self) -> ExprNode:
        """Parse multiplication → unary ( ("*" | "/" | "%") unary )*"""
        expr = self.unary()

        while self.check_operator(['*', '/', '%']):
            operator = self.advance().value
            right = self.unary()
            expr = ExprNode(
                node_type=ExprNodeType.BINARY_OP,
                value=operator,
                left=expr,
                right=right
            )

        return expr

    def unary(self) -> ExprNode:
        """Parse unary → ("not" | "-" | "+") unary | call"""
        # Check for unary operators
        if self.match(TokenType.KEYWORD, 'not'):
            operator = 'not'
            operand = self.unary()
            return ExprNode(
                node_type=ExprNodeType.UNARY_OP,
                value=operator,
                operand=operand
            )

        if self.check_operator(['-', '+']):
            operator = self.advance().value
            operand = self.unary()
            return ExprNode(
                node_type=ExprNodeType.UNARY_OP,
                value=operator,
                operand=operand
            )

        return self.call()

    def call(self) -> ExprNode:
        """Parse call → primary ( "(" arguments? ")" | "[" expression "]" | "." IDENTIFIER )*"""
        expr = self.primary()

        while True:
            if self.match(TokenType.LPAREN):
                # Function call
                args = self.arguments() if not self.check(TokenType.RPAREN) else []
                self.consume(TokenType.RPAREN, "Expected ')' after arguments")

                # Convert identifier to function name
                if expr.node_type == ExprNodeType.IDENTIFIER:
                    func_name = expr.value
                elif expr.node_type == ExprNodeType.MEMBER_ACCESS:
                    # Already a member access (e.g., ta.sma)
                    func_name = f"{expr.value}.{expr.member}"
                else:
                    raise ParseError(f"Cannot call non-identifier: {expr}")

                expr = ExprNode(
                    node_type=ExprNodeType.CALL,
                    value=func_name,
                    args=args
                )

            elif self.match(TokenType.LBRACKET):
                # Array access
                index = self.expression()
                self.consume(TokenType.RBRACKET, "Expected ']' after array index")

                # Get base object
                if expr.node_type == ExprNodeType.IDENTIFIER:
                    base = expr.value
                else:
                    # For complex expressions, we'll need to handle differently
                    base = expr

                expr = ExprNode(
                    node_type=ExprNodeType.ARRAY_ACCESS,
                    value=base if isinstance(base, str) else None,
                    left=expr if not isinstance(base, str) else None,
                    index=index
                )

            elif self.match(TokenType.DOT):
                # Member access (e.g., ta.sma, strategy.long)
                member = self.consume(TokenType.IDENTIFIER, "Expected member name after '.'")

                # Get base object
                if expr.node_type == ExprNodeType.IDENTIFIER:
                    base = expr.value
                else:
                    raise ParseError(f"Cannot access member of non-identifier: {expr}")

                expr = ExprNode(
                    node_type=ExprNodeType.MEMBER_ACCESS,
                    value=base,
                    member=member.value
                )

            else:
                break

        return expr

    def arguments(self) -> List[ExprNode]:
        """Parse arguments → expression ( "," expression )*"""
        args = [self.expression()]

        while self.match(TokenType.COMMA):
            args.append(self.expression())

        return args

    def primary(self) -> ExprNode:
        """Parse primary → NUMBER | STRING | BOOLEAN | IDENTIFIER | "(" expression ")" """
        # Number
        if self.check(TokenType.NUMBER):
            token = self.advance()
            # Convert to float or int
            try:
                value = float(token.value) if '.' in token.value else int(token.value)
            except ValueError:
                value = token.value
            return ExprNode(node_type=ExprNodeType.LITERAL, value=value)

        # String
        if self.check(TokenType.STRING):
            token = self.advance()
            # Remove quotes
            value = token.value.strip('"').strip("'")
            return ExprNode(node_type=ExprNodeType.LITERAL, value=value)

        # Boolean
        if self.match(TokenType.KEYWORD, 'true') or self.match(TokenType.KEYWORD, 'false'):
            value = self.previous().value == 'true'
            return ExprNode(node_type=ExprNodeType.LITERAL, value=value)

        # Identifier (includes KEYWORD tokens that are used as identifiers like 'ta', 'strategy', etc.)
        if self.check(TokenType.IDENTIFIER) or self.check(TokenType.KEYWORD):
            token = self.advance()
            # Skip logical keywords (and, or, not) - they should be handled elsewhere
            if token.value in ['and', 'or', 'not']:
                raise ParseError(f"Unexpected keyword: {token.value}")
            return ExprNode(node_type=ExprNodeType.IDENTIFIER, value=token.value)

        # Parenthesized expression
        if self.match(TokenType.LPAREN):
            expr = self.expression()
            self.consume(TokenType.RPAREN, "Expected ')' after expression")
            return expr

        # Error
        if not self.is_at_end():
            raise ParseError(f"Unexpected token: {self.peek().value}")
        else:
            raise ParseError("Unexpected end of expression")

    # Helper methods for token management

    def match(self, token_type: TokenType, value: Optional[str] = None) -> bool:
        """Check if current token matches type and optionally value, and advance if so."""
        if self.check(token_type, value):
            self.advance()
            return True
        return False

    def check(self, token_type: TokenType, value: Optional[str] = None) -> bool:
        """Check if current token matches type and optionally value."""
        if self.is_at_end():
            return False

        token = self.peek()
        if token.type != token_type:
            return False

        if value is not None and token.value != value:
            return False

        return True

    def check_operator(self, operators: List[str]) -> bool:
        """Check if current token is one of the given operators."""
        if self.is_at_end():
            return False

        token = self.peek()
        return token.type == TokenType.OPERATOR and token.value in operators

    def advance(self) -> Token:
        """Consume and return current token."""
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def is_at_end(self) -> bool:
        """Check if we've consumed all tokens."""
        return self.current >= len(self.tokens)

    def peek(self) -> Token:
        """Return current token without consuming."""
        if self.current < len(self.tokens):
            return self.tokens[self.current]
        # Return a dummy EOF token
        return Token(TokenType.IDENTIFIER, '', 0, 0)

    def previous(self) -> Token:
        """Return previous token."""
        return self.tokens[self.current - 1]

    def consume(self, token_type: TokenType, error_message: str) -> Token:
        """Consume token of given type or raise error."""
        if self.check(token_type):
            return self.advance()

        raise ParseError(f"{error_message} (got {self.peek().type})")
