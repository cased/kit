"""LLM client interfaces and implementations."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from kit.models.base import LLMError
from kit.models.config import AnthropicConfig, GoogleConfig, OpenAIConfig
from kit.models.llm_utils import count_openai_chat_tokens

# Conditionally import google.genai
try:
    import google.genai as genai
    from google.genai import types as genai_types
except ImportError:
    genai = None  # type: ignore
    genai_types = None  # type: ignore

logger = logging.getLogger(__name__)

# Constants
OPENAI_MAX_PROMPT_TOKENS = 15000  # Max tokens for the prompt to OpenAI


class LLMClient(ABC):
    """Base class for LLM clients."""

    @abstractmethod
    def generate_completion(self, system_prompt: str, user_prompt: str, model_name: Optional[str] = None) -> str:
        """Generate a completion from the LLM.

        Args:
            system_prompt: The system prompt to use.
            user_prompt: The user prompt to use.
            model_name: Optional model name to override the default.

        Returns:
            The generated completion text.

        Raises:
            LLMError: If there was an error generating the completion.
        """
        pass

    @staticmethod
    def create_client(config: Union[OpenAIConfig, AnthropicConfig, GoogleConfig]) -> "LLMClient":
        """Factory method to create an appropriate LLM client.

        Args:
            config: The LLM configuration to use.

        Returns:
            An LLMClient instance.

        Raises:
            TypeError: If config is None or an unsupported configuration type.
            LLMError: If there was an error initializing the client.
        """
        # Require a valid config
        if config is None:
            raise TypeError("LLM configuration must be provided")

        if isinstance(config, OpenAIConfig):
            return OpenAIClient(config)
        elif isinstance(config, AnthropicConfig):
            return AnthropicClient(config)
        elif isinstance(config, GoogleConfig):
            return GoogleClient(config)
        else:
            raise TypeError(f"Unsupported LLM configuration type: {type(config)}")


class OpenAIClient(LLMClient):
    """Client for OpenAI's API."""

    def __init__(self, config: OpenAIConfig):
        """Initialize with OpenAI configuration.

        Args:
            config: The OpenAI configuration.

        Raises:
            LLMError: If the OpenAI SDK is not available.
        """
        self.config = config
        try:
            from openai import OpenAI

            if self.config.base_url:
                self.client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)
            else:
                self.client = OpenAI(api_key=self.config.api_key)
        except ImportError:
            raise LLMError("OpenAI SDK (openai) not available. Please install it.")

    def generate_completion(self, system_prompt: str, user_prompt: str, model_name: Optional[str] = None) -> str:
        """Generate a completion using OpenAI's API.

        Args:
            system_prompt: The system prompt to use.
            user_prompt: The user prompt to use.
            model_name: Optional model name to override the config's model.

        Returns:
            The generated completion text.

        Raises:
            LLMError: If there was an error generating the completion.
        """
        # Use provided model_name or fall back to config
        actual_model = model_name if model_name is not None else self.config.model

        messages_for_api = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Check token count
        prompt_token_count = count_openai_chat_tokens(messages_for_api, actual_model)
        if prompt_token_count is not None and prompt_token_count > OPENAI_MAX_PROMPT_TOKENS:
            return f"Completion generation failed: OpenAI prompt too large ({prompt_token_count} tokens). Limit is {OPENAI_MAX_PROMPT_TOKENS} tokens."

        try:
            response = self.client.chat.completions.create(
                model=actual_model,
                messages=messages_for_api,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            if response.usage:
                logger.debug(f"OpenAI API usage: {response.usage}")

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error communicating with OpenAI API: {e}")
            raise LLMError(f"Error communicating with OpenAI API: {e}") from e


class AnthropicClient(LLMClient):
    """Client for Anthropic's API."""

    def __init__(self, config: AnthropicConfig):
        """Initialize with Anthropic configuration.

        Args:
            config: The Anthropic configuration.

        Raises:
            LLMError: If the Anthropic SDK is not available.
        """
        self.config = config
        try:
            from anthropic import Anthropic

            self.client = Anthropic(api_key=self.config.api_key)
        except ImportError:
            raise LLMError("Anthropic SDK (anthropic) not available. Please install it.")

    def generate_completion(self, system_prompt: str, user_prompt: str, model_name: Optional[str] = None) -> str:
        """Generate a completion using Anthropic's API.

        Args:
            system_prompt: The system prompt to use.
            user_prompt: The user prompt to use.
            model_name: Optional model name to override the config's model.

        Returns:
            The generated completion text.

        Raises:
            LLMError: If there was an error generating the completion.
        """
        # Use provided model_name or fall back to config
        actual_model = model_name if model_name is not None else self.config.model

        try:
            response = self.client.messages.create(
                model=actual_model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            return response.content[0].text
        except Exception as e:
            logger.error(f"Error communicating with Anthropic API: {e}")
            raise LLMError(f"Error communicating with Anthropic API: {e}") from e


class GoogleClient(LLMClient):
    """Client for Google's Generative AI API."""

    def __init__(self, config: GoogleConfig):
        """Initialize with Google configuration.

        Args:
            config: The Google configuration.

        Raises:
            LLMError: If the Google Gen AI SDK is not available.
        """
        self.config = config
        if genai is None:
            raise LLMError("Google Gen AI SDK (google-genai) not available. Please install it.")

        try:
            self.client = genai.Client(api_key=self.config.api_key)
        except Exception as e:
            raise LLMError(f"Error initializing Google Gen AI client: {e}") from e

    def generate_completion(self, system_prompt: str, user_prompt: str, model_name: Optional[str] = None) -> str:
        """Generate a completion using Google's Generative AI API.

        Args:
            system_prompt: The system prompt to use (Note: currently not used by Google's API directly).
            user_prompt: The user prompt to use.
            model_name: Optional model name to override the config's model.

        Returns:
            The generated completion text.

        Raises:
            LLMError: If there was an error generating the completion.
        """
        # Use provided model_name or fall back to config
        actual_model = model_name if model_name is not None else self.config.model

        if genai_types is None:
            raise LLMError(
                "Google Gen AI SDK (google-genai) types not available. SDK might not be installed correctly."
            )

        # Prepare generation config from model_kwargs
        generation_config_params: Dict[str, Any] = (
            self.config.model_kwargs.copy() if self.config.model_kwargs is not None else {}
        )

        if self.config.temperature is not None:
            generation_config_params["temperature"] = self.config.temperature
        if self.config.max_output_tokens is not None:
            generation_config_params["max_output_tokens"] = self.config.max_output_tokens

        final_sdk_params = generation_config_params if generation_config_params else None

        # TODO: Incorporate system_prompt into user_prompt for Google models
        # Since Google models don't have a direct system prompt parameter,
        # we might need to combine them or use a different approach

        try:
            response = self.client.models.generate_content(
                model=actual_model, contents=user_prompt, generation_config=final_sdk_params
            )

            # Check for blocked prompt
            if (
                hasattr(response, "prompt_feedback")
                and response.prompt_feedback
                and response.prompt_feedback.block_reason
            ):
                logger.warning(f"Google LLM prompt blocked. Reason: {response.prompt_feedback.block_reason}")
                return f"Completion generation failed: Prompt blocked by API (Reason: {response.prompt_feedback.block_reason})"

            # Check for empty response
            if not response.text:
                logger.warning(f"Google LLM returned no text. Response: {response}")
                return "Completion generation failed: No text returned by API."

            return response.text
        except Exception as e:
            logger.error(f"Error communicating with Google Gen AI API: {e}")
            raise LLMError(f"Error communicating with Google Gen AI API: {e}") from e
