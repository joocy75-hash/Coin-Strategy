"""
Python Code Builder for Pine Script Expressions

Converts expression AST nodes into executable Python code strings.
Handles operator transformations, function mapping, and built-in variable resolution.
"""

from typing import Optional
import logging

from .expression_parser import ExprNode, ExprNodeType
from .transformation_context import TransformationContext
from .indicator_mapper import IndicatorMapper

logger = logging.getLogger(__name__)


class PythonCodeBuilder:
    """
    Builds Python code from expression AST nodes.

    Converts Pine Script expression trees into Python code strings,
    handling operator transformations, function mapping, and context-aware
    variable resolution.

    Example:
        >>> builder = PythonCodeBuilder()
        >>> context = TransformationContext()
        >>> node = ExprNode(node_type=ExprNodeType.LITERAL, value=42)
        >>> builder.build(node, context)
        '42'
    """

    def __init__(self, indicator_mapper: Optional[IndicatorMapper] = None):
        """
        Initialize code builder.

        Args:
            indicator_mapper: IndicatorMapper instance for ta.* function mapping.
                            If None, creates a new instance.
        """
        self.indicator_mapper = indicator_mapper or IndicatorMapper()

        # Pine operator to Python operator mappings
        self.operator_map = {
            # Assignment operators
            ':=': '=',
            '=': '=',

            # Comparison operators (unchanged)
            '==': '==',
            '!=': '!=',
            '<': '<',
            '>': '>',
            '<=': '<=',
            '>=': '>=',

            # Arithmetic operators (unchanged)
            '+': '+',
            '-': '-',
            '*': '*',
            '/': '/',
            '%': '%',

            # Logical operators (unchanged)
            'and': 'and',
            'or': 'or',
            'not': 'not',
        }

    def build(self, node: ExprNode, context: TransformationContext) -> str:
        """
        Build Python code from an expression AST node.

        Args:
            node: Expression AST node to convert
            context: Transformation context for variable resolution

        Returns:
            Python code string

        Raises:
            ValueError: If node type is unsupported

        Example:
            >>> builder = PythonCodeBuilder()
            >>> context = TransformationContext()
            >>> # Binary operation: 10 + 20
            >>> node = ExprNode(
            ...     node_type=ExprNodeType.BINARY_OP,
            ...     value='+',
            ...     left=ExprNode(node_type=ExprNodeType.LITERAL, value=10),
            ...     right=ExprNode(node_type=ExprNodeType.LITERAL, value=20)
            ... )
            >>> builder.build(node, context)
            '10 + 20'
        """
        if node.node_type == ExprNodeType.LITERAL:
            return self._build_literal(node)

        elif node.node_type == ExprNodeType.IDENTIFIER:
            return self._build_identifier(node, context)

        elif node.node_type == ExprNodeType.BINARY_OP:
            return self._build_binary_op(node, context)

        elif node.node_type == ExprNodeType.UNARY_OP:
            return self._build_unary_op(node, context)

        elif node.node_type == ExprNodeType.CALL:
            return self._build_call(node, context)

        elif node.node_type == ExprNodeType.TERNARY:
            return self._build_ternary(node, context)

        elif node.node_type == ExprNodeType.MEMBER_ACCESS:
            return self._build_member_access(node, context)

        elif node.node_type == ExprNodeType.ARRAY_ACCESS:
            return self._build_array_access(node, context)

        else:
            raise ValueError(f"Unsupported node type: {node.node_type}")

    def _build_literal(self, node: ExprNode) -> str:
        """
        Build Python code for a literal value.

        Args:
            node: LITERAL node

        Returns:
            Python literal string
        """
        value = node.value

        # Handle different literal types
        if isinstance(value, str):
            # String literal - ensure quotes
            if not (value.startswith('"') or value.startswith("'")):
                return f'"{value}"'
            return value

        elif isinstance(value, bool):
            # Boolean - Python uses capitalized True/False
            return str(value)

        elif isinstance(value, (int, float)):
            # Number
            return str(value)

        else:
            # Default
            return str(value)

    def _build_identifier(self, node: ExprNode, context: TransformationContext) -> str:
        """
        Build Python code for an identifier.

        Resolves Pine variable names to Python equivalents using context.

        Args:
            node: IDENTIFIER node
            context: Transformation context

        Returns:
            Python identifier or expression
        """
        name = node.value

        # Resolve through context (checks built-ins and user variables)
        return context.resolve_name(name)

    def _build_binary_op(self, node: ExprNode, context: TransformationContext) -> str:
        """
        Build Python code for a binary operation.

        Args:
            node: BINARY_OP node
            context: Transformation context

        Returns:
            Python binary expression
        """
        operator = node.value

        # Transform operator if needed
        python_op = self.operator_map.get(operator, operator)

        # Build left and right operands
        left_code = self.build(node.left, context)
        right_code = self.build(node.right, context)

        # Return with proper spacing
        return f"{left_code} {python_op} {right_code}"

    def _build_unary_op(self, node: ExprNode, context: TransformationContext) -> str:
        """
        Build Python code for a unary operation.

        Args:
            node: UNARY_OP node
            context: Transformation context

        Returns:
            Python unary expression
        """
        operator = node.value

        # Transform operator if needed
        python_op = self.operator_map.get(operator, operator)

        # Build operand
        operand_code = self.build(node.operand, context)

        # 'not' needs a space, others don't
        if operator == 'not':
            return f"{python_op} {operand_code}"
        else:
            return f"{python_op}{operand_code}"

    def _build_call(self, node: ExprNode, context: TransformationContext) -> str:
        """
        Build Python code for a function call.

        Handles special Pine functions like ta.ema, ta.sma, etc.

        Args:
            node: CALL node
            context: Transformation context

        Returns:
            Python function call

        Example:
            ta.ema(close, 9) → self.indicators.ema(self.close, 9)
        """
        func_name = node.value
        args = node.args

        # Check if this is a Pine indicator function (ta.*)
        if func_name.startswith('ta.'):
            # Track indicator usage
            context.add_indicator(func_name)

            # TODO: Map ta.* function to IndicatorMapper method call
            #
            # Instructions for user:
            # Transform Pine indicator functions to Python IndicatorMapper calls.
            #
            # Pattern:
            #   ta.ema(close, 9) → self.indicator_mapper.calculate('ta.ema', self.close, length=9)
            #   ta.sma(close, 20) → self.indicator_mapper.calculate('ta.sma', self.close, length=20)
            #   ta.rsi(close, 14) → self.indicator_mapper.calculate('ta.rsi', self.close, length=14)
            #
            # Steps:
            # 1. Build argument code from args list
            # 2. For most indicators, first arg is 'source', second is 'length'
            # 3. Return: f"self.indicator_mapper.calculate('{func_name}', {arg_code})"
            #
            # Handle special cases:
            #   - ta.crossover(a, b) → self.indicator_mapper.calculate('ta.crossover', a, b)
            #   - ta.crossunder(a, b) → self.indicator_mapper.calculate('ta.crossunder', a, b)

            # Build arguments
            arg_codes = [self.build(arg, context) for arg in args]
            arg_str = ', '.join(arg_codes)

            # Return the mapped call
            return f"self.indicator_mapper.calculate('{func_name}', {arg_str})"

        # Check if this is a strategy function (strategy.*)
        elif func_name.startswith('strategy.'):
            # Strategy calls are handled separately, but for expressions:
            # strategy.position_size, etc.
            arg_codes = [self.build(arg, context) for arg in args]
            arg_str = ', '.join(arg_codes)
            return f"{func_name}({arg_str})"

        # Check if this is a math function (math.*)
        elif func_name.startswith('math.'):
            # Map to Python math module
            # math.abs → abs, math.max → max, math.min → min, etc.
            import_name = func_name.replace('math.', '')

            # Some Pine math functions map to builtins
            builtin_map = {
                'abs': 'abs',
                'max': 'max',
                'min': 'min',
                'round': 'round',
            }

            if import_name in builtin_map:
                python_func = builtin_map[import_name]
            else:
                python_func = f"np.{import_name}"

            arg_codes = [self.build(arg, context) for arg in args]
            arg_str = ', '.join(arg_codes)
            return f"{python_func}({arg_str})"

        # Regular function call
        else:
            arg_codes = [self.build(arg, context) for arg in args]
            arg_str = ', '.join(arg_codes)
            return f"{func_name}({arg_str})"

    def _build_ternary(self, node: ExprNode, context: TransformationContext) -> str:
        """
        Build Python code for a ternary operator.

        Pine: condition ? true_value : false_value
        Python: true_value if condition else false_value

        Args:
            node: TERNARY node
            context: Transformation context

        Returns:
            Python ternary expression
        """
        # TODO: Build Python ternary expression
        #
        # Instructions for user:
        # Convert Pine ternary operator to Python ternary expression.
        #
        # Pine syntax:  condition ? true_expr : false_expr
        # Python syntax: true_expr if condition else false_expr
        #
        # Steps:
        # 1. Build condition code from node.condition
        # 2. Build true_expr code from node.true_expr
        # 3. Build false_expr code from node.false_expr
        # 4. Return: f"{true_code} if {cond_code} else {false_code}"

        cond_code = self.build(node.condition, context)
        true_code = self.build(node.true_expr, context)
        false_code = self.build(node.false_expr, context)

        return f"{true_code} if {cond_code} else {false_code}"

    def _build_member_access(self, node: ExprNode, context: TransformationContext) -> str:
        """
        Build Python code for member access.

        Example: ta.ema → 'ta.ema' (for later function call handling)

        Args:
            node: MEMBER_ACCESS node
            context: Transformation context

        Returns:
            Python member access expression
        """
        base = node.value
        member = node.member

        # Check if base is a Pine built-in namespace
        if base in ['ta', 'strategy', 'math', 'barstate']:
            # Keep as-is for now (will be handled in _build_call)
            return f"{base}.{member}"

        # Otherwise, resolve base and access member
        base_code = context.resolve_name(base)
        return f"{base_code}.{member}"

    def _build_array_access(self, node: ExprNode, context: TransformationContext) -> str:
        """
        Build Python code for array access.

        Pine: array[index] or series[offset]
        Python: array[index] or series.iloc[offset]

        Args:
            node: ARRAY_ACCESS node
            context: Transformation context

        Returns:
            Python array access expression
        """
        # Get base array/series
        if node.value:
            base = context.resolve_name(node.value)
        else:
            base = self.build(node.left, context)

        # Build index
        index_code = self.build(node.index, context)

        # For pandas Series (most Pine series), use .iloc
        # For simple arrays/lists, use []
        # We'll default to .iloc for now (safer for backtesting)
        return f"{base}.iloc[{index_code}]"
