"""Tests for Ollama integration."""

from unittest.mock import Mock, patch

import pytest

from kit.pr_review.config import GitHubConfig, LLMConfig, LLMProvider, ReviewConfig
from kit.pr_review.cost_tracker import CostTracker
from kit.summaries import LLMError, OllamaConfig, Summarizer


class TestOllamaConfig:
    """Test OllamaConfig dataclass."""

    def test_ollama_config_defaults(self):
        """Test OllamaConfig with default values."""
        config = OllamaConfig()
        assert config.model == "qwen2.5-coder:latest"
        assert config.base_url == "http://localhost:11434"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        assert config.api_key == "ollama"

    def test_ollama_config_custom_values(self):
        """Test OllamaConfig with custom values."""
        config = OllamaConfig(model="codellama:latest", base_url="http://custom:8080", temperature=0.1, max_tokens=2000)
        assert config.model == "codellama:latest"
        assert config.base_url == "http://custom:8080"
        assert config.temperature == 0.1
        assert config.max_tokens == 2000

    def test_ollama_config_url_validation(self):
        """Test URL validation in OllamaConfig."""
        # Valid URLs
        OllamaConfig(base_url="http://localhost:11434")
        OllamaConfig(base_url="https://remote.server.com:8080")

        # Invalid URLs should raise ValueError
        with pytest.raises(ValueError, match="Invalid Ollama base_url"):
            OllamaConfig(base_url="localhost:11434")

        with pytest.raises(ValueError, match="Invalid Ollama base_url"):
            OllamaConfig(base_url="ftp://invalid.com")

    def test_ollama_config_url_normalization(self):
        """Test URL normalization (trailing slash removal)."""
        config = OllamaConfig(base_url="http://localhost:11434/")
        assert config.base_url == "http://localhost:11434"


class TestOllamaSummarizer:
    """Test Ollama integration with Summarizer."""

    @pytest.fixture
    def mock_repo(self):
        """Mock repository for testing."""
        repo = Mock()
        repo.get_abs_path.return_value = "/abs/path/to/test_file.py"
        repo.get_file_content.return_value = "def hello():\n    print('Hello, World!')"
        repo.extract_symbols.return_value = [
            {"name": "hello", "type": "FUNCTION", "code": "def hello():\n    print('Hello, World!')"}
        ]
        return repo

    @patch("requests.Session")
    def test_ollama_summarizer_initialization(self, mock_session, mock_repo):
        """Test Ollama Summarizer initialization."""
        config = OllamaConfig(model="llama3.2:latest")
        summarizer = Summarizer(repo=mock_repo, config=config)

        assert summarizer.config == config
        assert isinstance(summarizer.config, OllamaConfig)

    @patch("requests.Session")
    def test_ollama_client_creation(self, mock_session, mock_repo):
        """Test that Ollama client is created correctly."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        config = OllamaConfig(model="llama3.2:latest", base_url="http://localhost:11434")
        summarizer = Summarizer(repo=mock_repo, config=config)

        # Get the client (this should create the OllamaClient)
        client = summarizer._get_llm_client()

        # Verify the client was created with correct parameters
        assert hasattr(client, "base_url")
        assert hasattr(client, "model")
        assert hasattr(client, "generate")
        assert client.base_url == "http://localhost:11434"
        assert client.model == "llama3.2:latest"

    @patch("requests.Session")
    def test_ollama_file_summarization(self, mock_session, mock_repo):
        """Test file summarization with Ollama."""
        # Setup mock response
        mock_session_instance = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"response": "This is a test summary from Ollama."}
        mock_response.raise_for_status.return_value = None
        mock_session_instance.post.return_value = mock_response
        mock_session.return_value = mock_session_instance

        config = OllamaConfig(model="llama3.2:latest")
        summarizer = Summarizer(repo=mock_repo, config=config)

        summary = summarizer.summarize_file("test_file.py")

        assert summary == "This is a test summary from Ollama."

        # Verify the API call was made correctly
        mock_session_instance.post.assert_called_once()
        call_args = mock_session_instance.post.call_args
        assert call_args[1]["json"]["model"] == "llama3.2:latest"
        assert call_args[1]["json"]["stream"] is False
        assert "prompt" in call_args[1]["json"]

    @patch("requests.Session")
    def test_ollama_function_summarization(self, mock_session, mock_repo):
        """Test function summarization with Ollama."""
        # Setup mock response
        mock_session_instance = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"response": "This function prints 'Hello, World!' to the console."}
        mock_response.raise_for_status.return_value = None
        mock_session_instance.post.return_value = mock_response
        mock_session.return_value = mock_session_instance

        config = OllamaConfig(model="codellama:latest", temperature=0.1, max_tokens=500)
        summarizer = Summarizer(repo=mock_repo, config=config)

        summary = summarizer.summarize_function("test_file.py", "hello")

        assert summary == "This function prints 'Hello, World!' to the console."

        # Verify the API call parameters
        call_args = mock_session_instance.post.call_args
        assert call_args[1]["json"]["model"] == "codellama:latest"
        assert call_args[1]["json"]["temperature"] == 0.1
        assert call_args[1]["json"]["num_predict"] == 500

    @patch("requests.Session")
    def test_ollama_class_summarization(self, mock_session, mock_repo):
        """Test class summarization with Ollama."""
        # Update mock repo for class
        mock_repo.extract_symbols.return_value = [
            {"name": "TestClass", "type": "CLASS", "code": "class TestClass:\n    def __init__(self):\n        pass"}
        ]

        # Setup mock response
        mock_session_instance = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"response": "This is a simple test class with a constructor."}
        mock_response.raise_for_status.return_value = None
        mock_session_instance.post.return_value = mock_response
        mock_session.return_value = mock_session_instance

        config = OllamaConfig()
        summarizer = Summarizer(repo=mock_repo, config=config)

        summary = summarizer.summarize_class("test_file.py", "TestClass")

        assert summary == "This is a simple test class with a constructor."

    @patch("requests.Session")
    def test_ollama_api_error_handling(self, mock_session, mock_repo):
        """Test error handling when Ollama API fails."""
        # Setup mock to raise an exception
        mock_session_instance = Mock()
        mock_session_instance.post.side_effect = Exception("Connection refused")
        mock_session.return_value = mock_session_instance

        config = OllamaConfig()
        summarizer = Summarizer(repo=mock_repo, config=config)

        summary = summarizer.summarize_file("test_file.py")

        # Should return error message instead of raising exception
        assert "Summary generation failed: Ollama API error" in summary
        assert "Connection refused" in summary

    def test_ollama_without_requests(self, mock_repo):
        """Test that missing requests library is handled properly."""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'requests'")):
            config = OllamaConfig()

            with pytest.raises(LLMError, match="requests library not available"):
                Summarizer(repo=mock_repo, config=config)


class TestOllamaPRReview:
    """Test Ollama integration with PR review system."""

    def test_ollama_llm_config_creation(self):
        """Test creating LLMConfig with OLLAMA provider."""
        config = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama3.2:latest",
            api_key="ollama",
            max_tokens=2000,
            temperature=0.1,
            api_base_url="http://localhost:11434",
        )

        assert config.provider == LLMProvider.OLLAMA
        assert config.model == "llama3.2:latest"
        assert config.api_base_url == "http://localhost:11434"

    def test_ollama_provider_detection(self):
        """Test automatic provider detection from model names."""
        from kit.pr_review.config import _detect_provider_from_model

        # Test Ollama model detection
        assert _detect_provider_from_model("llama3.2:latest") == LLMProvider.OLLAMA
        assert _detect_provider_from_model("codellama:7b") == LLMProvider.OLLAMA
        assert _detect_provider_from_model("mistral:latest") == LLMProvider.OLLAMA
        assert _detect_provider_from_model("deepseek-coder:33b") == LLMProvider.OLLAMA
        assert _detect_provider_from_model("qwen2.5:7b") == LLMProvider.OLLAMA

        # Test non-Ollama models still work
        assert _detect_provider_from_model("gpt-4o") == LLMProvider.OPENAI
        assert _detect_provider_from_model("claude-3-opus") == LLMProvider.ANTHROPIC

    def test_ollama_cost_tracking(self):
        """Test that Ollama models are tracked as free."""
        tracker = CostTracker()

        # Test known Ollama models
        tracker.track_llm_usage(LLMProvider.OLLAMA, "llama3.2:latest", 1000, 500)
        assert tracker.get_total_cost() == 0.0

        tracker.track_llm_usage(LLMProvider.OLLAMA, "codellama:latest", 2000, 1000)
        assert tracker.get_total_cost() == 0.0

        # Test unknown Ollama model falls back to free
        tracker.track_llm_usage(LLMProvider.OLLAMA, "unknown-model:latest", 1000, 500)
        assert tracker.get_total_cost() == 0.0

    def test_ollama_in_review_config(self):
        """Test creating ReviewConfig with Ollama provider."""
        github_config = GitHubConfig(token="test_token")
        llm_config = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama3.2:latest",
            api_key="ollama",
            api_base_url="http://localhost:11434",
        )

        config = ReviewConfig(github=github_config, llm=llm_config)

        assert config.llm.provider == LLMProvider.OLLAMA
        assert config.llm.model == "llama3.2:latest"


class TestOllamaConfigValidation:
    """Test configuration validation and loading."""

    def test_ollama_model_patterns(self):
        """Test that Ollama model patterns are correctly detected."""
        from kit.pr_review.config import _detect_provider_from_model

        test_cases = [
            # Latest popular Ollama models (2025)
            ("qwen2.5-coder:latest", LLMProvider.OLLAMA),
            ("deepseek-r1:latest", LLMProvider.OLLAMA),
            ("devstral:latest", LLMProvider.OLLAMA),
            ("qwen3:latest", LLMProvider.OLLAMA),
            ("gemma3:latest", LLMProvider.OLLAMA),
            ("llama3.3:latest", LLMProvider.OLLAMA),
            ("phi4:latest", LLMProvider.OLLAMA),
            # Legacy Ollama models
            ("llama3.2:latest", LLMProvider.OLLAMA),
            ("llama3.1:8b", LLMProvider.OLLAMA),
            ("mistral:7b-instruct", LLMProvider.OLLAMA),
            ("codellama:13b-python", LLMProvider.OLLAMA),
            ("deepseek-coder:6.7b", LLMProvider.OLLAMA),
            ("qwen2.5:14b", LLMProvider.OLLAMA),
            ("phi3:mini", LLMProvider.OLLAMA),
            ("gemma2:9b", LLMProvider.OLLAMA),
            ("wizardcoder:15b", LLMProvider.OLLAMA),
            ("starcoder:3b", LLMProvider.OLLAMA),
            # Non-Ollama models
            ("gpt-4o-mini", LLMProvider.OPENAI),
            ("claude-3-sonnet", LLMProvider.ANTHROPIC),
            ("unknown-model", None),
        ]

        for model_name, expected_provider in test_cases:
            result = _detect_provider_from_model(model_name)
            assert result == expected_provider, f"Model {model_name} should detect as {expected_provider}, got {result}"


if __name__ == "__main__":
    pytest.main([__file__])
