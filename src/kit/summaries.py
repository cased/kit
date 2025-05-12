"""Handles code summarization using LLMs."""

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, Union, runtime_checkable

import tiktoken


# Define a Protocol for LLM clients to help with type checking
@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol defining the interface for LLM clients."""

    # This is a structural protocol - any object with compatible methods will be accepted
    pass


# Conditionally import google.genai
try:
    import google.genai as genai
    from google.genai import types as genai_types
except ImportError:
    genai = None  # type: ignore
    genai_types = None  # type: ignore

logger = logging.getLogger(__name__)

# Use TYPE_CHECKING to avoid circular import issues with Repository
if TYPE_CHECKING:
    from kit.repository import Repository


class LLMError(Exception):
    """Custom exception for LLM related errors."""

    pass


class SymbolNotFoundError(Exception):
    """Custom exception for when a symbol (function, class) is not found."""

    pass


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


# todo: make configurable
MAX_CODE_LENGTH_CHARS = 50000  # Max characters for a single function/class summary
MAX_FILE_SUMMARIZE_CHARS = 25000  # Max characters for file content in summarize_file
OPENAI_MAX_PROMPT_TOKENS = 15000  # Max tokens for the prompt to OpenAI


class Summarizer:
    """Provides methods to summarize code using a configured LLM."""

    _tokenizer_cache: Dict[str, Any] = {}  # Cache for tiktoken encoders
    config: Optional[Union[OpenAIConfig, AnthropicConfig, GoogleConfig]]
    repo: "Repository"
    _llm_client: Optional[Any]  # type: ignore

    def _get_tokenizer(self, model_name: str):
        if model_name in self._tokenizer_cache:
            return self._tokenizer_cache[model_name]
        try:
            encoding = tiktoken.encoding_for_model(model_name)
            self._tokenizer_cache[model_name] = encoding
            return encoding
        except KeyError:
            try:
                # Fallback for models not directly in tiktoken.model.MODEL_TO_ENCODING
                encoding = tiktoken.get_encoding("cl100k_base")
                self._tokenizer_cache[model_name] = encoding
                return encoding
            except Exception as e:
                logger.warning(
                    f"Could not load tiktoken encoder for {model_name} due to {e}, token count will be approximate (char count)."
                )
                return None

    def _count_tokens(self, text: str, model_name: Optional[str] = None) -> int:
        """Count the number of tokens in a text string for a given model."""
        if not text:
            return 0

        # Use model from config if available, otherwise use a default
        if model_name is None:
            if self.config is not None and hasattr(self.config, "model"):
                model_name = self.config.model
            else:
                # Default to a common model if no config or model specified
                model_name = "gpt-4o"  # Default fallback

        try:
            # Try to use tiktoken for accurate token counting
            if tiktoken:
                try:
                    if model_name in self._tokenizer_cache:
                        encoder = self._tokenizer_cache[model_name]
                    else:
                        try:
                            encoder = tiktoken.encoding_for_model(model_name)
                        except KeyError:
                            # Model not found, use cl100k_base as fallback
                            encoder = tiktoken.get_encoding("cl100k_base")
                        self._tokenizer_cache[model_name] = encoder

                    return len(encoder.encode(text))
                except Exception as e:
                    logger.warning(f"Error using tiktoken for model {model_name}: {e}")
                    # Fall through to character-based approximation
            else:
                logger.warning(
                    f"No tiktoken encoder found for model {model_name}, token count will be approximate (char count)."
                )
        except NameError:
            # tiktoken not available
            logger.warning("tiktoken not available, token count will be approximate (char count).")

        # Fallback: approximate token count based on characters (4 chars ~= 1 token)
        return len(text) // 4

    def _count_openai_chat_tokens(self, messages: List[Dict[str, str]], model_name: str) -> Optional[int]:
        """Return the number of tokens used by a list of messages for OpenAI chat models."""
        encoding = self._get_tokenizer(model_name)
        if not encoding:
            logger.warning(f"Cannot count OpenAI chat tokens for {model_name}, no tiktoken encoder available.")
            return None

        # Logic adapted from OpenAI cookbook for counting tokens for chat completions
        # See: https://github.com/openai/openai-cookbook/blob/main/examples/how_to_count_tokens_with_tiktoken.ipynb
        if model_name in {
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-16k-0613",
            "gpt-4-0314",
            "gpt-4-32k-0314",
            "gpt-4-0613",
            "gpt-4-32k-0613",
        }:
            tokens_per_message = 3
            tokens_per_name = 1
        elif model_name == "gpt-3.5-turbo-0301":
            tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
            tokens_per_name = -1  # if there's a name, the role is omitted
        elif "gpt-3.5-turbo" in model_name:  # Covers general gpt-3.5-turbo and variants not explicitly listed
            # Defaulting to newer model token counts as a general heuristic
            logger.debug(f"Using token counting parameters for gpt-3.5-turbo-0613 for model {model_name}.")
            tokens_per_message = 3
            tokens_per_name = 1
        elif "gpt-4" in model_name:  # Covers general gpt-4 and variants not explicitly listed
            logger.debug(f"Using token counting parameters for gpt-4-0613 for model {model_name}.")
            tokens_per_message = 3
            tokens_per_name = 1
        else:
            # Fallback for unknown models; this might not be perfectly accurate.
            # Raise an error or use a default if this model is not supported by tiktoken's encoding_for_model
            # For now, using a common default and logging a warning.
            logger.warning(
                f"_count_openai_chat_tokens() may not be accurate for model {model_name}. "
                f"It's not explicitly handled. Using default token counting parameters (3 tokens/message, 1 token/name). "
                f"See OpenAI's documentation for details on your specific model."
            )
            tokens_per_message = 3
            tokens_per_name = 1

        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                if value is None:  # Ensure value is not None before attempting to encode
                    logger.debug(f"Encountered None value for key '{key}' in message, skipping for token counting.")
                    continue
                try:
                    num_tokens += len(encoding.encode(str(value)))  # Ensure value is string
                except Exception as e:
                    # This catch is a safeguard; tiktoken should handle most string inputs.
                    logger.error(f"Could not encode value for token counting: '{str(value)[:50]}...', error: {e}")
                    return None  # Inability to encode part of message means count is unreliable
                if key == "name":
                    num_tokens += tokens_per_name
        num_tokens += (
            3  # every reply is primed with <|start|>assistant<|message|> (approximates assistant's first tokens)
        )
        return num_tokens

    def __init__(
        self,
        repo: "Repository",
        config: Optional[Union[OpenAIConfig, AnthropicConfig, GoogleConfig]] = None,
        llm_client: Optional[Any] = None,
    ):
        """
        Initializes the Summarizer.

        Args:
            repo: The kit.Repository instance containing the code.
            config: LLM configuration (OpenAIConfig, AnthropicConfig, or GoogleConfig).
                    If None, defaults to OpenAIConfig.
            llm_client: Optional pre-initialized LLM client. If None, client will be
                        lazy-loaded on first use based on the config.
        """
        self.repo = repo
        self._llm_client = llm_client  # Store provided llm_client directly
        self.config = config  # Store provided config

        if self._llm_client is None:
            # Only create/setup LLM if a client wasn't directly provided
            if self.config is None:
                # If no config is provided either, default to OpenAIConfig
                # This will raise ValueError if OPENAI_API_KEY is not set.
                self.config = OpenAIConfig()

            if isinstance(self.config, OpenAIConfig):
                try:
                    import openai

                    if self.config.base_url:
                        self._llm_client = openai.OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)
                    else:
                        self._llm_client = openai.OpenAI(api_key=self.config.api_key)
                except ImportError:
                    raise LLMError("OpenAI SDK (openai) not available. Please install it.")
            elif isinstance(self.config, AnthropicConfig):
                try:
                    import anthropic

                    self._llm_client = anthropic.Anthropic(api_key=self.config.api_key)
                except ImportError:
                    raise LLMError("Anthropic SDK (anthropic) not available. Please install it.")
            elif isinstance(self.config, GoogleConfig):
                try:
                    import google.genai as genai

                    self._llm_client = genai.Client(api_key=self.config.api_key)  # Use the new client
                except ImportError:
                    raise LLMError("Google Gen AI SDK (google-genai) not available. Please install it.")
            else:
                # This case implies self.config was set to something unexpected if self._llm_client was None
                # and self.config was also None initially. Or self.config was passed with an invalid type.
                if self.config is not None:  # Only raise if config is of an unsupported type
                    raise TypeError(f"Unsupported LLM configuration type: {type(self.config)}")
                # If self.config is None here, it means OpenAIConfig() failed, but that should raise its own error.
                # Or, it implies a logic flaw if this path is reached with self.config being None.
        # If _llm_client was provided, we assume it's configured and ready.
        # self.config might be None if only llm_client was passed.

    def _get_llm_client(self) -> Any:
        """Lazy loads the appropriate LLM client based on self.config."""
        if self._llm_client is not None:
            return self._llm_client

        try:
            if isinstance(self.config, OpenAIConfig):
                from openai import OpenAI  # Local import for OpenAI client

                if self.config.base_url:
                    client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)
                else:
                    client = OpenAI(api_key=self.config.api_key)
            elif isinstance(self.config, AnthropicConfig):
                from anthropic import Anthropic  # Local import for Anthropic client

                client = Anthropic(api_key=self.config.api_key)  # type: ignore # Different client type
            elif isinstance(self.config, GoogleConfig):
                if genai is None or genai_types is None:
                    raise LLMError(
                        "Google Gen AI SDK (google-genai) is not installed. Please install it to use Google models."
                    )
                # API key is picked up from GOOGLE_API_KEY env var by default if not passed to Client()
                # However, we have it in self.config.api_key, so we pass it explicitly.
                client = genai.Client(api_key=self.config.api_key)  # type: ignore # Different client type
            else:
                # This case should ideally be prevented by the __init__ type check,
                # but as a safeguard:
                raise LLMError(f"Unsupported LLM configuration type: {type(self.config)}")

            self._llm_client = client
            return self._llm_client
        except ImportError as e:
            sdk_name = ""
            if "openai" in str(e).lower():
                sdk_name = "openai"
            elif "anthropic" in str(e).lower():
                sdk_name = "anthropic"
            # google-genai import is handled by genai being None
            if sdk_name:
                raise LLMError(
                    f"{sdk_name.capitalize()} SDK not installed. Please install it to use {sdk_name.capitalize()} models."
                ) from e
            raise  # Re-raise if it's a different import error
        except Exception as e:
            logger.error(f"Error initializing LLM client: {e}")
            raise LLMError(f"Error initializing LLM client: {e}") from e

    def summarize_file(self, file_path: str) -> str:
        """
        Summarizes the content of a single file.

        Args:
            file_path: The path to the file to summarize.

        Returns:
            A string containing the summary of the file.

        Raises:
            FileNotFoundError: If the file_path does not exist.
            LLMError: If there's an error from the LLM API or an empty summary.
        """
        logger.debug(f"Attempting to summarize file: {file_path}")
        abs_file_path = self.repo.get_abs_path(file_path)  # Use get_abs_path

        try:
            file_content = self.repo.get_file_content(abs_file_path)
        except FileNotFoundError:
            # Re-raise to ensure the Summarizer's contract is met
            raise FileNotFoundError(f"File not found via repo: {abs_file_path}")

        if not file_content.strip():
            logger.warning(f"File {abs_file_path} is empty or contains only whitespace. Skipping summary.")
            return ""

        if len(file_content) > MAX_FILE_SUMMARIZE_CHARS:
            logger.warning(
                f"File content for {file_path} ({len(file_content)} chars) is too large for summarization (limit: {MAX_FILE_SUMMARIZE_CHARS})."
            )
            return f"File content too large ({len(file_content)} characters) to summarize with current limits."

        # Max model context is 128000 tokens. Avg ~4 chars/token -> ~512,000 chars for total message.
        # Let's set a threshold for the raw content itself.
        MAX_CHARS_FOR_SUMMARY = 400_000  # Approx 100k tokens
        if len(file_content) > MAX_CHARS_FOR_SUMMARY:
            logger.warning(
                f"File {abs_file_path} content is too large ({len(file_content)} chars) "
                f"to summarize reliably. Skipping."
            )
            # Return a placeholder summary or an empty string
            return f"File content too large ({len(file_content)} characters) to summarize."

        system_prompt_text = "You are an expert assistant skilled in creating concise and informative code summaries."
        user_prompt_text = f"Summarize the following code from the file '{file_path}'. Provide a high-level overview of its purpose, key components, and functionality. Focus on what the code does, not just how it's written. The code is:\n\n```\n{file_content}\n```"

        client = self._get_llm_client()
        summary = ""

        logger.debug(f"System Prompt for {file_path}: {system_prompt_text}")
        logger.debug(f"User Prompt for {file_path} (first 200 chars): {user_prompt_text[:200]}...")
        # Get model name from config if available, otherwise pass None for default
        model_name = self.config.model if self.config is not None and hasattr(self.config, "model") else None
        token_count = self._count_tokens(user_prompt_text, model_name)
        if token_count is not None:
            logger.debug(f"Estimated tokens for user prompt ({file_path}): {token_count}")
        else:
            logger.debug(f"Approximate characters for user prompt ({file_path}): {len(user_prompt_text)}")

        try:
            # If a custom llm_client was provided without a config, use it directly
            if self.config is None:
                # For custom llm_client without config, assume it knows how to handle the prompt
                # This is used in tests with FakeOpenAI
                try:
                    # Try OpenAI-style interface first
                    response = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt_text},
                            {"role": "user", "content": user_prompt_text},
                        ]
                    )
                    summary = response.choices[0].message.content
                except (AttributeError, TypeError) as e:
                    # If that fails, the client might have a different interface
                    logger.warning(f"Custom LLM client doesn't support OpenAI-style interface: {e}")
                    raise LLMError(f"Custom LLM client without config doesn't support expected interface: {e}")
            elif isinstance(self.config, OpenAIConfig):
                messages_for_api = [
                    {"role": "system", "content": system_prompt_text},
                    {"role": "user", "content": user_prompt_text},
                ]
                prompt_token_count = self._count_openai_chat_tokens(messages_for_api, self.config.model)
                if prompt_token_count is not None and prompt_token_count > OPENAI_MAX_PROMPT_TOKENS:
                    summary = f"Summary generation failed: OpenAI prompt too large ({prompt_token_count} tokens). Limit is {OPENAI_MAX_PROMPT_TOKENS} tokens."
                else:
                    response = client.chat.completions.create(
                        model=self.config.model,
                        messages=messages_for_api,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens,
                    )
                    summary = response.choices[0].message.content
                    if response.usage:
                        logger.debug(f"OpenAI API usage for {file_path}: {response.usage}")
            elif isinstance(self.config, AnthropicConfig):
                response = client.messages.create(
                    model=self.config.model,
                    system=system_prompt_text,
                    messages=[{"role": "user", "content": user_prompt_text}],
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )
                summary = response.content[0].text
            elif isinstance(self.config, GoogleConfig):
                if not genai_types:
                    raise LLMError(
                        "Google Gen AI SDK (google-genai) types not available. SDK might not be installed correctly."
                    )

                generation_config_params: Dict[str, Any] = (
                    self.config.model_kwargs.copy() if self.config.model_kwargs is not None else {}
                )

                if self.config.temperature is not None:
                    generation_config_params["temperature"] = self.config.temperature
                if self.config.max_output_tokens is not None:
                    generation_config_params["max_output_tokens"] = self.config.max_output_tokens

                final_sdk_params = generation_config_params if generation_config_params else None

                response = client.models.generate_content(
                    model=self.config.model, contents=user_prompt_text, generation_config=final_sdk_params
                )
                # Check for blocked prompt first
                if (
                    hasattr(response, "prompt_feedback")
                    and response.prompt_feedback
                    and response.prompt_feedback.block_reason
                ):
                    logger.warning(
                        f"Google LLM prompt for file {file_path} blocked. Reason: {response.prompt_feedback.block_reason}"
                    )
                    summary = f"Summary generation failed: Prompt blocked by API (Reason: {response.prompt_feedback.block_reason})"
                elif not response.text:
                    logger.warning(f"Google LLM returned no text for file {file_path}. Response: {response}")
                    summary = "Summary generation failed: No text returned by API."
                else:
                    summary = response.text

            if not summary or not summary.strip():
                logger.warning(f"LLM returned an empty or whitespace-only summary for file {file_path}.")
                raise LLMError(f"LLM returned an empty summary for file {file_path}.")

            logger.debug(f"LLM summary for file {file_path} (first 200 chars): {summary[:200]}...")
            return summary.strip()

        except Exception as e:
            logger.error(f"Error communicating with LLM API for file {file_path}: {e}")
            raise LLMError(f"Error communicating with LLM API: {e}") from e

    def summarize_function(self, file_path: str, function_name: str) -> str:
        """
        Summarizes a specific function within a file.

        Args:
            file_path: The path to the file containing the function.
            function_name: The name of the function to summarize.

        Returns:
            A string containing the summary of the function.

        Raises:
            FileNotFoundError: If the file_path does not exist.
            ValueError: If the function cannot be found in the file.
            LLMError: If there's an error from the LLM API or an empty summary.
        """
        logger.debug(f"Attempting to summarize function: {function_name} in file: {file_path}")

        symbols = self.repo.extract_symbols(file_path)
        function_code = None
        for symbol in symbols:
            # Use node_path if available (more precise), fallback to name
            current_symbol_name = symbol.get("node_path", symbol.get("name"))
            if current_symbol_name == function_name and symbol.get("type", "").upper() in ["FUNCTION", "METHOD"]:
                function_code = symbol.get("code")
                break

        if not function_code:
            raise ValueError(f"Could not find function '{function_name}' in '{file_path}'.")

        # Max model context is 128000 tokens. Avg ~4 chars/token -> ~512,000 chars for total message.
        # Let's set a threshold for the raw content itself.
        MAX_CHARS_FOR_SUMMARY = 400_000  # Approx 100k tokens
        if len(function_code) > MAX_CHARS_FOR_SUMMARY:
            logger.warning(
                f"Function {function_name} in file {file_path} content is too large ({len(function_code)} chars) "
                f"to summarize reliably. Skipping."
            )
            return f"Function content too large ({len(function_code)} characters) to summarize."

        system_prompt_text = "You are an expert assistant skilled in creating concise code summaries for functions."
        user_prompt_text = f"Summarize the following function named '{function_name}' from the file '{file_path}'. Describe its purpose, parameters, and return value. The function definition is:\n\n```\n{function_code}\n```"

        client = self._get_llm_client()
        summary = ""

        logger.debug(f"System Prompt for {function_name} in {file_path}: {system_prompt_text}")
        logger.debug(f"User Prompt for {function_name} in {file_path} (first 200 chars): {user_prompt_text[:200]}...")
        # Get model name from config if available, otherwise pass None for default
        model_name = self.config.model if self.config is not None and hasattr(self.config, "model") else None
        token_count = self._count_tokens(user_prompt_text, model_name)
        logger.debug(f"Token count for {function_name} in {file_path}: {token_count}")

        try:
            # If a custom llm_client was provided without a config, use it directly
            if self.config is None:
                # For custom llm_client without config, assume it knows how to handle the prompt
                # This is used in tests with FakeOpenAI
                try:
                    # Try OpenAI-style interface first
                    response = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt_text},
                            {"role": "user", "content": user_prompt_text},
                        ]
                    )
                    summary = response.choices[0].message.content
                except (AttributeError, TypeError) as e:
                    # If that fails, the client might have a different interface
                    # In a real implementation, you'd need more robust handling here
                    logger.warning(f"Custom LLM client doesn't support OpenAI-style interface: {e}")
                    raise LLMError(f"Custom LLM client without config doesn't support expected interface: {e}")
            elif isinstance(self.config, OpenAIConfig):
                messages_for_api = [
                    {"role": "system", "content": system_prompt_text},
                    {"role": "user", "content": user_prompt_text},
                ]
                prompt_token_count = self._count_openai_chat_tokens(messages_for_api, self.config.model)
                if prompt_token_count is not None and prompt_token_count > OPENAI_MAX_PROMPT_TOKENS:
                    summary = f"Summary generation failed: OpenAI prompt too large ({prompt_token_count} tokens). Limit is {OPENAI_MAX_PROMPT_TOKENS} tokens."
                else:
                    response = client.chat.completions.create(
                        model=self.config.model,
                        messages=messages_for_api,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens,
                    )
                    summary = response.choices[0].message.content
                    if response.usage:
                        logger.debug(f"OpenAI API usage for {function_name} in {file_path}: {response.usage}")
            elif isinstance(self.config, AnthropicConfig):
                response = client.messages.create(
                    model=self.config.model,
                    system=system_prompt_text,
                    messages=[{"role": "user", "content": user_prompt_text}],
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )
                summary = response.content[0].text
                # Anthropic usage might be in response.usage (confirm API docs)
                # Example: logger.debug(f"Anthropic API usage for {function_name} in {file_path}: {response.usage}")
            elif isinstance(self.config, GoogleConfig):
                if not genai_types:
                    raise LLMError(
                        "Google Gen AI SDK (google-genai) types not available. SDK might not be installed correctly."
                    )

                generation_config_params: Dict[str, Any] = (
                    self.config.model_kwargs.copy() if self.config.model_kwargs is not None else {}
                )

                if self.config.temperature is not None:
                    generation_config_params["temperature"] = self.config.temperature
                if self.config.max_output_tokens is not None:
                    generation_config_params["max_output_tokens"] = self.config.max_output_tokens

                final_sdk_params = generation_config_params if generation_config_params else None

                response = client.models.generate_content(
                    model=self.config.model, contents=user_prompt_text, generation_config=final_sdk_params
                )
                if (
                    hasattr(response, "prompt_feedback")
                    and response.prompt_feedback
                    and response.prompt_feedback.block_reason
                ):
                    logger.warning(
                        f"Google LLM prompt for {function_name} in {file_path} blocked. Reason: {response.prompt_feedback.block_reason}"
                    )
                    summary = f"Summary generation failed: Prompt blocked by API (Reason: {response.prompt_feedback.block_reason})"
                elif not response.text:
                    logger.warning(
                        f"Google LLM returned no text for {function_name} in {file_path}. Response: {response}"
                    )
                    summary = "Summary generation failed: No text returned by API."
                else:
                    summary = response.text
            else:
                # This should never happen with our current logic, but as a safeguard
                raise LLMError(f"Unsupported LLM configuration type: {type(self.config) if self.config else None}")

            if not summary or not summary.strip():
                logger.warning(
                    f"LLM returned an empty or whitespace-only summary for function {function_name} in {file_path}."
                )
                raise LLMError(f"LLM returned an empty summary for function {function_name}.")

            logger.debug(f"LLM summary for {function_name} in {file_path} (first 200 chars): {summary[:200]}...")
            return summary.strip()

        except Exception as e:
            logger.error(f"Error communicating with LLM API for function {function_name} in {file_path}: {e}")
            raise LLMError(f"Error communicating with LLM API for function {function_name}: {e}") from e

    def summarize_class(self, file_path: str, class_name: str) -> str:
        """
        Summarizes a specific class within a file.

        Args:
            file_path: The path to the file containing the class.
            class_name: The name of the class to summarize.

        Returns:
            A string containing the summary of the class.

        Raises:
            FileNotFoundError: If the file_path does not exist.
            ValueError: If the class cannot be found in the file.
            LLMError: If there's an error from the LLM API or an empty summary.
        """
        logger.debug(f"Attempting to summarize class: {class_name} in file: {file_path}")

        symbols = self.repo.extract_symbols(file_path)
        class_code = None
        for symbol in symbols:
            # Use node_path if available (more precise), fallback to name
            current_symbol_name = symbol.get("node_path", symbol.get("name"))
            if current_symbol_name == class_name and symbol.get("type", "").upper() == "CLASS":
                class_code = symbol.get("code")
                break

        if not class_code:
            raise ValueError(f"Could not find class '{class_name}' in '{file_path}'.")

        # Max model context is 128000 tokens. Avg ~4 chars/token -> ~512,000 chars for total message.
        # Let's set a threshold for the raw content itself.
        MAX_CHARS_FOR_SUMMARY = 400_000  # Approx 100k tokens
        if len(class_code) > MAX_CHARS_FOR_SUMMARY:
            logger.warning(
                f"Class {class_name} in file {file_path} content is too large ({len(class_code)} chars) "
                f"to summarize reliably. Skipping."
            )
            return f"Class content too large ({len(class_code)} characters) to summarize."

        system_prompt_text = "You are an expert assistant skilled in creating concise code summaries for classes."
        user_prompt_text = f"Summarize the following class named '{class_name}' from the file '{file_path}'. Describe its purpose, key attributes, and main methods. The class definition is:\n\n```\n{class_code}\n```"

        client = self._get_llm_client()
        summary = ""

        logger.debug(f"System Prompt for {class_name} in {file_path}: {system_prompt_text}")
        logger.debug(f"User Prompt for {class_name} (first 200 chars): {user_prompt_text[:200]}...")
        # Get model name from config if available, otherwise pass None for default
        model_name = self.config.model if self.config is not None and hasattr(self.config, "model") else None
        token_count = self._count_tokens(user_prompt_text, model_name)
        logger.debug(f"Token count for {class_name} in {file_path}: {token_count}")

        try:
            # If a custom llm_client was provided without a config, use it directly
            if self.config is None:
                # For custom llm_client without config, assume it knows how to handle the prompt
                # This is used in tests with FakeOpenAI
                try:
                    # Try OpenAI-style interface first
                    response = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt_text},
                            {"role": "user", "content": user_prompt_text},
                        ]
                    )
                    summary = response.choices[0].message.content
                except (AttributeError, TypeError) as e:
                    logger.warning(f"Custom LLM client doesn't support OpenAI-style interface: {e}")
                    raise LLMError(f"Custom LLM client without config doesn't support expected interface: {e}")
            elif isinstance(self.config, OpenAIConfig):
                messages_for_api = [
                    {"role": "system", "content": system_prompt_text},
                    {"role": "user", "content": user_prompt_text},
                ]
                prompt_token_count = self._count_openai_chat_tokens(messages_for_api, self.config.model)
                if prompt_token_count is not None and prompt_token_count > OPENAI_MAX_PROMPT_TOKENS:
                    summary = f"Summary generation failed: OpenAI prompt too large ({prompt_token_count} tokens). Limit is {OPENAI_MAX_PROMPT_TOKENS} tokens."
                else:
                    response = client.chat.completions.create(
                        model=self.config.model,
                        messages=messages_for_api,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens,
                    )
                    summary = response.choices[0].message.content
                    if response.usage:
                        logger.debug(f"OpenAI API usage for {class_name} in {file_path}: {response.usage}")
            elif isinstance(self.config, AnthropicConfig):
                response = client.messages.create(
                    model=self.config.model,
                    system=system_prompt_text,
                    messages=[{"role": "user", "content": user_prompt_text}],
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )
                summary = response.content[0].text
                # Anthropic usage might be in response.usage (confirm API docs)
                # Example: logger.debug(f"Anthropic API usage for {class_name} in {file_path}: {response.usage}")
            elif isinstance(self.config, GoogleConfig):
                if not genai_types:
                    raise LLMError(
                        "Google Gen AI SDK (google-genai) types not available. SDK might not be installed correctly."
                    )

                generation_config_params: Dict[str, Any] = (
                    self.config.model_kwargs.copy() if self.config.model_kwargs is not None else {}
                )

                if self.config.temperature is not None:
                    generation_config_params["temperature"] = self.config.temperature
                if self.config.max_output_tokens is not None:
                    generation_config_params["max_output_tokens"] = self.config.max_output_tokens

                final_sdk_params = generation_config_params if generation_config_params else None

                response = client.models.generate_content(
                    model=self.config.model, contents=user_prompt_text, generation_config=final_sdk_params
                )
                if (
                    hasattr(response, "prompt_feedback")
                    and response.prompt_feedback
                    and response.prompt_feedback.block_reason
                ):
                    logger.warning(
                        f"Google LLM prompt for {class_name} in {file_path} blocked. Reason: {response.prompt_feedback.block_reason}"
                    )
                    summary = f"Summary generation failed: Prompt blocked by API (Reason: {response.prompt_feedback.block_reason})"
                elif not response.text:
                    logger.warning(f"Google LLM returned no text for {class_name} in {file_path}. Response: {response}")
                    summary = "Summary generation failed: No text returned by API."
                else:
                    summary = response.text
            else:
                # This should never happen with our current logic, but as a safeguard
                raise LLMError(f"Unsupported LLM configuration type: {type(self.config) if self.config else None}")

            if not summary or not summary.strip():
                logger.warning(
                    f"LLM returned an empty or whitespace-only summary for class {class_name} in {file_path}."
                )
                raise LLMError(f"LLM returned an empty summary for class {class_name}.")

            logger.debug(f"LLM summary for {class_name} in {file_path} (first 200 chars): {summary[:200]}...")
            return summary.strip()

        except Exception as e:
            logger.error(f"Error communicating with LLM API for class {class_name} in {file_path}: {e}")
            raise LLMError(f"Error communicating with LLM API for class {class_name}: {e}") from e
