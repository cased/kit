"""Tests for the LLM client factory module."""

from unittest.mock import MagicMock, patch

import pytest

from kit.llm_client_factory import (
    create_anthropic_client,
    create_client_from_config,
    create_client_from_review_config,
    create_google_client,
    create_ollama_client,
    create_openai_client,
)


class TestCreateOpenAIClient:
    """Tests for create_openai_client function."""

    def test_creates_client_without_base_url(self):
        """Test creating OpenAI client without custom base URL."""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            result = create_openai_client("sk-test-key")

            mock_openai.assert_called_once_with(api_key="sk-test-key")
            assert result == mock_client

    def test_creates_client_with_base_url(self):
        """Test creating OpenAI client with custom base URL."""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            result = create_openai_client("sk-test-key", "https://custom.api.com")

            mock_openai.assert_called_once_with(api_key="sk-test-key", base_url="https://custom.api.com")
            assert result == mock_client

    @pytest.mark.skip(reason="Import error testing requires module reload which has side effects")
    def test_raises_error_when_package_missing(self):
        """Test that LLMClientError is raised when openai package is missing."""
        pass


class TestCreateAnthropicClient:
    """Tests for create_anthropic_client function."""

    def test_creates_client(self):
        """Test creating Anthropic client."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client

            result = create_anthropic_client("sk-ant-test")

            mock_anthropic.assert_called_once_with(api_key="sk-ant-test")
            assert result == mock_client

    @pytest.mark.skip(reason="Import error testing requires module reload which has side effects")
    def test_raises_error_when_package_missing(self):
        """Test that LLMClientError is raised when anthropic package is missing."""
        pass


class TestCreateGoogleClient:
    """Tests for create_google_client function."""

    def test_creates_client(self):
        """Test creating Google client."""
        with patch("google.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            result = create_google_client("AIza-test")

            mock_client_class.assert_called_once_with(api_key="AIza-test")
            assert result == mock_client


class TestCreateOllamaClient:
    """Tests for create_ollama_client function."""

    def test_creates_client_with_defaults(self):
        """Test creating Ollama client with default values."""
        with patch("kit.ollama_client.OllamaClient") as mock_ollama:
            mock_client = MagicMock()
            mock_ollama.return_value = mock_client

            result = create_ollama_client()

            mock_ollama.assert_called_once_with("http://localhost:11434", "qwen2.5-coder:latest", None)
            assert result == mock_client

    def test_creates_client_with_custom_values(self):
        """Test creating Ollama client with custom values."""
        with patch("kit.ollama_client.OllamaClient") as mock_ollama:
            mock_client = MagicMock()
            mock_ollama.return_value = mock_client
            mock_session = MagicMock()

            result = create_ollama_client("http://custom:8080", "llama3", mock_session)

            mock_ollama.assert_called_once_with("http://custom:8080", "llama3", mock_session)
            assert result == mock_client


class TestCreateClientFromConfig:
    """Tests for create_client_from_config function."""

    def test_creates_openai_client_from_config(self):
        """Test creating client from OpenAIConfig."""
        from kit.summaries import OpenAIConfig

        with patch("kit.llm_client_factory.create_openai_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            config = OpenAIConfig(api_key="sk-test")
            result = create_client_from_config(config)

            mock_create.assert_called_once_with("sk-test", None)
            assert result == mock_client

    def test_creates_anthropic_client_from_config(self):
        """Test creating client from AnthropicConfig."""
        from kit.summaries import AnthropicConfig

        with patch("kit.llm_client_factory.create_anthropic_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            config = AnthropicConfig(api_key="sk-ant-test")
            result = create_client_from_config(config)

            mock_create.assert_called_once_with("sk-ant-test")
            assert result == mock_client

    def test_creates_google_client_from_config(self):
        """Test creating client from GoogleConfig."""
        from kit.summaries import GoogleConfig

        with patch("kit.llm_client_factory.create_google_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            config = GoogleConfig(api_key="AIza-test")
            result = create_client_from_config(config)

            mock_create.assert_called_once_with("AIza-test")
            assert result == mock_client

    def test_creates_ollama_client_from_config(self):
        """Test creating client from OllamaConfig."""
        from kit.summaries import OllamaConfig

        with patch("kit.llm_client_factory.create_ollama_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            config = OllamaConfig(base_url="http://localhost:11434", model="llama3")
            result = create_client_from_config(config)

            mock_create.assert_called_once_with("http://localhost:11434", "llama3")
            assert result == mock_client

    def test_raises_type_error_for_unsupported_config(self):
        """Test that TypeError is raised for unsupported config type."""
        with pytest.raises(TypeError, match="Unsupported config type"):
            create_client_from_config("invalid config")


class TestCreateClientFromReviewConfig:
    """Tests for create_client_from_review_config function."""

    def test_creates_openai_client_from_review_config(self):
        """Test creating client from LLMConfig with OPENAI provider."""
        from kit.pr_review.config import LLMConfig, LLMProvider

        with patch("kit.llm_client_factory.create_openai_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            config = LLMConfig(provider=LLMProvider.OPENAI, api_key="sk-test", model="gpt-4")
            result = create_client_from_review_config(config)

            mock_create.assert_called_once_with("sk-test", None)
            assert result == mock_client

    def test_creates_anthropic_client_from_review_config(self):
        """Test creating client from LLMConfig with ANTHROPIC provider."""
        from kit.pr_review.config import LLMConfig, LLMProvider

        with patch("kit.llm_client_factory.create_anthropic_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            config = LLMConfig(provider=LLMProvider.ANTHROPIC, api_key="sk-ant-test", model="claude-3")
            result = create_client_from_review_config(config)

            mock_create.assert_called_once_with("sk-ant-test")
            assert result == mock_client

    def test_creates_google_client_from_review_config(self):
        """Test creating client from LLMConfig with GOOGLE provider."""
        from kit.pr_review.config import LLMConfig, LLMProvider

        with patch("kit.llm_client_factory.create_google_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            config = LLMConfig(provider=LLMProvider.GOOGLE, api_key="AIza-test", model="gemini")
            result = create_client_from_review_config(config)

            mock_create.assert_called_once_with("AIza-test")
            assert result == mock_client

    def test_creates_ollama_client_from_review_config(self):
        """Test creating client from LLMConfig with OLLAMA provider."""
        from kit.pr_review.config import LLMConfig, LLMProvider

        with patch("kit.llm_client_factory.create_ollama_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client
            mock_session = MagicMock()

            config = LLMConfig(
                provider=LLMProvider.OLLAMA,
                api_key="ollama",
                model="llama3",
                api_base_url="http://localhost:11434",
            )
            result = create_client_from_review_config(config, session=mock_session)

            mock_create.assert_called_once_with("http://localhost:11434", "llama3", mock_session)
            assert result == mock_client
