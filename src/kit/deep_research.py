"""Deep Research - Simple LLM prompting for comprehensive answers."""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Union

from kit.summaries import (
    AnthropicConfig,
    GoogleConfig,
    LLMError,
    OllamaConfig,
    OpenAIConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    """Result from deep research."""

    query: str
    answer: str
    execution_time: float
    model: str


class DeepResearch:
    """LLM-based research for comprehensive answers."""

    def __init__(self, config: Optional[Union[OpenAIConfig, AnthropicConfig, GoogleConfig, OllamaConfig]] = None):
        """Initialize with LLM config."""
        self.config = config
        self._llm_client = None
        if config:
            self._init_llm_client()

    def _init_llm_client(self):
        """Initialize the LLM client based on config."""
        if isinstance(self.config, OpenAIConfig):
            try:
                from openai import OpenAI

                self._llm_client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)
            except ImportError:
                raise LLMError("OpenAI library not installed. Run: pip install openai")

        elif isinstance(self.config, AnthropicConfig):
            try:
                import anthropic

                self._llm_client = anthropic.Anthropic(api_key=self.config.api_key)
            except ImportError:
                raise LLMError("Anthropic library not installed. Run: pip install anthropic")

        elif isinstance(self.config, GoogleConfig):
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.config.api_key)
                self._llm_client = genai.GenerativeModel(self.config.model)
            except ImportError:
                raise LLMError("Google GenAI library not installed. Run: pip install google-generativeai")

        elif isinstance(self.config, OllamaConfig):
            self._llm_client = "ollama"

    def research(self, query: str) -> ResearchResult:
        """
        Perform research by prompting an LLM for a comprehensive answer.

        Args:
            query: What you want to know

        Returns:
            The LLM's comprehensive answer
        """
        start_time = time.time()

        if not self.config or not self._llm_client:
            raise LLMError("No LLM configuration provided")

        system_prompt = "You are an expert assistant skilled in providing comprehensive, well-researched answers."
        user_prompt = f"""Answer this question comprehensively:

{query}

Provide:
1. A clear, direct answer
2. Important context and nuances
3. Practical examples where relevant
4. Common pitfalls or considerations
5. Recommended next steps

Be thorough but concise. Focus on accuracy and usefulness."""

        try:
            if isinstance(self.config, OpenAIConfig):
                # GPT-5 models use max_completion_tokens instead of max_tokens
                completion_params = {
                    "model": self.config.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                }
                if "gpt-5" in self.config.model.lower():
                    completion_params["max_completion_tokens"] = self.config.max_tokens
                else:
                    completion_params["max_tokens"] = self.config.max_tokens

                response = self._llm_client.chat.completions.create(**completion_params)
                answer = response.choices[0].message.content

                # Handle None or empty responses
                if not answer:
                    answer = "The LLM returned an empty response. Please try again."

            elif isinstance(self.config, AnthropicConfig):
                response = self._llm_client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                answer = response.content[0].text

                # Handle None or empty responses
                if not answer:
                    answer = "The LLM returned an empty response. Please try again."

            elif isinstance(self.config, GoogleConfig):
                response = self._llm_client.generate_content(f"{system_prompt}\n\n{user_prompt}")
                answer = response.text

            elif isinstance(self.config, OllamaConfig):
                import requests

                response = requests.post(
                    f"{self.config.base_url}/api/generate",
                    json={"model": self.config.model, "prompt": f"{system_prompt}\n\n{user_prompt}", "stream": False},
                    timeout=60,
                )
                if response.status_code == 200:
                    answer = response.json().get("response", "No response from Ollama")
                else:
                    answer = f"Ollama error: {response.status_code}"
            else:
                answer = "No LLM configured."

            model = self.config.model if self.config else "none"

        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
            answer = f"Unable to research: {e}"
            model = "error"

        execution_time = time.time() - start_time

        return ResearchResult(query=query, answer=answer, execution_time=execution_time, model=model)
