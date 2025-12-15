"""
Cost Tracker Service for AI API Usage

Calculates estimated costs for AI API requests using provider-specific token rates.
Supports multi-image cost calculation and configurable rate overrides.

Story P3-7.1: Implement Cost Tracking Service
"""

import os
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Provider cost rates per 1K tokens (USD)
# Updated Dec 2025 - can be overridden via environment variables
PROVIDER_COST_RATES: Dict[str, Dict[str, float]] = {
    "openai": {
        "input": 0.00015,   # GPT-4o-mini input
        "output": 0.0006,   # GPT-4o-mini output
    },
    "grok": {
        "input": 0.0001,    # xAI Grok 2 Vision
        "output": 0.0003,
    },
    "claude": {
        "input": 0.00025,   # Claude 3 Haiku
        "output": 0.00125,
    },
    "gemini": {
        "input": 0.0,       # Gemini Flash free tier
        "output": 0.0,
    },
    "whisper": {
        "input": 0.006,     # $0.006 per minute (stored as per-minute rate)
        "output": 0.0,
    },
}

# Image token estimates per provider
# These are approximate tokens consumed per image in vision API calls
TOKENS_PER_IMAGE: Dict[str, Dict[str, int]] = {
    "openai": {
        "low_res": 85,      # Low detail mode
        "high_res": 765,    # High detail mode
        "default": 85,
    },
    "grok": {
        "low_res": 85,      # OpenAI-compatible
        "high_res": 765,
        "default": 85,
    },
    "claude": {
        "default": 1334,    # Claude's image token estimate
    },
    "gemini": {
        "default": 258,     # Gemini's approximate image token usage
    },
}

# Default output token estimate when provider doesn't report
DEFAULT_OUTPUT_TOKENS = 150


class CostTracker:
    """
    Service for calculating and tracking AI API usage costs.

    Provides methods to calculate costs based on token usage,
    with support for multi-image requests and provider-specific rates.
    """

    def __init__(self):
        """Initialize CostTracker with cost rates, allowing env overrides."""
        self.rates = self._load_rates_with_overrides()
        self.image_tokens = TOKENS_PER_IMAGE.copy()

    def _load_rates_with_overrides(self) -> Dict[str, Dict[str, float]]:
        """
        Load cost rates with environment variable overrides.

        Environment variables follow pattern:
        AI_COST_RATE_{PROVIDER}_{TYPE} (e.g., AI_COST_RATE_OPENAI_INPUT)
        """
        rates = {}
        for provider, provider_rates in PROVIDER_COST_RATES.items():
            rates[provider] = {}
            for rate_type, default_value in provider_rates.items():
                env_key = f"AI_COST_RATE_{provider.upper()}_{rate_type.upper()}"
                env_value = os.environ.get(env_key)
                if env_value is not None:
                    try:
                        rates[provider][rate_type] = float(env_value)
                        logger.info(f"Using env override for {provider} {rate_type}: {env_value}")
                    except ValueError:
                        logger.warning(f"Invalid env value for {env_key}: {env_value}, using default")
                        rates[provider][rate_type] = default_value
                else:
                    rates[provider][rate_type] = default_value
        return rates

    def calculate_cost(
        self,
        provider: str,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """
        Calculate cost for an AI request based on token usage.

        Args:
            provider: AI provider name (openai, grok, claude, gemini)
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens

        Returns:
            Decimal cost in USD with 6 decimal places precision
        """
        provider_key = provider.lower()
        if provider_key not in self.rates:
            logger.warning(f"Unknown provider '{provider}', using zero cost")
            return Decimal("0.000000")

        rates = self.rates[provider_key]

        # Calculate input and output costs (rates are per 1K tokens)
        input_cost = (input_tokens / 1000) * rates.get("input", 0)
        output_cost = (output_tokens / 1000) * rates.get("output", 0)

        total_cost = Decimal(str(input_cost + output_cost))

        # Round to 6 decimal places
        return total_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def calculate_multi_image_cost(
        self,
        provider: str,
        image_count: int,
        resolution: str = "default",
        output_tokens: int = DEFAULT_OUTPUT_TOKENS
    ) -> Decimal:
        """
        Calculate cost for a multi-image AI request.

        Estimates input tokens based on image count and resolution,
        then calculates total cost including output tokens.

        Args:
            provider: AI provider name
            image_count: Number of images in the request
            resolution: Image resolution mode ("low_res", "high_res", "default")
            output_tokens: Estimated or actual output tokens

        Returns:
            Decimal cost in USD with 6 decimal places precision
        """
        provider_key = provider.lower()

        # Get tokens per image for this provider
        provider_image_tokens = self.image_tokens.get(provider_key, {"default": 100})
        tokens_per_image = provider_image_tokens.get(
            resolution,
            provider_image_tokens.get("default", 100)
        )

        # Calculate total input tokens from images
        # Add base prompt tokens (~50) plus image tokens
        base_prompt_tokens = 50
        image_tokens = image_count * tokens_per_image
        total_input_tokens = base_prompt_tokens + image_tokens

        return self.calculate_cost(provider_key, total_input_tokens, output_tokens)

    def estimate_tokens(
        self,
        image_count: int,
        response_length: int,
        provider: str = "openai"
    ) -> tuple[int, int, bool]:
        """
        Estimate token counts when provider doesn't return them.

        Uses conservative estimates to avoid underreporting costs.

        Args:
            image_count: Number of images in request
            response_length: Character length of response
            provider: AI provider name

        Returns:
            Tuple of (input_tokens, output_tokens, is_estimated)
        """
        provider_key = provider.lower()

        # Estimate input tokens from images
        provider_image_tokens = self.image_tokens.get(provider_key, {"default": 100})
        tokens_per_image = provider_image_tokens.get("default", 100)

        # Conservative estimate: images + base prompt (100 tokens)
        input_tokens = (image_count * tokens_per_image) + 100

        # Output tokens: ~4 characters per token (conservative)
        output_tokens = max(response_length // 4, 50)

        # Add 20% safety margin for conservative estimates
        input_tokens = int(input_tokens * 1.2)
        output_tokens = int(output_tokens * 1.2)

        return input_tokens, output_tokens, True

    def get_provider_rates(self, provider: str) -> Optional[Dict[str, float]]:
        """
        Get the current cost rates for a provider.

        Args:
            provider: AI provider name

        Returns:
            Dict with 'input' and 'output' rates, or None if unknown provider
        """
        return self.rates.get(provider.lower())

    def get_all_rates(self) -> Dict[str, Dict[str, float]]:
        """
        Get all current cost rates.

        Returns:
            Dict mapping provider names to their rate dicts
        """
        return self.rates.copy()


# Singleton instance for use across the application
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """
    Get the singleton CostTracker instance.

    Returns:
        CostTracker instance
    """
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
