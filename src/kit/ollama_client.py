"""Unified Ollama client for kit.

This module provides a single OllamaClient implementation used across all
kit modules that interact with Ollama's API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import requests as requests_module


class OllamaClient:
    """Simple HTTP client for Ollama's API.

    Args:
        base_url: The base URL for the Ollama API (e.g., "http://localhost:11434")
        model: The model name to use for generation
        session: Optional requests.Session to use. If not provided, creates a new one.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        session: Optional["requests_module.Session"] = None,
    ):
        self.base_url = base_url
        self.model = model
        if session is not None:
            self.session = session
            self._owns_session = False
        else:
            import requests

            self.session = requests.Session()
            self._owns_session = True

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text using Ollama's API.

        Args:
            prompt: The prompt to send to the model
            **kwargs: Additional parameters to pass to the Ollama API
                     (e.g., num_predict, temperature)

        Returns:
            The generated text response

        Raises:
            requests.HTTPError: If the API request fails
        """
        url = f"{self.base_url}/api/generate"
        data = {"model": self.model, "prompt": prompt, "stream": False, **kwargs}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json().get("response", "")

    def close(self) -> None:
        """Close the session if we own it."""
        if self._owns_session:
            self.session.close()

    def __enter__(self) -> "OllamaClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
