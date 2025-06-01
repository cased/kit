"""Cost tracking for PR review operations."""

from dataclasses import dataclass
from typing import ClassVar, Dict, Optional

from .config import LLMProvider


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

    # Default pricing (as of May 2025) - can be overridden in config
    DEFAULT_PRICING: ClassVar[Dict] = {
        LLMProvider.ANTHROPIC: {
            "claude-opus-4-20250514": {
                "input_per_million": 15.00,  # $15.00 per million input tokens
                "output_per_million": 75.00,  # $75.00 per million output tokens
            },
            "claude-sonnet-4-20250514": {
                "input_per_million": 3.00,  # $3.00 per million input tokens
                "output_per_million": 15.00,  # $15.00 per million output tokens
            },
            "claude-3-5-sonnet-20241022": {
                "input_per_million": 3.00,  # $3.00 per million input tokens
                "output_per_million": 15.00,  # $15.00 per million output tokens
            },
            "claude-3-5-sonnet-latest": {
                "input_per_million": 3.00,  # $3.00 per million input tokens
                "output_per_million": 15.00,  # $15.00 per million output tokens
            },
            "claude-3-5-haiku-20241022": {
                "input_per_million": 0.80,  # $0.80 per million input tokens
                "output_per_million": 4.00,  # $4.00 per million output tokens
            },
            "claude-3-5-haiku-latest": {
                "input_per_million": 0.80,  # $0.80 per million input tokens
                "output_per_million": 4.00,  # $4.00 per million output tokens
            },
        },
        LLMProvider.OPENAI: {
            "gpt-4.1": {
                "input_per_million": 2.00,  # $2.00 per million input tokens
                "output_per_million": 8.00,  # $8.00 per million output tokens
            },
            "gpt-4.1-mini": {
                "input_per_million": 0.40,  # $0.40 per million input tokens
                "output_per_million": 1.60,  # $1.60 per million output tokens
            },
            "gpt-4.1-nano": {
                "input_per_million": 0.10,  # $0.10 per million input tokens
                "output_per_million": 0.40,  # $0.40 per million output tokens
            },
            "gpt-4o": {
                "input_per_million": 2.50,  # $2.50 per million input tokens
                "output_per_million": 10.00,  # $10.00 per million output tokens
            },
            "gpt-4o-mini": {
                "input_per_million": 0.15,  # $0.15 per million input tokens
                "output_per_million": 0.60,  # $0.60 per million output tokens
            },
            "gpt-4-turbo": {
                "input_per_million": 10.00,  # $10.00 per million input tokens
                "output_per_million": 30.00,  # $30.00 per million output tokens
            },
        },
    }

    def __init__(self, custom_pricing: Optional[Dict] = None):
        """Initialize cost tracker with optional custom pricing."""
        self.pricing = custom_pricing or self.DEFAULT_PRICING
        self.reset()

    def reset(self):
        """Reset cost tracking for a new review."""
        self.breakdown = CostBreakdown()

    def track_llm_usage(self, provider: LLMProvider, model: str, input_tokens: int, output_tokens: int):
        """Track LLM API usage and calculate costs."""
        self.breakdown.llm_input_tokens += input_tokens
        self.breakdown.llm_output_tokens += output_tokens

        # Get pricing for this provider/model
        if provider in self.pricing and model in self.pricing[provider]:
            pricing = self.pricing[provider][model]
            input_cost = (input_tokens / 1_000_000) * pricing["input_per_million"]
            output_cost = (output_tokens / 1_000_000) * pricing["output_per_million"]

            self.breakdown.llm_cost_usd += input_cost + output_cost
        else:
            # Unknown model - use a reasonable estimate and warn
            print(f"⚠️  Unknown pricing for {provider.value}/{model}, using estimates")
            print("   Update pricing in ~/.kit/review-config.yaml or check current rates")
            self.breakdown.llm_cost_usd += (input_tokens / 1_000_000) * 3.0
            self.breakdown.llm_cost_usd += (output_tokens / 1_000_000) * 15.0

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

    @classmethod
    def get_available_models(cls) -> Dict[str, list[str]]:
        """Get all available models organized by provider."""
        available = {}
        for provider, models in cls.DEFAULT_PRICING.items():
            available[provider.value] = list(models.keys())
        return available

    @classmethod
    def get_all_model_names(cls) -> list[str]:
        """Get a flat list of all available model names."""
        all_models = []
        for provider_models in cls.DEFAULT_PRICING.values():
            all_models.extend(provider_models.keys())
        return sorted(all_models)

    @classmethod
    def is_valid_model(cls, model_name: str) -> bool:
        """Check if a model name is valid/supported."""
        return model_name in cls.get_all_model_names()

    @classmethod
    def get_model_suggestions(cls, invalid_model: str) -> list[str]:
        """Get model suggestions for an invalid model name."""
        all_models = cls.get_all_model_names()
        # Simple similarity matching - starts with same prefix or contains common parts
        suggestions = []

        # Check for models that start similarly
        lower_invalid = invalid_model.lower()
        for model in all_models:
            lower_model = model.lower()
            if lower_model.startswith(lower_invalid[:3]) or lower_invalid.startswith(lower_model[:3]):
                suggestions.append(model)

        # If no good matches, return a few popular ones
        if not suggestions:
            suggestions = ["gpt-4.1-nano", "gpt-4o-mini", "claude-3-5-sonnet-20241022"]

        return suggestions[:5]  # Limit to 5 suggestions
