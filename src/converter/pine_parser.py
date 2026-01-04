"""
Pine Script Parser and AST Builder

Converts tokenized Pine Script into an Abstract Syntax Tree (AST) for analysis
and conversion. Calculates complexity scores to determine LLM usage.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum, auto
import logging

from .pine_lexer import Token, TokenType, PineLexer

logger = logging.getLogger(__name__)


# ============================================================================
# AST Node Definitions
# ============================================================================

@dataclass
class ASTNode:
    """Base class for all AST nodes"""
    line: int = 0
    column: int = 0


@dataclass
class InputNode:
    """Represents an input declaration (input.int, input.float, etc.)"""
    input_type: str  # 'int', 'float', 'bool', 'string'
    name: str
    default_value: Any
    title: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    options: List[Any] = field(default_factory=list)
    line: int = 0
    column: int = 0


@dataclass
class VariableNode:
    """Represents a variable declaration (var, varip)"""
    modifier: str  # 'var', 'varip', or '' for regular
    name: str
    value_expr: str  # The expression as string (will be parsed separately)
    var_type: Optional[str] = None  # 'int', 'float', 'array<float>', etc.
    line: int = 0
    column: int = 0


@dataclass
class FunctionNode:
    """Represents a user-defined function"""
    name: str
    parameters: List[Tuple[str, Optional[str]]]  # [(param_name, param_type), ...]
    return_type: Optional[str]
    body: str  # Function body as string
    line: int = 0
    column: int = 0


@dataclass
class StrategyCallNode:
    """Represents strategy.entry/close/exit calls"""
    call_type: str  # 'entry', 'close', 'exit'
    id_value: str
    direction: Optional[str] = None  # 'long', 'short'
    qty: Optional[str] = None
    limit: Optional[str] = None
    stop: Optional[str] = None
    when: Optional[str] = None  # Condition expression
    line: int = 0
    column: int = 0


@dataclass
class PlotNode:
    """Represents plot/plotshape/plotchar calls"""
    plot_type: str  # 'plot', 'plotshape', 'plotchar'
    series: str  # Expression to plot
    title: str = ""
    color: str = ""
    linewidth: int = 1
    style: str = ""
    location: str = ""
    line: int = 0
    column: int = 0


@dataclass
class ConditionNode:
    """Represents if/else conditions"""
    condition: str
    true_branch: List[str]  # Code lines in if block
    false_branch: List[str] = field(default_factory=list)  # Code lines in else block
    line: int = 0
    column: int = 0


@dataclass
class ExpressionNode:
    """Represents a general expression"""
    expression: str
    expr_type: str  # 'assignment', 'function_call', 'operator', etc.
    line: int = 0
    column: int = 0


@dataclass
class PineAST:
    """Complete Abstract Syntax Tree for a Pine Script"""
    version: int  # Pine Script version (5, 4, etc.)
    script_type: str  # "indicator" or "strategy"
    script_name: str  # Name from indicator() or strategy()

    # Core components
    inputs: List[InputNode] = field(default_factory=list)
    variables: List[VariableNode] = field(default_factory=list)
    functions: List[FunctionNode] = field(default_factory=list)
    strategy_calls: List[StrategyCallNode] = field(default_factory=list)
    plots: List[PlotNode] = field(default_factory=list)
    conditions: List[ConditionNode] = field(default_factory=list)

    # Metadata
    raw_code: str = ""
    complexity_score: float = 0.0  # 0.0-1.0

    # Complexity factors (for debugging)
    complexity_factors: Dict[str, float] = field(default_factory=dict)

    # Detected indicators
    indicators_used: List[str] = field(default_factory=list)

    # Statistics
    total_lines: int = 0
    code_lines: int = 0  # Excluding comments and blank lines


# ============================================================================
# Pine Parser
# ============================================================================

class PineParser:
    """
    Parser for Pine Script code

    Converts a token stream into an Abstract Syntax Tree (AST) that can be
    used for analysis and Python code generation.

    Example:
        lexer = PineLexer()
        tokens = lexer.tokenize(pine_code)

        parser = PineParser(tokens)
        ast = parser.parse()

        print(f"Script: {ast.script_name}")
        print(f"Complexity: {ast.complexity_score:.2f}")
        print(f"Indicators: {len(ast.indicators_used)}")
    """

    def __init__(self, tokens: List[Token], raw_code: str = ""):
        """
        Initialize parser with token stream

        Args:
            tokens: List of tokens from PineLexer
            raw_code: Original source code (optional)
        """
        self.tokens = tokens
        self.current = 0
        self.raw_code = raw_code if raw_code else self._reconstruct_code()

    def _reconstruct_code(self) -> str:
        """Reconstruct original code from tokens"""
        return ''.join(token.value for token in self.tokens)

    def parse(self) -> PineAST:
        """
        Main parsing method

        Returns:
            PineAST object with all parsed components
        """
        ast = PineAST(
            version=5,  # Default
            script_type="indicator",  # Default
            script_name="Unknown",
            raw_code=self.raw_code
        )

        # Extract version
        ast.version = self._extract_version()

        # Extract script type and name
        ast.script_type, ast.script_name = self._extract_script_declaration()

        # Parse all components
        ast.inputs = self.parse_inputs()
        ast.variables = self.parse_variables()
        ast.functions = self.parse_functions()
        ast.strategy_calls = self.parse_strategy_calls()
        ast.plots = self.parse_plots()
        ast.conditions = self.parse_conditions()

        # Extract indicators
        ast.indicators_used = self._extract_indicators()

        # Calculate statistics
        ast.total_lines = len(self.raw_code.split('\n'))
        ast.code_lines = self._count_code_lines()

        # Calculate complexity score
        ast.complexity_score, ast.complexity_factors = self.calculate_complexity(ast)

        return ast

    # ------------------------------------------------------------------------
    # Version and Script Type Extraction
    # ------------------------------------------------------------------------

    def _extract_version(self) -> int:
        """Extract Pine Script version from //@version comment"""
        for token in self.tokens:
            if token.type == TokenType.COMMENT:
                match = re.search(r'@version[=\s]+(\d+)', token.value)
                if match:
                    return int(match.group(1))
        return 5  # Default to v5

    def _extract_script_declaration(self) -> Tuple[str, str]:
        """Extract script type (indicator/strategy) and name"""
        script_type = "indicator"
        script_name = "Unknown"

        # Look for indicator() or strategy() declaration
        for i, token in enumerate(self.tokens):
            if token.value in ('indicator', 'strategy'):
                script_type = token.value

                # Extract name from function call
                # pattern: indicator("Name", ...) or strategy("Name", ...)
                if i + 2 < len(self.tokens):
                    if self.tokens[i + 1].type == TokenType.LPAREN:
                        # Find the first string literal
                        for j in range(i + 2, min(i + 10, len(self.tokens))):
                            if self.tokens[j].type == TokenType.STRING:
                                script_name = self.tokens[j].value.strip('"\'')
                                break
                break

        return script_type, script_name

    # ------------------------------------------------------------------------
    # Component Parsing
    # ------------------------------------------------------------------------

    def parse_inputs(self) -> List[InputNode]:
        """
        Extract input.* declarations

        Looks for patterns like:
        - length = input.int(20, "Length", minval=1)
        - useSMA = input.bool(true, "Use SMA")
        """
        inputs = []

        # Pattern: identifier = input.type(...)
        i = 0
        while i < len(self.tokens):
            token = self.tokens[i]

            # Look for "input." pattern
            if (token.value == "input" and
                i + 2 < len(self.tokens) and
                self.tokens[i + 1].type == TokenType.DOT):

                input_type = self.tokens[i + 2].value  # int, float, bool, string

                # Find variable name (before the =)
                var_name = "unknown"
                for j in range(i - 1, max(0, i - 5), -1):
                    if self.tokens[j].type == TokenType.IDENTIFIER:
                        var_name = self.tokens[j].value
                        break

                # Extract parameters
                default_value, title, min_val, max_val = self._extract_input_params(i + 2)

                inputs.append(InputNode(
                    input_type=input_type,
                    name=var_name,
                    default_value=default_value,
                    title=title,
                    min_value=min_val,
                    max_value=max_val,
                    line=token.line,
                    column=token.column
                ))

            i += 1

        return inputs

    def _extract_input_params(self, start_idx: int) -> Tuple[Any, str, Optional[float], Optional[float]]:
        """Extract parameters from input function call"""
        default_value = None
        title = ""
        min_val = None
        max_val = None

        # Find the opening parenthesis
        i = start_idx
        while i < len(self.tokens) and self.tokens[i].type != TokenType.LPAREN:
            i += 1

        if i >= len(self.tokens):
            return default_value, title, min_val, max_val

        # Collect tokens until closing parenthesis
        i += 1
        paren_depth = 1
        param_tokens = []

        while i < len(self.tokens) and paren_depth > 0:
            if self.tokens[i].type == TokenType.LPAREN:
                paren_depth += 1
            elif self.tokens[i].type == TokenType.RPAREN:
                paren_depth -= 1
                if paren_depth == 0:
                    break
            param_tokens.append(self.tokens[i])
            i += 1

        # Parse parameters
        if param_tokens:
            # First parameter is usually default value
            if param_tokens[0].type in (TokenType.NUMBER, TokenType.BOOLEAN):
                default_value = param_tokens[0].value

            # Look for title (usually second parameter or "title=...")
            for j, tok in enumerate(param_tokens):
                if tok.type == TokenType.STRING:
                    title = tok.value.strip('"\'')
                    break
                elif tok.value == "title" and j + 2 < len(param_tokens):
                    if param_tokens[j + 2].type == TokenType.STRING:
                        title = param_tokens[j + 2].value.strip('"\'')

            # Look for minval and maxval
            for j, tok in enumerate(param_tokens):
                if tok.value == "minval" and j + 2 < len(param_tokens):
                    try:
                        min_val = float(param_tokens[j + 2].value)
                    except (ValueError, AttributeError):
                        pass
                elif tok.value == "maxval" and j + 2 < len(param_tokens):
                    try:
                        max_val = float(param_tokens[j + 2].value)
                    except (ValueError, AttributeError):
                        pass

        return default_value, title, min_val, max_val

    def parse_variables(self) -> List[VariableNode]:
        """
        Extract var/varip declarations and regular assignments

        Looks for patterns like:
        - var float sum = 0.0
        - varip int count = 0
        - fast = ta.ema(close, 9)
        """
        variables = []

        i = 0
        while i < len(self.tokens):
            token = self.tokens[i]

            # Check for 'var' or 'varip'
            modifier = ""
            var_type = None

            if token.value in ('var', 'varip'):
                modifier = token.value
                i += 1

                # Check for type annotation
                if i < len(self.tokens) and self.tokens[i].value in ('int', 'float', 'bool', 'string', 'color'):
                    var_type = self.tokens[i].value
                    i += 1

            # Look for identifier = expression
            if i < len(self.tokens) and self.tokens[i].type == TokenType.IDENTIFIER:
                var_name = self.tokens[i].value

                # Check if next is assignment operator
                if i + 1 < len(self.tokens) and self.tokens[i + 1].value in ('=', ':='):
                    # Extract the expression (until newline or comment)
                    expr_tokens = []
                    j = i + 2
                    while j < len(self.tokens):
                        if self.tokens[j].type in (TokenType.NEWLINE, TokenType.COMMENT, TokenType.EOF):
                            break
                        expr_tokens.append(self.tokens[j].value)
                        j += 1

                    value_expr = ''.join(expr_tokens).strip()

                    if value_expr and not var_name.startswith('_'):  # Skip internal vars
                        variables.append(VariableNode(
                            modifier=modifier,
                            name=var_name,
                            value_expr=value_expr,
                            var_type=var_type,
                            line=token.line,
                            column=token.column
                        ))

                    i = j
                    continue

            i += 1

        return variables

    def parse_functions(self) -> List[FunctionNode]:
        """
        Extract user-defined functions

        Looks for patterns like:
        - myFunction(param1, param2) =>
        - method myMethod(this Type, param) => ...
        """
        functions = []

        i = 0
        while i < len(self.tokens):
            token = self.tokens[i]

            # Look for function definition: identifier(...) =>
            if token.type == TokenType.IDENTIFIER:
                # Check if followed by (
                if i + 1 < len(self.tokens) and self.tokens[i + 1].type == TokenType.LPAREN:
                    # Find matching )
                    paren_depth = 0
                    j = i + 1
                    param_start = j

                    while j < len(self.tokens):
                        if self.tokens[j].type == TokenType.LPAREN:
                            paren_depth += 1
                        elif self.tokens[j].type == TokenType.RPAREN:
                            paren_depth -= 1
                            if paren_depth == 0:
                                break
                        j += 1

                    # Check if followed by =>
                    if j + 1 < len(self.tokens) and self.tokens[j + 1].value == '=>':
                        func_name = token.value

                        # Extract parameters
                        params = self._extract_function_params(param_start, j)

                        # Extract function body (until next function or end)
                        body_tokens = []
                        k = j + 2
                        while k < len(self.tokens):
                            # Stop at next function definition or end
                            if (self.tokens[k].type == TokenType.IDENTIFIER and
                                k + 1 < len(self.tokens) and
                                self.tokens[k + 1].type == TokenType.LPAREN):
                                break
                            body_tokens.append(self.tokens[k].value)
                            k += 1

                        body = ''.join(body_tokens).strip()

                        functions.append(FunctionNode(
                            name=func_name,
                            parameters=params,
                            return_type=None,
                            body=body,
                            line=token.line,
                            column=token.column
                        ))

                        i = k
                        continue

            i += 1

        return functions

    def _extract_function_params(self, start_idx: int, end_idx: int) -> List[Tuple[str, Optional[str]]]:
        """Extract function parameters from token range"""
        params = []

        # Simple extraction: look for identifiers separated by commas
        current_param = None
        current_type = None

        for i in range(start_idx, end_idx + 1):
            token = self.tokens[i]

            if token.type == TokenType.IDENTIFIER:
                if current_param is None:
                    current_param = token.value
                else:
                    # This might be a type
                    current_type = token.value
            elif token.type == TokenType.COMMA:
                if current_param:
                    params.append((current_param, current_type))
                current_param = None
                current_type = None

        # Add last parameter
        if current_param:
            params.append((current_param, current_type))

        return params

    def parse_strategy_calls(self) -> List[StrategyCallNode]:
        """
        Extract strategy.entry/close/exit calls

        Looks for patterns like:
        - strategy.entry("Long", strategy.long, when=crossover)
        - strategy.close("Long", when=crossunder)
        """
        calls = []

        i = 0
        while i < len(self.tokens):
            token = self.tokens[i]

            # Look for "strategy."
            if (token.value == "strategy" and
                i + 2 < len(self.tokens) and
                self.tokens[i + 1].type == TokenType.DOT):

                call_type = self.tokens[i + 2].value  # entry, close, exit

                if call_type in ('entry', 'close', 'exit'):
                    # Extract parameters
                    id_val, direction, qty, limit, stop, when = self._extract_strategy_params(i + 2)

                    calls.append(StrategyCallNode(
                        call_type=call_type,
                        id_value=id_val,
                        direction=direction,
                        qty=qty,
                        limit=limit,
                        stop=stop,
                        when=when,
                        line=token.line,
                        column=token.column
                    ))

            i += 1

        return calls

    def _extract_strategy_params(self, start_idx: int) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Extract parameters from strategy call"""
        id_val = ""
        direction = None
        qty = None
        limit = None
        stop = None
        when = None

        # Find opening parenthesis
        i = start_idx
        while i < len(self.tokens) and self.tokens[i].type != TokenType.LPAREN:
            i += 1

        if i >= len(self.tokens):
            return id_val, direction, qty, limit, stop, when

        # Collect parameter tokens
        i += 1
        paren_depth = 1
        param_tokens = []

        while i < len(self.tokens) and paren_depth > 0:
            if self.tokens[i].type == TokenType.LPAREN:
                paren_depth += 1
            elif self.tokens[i].type == TokenType.RPAREN:
                paren_depth -= 1
                if paren_depth == 0:
                    break
            param_tokens.append(self.tokens[i])
            i += 1

        # Parse parameters
        if param_tokens:
            # First parameter is usually the ID
            if param_tokens[0].type == TokenType.STRING:
                id_val = param_tokens[0].value.strip('"\'')

            # Look for named parameters
            for j, tok in enumerate(param_tokens):
                if tok.value == "when" and j + 2 < len(param_tokens):
                    # Extract condition expression
                    when_tokens = []
                    k = j + 2
                    while k < len(param_tokens) and param_tokens[k].type != TokenType.COMMA:
                        when_tokens.append(param_tokens[k].value)
                        k += 1
                    when = ''.join(when_tokens).strip()

                elif tok.value in ('strategy.long', 'strategy.short'):
                    direction = tok.value.split('.')[1]

                elif tok.value == "qty" and j + 2 < len(param_tokens):
                    qty = param_tokens[j + 2].value

        return id_val, direction, qty, limit, stop, when

    def parse_plots(self) -> List[PlotNode]:
        """
        Extract plot/plotshape/plotchar calls
        """
        plots = []

        i = 0
        while i < len(self.tokens):
            token = self.tokens[i]

            if token.value in ('plot', 'plotshape', 'plotchar'):
                plot_type = token.value

                # Extract plot parameters
                series, title, color_val = self._extract_plot_params(i)

                plots.append(PlotNode(
                    plot_type=plot_type,
                    series=series,
                    title=title,
                    color=color_val,
                    line=token.line,
                    column=token.column
                ))

            i += 1

        return plots

    def _extract_plot_params(self, start_idx: int) -> Tuple[str, str, str]:
        """Extract parameters from plot call"""
        series = ""
        title = ""
        color_val = ""

        # Find opening parenthesis
        i = start_idx
        while i < len(self.tokens) and self.tokens[i].type != TokenType.LPAREN:
            i += 1

        if i >= len(self.tokens):
            return series, title, color_val

        # First parameter is the series
        i += 1
        series_tokens = []
        while i < len(self.tokens) and self.tokens[i].type not in (TokenType.COMMA, TokenType.RPAREN):
            series_tokens.append(self.tokens[i].value)
            i += 1

        series = ''.join(series_tokens).strip()

        return series, title, color_val

    def parse_conditions(self) -> List[ConditionNode]:
        """Extract if/else conditions"""
        conditions = []

        i = 0
        while i < len(self.tokens):
            token = self.tokens[i]

            if token.value == "if":
                # Extract condition expression
                cond_tokens = []
                j = i + 1
                while j < len(self.tokens) and self.tokens[j].type not in (TokenType.NEWLINE, TokenType.INDENT):
                    cond_tokens.append(self.tokens[j].value)
                    j += 1

                condition = ''.join(cond_tokens).strip()

                conditions.append(ConditionNode(
                    condition=condition,
                    true_branch=[],
                    false_branch=[],
                    line=token.line,
                    column=token.column
                ))

                i = j
                continue

            i += 1

        return conditions

    # ------------------------------------------------------------------------
    # Indicator Detection
    # ------------------------------------------------------------------------

    def _extract_indicators(self) -> List[str]:
        """Extract all ta.* indicator calls"""
        indicators = set()

        i = 0
        while i < len(self.tokens):
            token = self.tokens[i]

            # Look for "ta." pattern
            if (token.value == "ta" and
                i + 2 < len(self.tokens) and
                self.tokens[i + 1].type == TokenType.DOT):

                indicator_name = f"ta.{self.tokens[i + 2].value}"
                indicators.add(indicator_name)

            i += 1

        return sorted(list(indicators))

    # ------------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------------

    def _count_code_lines(self) -> int:
        """Count non-empty, non-comment lines"""
        lines = self.raw_code.split('\n')
        code_lines = 0

        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('//'):
                code_lines += 1

        return code_lines

    # ------------------------------------------------------------------------
    # Complexity Calculation
    # ------------------------------------------------------------------------

    def calculate_complexity(self, ast: PineAST) -> Tuple[float, Dict[str, float]]:
        """
        Calculate complexity score (0.0-1.0)

        Factors:
        - Line count (weight: 0.25)
        - Custom function count (weight: 0.20)
        - Custom type definitions (weight: 0.15)
        - Array/matrix operations (weight: 0.10)
        - Drawing functions (weight: 0.05)
        - Nested conditionals depth (weight: 0.10)
        - Indicator usage count (weight: 0.10)
        - Variable count (weight: 0.05)

        Returns:
            (score, factors_dict)
        """
        factors = {}

        # 1. Line count factor (0-1, normalized)
        # Simple: <50 lines = 0-0.3, Medium: 50-150 = 0.3-0.7, Complex: 150+ = 0.7-1.0
        line_score = min(ast.code_lines / 150.0, 1.0)
        factors['lines'] = line_score

        # 2. Custom functions
        # 0 functions = 0, 3+ functions = 1.0
        func_score = min(len(ast.functions) / 3.0, 1.0)
        factors['functions'] = func_score

        # 3. Custom types (check for 'type' keyword in code)
        type_count = self.raw_code.count('type ')
        type_score = min(type_count / 2.0, 1.0)
        factors['custom_types'] = type_score

        # 4. Array/Matrix operations
        array_count = self.raw_code.count('array.') + self.raw_code.count('matrix.')
        array_score = min(array_count / 8.0, 1.0)
        factors['array_matrix'] = array_score

        # 5. Drawing functions
        drawing_count = (self.raw_code.count('line.') +
                        self.raw_code.count('label.') +
                        self.raw_code.count('box.'))
        drawing_score = min(drawing_count / 3.0, 1.0)
        factors['drawing'] = drawing_score

        # 6. Nested conditionals
        # Count depth of if statements
        max_depth = self._calculate_condition_depth()
        depth_score = min(max_depth / 3.0, 1.0)
        factors['nesting'] = depth_score

        # 7. Indicator usage
        indicator_score = min(len(ast.indicators_used) / 8.0, 1.0)
        factors['indicators'] = indicator_score

        # 8. Variable count (more variables = more complexity)
        var_score = min(len(ast.variables) / 20.0, 1.0)
        factors['variables'] = var_score

        # Weighted sum
        weights = {
            'lines': 0.25,
            'functions': 0.20,
            'custom_types': 0.15,
            'array_matrix': 0.10,
            'drawing': 0.05,
            'nesting': 0.10,
            'indicators': 0.10,
            'variables': 0.05
        }

        total_score = sum(factors[key] * weights[key] for key in factors)

        return total_score, factors

    def _calculate_condition_depth(self) -> int:
        """Calculate maximum nesting depth of conditionals"""
        max_depth = 0
        current_depth = 0

        for token in self.tokens:
            if token.value == 'if':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif token.type == TokenType.DEDENT:
                current_depth = max(0, current_depth - 1)

        return max_depth


# ============================================================================
# Utility Functions
# ============================================================================

def parse_pine_script(pine_code: str) -> PineAST:
    """
    Convenience function to tokenize and parse Pine Script in one step

    Args:
        pine_code: Pine Script source code as string

    Returns:
        PineAST object

    Example:
        ast = parse_pine_script(pine_code)
        print(f"Complexity: {ast.complexity_score:.2f}")
    """
    lexer = PineLexer()
    tokens = lexer.tokenize(pine_code)

    parser = PineParser(tokens, raw_code=pine_code)
    ast = parser.parse()

    return ast


def print_ast_summary(ast: PineAST):
    """Print a human-readable summary of the AST"""
    print("=" * 70)
    print(f"Pine Script AST Summary: {ast.script_name}")
    print("=" * 70)
    print(f"Version:      v{ast.version}")
    print(f"Type:         {ast.script_type}")
    print(f"Total Lines:  {ast.total_lines}")
    print(f"Code Lines:   {ast.code_lines}")
    print()
    print(f"Complexity:   {ast.complexity_score:.3f} ", end="")

    if ast.complexity_score < 0.3:
        print("(LOW - Use rule-based conversion)")
    elif ast.complexity_score < 0.7:
        print("(MEDIUM - Hybrid approach)")
    else:
        print("(HIGH - Use LLM conversion)")

    print()
    print("Complexity Factors:")
    for factor, value in ast.complexity_factors.items():
        bar = "█" * int(value * 20)
        print(f"  {factor:15s}: {value:.2f} {bar}")

    print()
    print(f"Inputs:           {len(ast.inputs)}")
    for inp in ast.inputs:
        print(f"  - {inp.name} ({inp.input_type}): {inp.default_value}")

    print(f"\nVariables:        {len(ast.variables)}")
    for var in ast.variables[:5]:  # Show first 5
        print(f"  - {var.name} = {var.value_expr[:40]}...")

    print(f"\nFunctions:        {len(ast.functions)}")
    for func in ast.functions:
        print(f"  - {func.name}({len(func.parameters)} params)")

    print(f"\nStrategy Calls:   {len(ast.strategy_calls)}")
    for call in ast.strategy_calls:
        print(f"  - {call.call_type}('{call.id_value}')")

    print(f"\nPlots:            {len(ast.plots)}")
    for plot in ast.plots[:3]:
        print(f"  - {plot.plot_type}({plot.series[:30]}...)")

    print(f"\nIndicators Used:  {len(ast.indicators_used)}")
    print(f"  {', '.join(ast.indicators_used[:10])}")

    print("=" * 70)
