"""Unified LLM client factory for kit.

This module provides a centralized way to create LLM clients for various providers,
eliminating duplicated client initialization logic across the codebase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from kit.pr_review.config import LLMConfig
    from kit.summaries import AnthropicConfig, GoogleConfig, OllamaConfig, OpenAIConfig


class LLMClientError(Exception):
    """Error raised when LLM client creation fails."""

    pass


def create_openai_client(
    api_key: str,
    base_url: Optional[str] = None,
) -> Any:
    """Create an OpenAI client.

    Args:
        api_key: The OpenAI API key
        base_url: Optional custom base URL for OpenAI-compatible APIs

    Returns:
        An OpenAI client instance

    Raises:
        LLMClientError: If the openai package is not installed
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise LLMClientError("openai package not installed. Run: pip install openai")

    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def create_anthropic_client(api_key: str) -> Any:
    """Create an Anthropic client.

    Args:
        api_key: The Anthropic API key

    Returns:
        An Anthropic client instance

    Raises:
        LLMClientError: If the anthropic package is not installed
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        raise LLMClientError("anthropic package not installed. Run: pip install anthropic")

    return Anthropic(api_key=api_key)


def create_google_client(api_key: str) -> Any:
    """Create a Google Generative AI client.

    Args:
        api_key: The Google API key

    Returns:
        A Google genai Client instance

    Raises:
        LLMClientError: If the google-genai package is not installed
    """
    try:
        import google.genai as genai
    except ImportError:
        raise LLMClientError("google-genai package not installed. Run: pip install google-genai")

    return genai.Client(api_key=api_key)


def create_ollama_client(
    base_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder:latest",
    session: Optional[Any] = None,
) -> Any:
    """Create an Ollama client.

    Args:
        base_url: The Ollama API base URL
        model: The model name to use
        session: Optional requests.Session to reuse

    Returns:
        An OllamaClient instance

    Raises:
        LLMClientError: If the requests package is not installed
    """
    try:
        from kit.ollama_client import OllamaClient
    except ImportError:
        raise LLMClientError("requests package not installed. Run: pip install requests")

    return OllamaClient(base_url, model, session)


def create_client_from_config(
    config: Union["OpenAIConfig", "AnthropicConfig", "GoogleConfig", "OllamaConfig"],
) -> Any:
    """Create an LLM client from a summaries config object.

    Args:
        config: One of the config dataclasses from kit.summaries

    Returns:
        The appropriate LLM client instance

    Raises:
        LLMClientError: If the required package is not installed
        TypeError: If the config type is not recognized
    """
    # Import here to avoid circular imports
    from kit.summaries import AnthropicConfig, GoogleConfig, OllamaConfig, OpenAIConfig

    if isinstance(config, OpenAIConfig):
        return create_openai_client(config.api_key or "", config.base_url)
    elif isinstance(config, AnthropicConfig):
        return create_anthropic_client(config.api_key or "")
    elif isinstance(config, GoogleConfig):
        return create_google_client(config.api_key or "")
    elif isinstance(config, OllamaConfig):
        return create_ollama_client(config.base_url, config.model)
    else:
        raise TypeError(f"Unsupported config type: {type(config)}")


def create_client_from_review_config(
    llm_config: "LLMConfig",
    session: Optional[Any] = None,
) -> Any:
    """Create an LLM client from a ReviewConfig's LLM settings.

    Args:
        llm_config: The LLMConfig from ReviewConfig
        session: Optional requests.Session for Ollama

    Returns:
        The appropriate LLM client instance

    Raises:
        LLMClientError: If the required package is not installed
        ValueError: If the provider is not recognized
    """
    # Import here to avoid circular imports
    from kit.pr_review.config import LLMProvider

    if llm_config.provider == LLMProvider.OPENAI:
        return create_openai_client(llm_config.api_key, llm_config.api_base_url)
    elif llm_config.provider == LLMProvider.ANTHROPIC:
        return create_anthropic_client(llm_config.api_key)
    elif llm_config.provider == LLMProvider.GOOGLE:
        return create_google_client(llm_config.api_key)
    elif llm_config.provider == LLMProvider.OLLAMA:
        return create_ollama_client(
            llm_config.api_base_url or "http://localhost:11434",
            llm_config.model,
            session,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_config.provider}")
