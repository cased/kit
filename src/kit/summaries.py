"""Handles code summarization using LLMs."""

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Any, Union, Dict, List
import logging
import tiktoken

logger = logging.getLogger(__name__)

# Use TYPE_CHECKING to avoid circular import issues with Repository
if TYPE_CHECKING:
    from kit.repository import Repository
    from kit.repo_mapper import RepoMapper # For type hinting


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

    def __post_init__(self):
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Set OPENAI_API_KEY environment variable or pass api_key directly."
            )


@dataclass
class AnthropicConfig:
    """Configuration for Anthropic API access."""
    api_key: Optional[str] = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY"))
    model: str = "claude-3-opus-20240229"
    temperature: float = 0.7
    max_tokens: int = 1000 # Corresponds to Anthropic's max_tokens_to_sample

    def __post_init__(self):
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key directly."
            )


@dataclass
class GoogleConfig:
    """Configuration for Google Generative AI API access."""
    api_key: Optional[str] = field(default_factory=lambda: os.environ.get("GOOGLE_API_KEY"))
    model: str = "gemini-1.5-pro-latest"
    temperature: Optional[float] = 0.7
    max_output_tokens: Optional[int] = 1000 # Corresponds to Gemini's max_output_tokens

    def __post_init__(self):
        if not self.api_key:
            raise ValueError(
                "Google API key not found. "
                "Set GOOGLE_API_KEY environment variable or pass api_key directly."
            )


MAX_CODE_LENGTH_CHARS = 50000  # Max characters for a single function/class summary
MAX_FILE_SUMMARIZE_CHARS = 25000 # Max characters for file content in summarize_file
OPENAI_MAX_PROMPT_TOKENS = 15000 # Max tokens for the prompt to OpenAI

class Summarizer:
    """Provides methods to summarize code using a configured LLM."""

    _tokenizer_cache: Dict[str, Any] = {} # Cache for tiktoken encoders

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
                # For gpt-3.5-turbo and gpt-4 series, cl100k_base is standard.
                # Adjust if other model families need different fallback encodings.
                if "gpt-4" in model_name or "gpt-3.5-turbo" in model_name:
                    encoding = tiktoken.get_encoding("cl100k_base")
                    self._tokenizer_cache[model_name] = encoding
                    return encoding
                else:
                    logger.warning(f"No tiktoken encoder found for model {model_name}, token count will be approximate (char count).")
                    return None
            except Exception as e:
                logger.warning(f"Could not load tiktoken encoder for {model_name} due to {e}, token count will be approximate (char count).")
                return None

    def _count_tokens(self, text: str, model_name: str) -> Optional[int]:
        tokenizer = self._get_tokenizer(model_name)
        if tokenizer:
            return len(tokenizer.encode(text))
        return None # Indicates token count could not be determined

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
        elif "gpt-3.5-turbo" in model_name: # Covers general gpt-3.5-turbo and variants not explicitly listed
            # Defaulting to newer model token counts as a general heuristic
            logger.debug(f"Using token counting parameters for gpt-3.5-turbo-0613 for model {model_name}.")
            tokens_per_message = 3
            tokens_per_name = 1
        elif "gpt-4" in model_name: # Covers general gpt-4 and variants not explicitly listed
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
                if value is None: # Ensure value is not None before attempting to encode
                    logger.debug(f"Encountered None value for key '{key}' in message, skipping for token counting.")
                    continue
                try:
                    num_tokens += len(encoding.encode(str(value))) # Ensure value is string
                except Exception as e:
                    # This catch is a safeguard; tiktoken should handle most string inputs.
                    logger.error(f"Could not encode value for token counting: '{str(value)[:50]}...', error: {e}")
                    return None # Inability to encode part of message means count is unreliable
                if key == "name":
                    num_tokens += tokens_per_name
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|> (approximates assistant's first tokens)
        return num_tokens

    def __init__(self, repo: 'Repository', 
                 config: Optional[Union[OpenAIConfig, AnthropicConfig, GoogleConfig]] = None, 
                 llm_client: Optional[Any] = None):
        """
        Initializes the Summarizer.

        Args:
            repo: The kit.Repository instance containing the code.
            config: LLM configuration (OpenAIConfig, AnthropicConfig, or GoogleConfig).
                    Defaults to OpenAIConfig loading from environment variables if None.
            llm_client: Optional pre-configured/mock client for testing.
        """
        self.repo = repo
        
        if config is None:
            # Default to OpenAI if no config is provided.
            self.config = OpenAIConfig()
        else:
            self.config = config
            
        self._llm_client = llm_client # Allow injecting a pre-configured/mock client

        if not isinstance(self.config, (OpenAIConfig, AnthropicConfig, GoogleConfig)):
            raise TypeError(
                "Unsupported LLM configuration type. "
                "Expected OpenAIConfig, AnthropicConfig, or GoogleConfig."
            )

    def _get_llm_client(self):
        """Lazy loads the appropriate LLM client based on self.config."""
        if self._llm_client is not None:
            return self._llm_client

        if isinstance(self.config, OpenAIConfig):
            try:
                from openai import OpenAI
            except ImportError as e:
                raise ImportError(
                    "OpenAI client not found. Install with 'pip install kit[openai]' or 'pip install openai'"
                ) from e
            self._llm_client = OpenAI(api_key=self.config.api_key)
        
        elif isinstance(self.config, AnthropicConfig):
            try:
                from anthropic import Anthropic
            except ImportError as e:
                raise ImportError(
                    "Anthropic client not found. Install with 'pip install kit[anthropic]' or 'pip install anthropic'"
                ) from e
            self._llm_client = Anthropic(api_key=self.config.api_key)
            
        elif isinstance(self.config, GoogleConfig):
            try:
                import google.generativeai as genai
            except ImportError as e:
                raise ImportError(
                    "Google client not found. Install with 'pip install kit[google]' or 'pip install google-generativeai'"
                ) from e
            genai.configure(api_key=self.config.api_key)
            self._llm_client = genai.GenerativeModel(self.config.model) # Corrected instantiation
        else:
            raise TypeError(f"Unsupported LLM configuration: {type(self.config)}")
            
        return self._llm_client

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
        abs_file_path = str(self.repo.local_path / file_path)
        
        try:
            file_content = self.repo.get_file_content(abs_file_path)
        except FileNotFoundError:
            # Re-raise to ensure the Summarizer's contract is met
            raise FileNotFoundError(f"File not found via repo: {abs_file_path}")

        if not file_content.strip():
            logger.warning(f"File {abs_file_path} is empty or contains only whitespace. Skipping summary.")
            return ""

        if len(file_content) > MAX_FILE_SUMMARIZE_CHARS:
            logger.warning(f"File content for {file_path} ({len(file_content)} chars) is too large for summarization (limit: {MAX_FILE_SUMMARIZE_CHARS}).")
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
        token_count = self._count_tokens(user_prompt_text, self.config.model)
        if token_count is not None:
            logger.debug(f"Estimated tokens for user prompt ({file_path}): {token_count}")
        else:
            logger.debug(f"Approximate characters for user prompt ({file_path}): {len(user_prompt_text)}")

        try:
            if isinstance(self.config, OpenAIConfig):
                messages_for_api = [
                    {"role": "system", "content": system_prompt_text},
                    {"role": "user", "content": user_prompt_text}
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
                    messages=[
                        {"role": "user", "content": user_prompt_text}
                    ],
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )
                summary = response.content[0].text
                # Anthropic usage might be in response.usage (confirm API docs)
                # Example: logger.debug(f"Anthropic API usage for {file_path}: {response.usage}")
            elif isinstance(self.config, GoogleConfig):
                response = client.generate_content(
                    user_prompt_text,
                    generation_config=genai.types.GenerationConfig(
                        candidate_count=1,
                        temperature=self.config.temperature,
                        max_output_tokens=self.config.max_output_tokens
                    )
                )
                try:
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        logger.warning(f"Google LLM prompt for {file_path} blocked. Reason: {response.prompt_feedback.block_reason}")
                        summary = f"Summary generation failed: Prompt blocked by API (Reason: {response.prompt_feedback.block_reason})"
                    elif not response.candidates:
                        logger.warning(f"Google LLM returned no candidates for {file_path}.")
                        summary = "Summary generation failed: No candidates returned by API."
                    else:
                        summary = response.candidates[0].content.parts[0].text
                except (IndexError, AttributeError) as e_parse:
                    logger.warning(f"Error parsing Google LLM response for {file_path}: {e_parse}. Response: {response}")
                    summary = f"Summary generation failed: Error parsing API response."
                # Google API doesn't typically return token counts in the same way by default in simple response.text

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
        user_prompt_text = f"Summarize the following function named '{function_name}' from the file '{file_path}'. Describe its purpose, parameters, and return value. The function code is:\n\n```\n{function_code}\n```"

        client = self._get_llm_client()
        summary = ""

        logger.debug(f"System Prompt for {function_name} in {file_path}: {system_prompt_text}")
        logger.debug(f"User Prompt for {function_name} (first 200 chars): {user_prompt_text[:200]}...")
        token_count = self._count_tokens(user_prompt_text, self.config.model)
        if token_count is not None:
            logger.debug(f"Estimated tokens for user prompt ({function_name} in {file_path}): {token_count}")
        else:
            logger.debug(f"Approximate characters for user prompt ({function_name} in {file_path}): {len(user_prompt_text)}")

        try:
            if isinstance(self.config, OpenAIConfig):
                messages_for_api = [
                    {"role": "system", "content": system_prompt_text},
                    {"role": "user", "content": user_prompt_text}
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
                    messages=[
                        {"role": "user", "content": user_prompt_text}
                    ],
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )
                summary = response.content[0].text
                # logger.debug(f"Anthropic API usage for {function_name} in {file_path}: {response.usage}")
            elif isinstance(self.config, GoogleConfig):
                response = client.generate_content(
                    user_prompt_text,
                    generation_config=genai.types.GenerationConfig(
                        candidate_count=1,
                        temperature=self.config.temperature,
                        max_output_tokens=self.config.max_output_tokens
                    )
                )
                try:
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        logger.warning(f"Google LLM prompt for {function_name} in {file_path} blocked. Reason: {response.prompt_feedback.block_reason}")
                        summary = f"Summary generation failed: Prompt blocked by API (Reason: {response.prompt_feedback.block_reason})"
                    elif not response.candidates:
                        logger.warning(f"Google LLM returned no candidates for {function_name} in {file_path}.")
                        summary = "Summary generation failed: No candidates returned by API."
                    else:
                        summary = response.candidates[0].content.parts[0].text
                except (IndexError, AttributeError) as e_parse:
                    logger.warning(f"Error parsing Google LLM response for {function_name} in {file_path}: {e_parse}. Response: {response}")
                    summary = f"Summary generation failed: Error parsing API response."

            if not summary or not summary.strip():
                logger.warning(f"LLM returned an empty or whitespace-only summary for function {function_name} in {file_path}.")
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
        token_count = self._count_tokens(user_prompt_text, self.config.model)
        if token_count is not None:
            logger.debug(f"Estimated tokens for user prompt ({class_name} in {file_path}): {token_count}")
        else:
            logger.debug(f"Approximate characters for user prompt ({class_name} in {file_path}): {len(user_prompt_text)}")

        try:
            if isinstance(self.config, OpenAIConfig):
                messages_for_api = [
                    {"role": "system", "content": system_prompt_text},
                    {"role": "user", "content": user_prompt_text}
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
                    messages=[
                        {"role": "user", "content": user_prompt_text}
                    ],
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )
                summary = response.content[0].text
                # logger.debug(f"Anthropic API usage for {class_name} in {file_path}: {response.usage}")
            elif isinstance(self.config, GoogleConfig):
                response = client.generate_content(
                    user_prompt_text,
                    generation_config=genai.types.GenerationConfig(
                        candidate_count=1,
                        temperature=self.config.temperature,
                        max_output_tokens=self.config.max_output_tokens # type: ignore
                    )
                )
                try:
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        logger.warning(f"Google LLM prompt for {class_name} in {file_path} blocked. Reason: {response.prompt_feedback.block_reason}")
                        summary = f"Summary generation failed: Prompt blocked by API (Reason: {response.prompt_feedback.block_reason})"
                    elif not response.candidates:
                        logger.warning(f"Google LLM returned no candidates for {class_name} in {file_path}.")
                        summary = "Summary generation failed: No candidates returned by API."
                    else:
                        summary = response.candidates[0].content.parts[0].text
                except (IndexError, AttributeError) as e_parse:
                    logger.warning(f"Error parsing Google LLM response for {class_name} in {file_path}: {e_parse}. Response: {response}")
                    summary = f"Summary generation failed: Error parsing API response."
            
            if not summary or not summary.strip():
                logger.warning(f"LLM returned an empty or whitespace-only summary for class {class_name} in {file_path}.")
                raise LLMError(f"LLM returned an empty summary for class {class_name}.")
            
            logger.debug(f"LLM summary for {class_name} in {file_path} (first 200 chars): {summary[:200]}...")
            return summary.strip()

        except Exception as e:
            logger.error(f"Error communicating with LLM API for class {class_name} in {file_path}: {e}")
            raise LLMError(f"Error communicating with LLM API for class {class_name}: {e}") from e
