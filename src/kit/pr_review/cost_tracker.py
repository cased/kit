"""Cost tracking for PR review operations."""

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import ClassVar, Dict, Optional

import requests

from .config import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class CostBreakdown:
    """Breakdown of costs for a PR review."""

    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_cost_usd: float = 0.0
    model_used: str = ""
    pricing_date: str = "2025-05-22"

    def __str__(self) -> str:
        """Human-readable cost summary."""
        return f"""
💰 Cost Breakdown:
   LLM Usage: ${self.llm_cost_usd:.4f} ({self.llm_input_tokens:,} input + {self.llm_output_tokens:,} output tokens)
   Model: {self.model_used}
"""


class CostTracker:
    """Tracks costs for PR review operations."""

    # Cache pricing data for 24 hours
    CACHE_TTL_SECONDS = 86400
    HELICONE_API_URL = "https://helicone.ai/api/llm-costs"

    # Minimal fallback pricing for when API is unavailable
    FALLBACK_PRICING: ClassVar[Dict] = {
        LLMProvider.ANTHROPIC: {
            "_default": {"input_per_million": 3.00, "output_per_million": 15.00},
        },
        LLMProvider.OPENAI: {
            "_default": {"input_per_million": 2.50, "output_per_million": 10.00},
        },
        LLMProvider.GOOGLE: {
            "_default": {"input_per_million": 0.50, "output_per_million": 1.50},
        },
        LLMProvider.OLLAMA: {
            "_default": {"input_per_million": 0.00, "output_per_million": 0.00},
        },
    }

    def __init__(self, custom_pricing: Optional[Dict] = None):
        """Initialize cost tracker with optional custom pricing."""
        self.custom_pricing = custom_pricing
        self.reset()

    def reset(self):
        """Reset cost tracking for a new review."""
        self.breakdown = CostBreakdown()

    @staticmethod
    @lru_cache(maxsize=1)
    def _fetch_pricing_with_cache(cache_key: str) -> Dict:
        """Fetch pricing from Helicone API with caching.

        The cache_key is just the current hour to ensure we refresh hourly.
        """
        try:
            logger.info("Fetching latest pricing from Helicone API...")
            response = requests.get(CostTracker.HELICONE_API_URL, timeout=5)
            response.raise_for_status()

            data = response.json()

            # Convert Helicone format to Kit format
            pricing = {
                LLMProvider.ANTHROPIC: {},
                LLMProvider.OPENAI: {},
                LLMProvider.GOOGLE: {},
                LLMProvider.OLLAMA: {"_default": {"input_per_million": 0.00, "output_per_million": 0.00}},
            }

            for model_data in data.get("data", []):
                provider_name = model_data.get("provider", "").upper()
                model_name = model_data.get("model", "")
                input_cost = model_data.get("input_cost_per_1m", 0.0)
                output_cost = model_data.get("output_cost_per_1m", 0.0)

                # Map Helicone providers to Kit providers
                provider_map = {
                    "OPENAI": LLMProvider.OPENAI,
                    "ANTHROPIC": LLMProvider.ANTHROPIC,
                    "GOOGLE": LLMProvider.GOOGLE,
                    "GOOGLEVERTEXAI": LLMProvider.GOOGLE,
                    "OLLAMA": LLMProvider.OLLAMA,
                }

                if provider_name in provider_map:
                    kit_provider = provider_map[provider_name]
                    # Handle model name normalization
                    normalized_model = CostTracker._normalize_model_name(model_name, kit_provider)
                    pricing[kit_provider][normalized_model] = {
                        "input_per_million": input_cost,
                        "output_per_million": output_cost,
                    }

            logger.info(f"Successfully fetched pricing for {sum(len(p) for p in pricing.values())} models")
            return pricing

        except Exception as e:
            logger.warning(f"Failed to fetch pricing from Helicone API: {e}")
            logger.warning("Using fallback pricing")
            return CostTracker.FALLBACK_PRICING

    @staticmethod
    def _normalize_model_name(model_name: str, provider: LLMProvider) -> str:
        """Normalize model names from Helicone to match Kit's naming."""
        # Handle special cases and normalization
        if provider == LLMProvider.ANTHROPIC:
            # Convert Helicone's claude names to Kit's format
            if "claude-3-opus" in model_name:
                return "claude-opus-4-20250514"  # Map to Kit's naming
            elif "claude-3.5-sonnet" in model_name or "claude-3-5-sonnet" in model_name:
                if "20241022" in model_name:
                    return "claude-3-5-sonnet-20241022"
                return "claude-sonnet-4-20250514"
            elif "claude-3.5-haiku" in model_name or "claude-3-5-haiku" in model_name:
                if "20241022" in model_name:
                    return "claude-3-5-haiku-20241022"
                return "claude-3-5-haiku-latest"
            elif "claude-2" in model_name:
                return "claude-2"

        elif provider == LLMProvider.OPENAI:
            # Normalize OpenAI model names
            if model_name == "gpt-4":
                return "gpt-4.1"
            elif model_name == "gpt-4-1106-preview":
                return "gpt-4-turbo"
            elif model_name.startswith("gpt-3.5"):
                return "gpt-3.5-turbo"
            # Keep specific model names as is
            elif model_name in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"]:
                return model_name

        elif provider == LLMProvider.GOOGLE:
            # Normalize Gemini model names
            if "gemini-pro" in model_name and "1.0" in model_name:
                return "gemini-1.0-pro"
            elif "gemini-pro" in model_name and "1.5" in model_name:
                return "gemini-1.5-pro"
            # Keep other Google model names mostly as-is
            return model_name

        return model_name

    def _get_current_pricing(self) -> Dict:
        """Get current pricing, using cache or fetching from API."""
        if self.custom_pricing:
            return self.custom_pricing

        # Use current hour as cache key (refreshes hourly)
        cache_key = str(int(time.time() / 3600))
        return self._fetch_pricing_with_cache(cache_key)

    def track_llm_usage(self, provider: LLMProvider, model: str, input_tokens: int, output_tokens: int):
        """Track LLM API usage and calculate costs."""
        self.breakdown.llm_input_tokens += input_tokens
        self.breakdown.llm_output_tokens += output_tokens

        # Strip prefix from model name for pricing lookup
        stripped_model = self._strip_model_prefix(model)

        # Get current pricing
        current_pricing = self._get_current_pricing()

        # Get pricing for this provider/model
        if provider in current_pricing and stripped_model in current_pricing[provider]:
            pricing = current_pricing[provider][stripped_model]
            input_cost = (input_tokens / 1_000_000) * pricing["input_per_million"]
            output_cost = (output_tokens / 1_000_000) * pricing["output_per_million"]

            self.breakdown.llm_cost_usd += input_cost + output_cost
        elif provider == LLMProvider.OLLAMA:
            # All Ollama models are free - use default $0.00 pricing
            if provider in current_pricing and "_default" in current_pricing[provider]:
                pricing = current_pricing[provider]["_default"]
                self.breakdown.llm_cost_usd += 0.00  # Always free
            else:
                self.breakdown.llm_cost_usd += 0.00  # Fallback - still free
        else:
            # Try the default pricing for the provider first
            if provider in current_pricing and "_default" in current_pricing[provider]:
                pricing = current_pricing[provider]["_default"]
                input_cost = (input_tokens / 1_000_000) * pricing["input_per_million"]
                output_cost = (output_tokens / 1_000_000) * pricing["output_per_million"]
                self.breakdown.llm_cost_usd += input_cost + output_cost
                logger.info(f"Using default pricing for {provider.value}/{stripped_model}")
            else:
                # Unknown model - use a reasonable estimate and warn
                logger.warning(f"Unknown pricing for {provider.value}/{stripped_model}, using estimates")
                logger.warning("Check if Helicone API has pricing for this model")
                self.breakdown.llm_cost_usd += (input_tokens / 1_000_000) * 3.0
                self.breakdown.llm_cost_usd += (output_tokens / 1_000_000) * 15.0

        # Store the original model name with prefix for reference
        self.breakdown.model_used = model
        self._update_total()

    def _update_total(self):
        """Update total cost."""
        self.breakdown.total_cost_usd = self.breakdown.llm_cost_usd

    def get_cost_summary(self) -> str:
        """Get human-readable cost summary."""
        return str(self.breakdown)

    def get_total_cost(self) -> float:
        """Get total cost in USD for the current review."""
        return self.breakdown.llm_cost_usd

    def extract_anthropic_usage(self, response) -> tuple[int, int]:
        """Extract token usage from Anthropic response."""
        try:
            usage = response.usage
            return usage.input_tokens, usage.output_tokens
        except AttributeError:
            # Fallback if usage info not available
            return 0, 0

    def extract_openai_usage(self, response) -> tuple[int, int]:
        """Extract token usage from OpenAI response."""
        try:
            usage = response.usage
            return usage.prompt_tokens, usage.completion_tokens
        except AttributeError:
            # Fallback if usage info not available
            return 0, 0

    def get_available_models(self) -> Dict[str, list[str]]:
        """Get all available models organized by provider."""
        available = {}
        current_pricing = self._get_current_pricing()
        for provider, models in current_pricing.items():
            available[provider.value] = list(models.keys())
        return available

    def get_all_model_names(self) -> list[str]:
        """Get a flat list of all available model names."""
        all_models = []
        current_pricing = self._get_current_pricing()
        for provider_models in current_pricing.values():
            all_models.extend(provider_models.keys())
        return sorted(all_models)

    @classmethod
    def _strip_model_prefix(cls, model_name: str) -> str:
        """Strip provider prefixes from model names.

        Examples:
        - vertex_ai/claude-sonnet-4-20250514 -> claude-sonnet-4-20250514
        - openrouter/meta-llama/llama-3.3-70b -> meta-llama/llama-3.3-70b
        - gpt-4o -> gpt-4o (unchanged)
        """
        # Remove anything before the first "/"
        if "/" in model_name:
            return model_name.split("/", 1)[1]

        return model_name

    @classmethod
    def is_valid_model(cls, model_name: str) -> bool:
        """Check if a model name is valid/supported.

        Supports prefixed model names like 'vertex_ai/claude-sonnet-4-20250514'.
        """
        # Create a temporary instance to get current pricing
        temp_tracker = cls()
        all_models = temp_tracker.get_all_model_names()

        # Try exact match first
        if model_name in all_models:
            return True

        # Try with prefix stripped
        stripped_model = cls._strip_model_prefix(model_name)
        if stripped_model in all_models:
            return True

        # Special case for Ollama - any model is valid since it's local
        if ":" in model_name and not model_name.startswith("http"):
            # Looks like an Ollama model (e.g., "llama3:latest", "qwen2.5-coder:7b")
            return True

        return False

    @classmethod
    def get_model_suggestions(cls, invalid_model: str) -> list[str]:
        """Get model suggestions for an invalid model name."""
        # Create a temporary instance to get current pricing
        temp_tracker = cls()
        all_models = temp_tracker.get_all_model_names()
        suggestions = []

        # Strip prefix for comparison
        stripped_invalid = cls._strip_model_prefix(invalid_model).lower()

        # Check for models that start similarly or contain common parts
        for model in all_models:
            lower_model = model.lower()
            # Check if models start similarly
            starts_similar = lower_model.startswith(stripped_invalid[:4]) or stripped_invalid.startswith(
                lower_model[:4]
            )
            # Check if any significant parts match
            parts_match = any(part in lower_model for part in stripped_invalid.split("-")[:2] if len(part) > 2)

            if starts_similar or parts_match:
                suggestions.append(model)

        # If no good matches, return a few popular ones
        if not suggestions:
            popular_models = ["gpt-4.1-nano", "gpt-4o-mini", "claude-3-5-sonnet-20241022"]
            suggestions = popular_models

        return suggestions[:5]  # Limit to 5 suggestions
