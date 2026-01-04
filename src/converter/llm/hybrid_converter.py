"""
Hybrid Converter: Rule-Based + LLM

Combines fast rule-based conversion with LLM verification and fallback.
Optimizes for both cost and quality.
"""

import logging
from typing import Optional
import asyncio

from ..pine_parser import PineAST
from ..rule_based_converter import RuleBasedConverter, ComplexityError, ConversionError
from ..ast_code_generator import GeneratedCode

logger = logging.getLogger(__name__)


# ============================================================================
# Hybrid Converter
# ============================================================================

class HybridConverter:
    """
    Hybrid Pine Script converter using Rule-Based + LLM strategy.

    Workflow:
    1. Attempt rule-based conversion (fast, free)
    2. If successful: optionally verify with LLM
    3. If failed: fall back to LLM conversion
    4. Return best result with metadata

    Benefits:
    - Cost-effective (only uses LLM when needed)
    - High quality (LLM verification available)
    - Fast for simple strategies
    - Robust fallback for complex strategies

    Example:
        >>> hybrid = HybridConverter(api_key="sk-ant-...")
        >>> result = await hybrid.convert(ast)
        >>> print(f"Used: {result.strategy_used}")
        rule_based_with_verification
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        verify_rule_based: bool = False,
        max_retries: int = 2,
    ):
        """
        Initialize hybrid converter.

        Args:
            api_key: Anthropic API key (for LLM fallback)
            verify_rule_based: Use LLM to verify rule-based results
            max_retries: Max LLM conversion attempts
        """
        self.verify_rule_based = verify_rule_based
        self.max_retries = max_retries

        # Initialize converters
        self.rule_converter = RuleBasedConverter()

        # Lazy-load LLM converter (only if needed)
        self._llm_converter = None
        self._api_key = api_key

        logger.info(
            f"Initialized HybridConverter "
            f"(verify={verify_rule_based}, retries={max_retries})"
        )

    @property
    def llm_converter(self):
        """Lazy-load LLM converter"""
        if self._llm_converter is None:
            from .llm_converter import LLMConverter
            self._llm_converter = LLMConverter(api_key=self._api_key)
        return self._llm_converter

    async def convert(
        self,
        ast: PineAST,
        force_llm: bool = False,
    ) -> dict:
        """
        Convert Pine Script using hybrid strategy.

        Args:
            ast: Pine Script AST
            force_llm: Skip rule-based, go directly to LLM

        Returns:
            Dict with:
                - generated_code: GeneratedCode object
                - strategy_used: 'rule_based', 'llm', or 'hybrid'
                - cost_usd: Total cost
                - time_seconds: Total time
                - rule_based_succeeded: bool
                - llm_used: bool

        Example:
            >>> result = await hybrid.convert(ast)
            >>> result['strategy_used']
            'rule_based'
        """
        logger.info(f"Starting hybrid conversion for '{ast.script_name}'")

        import time
        start_time = time.time()

        total_cost = 0.0
        rule_based_succeeded = False
        llm_used = False
        generated_code = None
        strategy_used = None

        # Step 1: Try rule-based conversion (unless forced to LLM)
        if not force_llm:
            logger.debug("Attempting rule-based conversion")

            try:
                python_code = self.rule_converter.convert(ast)

                # Success!
                generated_code = self._create_generated_code(
                    python_code,
                    ast,
                    strategy="rule_based"
                )

                rule_based_succeeded = True
                strategy_used = "rule_based"

                logger.info("Rule-based conversion succeeded")

                # Optional: Verify with LLM
                if self.verify_rule_based:
                    logger.debug("Verifying rule-based result with LLM")
                    verification = await self._verify_with_llm(ast, python_code)

                    total_cost += verification.get('cost', 0)
                    llm_used = True

                    if not verification.get('is_correct', True):
                        logger.warning(
                            f"LLM verification found issues: "
                            f"{verification.get('issues', [])}"
                        )
                        generated_code.warnings.extend(
                            verification.get('issues', [])
                        )
                        strategy_used = "hybrid_verified"

            except ComplexityError as e:
                # Expected for complex strategies
                logger.info(f"Rule-based failed (complexity): {e}")

            except ConversionError as e:
                # Unexpected but handleable
                logger.warning(f"Rule-based failed (error): {e}")

        # Step 2: Fall back to LLM if rule-based failed or forced
        if generated_code is None:
            logger.info("Falling back to LLM conversion")

            try:
                llm_result = await self.llm_converter.convert(ast)

                generated_code = llm_result.generated_code
                total_cost += llm_result.cost_usd
                llm_used = True
                strategy_used = "llm_only"

                logger.info(f"LLM conversion succeeded (${llm_result.cost_usd:.4f})")

            except Exception as e:
                logger.error(f"LLM conversion failed: {e}")
                raise ConversionError(
                    f"Both rule-based and LLM conversion failed: {e}"
                ) from e

        # Calculate total time
        elapsed_time = time.time() - start_time

        result = {
            "generated_code": generated_code,
            "strategy_used": strategy_used,
            "cost_usd": total_cost,
            "time_seconds": elapsed_time,
            "rule_based_succeeded": rule_based_succeeded,
            "llm_used": llm_used,
        }

        logger.info(
            f"Hybrid conversion complete: {strategy_used} "
            f"(${total_cost:.4f}, {elapsed_time:.1f}s)"
        )

        return result

    async def _verify_with_llm(
        self,
        ast: PineAST,
        python_code: str,
    ) -> dict:
        """
        Verify rule-based conversion with LLM.

        Args:
            ast: Original Pine AST
            python_code: Generated Python code

        Returns:
            Verification result dict
        """
        from .llm_prompt_builder import LLMPromptBuilder

        prompt_builder = LLMPromptBuilder()

        verification_prompt = prompt_builder.build_verification_prompt(
            ast.raw_code,
            python_code
        )

        # Call LLM for verification
        response = await self.llm_converter._call_claude_api(verification_prompt)

        # Parse response
        response_text = response.content[0].text.strip()

        is_correct = "CORRECT" in response_text.upper()
        issues = []

        if "INCORRECT" in response_text.upper():
            # Extract issues
            lines = response_text.split('\n')
            issues = [line.strip() for line in lines if line.strip()]

        # Calculate cost
        cost = self.llm_converter._calculate_cost(response.usage)

        return {
            "is_correct": is_correct,
            "issues": issues,
            "cost": cost,
        }

    def _create_generated_code(
        self,
        python_code: str,
        ast: PineAST,
        strategy: str,
    ) -> GeneratedCode:
        """Create GeneratedCode object from rule-based conversion"""
        from .llm_response_parser import LLMResponseParser

        parser = LLMResponseParser()

        # Extract metadata
        class_name = parser._extract_class_name(python_code)
        imports = parser._extract_imports(python_code)
        indicators = parser._extract_indicators_used(python_code)

        return GeneratedCode(
            full_code=python_code,
            class_name=class_name or f"{ast.script_name}Strategy",
            imports=imports,
            indicators_used=indicators,
            warnings=[],
            errors=[],
        )
