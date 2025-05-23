"""Handles code summarization using LLMs."""

import logging
from typing import TYPE_CHECKING, Any, Optional, Union

from kit.models.base import LLMError
from kit.models.config import AnthropicConfig, GoogleConfig, OpenAIConfig
from kit.models.llm_client import LLMClient
from kit.models.llm_utils import count_tokens

logger = logging.getLogger(__name__)

# Use TYPE_CHECKING to avoid circular import issues with Repository
if TYPE_CHECKING:
    from kit.repository import Repository


class SymbolNotFoundError(Exception):
    """Custom exception for when a symbol (function, class) is not found."""

    pass


# todo: make configurable
MAX_CODE_LENGTH_CHARS = 50000  # Max characters for a single function/class summary
MAX_FILE_SUMMARIZE_CHARS = 25000  # Max characters for file content in summarize_file


class Summarizer:
    """Provides methods to summarize code using a configured LLM."""

    repo: "Repository"
    _llm_client: LLMClient
    config: Optional[Union[OpenAIConfig, AnthropicConfig, GoogleConfig]]

    def __init__(
        self,
        repo: "Repository",
        config: Union[OpenAIConfig, AnthropicConfig, GoogleConfig],
    ):
        """
        Initializes the Summarizer.

        Args:
            repo: The kit.Repository instance containing the code.
            config: LLM configuration (OpenAIConfig, AnthropicConfig, or GoogleConfig).
                    This is required to specify which LLM provider to use.

        Raises:
            TypeError: If config is not provided or has an unsupported type.
        """
        self.repo = repo
        self.config = config

        # Create LLM client using factory method
        self._llm_client = LLMClient.create_client(config)

    def _get_llm_client(self) -> Any:
        """Returns the LLM client.

        This method is maintained for backward compatibility with tests.
        """
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

        # Get model name from config if available, otherwise pass None for default
        model_name = self.config.model if self.config is not None and hasattr(self.config, "model") else None
        token_count = count_tokens(user_prompt_text, model_name)

        if token_count is not None:
            logger.debug(f"Estimated tokens for user prompt ({file_path}): {token_count}")
        else:
            logger.debug(f"Approximate characters for user prompt ({file_path}): {len(user_prompt_text)}")

        try:
            # Generate the summary using the LLM client
            summary = self._llm_client.generate_completion(system_prompt_text, user_prompt_text, model_name)

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

        # Get model name from config if available, otherwise pass None for default
        model_name = self.config.model if self.config is not None and hasattr(self.config, "model") else None
        token_count = count_tokens(user_prompt_text, model_name)
        logger.debug(f"Token count for {function_name} in {file_path}: {token_count}")

        try:
            # Generate the summary using the LLM client
            summary = self._llm_client.generate_completion(system_prompt_text, user_prompt_text, model_name)

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

        # Get model name from config if available, otherwise pass None for default
        model_name = self.config.model if self.config is not None and hasattr(self.config, "model") else None
        token_count = count_tokens(user_prompt_text, model_name)
        logger.debug(f"Token count for {class_name} in {file_path}: {token_count}")

        try:
            # Generate the summary using the LLM client
            summary = self._llm_client.generate_completion(system_prompt_text, user_prompt_text, model_name)

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
