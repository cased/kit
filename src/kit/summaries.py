"""Handles code summarization using LLMs."""

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Any, Union
import logging

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


class Summarizer:
    """Provides methods to summarize code using a configured LLM."""

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
        abs_file_path = self.repo.get_abs_path(file_path)
        
        try:
            file_content = self.repo.get_file_content(abs_file_path)
        except FileNotFoundError:
            # Re-raise to ensure the Summarizer's contract is met
            raise FileNotFoundError(f"File not found via repo: {abs_file_path}")

        if not file_content.strip():
            logger.warning(f"File {abs_file_path} is empty or contains only whitespace. Skipping summary.")
            return ""

        system_prompt_text = "You are an expert assistant skilled in creating concise and informative code summaries."
        user_prompt_text = f"Summarize the following code from the file '{file_path}'. Provide a high-level overview of its purpose, key components, and functionality. Focus on what the code does, not just how it's written. The code is:\n\n```\n{file_content}\n```"

        client = self._get_llm_client()
        summary = ""

        try:
            if isinstance(self.config, OpenAIConfig):
                response = client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_prompt_text},
                        {"role": "user", "content": user_prompt_text}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                summary = response.choices[0].message.content
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
            elif isinstance(self.config, GoogleConfig):
                full_prompt = f"{system_prompt_text}\n\n{user_prompt_text}"
                # client is already a GenerativeModel instance here
                response = client.generate_content(
                    contents=[full_prompt],
                    generation_config={
                        'temperature': self.config.temperature,
                        'max_output_tokens': self.config.max_output_tokens,
                        'candidate_count': 1
                    }
                )
                summary = response.text

            if not summary:
                  raise LLMError("LLM returned an empty summary.")
            return summary.strip()
        except Exception as e:
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
        function_code = self.repo.get_symbol_text(file_path, function_name)
        if not function_code:
            raise ValueError(f"Could not find function '{function_name}' in '{file_path}'.")

        system_prompt_text = "You are an expert assistant skilled in creating concise code summaries for functions."
        user_prompt_text = f"Summarize the following Python function named '{function_name}' from the file '{file_path}'. Describe its purpose, parameters, and return value. The function code is:\n\n```python\n{function_code}\n```"

        client = self._get_llm_client()
        summary = ""

        try:
            if isinstance(self.config, OpenAIConfig):
                response = client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_prompt_text},
                        {"role": "user", "content": user_prompt_text}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                summary = response.choices[0].message.content
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
            elif isinstance(self.config, GoogleConfig):
                full_prompt = f"{system_prompt_text}\n\n{user_prompt_text}"
                response = client.generate_content(
                    contents=[full_prompt],
                    generation_config={
                        'temperature': self.config.temperature,
                        'max_output_tokens': self.config.max_output_tokens,
                        'candidate_count': 1
                    }
                )
                summary = response.text

            if not summary:
                  raise LLMError(f"LLM returned an empty summary for function {function_name}.")
            return summary.strip()
        except Exception as e:
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
        class_code = self.repo.get_symbol_text(file_path, class_name)
        if not class_code:
            raise ValueError(f"Could not find class '{class_name}' in '{file_path}'.")

        system_prompt_text = "You are an expert assistant skilled in creating concise code summaries for classes."
        user_prompt_text = f"Summarize the following Python class named '{class_name}' from the file '{file_path}'. Describe its purpose, key attributes, and main methods. The class code is:\n\n```python\n{class_code}\n```"
        
        client = self._get_llm_client()
        summary = ""

        try:
            if isinstance(self.config, OpenAIConfig):
                response = client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_prompt_text},
                        {"role": "user", "content": user_prompt_text}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                summary = response.choices[0].message.content
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
            elif isinstance(self.config, GoogleConfig):
                full_prompt = f"{system_prompt_text}\n\n{user_prompt_text}"
                response = client.generate_content(
                    contents=[full_prompt],
                    generation_config={
                        'temperature': self.config.temperature,
                        'max_output_tokens': self.config.max_output_tokens,
                        'candidate_count': 1
                    }
                )
                summary = response.text

            if not summary:
                  raise LLMError(f"LLM returned an empty summary for class {class_name}.")
            return summary.strip()
        except Exception as e:
            raise LLMError(f"Error communicating with LLM API for class {class_name}: {e}") from e
