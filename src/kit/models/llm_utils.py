"""Utilities for working with LLMs."""

import logging
from typing import Any, Dict, List, Optional

import tiktoken

logger = logging.getLogger(__name__)

# Cache for tiktoken encoders
_tokenizer_cache: Dict[str, Any] = {}


def get_tokenizer(model_name: str):
    """Get a tokenizer for a specific model.

    Args:
        model_name: The name of the model to get a tokenizer for.

    Returns:
        A tokenizer for the specified model, or None if no tokenizer is available.
    """
    if model_name in _tokenizer_cache:
        return _tokenizer_cache[model_name]
    try:
        encoding = tiktoken.encoding_for_model(model_name)
        _tokenizer_cache[model_name] = encoding
        return encoding
    except KeyError:
        try:
            # Fallback for models not directly in tiktoken.model.MODEL_TO_ENCODING
            encoding = tiktoken.get_encoding("cl100k_base")
            _tokenizer_cache[model_name] = encoding
            return encoding
        except Exception as e:
            logger.warning(
                f"Could not load tiktoken encoder for {model_name} due to {e}, token count will be approximate (char count)."
            )
            return None


def count_tokens(text: str, model_name: Optional[str] = None) -> int:
    """Count the number of tokens in a text string for a given model.

    Args:
        text: The text to count tokens for.
        model_name: The name of the model to count tokens for. If None, defaults to "gpt-4o".

    Returns:
        The number of tokens in the text.
    """
    if not text:
        return 0

    # Use a default model if none specified
    if model_name is None:
        model_name = "gpt-4o"  # Default fallback

    try:
        # Try to use tiktoken for accurate token counting
        if tiktoken:
            try:
                if model_name in _tokenizer_cache:
                    encoder = _tokenizer_cache[model_name]
                else:
                    try:
                        encoder = tiktoken.encoding_for_model(model_name)
                    except KeyError:
                        # Model not found, use cl100k_base as fallback
                        encoder = tiktoken.get_encoding("cl100k_base")
                    _tokenizer_cache[model_name] = encoder

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


def count_openai_chat_tokens(messages: List[Dict[str, str]], model_name: str) -> Optional[int]:
    """Return the number of tokens used by a list of messages for OpenAI chat models.

    Args:
        messages: A list of messages to count tokens for.
        model_name: The name of the model to count tokens for.

    Returns:
        The number of tokens in the messages, or None if the tokens could not be counted.
    """
    encoding = get_tokenizer(model_name)
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
        logger.warning(
            f"count_openai_chat_tokens() may not be accurate for model {model_name}. "
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
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|> (approximates assistant's first tokens)
    return num_tokens
