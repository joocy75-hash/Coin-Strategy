# Converter Module
# Pine Script to Python conversion and strategy generation

# Phase 1: Lexer and Indicator Mapping
from .pine_to_python import PineScriptConverter
from .strategy_generator import StrategyGenerator
from .pine_lexer import PineLexer, Token, TokenType, tokenize_pine_script
from .indicator_mapper import IndicatorMapper, IndicatorMapping

# Phase 2: Parser and AST
from .pine_parser import (
    PineParser,
    PineAST,
    InputNode,
    VariableNode,
    FunctionNode,
    StrategyCallNode,
    PlotNode,
    ConditionNode,
    ExpressionNode,
    parse_pine_script,
    print_ast_summary,
)

# Phase 3: Expression Transformation and Code Generation
from .transformation_context import TransformationContext
from .expression_parser import ExpressionParser, ExprNode, ExprNodeType, ParseError
from .python_code_builder import PythonCodeBuilder
from .expression_transformer import (
    ExpressionTransformer,
    TransformationResult,
    transform_pine_expression,
)
from .import_manager import ImportManager, ImportStatement
from .code_formatter import CodeFormatter, ValidationResult as FormatValidationResult
from .node_translator import NodeTranslator
from .template_manager import TemplateManager
from .ast_code_generator import ASTCodeGenerator, GeneratedCode
from .complexity_validator import (
    ComplexityValidator,
    ValidationResult as ComplexityValidationResult,
)
from .rule_based_converter import (
    RuleBasedConverter,
    ConversionError,
    ComplexityError,
    UnsupportedFeatureError,
    convert_pine_to_python,
)

# Phase 4: LLM-Based Conversion
from .llm import (
    # Core LLM Converter
    LLMConverter,
    LLMConversionError,
    LLMAPIError,
    # Prompt & Response
    LLMPromptBuilder,
    LLMResponseParser,
    LLMValidator,
    # Strategy & Hybrid
    ConversionStrategy,
    StrategySelector,
    HybridConverter,
    # Unified Interface
    UnifiedConverter,
    UnifiedConversionResult,
    # Utilities
    ConversionCache,
    CostOptimizer,
)

__all__ = [
    # Phase 1
    "PineScriptConverter",
    "StrategyGenerator",
    "PineLexer",
    "Token",
    "TokenType",
    "tokenize_pine_script",
    "IndicatorMapper",
    "IndicatorMapping",
    # Phase 2
    "PineParser",
    "PineAST",
    "InputNode",
    "VariableNode",
    "FunctionNode",
    "StrategyCallNode",
    "PlotNode",
    "ConditionNode",
    "ExpressionNode",
    "parse_pine_script",
    "print_ast_summary",
    # Phase 3: Expression Transformation
    "TransformationContext",
    "ExpressionParser",
    "ExprNode",
    "ExprNodeType",
    "ParseError",
    "PythonCodeBuilder",
    "ExpressionTransformer",
    "TransformationResult",
    "transform_pine_expression",
    # Phase 3: Code Generation
    "ImportManager",
    "ImportStatement",
    "CodeFormatter",
    "FormatValidationResult",
    "NodeTranslator",
    "TemplateManager",
    "ASTCodeGenerator",
    "GeneratedCode",
    # Phase 3: Rule-Based Conversion
    "ComplexityValidator",
    "ComplexityValidationResult",
    "RuleBasedConverter",
    "ConversionError",
    "ComplexityError",
    "UnsupportedFeatureError",
    "convert_pine_to_python",
    # Phase 4: LLM-Based Conversion
    "LLMConverter",
    "LLMConversionError",
    "LLMAPIError",
    "LLMPromptBuilder",
    "LLMResponseParser",
    "LLMValidator",
    "ConversionStrategy",
    "StrategySelector",
    "HybridConverter",
    "UnifiedConverter",
    "UnifiedConversionResult",
    "ConversionCache",
    "CostOptimizer",
]
