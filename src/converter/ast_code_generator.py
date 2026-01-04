"""
AST Code Generator - Main Python Code Generation Module

Orchestrates the transformation of Pine Script AST to complete Python strategy code.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime
import logging
import re

from .pine_parser import PineAST
from .node_translator import NodeTranslator
from .template_manager import TemplateManager
from .import_manager import ImportManager
from .code_formatter import CodeFormatter
from .transformation_context import TransformationContext

logger = logging.getLogger(__name__)


@dataclass
class GeneratedCode:
    """
    Result of code generation.

    Attributes:
        full_code: Complete Python code
        class_name: Generated class name
        imports: Import statements
        parameters: Strategy parameters
        indicators_used: List of indicators used
        warnings: Non-fatal issues
        errors: Fatal errors
    """
    full_code: str
    class_name: str
    imports: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    indicators_used: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ASTCodeGenerator:
    """
    Generate complete Python strategy code from Pine Script AST.

    Main orchestrator for AST → Python code pipeline. Coordinates node translation,
    template rendering, import management, and code formatting.

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
        >>> generator = ASTCodeGenerator()
        >>> result = generator.generate(ast)
        >>> 'class SimpleMAStrategy' in result.full_code
        True
    """

    def __init__(self):
        """Initialize code generator."""
        self.translator = NodeTranslator()
        self.template_manager = TemplateManager()
        self.import_manager = ImportManager()
        self.formatter = CodeFormatter()

    def generate(self, ast: PineAST) -> GeneratedCode:
        """
        Generate complete Python strategy code from AST.

        Args:
            ast: Pine Script AST from PineParser

        Returns:
            GeneratedCode with complete Python code

        Example:
            >>> generator = ASTCodeGenerator()
            >>> # Assume ast is from parse_pine_script()
            >>> result = generator.generate(ast)
            >>> result.class_name
            'MyStrategy'
        """
        logger.info(f"Generating Python code for: {ast.script_name}")

        # Reset state
        self.import_manager = ImportManager()
        self.translator.reset_context()

        try:
            # 1. Process AST nodes
            inputs_data = self._process_inputs(ast.inputs)
            variables_data = self._process_variables(ast.variables)
            conditions_data = self._process_conditions(ast.conditions)
            strategy_calls_data = self._process_strategy_calls(ast.strategy_calls)
            state_vars_data = self._extract_state_variables(ast.variables)

            # 2. Build template context
            context = self._build_template_context(
                ast=ast,
                inputs=inputs_data,
                variables=variables_data,
                conditions=conditions_data,
                strategy_calls=strategy_calls_data,
                state_variables=state_vars_data
            )

            # 3. Generate imports
            imports_code = self.import_manager.generate_import_block()

            # 4. Render template
            context['imports'] = imports_code
            python_code = self.template_manager.render_strategy(context)

            # 5. Format and validate
            python_code = self.formatter.format_code(python_code)
            validation = self.formatter.validate_syntax(python_code)

            if not validation.is_valid:
                logger.error(f"Generated code has syntax error: {validation.error_message}")
                # Try to fix common issues
                python_code = self._attempt_syntax_fix(python_code)

            # 6. Build result
            result = GeneratedCode(
                full_code=python_code,
                class_name=context['class_name'],
                imports=imports_code,
                parameters={inp['name']: inp['default_value'] for inp in inputs_data},
                indicators_used=list(self.translator.get_context().indicators_used)
            )

            logger.info(f"Successfully generated {len(python_code)} characters of Python code")
            return result

        except Exception as e:
            logger.error(f"Code generation failed: {e}", exc_info=True)
            # Return error result
            return GeneratedCode(
                full_code=f"# ERROR: Code generation failed\n# {e}",
                class_name="ErrorStrategy",
                imports="",
                errors=[str(e)]
            )

    def _process_inputs(self, inputs: list) -> List[Dict[str, Any]]:
        """Process InputNodes into template data."""
        return [
            {
                'name': inp.name,
                'type': inp.input_type,
                'default_value': inp.default_value,
                'title': inp.title,
                'min_value': inp.min_value,
                'max_value': inp.max_value
            }
            for inp in inputs
        ]

    def _process_variables(self, variables: list) -> List[Dict[str, Any]]:
        """Process VariableNodes into template data."""
        context = self.translator.get_context()
        variables_data = []

        for var in variables:
            # Skip state variables (var/varip) - handled separately
            if var.modifier in ['var', 'varip']:
                continue

            # Translate variable to Python code
            code = self.translator.translate_variable(var, context)

            variables_data.append({
                'name': var.name,
                'code': code,
                'modifier': var.modifier
            })

        return variables_data

    def _process_conditions(self, conditions: list) -> List[Dict[str, Any]]:
        """Process ConditionNodes into template data."""
        context = self.translator.get_context()
        conditions_data = []

        for cond in conditions:
            lines = self.translator.translate_condition(cond, context)
            code = '\n'.join(lines)

            conditions_data.append({
                'condition': cond.condition,
                'code': code
            })

        return conditions_data

    def _process_strategy_calls(self, strategy_calls: list) -> List[Dict[str, Any]]:
        """Process StrategyCallNodes into template data."""
        context = self.translator.get_context()
        calls_data = []

        for call in strategy_calls:
            call_info = self.translator.translate_strategy_call(call, context)
            calls_data.append(call_info)

        return calls_data

    def _extract_state_variables(self, variables: list) -> List[Dict[str, Any]]:
        """Extract state variables (var/varip) for initialization."""
        state_vars = []

        for var in variables:
            if var.modifier in ['var', 'varip']:
                # Try to determine initial value
                initial_value = var.value_expr if var.value_expr else '0'

                # Simple literals
                try:
                    # Check if it's a simple literal
                    if var.value_expr.replace('.', '').replace('-', '').isdigit():
                        initial_value = var.value_expr
                    elif var.value_expr in ['true', 'false']:
                        initial_value = var.value_expr.capitalize()
                    elif var.value_expr == 'na':
                        initial_value = 'None'
                    else:
                        # Complex expression - use default
                        initial_value = '0'
                except:
                    initial_value = '0'

                state_vars.append({
                    'name': var.name,
                    'initial_value': initial_value,
                    'type': var.var_type or 'float',
                    'comment': f"State variable ({var.modifier})"
                })

        return state_vars

    def _build_template_context(
        self,
        ast: PineAST,
        inputs: list,
        variables: list,
        conditions: list,
        strategy_calls: list,
        state_variables: list
    ) -> Dict[str, Any]:
        """Build complete template context."""
        # Generate class name from script name
        class_name = self._generate_class_name(ast.script_name)

        # Add indicators to import manager
        for indicator in ast.indicators_used:
            self.import_manager.add_indicator(indicator)

        # Build entry logic from strategy calls
        entry_logic = []
        for call in strategy_calls:
            if call['type'] == 'entry':
                condition = call['condition']
                direction = call.get('direction', 'long')
                action = 'buy' if direction == 'long' else 'sell'

                code = f"""if {condition}:
    return self._{action}_signal("{call['id']}", confidence=0.75)"""

                entry_logic.append({
                    'comment': f"{call['id']} entry",
                    'code': code
                })

        # Build exit logic
        exit_logic = []
        for call in strategy_calls:
            if call['type'] in ['close', 'exit']:
                condition = call['condition']
                code = f"""if {condition}:
    return {{'action': 'close', 'confidence': 0.8, 'reason': '{call['id']}'}}"""

                exit_logic.append({
                    'comment': f"{call['id']} exit",
                    'code': code
                })

        # Metadata
        metadata = {
            'strategy_name': ast.script_name,
            'pine_version': ast.version,
            'script_type': ast.script_type,
            'complexity_score': f"{ast.complexity_score:.3f}",
            'indicators_used': ast.indicators_used,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Pine code comment
        pine_code_comment = f'''"""
Original Pine Script Strategy
Generated from Pine Script v{ast.version}

Note: This is an automated conversion. Review carefully before use.
"""'''

        return {
            'class_name': class_name,
            'strategy_code': self._slugify(ast.script_name),
            'metadata': metadata,
            'pine_code_comment': pine_code_comment,
            'inputs': inputs,
            'calculated_variables': variables,
            'state_variables': state_variables,
            'entry_logic': entry_logic,
            'exit_logic': exit_logic,
            'custom_functions': [],  # TODO: Process FunctionNodes
            'min_candles': self._estimate_min_candles(ast)
        }

    def _generate_class_name(self, script_name: str) -> str:
        """Generate valid Python class name from script name."""
        # Remove special characters
        name = re.sub(r'[^\w\s]', '', script_name)
        # Convert to PascalCase
        name = ''.join(word.capitalize() for word in name.split())
        # Ensure it doesn't start with a number
        if name and name[0].isdigit():
            name = 'Strategy' + name
        # Ensure it's not empty
        if not name:
            name = 'GeneratedStrategy'

        return name

    def _slugify(self, text: str) -> str:
        """Convert text to slug (lowercase with underscores)."""
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '_', slug)
        return slug

    def _estimate_min_candles(self, ast: PineAST) -> int:
        """Estimate minimum candles needed based on indicators used."""
        min_candles = 50  # Default

        # Check for common indicators and their periods
        for indicator in ast.indicators_used:
            if 'sma' in indicator or 'ema' in indicator:
                min_candles = max(min_candles, 100)
            elif 'rsi' in indicator:
                min_candles = max(min_candles, 50)
            elif 'macd' in indicator:
                min_candles = max(min_candles, 100)
            elif 'bb' in indicator or 'bollinger' in indicator:
                min_candles = max(min_candles, 100)

        return min_candles

    def _attempt_syntax_fix(self, code: str) -> str:
        """Attempt to fix common syntax errors."""
        # Basic fixes
        # Remove multiple consecutive blank lines
        code = self.formatter.remove_duplicate_blank_lines(code)

        # Ensure proper indentation
        code = self.formatter._fix_indentation(code)

        return code
