"""
Conversion Strategy Selector

Intelligently selects the optimal conversion strategy based on
Pine Script complexity, features, and cost considerations.
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from ..pine_parser import PineAST
from ..complexity_validator import ComplexityValidator

logger = logging.getLogger(__name__)


# ============================================================================
# Strategy Types
# ============================================================================

class ConversionStrategy(Enum):
    """Available conversion strategies"""
    RULE_BASED = "rule_based"      # Pure deterministic rules (complexity < 0.3)
    HYBRID = "hybrid"              # Rules + LLM verification (complexity 0.3-0.7)
    LLM_ONLY = "llm_only"          # Full LLM conversion (complexity > 0.7)


@dataclass
class StrategyRecommendation:
    """Recommendation with reasoning"""
    strategy: ConversionStrategy
    confidence: float  # 0.0-1.0
    reason: str
    estimated_cost_usd: float
    estimated_time_seconds: float


# ============================================================================
# Strategy Selector
# ============================================================================

class StrategySelector:
    """
    Select optimal conversion strategy for Pine Script.

    Decision factors:
    1. Complexity score (primary)
    2. Feature detection (custom functions, arrays, etc.)
    3. Cost considerations
    4. Time constraints
    5. Quality requirements

    Example:
        >>> selector = StrategySelector()
        >>> recommendation = selector.recommend(ast)
        >>> print(recommendation.strategy)
        ConversionStrategy.HYBRID
    """

    # Complexity thresholds
    COMPLEXITY_THRESHOLDS = {
        "rule_based": 0.3,    # Below this: rule-based
        "hybrid": 0.7,        # Between thresholds: hybrid
        # Above 0.7: LLM only
    }

    # Estimated conversion times (seconds)
    TIME_ESTIMATES = {
        ConversionStrategy.RULE_BASED: 1.0,
        ConversionStrategy.HYBRID: 15.0,
        ConversionStrategy.LLM_ONLY: 30.0,
    }

    # Estimated costs (USD)
    COST_ESTIMATES = {
        ConversionStrategy.RULE_BASED: 0.0,      # Free
        ConversionStrategy.HYBRID: 0.005,        # Verification only
        ConversionStrategy.LLM_ONLY: 0.02,       # Full generation
    }

    def __init__(
        self,
        rule_threshold: float = 0.3,
        hybrid_threshold: float = 0.7,
        prefer_cost_efficiency: bool = True,
    ):
        """
        Initialize strategy selector.

        Args:
            rule_threshold: Max complexity for rule-based
            hybrid_threshold: Max complexity for hybrid
            prefer_cost_efficiency: Prefer cheaper strategies when possible
        """
        self.rule_threshold = rule_threshold
        self.hybrid_threshold = hybrid_threshold
        self.prefer_cost_efficiency = prefer_cost_efficiency

        self.complexity_validator = ComplexityValidator()

        logger.debug(
            f"Initialized StrategySelector "
            f"(rule<{rule_threshold}, hybrid<{hybrid_threshold})"
        )

    def select_strategy(
        self,
        ast: PineAST,
        force_strategy: Optional[ConversionStrategy] = None,
    ) -> ConversionStrategy:
        """
        Select conversion strategy for Pine Script AST.

        Args:
            ast: Pine Script AST
            force_strategy: Override automatic selection (for testing)

        Returns:
            Selected ConversionStrategy

        Example:
            >>> strategy = selector.select_strategy(ast)
            >>> strategy == ConversionStrategy.RULE_BASED
            True
        """
        if force_strategy:
            logger.info(f"Strategy forced to: {force_strategy.value}")
            return force_strategy

        recommendation = self.recommend(ast)

        logger.info(
            f"Selected {recommendation.strategy.value} "
            f"(confidence: {recommendation.confidence:.2f}, "
            f"reason: {recommendation.reason})"
        )

        return recommendation.strategy

    def recommend(
        self,
        ast: PineAST,
    ) -> StrategyRecommendation:
        """
        Get detailed recommendation with reasoning.

        Args:
            ast: Pine Script AST

        Returns:
            StrategyRecommendation with full details

        Example:
            >>> rec = selector.recommend(ast)
            >>> print(f"{rec.strategy.value}: {rec.reason}")
            hybrid: Moderate complexity with custom functions
        """
        complexity = ast.complexity_score

        # Primary decision: complexity-based
        if complexity < self.rule_threshold:
            strategy = ConversionStrategy.RULE_BASED
            reason = f"Low complexity ({complexity:.3f})"
            confidence = 0.95

        elif complexity < self.hybrid_threshold:
            strategy = ConversionStrategy.HYBRID
            reason = f"Moderate complexity ({complexity:.3f})"
            confidence = 0.85

        else:
            strategy = ConversionStrategy.LLM_ONLY
            reason = f"High complexity ({complexity:.3f})"
            confidence = 0.90

        # Feature detection modifiers
        if ast.functions and len(ast.functions) > 2:
            if strategy == ConversionStrategy.RULE_BASED:
                # Bump up to hybrid for complex custom functions
                strategy = ConversionStrategy.HYBRID
                reason += ", custom functions detected"
                confidence = 0.80

        if len(ast.indicators_used) > 5:
            if strategy == ConversionStrategy.RULE_BASED:
                # Many indicators may need LLM
                strategy = ConversionStrategy.HYBRID
                reason += ", multiple indicators"
                confidence = 0.75

        # Cost efficiency consideration
        if self.prefer_cost_efficiency and strategy == ConversionStrategy.LLM_ONLY:
            # Try hybrid first if complexity is borderline
            if complexity < self.hybrid_threshold + 0.1:
                strategy = ConversionStrategy.HYBRID
                reason += " (cost optimization)"
                confidence = 0.70

        # Get estimates
        estimated_cost = self.COST_ESTIMATES[strategy]
        estimated_time = self.TIME_ESTIMATES[strategy]

        return StrategyRecommendation(
            strategy=strategy,
            confidence=confidence,
            reason=reason,
            estimated_cost_usd=estimated_cost,
            estimated_time_seconds=estimated_time,
        )

    def can_use_rule_based(self, ast: PineAST) -> bool:
        """
        Check if rule-based conversion is possible.

        Args:
            ast: Pine Script AST

        Returns:
            True if rule-based converter can handle this

        Example:
            >>> selector.can_use_rule_based(simple_ast)
            True
        """
        return ast.complexity_score < self.rule_threshold

    def requires_llm(self, ast: PineAST) -> bool:
        """
        Check if LLM is required (no rule-based option).

        Args:
            ast: Pine Script AST

        Returns:
            True if LLM is required

        Example:
            >>> selector.requires_llm(complex_ast)
            True
        """
        return ast.complexity_score >= self.rule_threshold
