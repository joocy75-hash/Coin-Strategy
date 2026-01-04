"""
Node Translator - AST Node to Python Code Translation

Translates individual AST nodes (InputNode, VariableNode, etc.) to Python code fragments.
"""

from typing import List, Dict, Any
import logging

from .pine_parser import (
    InputNode, VariableNode, FunctionNode,
    StrategyCallNode, PlotNode, ConditionNode
)
from .expression_transformer import ExpressionTransformer
from .transformation_context import TransformationContext

logger = logging.getLogger(__name__)


class NodeTranslator:
    """
    Translate Pine Script AST nodes to Python code fragments.

    Works in conjunction with ExpressionTransformer to convert complete
    Pine AST nodes into Python code segments.

    Example:
        >>> translator = NodeTranslator()
        >>> input_node = InputNode(
        ...     input_type='int',
        ...     name='period',
        ...     default_value=14,
        ...     title='RSI Period'
        ... )
        >>> translator.translate_input(input_node)
        'self.period = self.params.get("period", 14)  # RSI Period'
    """

    def __init__(self, expression_transformer: ExpressionTransformer = None):
        """
        Initialize node translator.

        Args:
            expression_transformer: ExpressionTransformer instance for expressions.
                                  If None, creates a new instance.
        """
        self.expr_transformer = expression_transformer or ExpressionTransformer()
        self.context = TransformationContext()

    def translate_input(self, node: InputNode) -> str:
        """
        Translate InputNode to Python parameter initialization.

        Args:
            node: InputNode from Pine AST

        Returns:
            Python code line for parameter

        Example:
            >>> translator = NodeTranslator()
            >>> node = InputNode('int', 'length', 20, 'MA Length')
            >>> translator.translate_input(node)
            'self.length = self.params.get("length", 20)  # MA Length'
        """
        comment = f"  # {node.title}" if node.title else ""
        return f'self.{node.name} = self.params.get("{node.name}", {node.default_value}){comment}'

    def translate_variable(
        self,
        node: VariableNode,
        context: TransformationContext = None
    ) -> str:
        """
        Translate VariableNode to Python variable assignment.

        Args:
            node: VariableNode from Pine AST
            context: Transformation context (optional)

        Returns:
            Python code line for variable

        Example:
            >>> translator = NodeTranslator()
            >>> node = VariableNode('', 'fast_ma', 'ta.ema(close, 9)')
            >>> translator.translate_variable(node)
            'fast_ma = self.indicator_mapper.calculate(\\'ta.ema\\', self.close, 9)'
        """
        if context is None:
            context = self.context

        # Transform the expression using ExpressionTransformer
        result = self.expr_transformer.transform_assignment(
            var_name=node.name,
            pine_expr=node.value_expr,
            modifier=node.modifier,
            context=context
        )

        return result

    def translate_condition(
        self,
        node: ConditionNode,
        context: TransformationContext = None
    ) -> List[str]:
        """
        Translate ConditionNode to Python if/else block.

        Args:
            node: ConditionNode from Pine AST
            context: Transformation context (optional)

        Returns:
            List of Python code lines

        Example:
            >>> translator = NodeTranslator()
            >>> node = ConditionNode(
            ...     condition='close > ema',
            ...     true_branch=['strategy.entry("Long", strategy.long)']
            ... )
            >>> lines = translator.translate_condition(node)
            >>> 'if' in lines[0]
            True
        """
        if context is None:
            context = self.context

        lines = []

        # Transform condition
        condition_code = self.expr_transformer.transform_condition(
            node.condition,
            context
        )

        # if statement
        lines.append(f"if {condition_code}:")

        # True branch
        if node.true_branch:
            for stmt in node.true_branch:
                # Transform each statement
                result = self.expr_transformer.transform_expression(stmt, context)
                lines.append(f"    {result.python_code}")
        else:
            lines.append("    pass")

        # False branch (else)
        if node.false_branch:
            lines.append("else:")
            for stmt in node.false_branch:
                result = self.expr_transformer.transform_expression(stmt, context)
                lines.append(f"    {result.python_code}")

        return lines

    def translate_function(
        self,
        node: FunctionNode,
        context: TransformationContext = None
    ) -> List[str]:
        """
        Translate FunctionNode to Python method definition.

        Args:
            node: FunctionNode from Pine AST
            context: Transformation context (optional)

        Returns:
            List of Python code lines

        Example:
            >>> translator = NodeTranslator()
            >>> node = FunctionNode(
            ...     name='calculate_signal',
            ...     parameters=[('price', 'float')],
            ...     body='price > 100'
            ... )
            >>> lines = translator.translate_function(node)
            >>> 'def _calculate_signal' in lines[0]
            True
        """
        if context is None:
            context = self.context

        lines = []

        # Build parameter list
        params = ['self'] + [f"{name}: {ptype}" for name, ptype in node.parameters]
        params_str = ', '.join(params)

        # Return type
        return_type = f" -> {node.return_type}" if node.return_type else ""

        # Method definition
        lines.append(f"def _{node.name}({params_str}){return_type}:")

        # Docstring
        lines.append(f'    """Custom Pine Script function: {node.name}"""')

        # Body
        body_lines = self.expr_transformer.transform_function_body(node.body, context)

        if body_lines:
            for line in body_lines:
                lines.append(f"    {line}")
        else:
            lines.append("    pass")

        return lines

    def translate_strategy_call(
        self,
        node: StrategyCallNode,
        context: TransformationContext = None
    ) -> Dict[str, Any]:
        """
        Translate StrategyCallNode to Python signal generation code.

        Args:
            node: StrategyCallNode from Pine AST
            context: Transformation context (optional)

        Returns:
            Dictionary with signal information

        Example:
            >>> translator = NodeTranslator()
            >>> node = StrategyCallNode(
            ...     call_type='entry',
            ...     id_value='Long',
            ...     direction='long',
            ...     when='buy_signal'
            ... )
            >>> info = translator.translate_strategy_call(node)
            >>> info['type']
            'entry'
        """
        if context is None:
            context = self.context

        # Transform condition if present
        condition_code = "True"
        if node.when:
            result = self.expr_transformer.transform_condition(node.when, context)
            condition_code = result

        return {
            'type': node.call_type,
            'id': node.id_value,
            'direction': node.direction,
            'condition': condition_code,
            'qty': node.qty,
            'limit': node.limit,
            'stop': node.stop
        }

    def translate_plot(self, node: PlotNode) -> str:
        """
        Translate PlotNode to Python comment (plots not supported in backtesting).

        Args:
            node: PlotNode from Pine AST

        Returns:
            Python comment line

        Example:
            >>> translator = NodeTranslator()
            >>> node = PlotNode('plot', 'ma', title='MA', color='blue')
            >>> translator.translate_plot(node)
            '# Plot: MA (blue)'
        """
        title = node.title or node.series
        color = f" ({node.color})" if node.color else ""
        return f"# Plot: {title}{color}"

    def reset_context(self):
        """Reset the transformation context."""
        self.context = TransformationContext()

    def get_context(self) -> TransformationContext:
        """Get current transformation context."""
        return self.context
