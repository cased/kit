"""
LLM provider configuration classes.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI API access."""

    api_key: Optional[str] = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY"))
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 1000  # Default max tokens for summary
    base_url: Optional[str] = None

    def __post_init__(self):
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable or pass api_key directly."
            )


@dataclass
class AnthropicConfig:
    """Configuration for Anthropic API access."""

    api_key: Optional[str] = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY"))
    model: str = "claude-3-opus-20240229"
    temperature: float = 0.7
    max_tokens: int = 1000  # Corresponds to Anthropic's max_tokens_to_sample

    def __post_init__(self):
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable or pass api_key directly."
            )


@dataclass
class GoogleConfig:
    """Configuration for Google Generative AI API access."""

    api_key: Optional[str] = field(default_factory=lambda: os.environ.get("GOOGLE_API_KEY"))
    model: str = "gemini-1.5-pro-latest"
    temperature: Optional[float] = 0.7
    max_output_tokens: Optional[int] = 1000  # Corresponds to Gemini's max_output_tokens
    model_kwargs: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.api_key:
            raise ValueError(
                "Google API key not found. Set GOOGLE_API_KEY environment variable or pass api_key directly."
            )
