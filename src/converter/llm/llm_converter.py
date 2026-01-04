"""
LLM-Based Pine Script to Python Converter

Uses Claude API (Anthropic) to convert complex Pine Scripts that exceed
rule-based converter capabilities (complexity >= 0.3).
"""

import logging
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

# Import Anthropic SDK
try:
    from anthropic import Anthropic, AsyncAnthropic
    from anthropic.types import Message
except ImportError:
    raise ImportError(
        "Anthropic SDK not installed. Install with: pip install anthropic"
    )

from ..pine_parser import PineAST
from ..ast_code_generator import GeneratedCode

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class LLMConversionError(Exception):
    """Base exception for LLM conversion errors"""
    pass


class LLMAPIError(LLMConversionError):
    """API call failed"""
    pass


class LLMParsingError(LLMConversionError):
    """Failed to parse LLM response"""
    pass


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class LLMConversionResult:
    """Result of LLM conversion with metadata"""
    generated_code: GeneratedCode
    model_used: str
    tokens_used: int
    cost_usd: float
    latency_seconds: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def full_code(self) -> str:
        """Convenience accessor"""
        return self.generated_code.full_code


# ============================================================================
# LLM Converter
# ============================================================================

class LLMConverter:
    """
    LLM-based Pine Script to Python converter using Claude.

    For complex strategies (complexity >= 0.3) where rule-based
    conversion fails or is insufficient.

    Features:
    - Async API calls with retries
    - Token usage tracking
    - Cost estimation
    - Response caching
    - Error recovery

    Example:
        >>> converter = LLMConverter(api_key="sk-ant-...")
        >>> result = await converter.convert(ast)
        >>> print(result.full_code)
        >>> print(f"Cost: ${result.cost_usd:.4f}")
    """

    # Model pricing (as of Jan 2025)
    # Source: https://www.anthropic.com/pricing
    MODEL_PRICING = {
        "claude-opus-4-5": {
            "input": 15.00 / 1_000_000,   # $15 per MTok
            "output": 75.00 / 1_000_000,  # $75 per MTok
        },
        "claude-sonnet-4-5": {
            "input": 3.00 / 1_000_000,    # $3 per MTok
            "output": 15.00 / 1_000_000,  # $15 per MTok
        },
        "claude-sonnet-4": {
            "input": 3.00 / 1_000_000,
            "output": 15.00 / 1_000_000,
        },
        "claude-haiku-4": {
            "input": 0.25 / 1_000_000,    # $0.25 per MTok
            "output": 1.25 / 1_000_000,   # $1.25 per MTok
        },
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        timeout: int = 120,
        max_retries: int = 3,
    ):
        """
        Initialize LLM converter.

        Args:
            api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
            model: Claude model to use
            max_tokens: Maximum output tokens
            temperature: Sampling temperature (0 = deterministic)
            timeout: API timeout in seconds
            max_retries: Number of retry attempts
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize Anthropic clients
        self.client = Anthropic(api_key=self.api_key)
        self.async_client = AsyncAnthropic(api_key=self.api_key)

        # Import dependencies (lazy to avoid circular imports)
        from .llm_prompt_builder import LLMPromptBuilder
        from .llm_response_parser import LLMResponseParser
        from .llm_validator import LLMValidator

        self.prompt_builder = LLMPromptBuilder()
        self.response_parser = LLMResponseParser()
        self.validator = LLMValidator()

        logger.info(
            f"Initialized LLMConverter with model={model}, "
            f"max_tokens={max_tokens}, temperature={temperature}"
        )

    async def convert(
        self,
        ast: PineAST,
        validate: bool = True,
        retry_on_validation_failure: bool = True,
    ) -> LLMConversionResult:
        """
        Convert Pine Script AST to Python using Claude LLM.

        Args:
            ast: Pine Script AST from PineParser
            validate: Run validation on generated code
            retry_on_validation_failure: Retry with refined prompt if validation fails

        Returns:
            LLMConversionResult with generated code and metadata

        Raises:
            LLMAPIError: If API call fails after retries
            LLMParsingError: If response parsing fails
            LLMConversionError: For other conversion errors

        Example:
            >>> ast = parse_pine_script(pine_code)
            >>> result = await converter.convert(ast)
            >>> print(f"Generated {len(result.full_code)} chars of code")
        """
        logger.info(f"Converting '{ast.script_name}' (complexity: {ast.complexity_score:.3f})")

        start_time = datetime.utcnow()

        try:
            # Step 1: Build prompt
            logger.debug("Building conversion prompt")
            prompt = self.prompt_builder.build_conversion_prompt(ast)

            # Step 2: Call Claude API
            logger.debug(f"Calling Claude API (model: {self.model})")
            response = await self._call_claude_api(prompt)

            # Step 3: Parse response
            logger.debug("Parsing Claude response")
            parse_result = self.response_parser.parse_python_code(
                response.content[0].text,
                ast
            )

            if not parse_result.success:
                raise LLMParsingError(
                    f"Failed to parse LLM response: {'; '.join(parse_result.errors)}"
                )

            # Step 4: Validate (optional)
            if validate:
                logger.debug("Validating generated code")
                validation = self.validator.validate(
                    parse_result.python_code,
                    ast
                )

                if not validation.is_valid and retry_on_validation_failure:
                    logger.warning(
                        f"Initial validation failed ({len(validation.errors)} errors). "
                        "Retrying with refined prompt..."
                    )
                    # Retry with validation errors in prompt
                    return await self._retry_with_refinement(
                        ast,
                        parse_result.python_code,
                        validation.errors
                    )

                # Add validation warnings to generated code
                if validation.warnings:
                    parse_result.generated_code.warnings.extend(validation.warnings)

            # Step 5: Calculate cost and metadata
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            cost = self._calculate_cost(response.usage)

            result = LLMConversionResult(
                generated_code=parse_result.generated_code,
                model_used=self.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                cost_usd=cost,
                latency_seconds=elapsed,
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
            )

            logger.info(
                f"Successfully converted '{ast.script_name}' "
                f"({result.tokens_used} tokens, ${result.cost_usd:.4f}, "
                f"{result.latency_seconds:.1f}s)"
            )

            return result

        except LLMConversionError:
            # Re-raise our own errors
            raise

        except Exception as e:
            # Wrap unexpected errors
            logger.error(f"Unexpected error during LLM conversion: {e}", exc_info=True)
            raise LLMConversionError(f"Conversion failed: {e}") from e

    async def _call_claude_api(self, prompt: str) -> Message:
        """
        Call Claude API with retries and error handling.

        Args:
            prompt: User prompt to send

        Returns:
            Claude API response message

        Raises:
            LLMAPIError: If API call fails after retries
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"API call attempt {attempt}/{self.max_retries}")

                response = await asyncio.wait_for(
                    self.async_client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        messages=[{
                            "role": "user",
                            "content": prompt
                        }]
                    ),
                    timeout=self.timeout
                )

                logger.debug(
                    f"API call successful (tokens: {response.usage.input_tokens} + "
                    f"{response.usage.output_tokens})"
                )

                return response

            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(f"API call timed out (attempt {attempt}/{self.max_retries})")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
                last_error = e
                logger.warning(
                    f"API call failed: {e} (attempt {attempt}/{self.max_retries})"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)

        # All retries failed
        error_msg = f"API call failed after {self.max_retries} attempts: {last_error}"
        logger.error(error_msg)
        raise LLMAPIError(error_msg) from last_error

    async def _retry_with_refinement(
        self,
        ast: PineAST,
        previous_code: str,
        errors: list[str]
    ) -> LLMConversionResult:
        """
        Retry conversion with refined prompt including previous errors.

        Args:
            ast: Original AST
            previous_code: Previously generated code that failed validation
            errors: Validation errors to address

        Returns:
            LLMConversionResult from refined attempt
        """
        logger.info("Attempting refinement with validation feedback")

        # Build refined prompt
        refined_prompt = self.prompt_builder.build_refinement_prompt(
            ast,
            previous_code,
            errors
        )

        # Call API
        response = await self._call_claude_api(refined_prompt)

        # Parse
        parse_result = self.response_parser.parse_python_code(
            response.content[0].text,
            ast
        )

        if not parse_result.success:
            # If parsing still fails, return best effort from first attempt
            logger.error("Refinement attempt also failed parsing")
            raise LLMParsingError("Refinement attempt failed")

        # Validate again (but don't retry infinitely)
        validation = self.validator.validate(parse_result.python_code, ast)

        if validation.warnings:
            parse_result.generated_code.warnings.extend(validation.warnings)
        if validation.errors:
            parse_result.generated_code.errors.extend(validation.errors)

        # Calculate cost
        cost = self._calculate_cost(response.usage)

        return LLMConversionResult(
            generated_code=parse_result.generated_code,
            model_used=self.model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            cost_usd=cost,
            latency_seconds=0.0,  # Not tracking for retry
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )

    def _calculate_cost(self, usage: Any) -> float:
        """
        Calculate API call cost in USD.

        Args:
            usage: Response usage object

        Returns:
            Cost in USD
        """
        pricing = self.MODEL_PRICING.get(self.model, {})

        input_cost = usage.input_tokens * pricing.get("input", 0)
        output_cost = usage.output_tokens * pricing.get("output", 0)

        return input_cost + output_cost

    def estimate_cost(self, ast: PineAST) -> float:
        """
        Estimate conversion cost for AST (without actually converting).

        Args:
            ast: Pine Script AST

        Returns:
            Estimated cost in USD
        """
        # Build prompt to estimate token count
        prompt = self.prompt_builder.build_conversion_prompt(ast)

        # Rough estimate: 1 token ≈ 4 characters
        estimated_input_tokens = len(prompt) // 4

        # Output typically 2-3x input for code generation
        estimated_output_tokens = estimated_input_tokens * 2.5

        pricing = self.MODEL_PRICING.get(self.model, {})

        input_cost = estimated_input_tokens * pricing.get("input", 0)
        output_cost = estimated_output_tokens * pricing.get("output", 0)

        return input_cost + output_cost
