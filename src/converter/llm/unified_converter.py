"""
Unified Converter - Main Facade

Single entry point for all Pine Script conversions.
Automatically selects optimal strategy and manages the entire pipeline.
"""

import logging
from typing import Optional
from dataclasses import dataclass
import asyncio

from ..pine_parser import PineAST, parse_pine_script
from ..ast_code_generator import GeneratedCode
from .conversion_strategy import ConversionStrategy, StrategySelector
from .hybrid_converter import HybridConverter
from .llm_converter import LLMConverter
from ..rule_based_converter import RuleBasedConverter

logger = logging.getLogger(__name__)


# ============================================================================
# Unified Result
# ============================================================================

@dataclass
class UnifiedConversionResult:
    """Complete conversion result with full metadata"""
    # Core output
    generated_code: GeneratedCode
    python_code: str  # Convenience accessor

    # Strategy info
    strategy_used: str
    complexity_score: float

    # Cost/Performance
    cost_usd: float
    time_seconds: float
    tokens_used: int = 0

    # Quality metrics
    validation_passed: bool = True
    warnings: list = None
    errors: list = None

    # Metadata
    ast: Optional[PineAST] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []

        # Set convenience accessor
        if self.generated_code:
            self.python_code = self.generated_code.full_code


# ============================================================================
# Unified Converter
# ============================================================================

class UnifiedConverter:
    """
    Unified Pine Script to Python converter.

    Main entry point for all conversions. Automatically:
    - Selects optimal conversion strategy
    - Manages rule-based, hybrid, and LLM conversions
    - Handles caching and cost optimization
    - Provides detailed results and metadata

    Usage (Simple):
        >>> converter = UnifiedConverter(api_key="sk-ant-...")
        >>> result = await converter.convert_from_code(pine_script)
        >>> print(result.python_code)

    Usage (Advanced):
        >>> result = await converter.convert(
        ...     ast=my_ast,
        ...     force_strategy=ConversionStrategy.LLM_ONLY,
        ...     enable_cache=True
        ... )
        >>> print(f"Used {result.strategy_used} (${result.cost_usd:.4f})")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_strategy: Optional[ConversionStrategy] = None,
        enable_cache: bool = True,
        verify_rule_based: bool = False,
    ):
        """
        Initialize unified converter.

        Args:
            api_key: Anthropic API key (for LLM conversion)
            default_strategy: Force specific strategy (None = auto-select)
            enable_cache: Enable conversion caching
            verify_rule_based: Verify rule-based results with LLM
        """
        self.api_key = api_key
        self.default_strategy = default_strategy
        self.enable_cache = enable_cache

        # Initialize components
        self.strategy_selector = StrategySelector()
        self.rule_converter = RuleBasedConverter()
        self.hybrid_converter = HybridConverter(
            api_key=api_key,
            verify_rule_based=verify_rule_based
        )
        self.llm_converter = LLMConverter(api_key=api_key) if api_key else None

        # Cache (lazy-loaded)
        self._cache = None

        logger.info(
            f"Initialized UnifiedConverter "
            f"(cache={enable_cache}, verify={verify_rule_based})"
        )

    async def convert(
        self,
        ast: PineAST,
        force_strategy: Optional[ConversionStrategy] = None,
        enable_cache: Optional[bool] = None,
    ) -> UnifiedConversionResult:
        """
        Convert Pine Script AST to Python.

        Args:
            ast: Parsed Pine Script AST
            force_strategy: Override automatic strategy selection
            enable_cache: Override global cache setting

        Returns:
            UnifiedConversionResult with complete metadata

        Example:
            >>> result = await converter.convert(ast)
            >>> print(result.strategy_used)
            hybrid
        """
        logger.info(f"Converting '{ast.script_name}' (complexity: {ast.complexity_score:.3f})")

        use_cache = enable_cache if enable_cache is not None else self.enable_cache

        # Step 1: Check cache
        if use_cache:
            cached = await self._get_cached(ast)
            if cached:
                logger.info("Cache hit! Returning cached result")
                return cached

        # Step 2: Select strategy
        strategy = force_strategy or self.default_strategy or \
                   self.strategy_selector.select_strategy(ast)

        logger.debug(f"Using strategy: {strategy.value}")

        # Step 3: Convert based on strategy
        if strategy == ConversionStrategy.RULE_BASED:
            result = await self._convert_rule_based(ast)

        elif strategy == ConversionStrategy.HYBRID:
            result = await self._convert_hybrid(ast)

        else:  # LLM_ONLY
            result = await self._convert_llm_only(ast)

        # Step 4: Cache result
        if use_cache:
            await self._cache_result(ast, result)

        logger.info(
            f"Conversion complete: {result.strategy_used} "
            f"(${result.cost_usd:.4f}, {result.time_seconds:.1f}s)"
        )

        return result

    async def convert_from_code(
        self,
        pine_code: str,
        **kwargs
    ) -> UnifiedConversionResult:
        """
        Convert Pine Script source code to Python.

        Convenience method that handles parsing.

        Args:
            pine_code: Pine Script source code
            **kwargs: Passed to convert()

        Returns:
            UnifiedConversionResult

        Example:
            >>> result = await converter.convert_from_code('''
            ... //@version=5
            ... strategy("MA", overlay=true)
            ... sma20 = ta.sma(close, 20)
            ... if close > sma20
            ...     strategy.entry("Long", strategy.long)
            ... ''')
        """
        logger.debug("Parsing Pine Script code")

        # Parse to AST
        ast = parse_pine_script(pine_code)

        # Convert
        return await self.convert(ast, **kwargs)

    def estimate_cost(
        self,
        ast: PineAST,
        strategy: Optional[ConversionStrategy] = None,
    ) -> float:
        """
        Estimate conversion cost without actually converting.

        Args:
            ast: Pine Script AST
            strategy: Specific strategy (None = auto-select)

        Returns:
            Estimated cost in USD

        Example:
            >>> cost = converter.estimate_cost(ast)
            >>> print(f"Estimated cost: ${cost:.4f}")
            Estimated cost: $0.0150
        """
        selected_strategy = strategy or self.strategy_selector.select_strategy(ast)

        if selected_strategy == ConversionStrategy.RULE_BASED:
            return 0.0  # Free

        elif selected_strategy == ConversionStrategy.HYBRID:
            # May use LLM for fallback or verification
            return 0.01  # Average estimate

        else:  # LLM_ONLY
            if self.llm_converter:
                return self.llm_converter.estimate_cost(ast)
            else:
                return 0.025  # Rough estimate

    # ------------------------------------------------------------------------
    # Private Conversion Methods
    # ------------------------------------------------------------------------

    async def _convert_rule_based(self, ast: PineAST) -> UnifiedConversionResult:
        """Convert using rule-based converter"""
        import time
        start = time.time()

        try:
            python_code = self.rule_converter.convert(ast)

            # Create GeneratedCode
            generated_code = self.hybrid_converter._create_generated_code(
                python_code,
                ast,
                strategy="rule_based"
            )

            return UnifiedConversionResult(
                generated_code=generated_code,
                python_code=python_code,
                strategy_used="rule_based",
                complexity_score=ast.complexity_score,
                cost_usd=0.0,
                time_seconds=time.time() - start,
                validation_passed=True,
                ast=ast,
            )

        except Exception as e:
            logger.error(f"Rule-based conversion failed: {e}")
            # Fall back to hybrid
            return await self._convert_hybrid(ast)

    async def _convert_hybrid(self, ast: PineAST) -> UnifiedConversionResult:
        """Convert using hybrid converter"""
        result = await self.hybrid_converter.convert(ast)

        return UnifiedConversionResult(
            generated_code=result["generated_code"],
            python_code=result["generated_code"].full_code,
            strategy_used=result["strategy_used"],
            complexity_score=ast.complexity_score,
            cost_usd=result["cost_usd"],
            time_seconds=result["time_seconds"],
            validation_passed=len(result["generated_code"].errors) == 0,
            warnings=result["generated_code"].warnings,
            errors=result["generated_code"].errors,
            ast=ast,
        )

    async def _convert_llm_only(self, ast: PineAST) -> UnifiedConversionResult:
        """Convert using LLM only"""
        if not self.llm_converter:
            raise ValueError("LLM converter not initialized (API key required)")

        result = await self.llm_converter.convert(ast)

        return UnifiedConversionResult(
            generated_code=result.generated_code,
            python_code=result.full_code,
            strategy_used="llm_only",
            complexity_score=ast.complexity_score,
            cost_usd=result.cost_usd,
            time_seconds=result.latency_seconds,
            tokens_used=result.tokens_used,
            validation_passed=len(result.generated_code.errors) == 0,
            warnings=result.generated_code.warnings,
            errors=result.generated_code.errors,
            ast=ast,
        )

    # ------------------------------------------------------------------------
    # Caching Methods
    # ------------------------------------------------------------------------

    async def _get_cached(self, ast: PineAST) -> Optional[UnifiedConversionResult]:
        """Get cached conversion result"""
        if not self.enable_cache:
            return None

        # TODO: Implement caching
        # For now, return None (no cache)
        return None

    async def _cache_result(
        self,
        ast: PineAST,
        result: UnifiedConversionResult
    ):
        """Cache conversion result"""
        if not self.enable_cache:
            return

        # TODO: Implement caching
        pass


# ============================================================================
# Convenience Functions
# ============================================================================

async def convert_pine_to_python_async(
    pine_code: str,
    api_key: Optional[str] = None,
) -> str:
    """
    Convert Pine Script to Python (async convenience function).

    Args:
        pine_code: Pine Script source code
        api_key: Anthropic API key (optional)

    Returns:
        Python code as string

    Example:
        >>> python_code = await convert_pine_to_python_async(pine_script)
        >>> print(python_code)
    """
    converter = UnifiedConverter(api_key=api_key)
    result = await converter.convert_from_code(pine_code)
    return result.python_code


def convert_pine_to_python_sync(
    pine_code: str,
    api_key: Optional[str] = None,
) -> str:
    """
    Convert Pine Script to Python (synchronous convenience function).

    Args:
        pine_code: Pine Script source code
        api_key: Anthropic API key (optional)

    Returns:
        Python code as string

    Example:
        >>> python_code = convert_pine_to_python_sync(pine_script)
        >>> print(python_code)
    """
    return asyncio.run(convert_pine_to_python_async(pine_code, api_key))
