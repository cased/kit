import pytest
import os
from unittest.mock import patch, MagicMock

from kit.summaries import (
    Summarizer,
    OpenAIConfig,
    AnthropicConfig,
    GoogleConfig,
    LLMError,
)
from kit.repository import Repository

# --- Fixtures ---

@pytest.fixture
def mock_repo():
    """Provides a MagicMock instance of the Repository."""
    repo = MagicMock(spec=Repository)
    repo.get_abs_path = lambda x: f"/abs/path/to/{x}" # Mock get_abs_path
    return repo

@pytest.fixture
def temp_code_file(tmp_path):
    """Creates a temporary code file and returns its path."""
    file_path = tmp_path / "sample_code.py"
    file_content = "def hello():\n    print('Hello, world!')\n"
    file_path.write_text(file_content)
    return str(file_path)

# --- Test Summarizer Initialization ---

def test_summarizer_init_openai(mock_repo):
    config = OpenAIConfig(api_key="test_openai_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    assert summarizer.repo == mock_repo
    assert summarizer.config == config
    assert isinstance(summarizer.config, OpenAIConfig)

def test_summarizer_init_anthropic(mock_repo):
    config = AnthropicConfig(api_key="test_anthropic_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    assert summarizer.repo == mock_repo
    assert summarizer.config == config
    assert isinstance(summarizer.config, AnthropicConfig)

def test_summarizer_init_google(mock_repo):
    config = GoogleConfig(api_key="test_google_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    assert summarizer.repo == mock_repo
    assert summarizer.config == config
    assert isinstance(summarizer.config, GoogleConfig)

def test_summarizer_init_default_is_openai(mock_repo):
    # This test assumes OPENAI_API_KEY might not be set, 
    # so direct instantiation might be tricky if OpenAIConfig tries to validate key on init.
    # For now, we'll just check the type if config is None.
    # Actual API key validation is responsibility of OpenAIConfig or the API call itself.
    summarizer = Summarizer(repo=mock_repo) # No config provided
    assert summarizer.repo == mock_repo
    assert isinstance(summarizer.config, OpenAIConfig) # Defaults to OpenAIConfig

def test_summarizer_init_invalid_config_type(mock_repo):
    class InvalidConfig:
        pass
    config = InvalidConfig()
    with pytest.raises(TypeError, match="Unsupported LLM configuration"): # As per Summarizer.__init__
        Summarizer(repo=mock_repo, config=config)

# --- Test _get_llm_client --- 

@patch('kit.summaries.OpenAI')
def test_get_llm_client_openai(mock_openai_sdk, mock_repo):
    config = OpenAIConfig(api_key="test_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    client = summarizer._get_llm_client()
    mock_openai_sdk.assert_called_once_with(api_key="test_key")
    assert client == mock_openai_sdk.return_value
    # Test client is cached
    client2 = summarizer._get_llm_client()
    mock_openai_sdk.assert_called_once() # Should still be called only once
    assert client2 == client

@patch('kit.summaries.Anthropic')
def test_get_llm_client_anthropic(mock_anthropic_sdk, mock_repo):
    config = AnthropicConfig(api_key="test_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    client = summarizer._get_llm_client()
    mock_anthropic_sdk.assert_called_once_with(api_key="test_key")
    assert client == mock_anthropic_sdk.return_value
    client2 = summarizer._get_llm_client()
    mock_anthropic_sdk.assert_called_once()
    assert client2 == client

@patch('kit.summaries.genai')
def test_get_llm_client_google(mock_google_sdk, mock_repo):
    mock_model_instance = MagicMock()
    mock_google_sdk.GenerativeModel.return_value = mock_model_instance
    
    config = GoogleConfig(api_key="test_key", model="gemini-test")
    summarizer = Summarizer(repo=mock_repo, config=config)
    client = summarizer._get_llm_client()
    
    mock_google_sdk.configure.assert_called_once_with(api_key="test_key")
    mock_google_sdk.GenerativeModel.assert_called_once_with("gemini-test")
    assert client == mock_model_instance
    
    client2 = summarizer._get_llm_client()
    mock_google_sdk.configure.assert_called_once() # Should not be called again
    mock_google_sdk.GenerativeModel.assert_called_once() # Should not be called again
    assert client2 == client

# Placeholder for summarize_file tests (to be expanded)
# We will add more tests for summarize_file, summarize_function, and summarize_class here.
