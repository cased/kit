import os
import re
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from kit.summaries import AnthropicConfig, GoogleConfig, LLMError, OpenAIConfig, Summarizer
from kit.summaries import genai as kit_s_genai

# ---------------------------------------------------------
# Ensure external SDKs are importable even if not installed
# ---------------------------------------------------------
if "openai" not in sys.modules:
    openai_dummy = types.ModuleType("openai")
    openai_dummy.OpenAI = MagicMock()  # type: ignore[attr-defined]
    sys.modules["openai"] = openai_dummy

if "anthropic" not in sys.modules:
    anthropic_dummy = types.ModuleType("anthropic")
    anthropic_dummy.Anthropic = MagicMock()  # type: ignore[attr-defined]
    sys.modules["anthropic"] = anthropic_dummy

if "google" not in sys.modules:
    google_dummy = types.ModuleType("google")
    sys.modules["google"] = google_dummy

if "google.genai" not in sys.modules:
    genai_dummy = types.ModuleType("genai")
    genai_dummy.Client = MagicMock()  # type: ignore[attr-defined]

    # Mock the types submodule with GenerateContentConfig
    genai_types_dummy = types.ModuleType("types")
    genai_types_dummy.GenerateContentConfig = MagicMock()  # type: ignore[attr-defined]
    genai_dummy.types = genai_types_dummy  # type: ignore[attr-defined]

    sys.modules["google.genai"] = genai_dummy
    sys.modules["google.genai.types"] = genai_types_dummy
    # Attach submodule to parent "google"
    sys.modules["google"].genai = genai_dummy  # type: ignore[attr-defined]

# --- Fixtures ---


@pytest.fixture
def mock_repo():
    """Provides a MagicMock instance of the Repository with required methods."""
    repo = MagicMock()  # Do not enforce spec to allow arbitrary attributes
    repo.get_abs_path = MagicMock(side_effect=lambda x: f"/abs/path/to/{x}")  # Mock get_abs_path
    repo.get_symbol_text = MagicMock()
    repo.get_file_content = MagicMock()  # Mock get_file_content
    repo.extract_symbols = MagicMock()  # Mock extract_symbols
    return repo


@pytest.fixture
def temp_code_file(tmp_path):
    """Creates a temporary code file and returns its path."""
    file_path = tmp_path / "sample_code.py"
    file_content = "def hello():\n    print('Hello, world!')\n"
    file_path.write_text(file_content)
    return str(file_path)


# --- Test Summarizer Initialization ---


@patch("kit.llm_client_factory.create_openai_client")
@patch("kit.summaries.tiktoken", create=True)  # Mock tiktoken
def test_summarizer_init_default_is_openai(mock_tiktoken, mock_create_openai, mock_repo):
    # Test that Summarizer defaults to OpenAIConfig if no config is provided.
    # The Summarizer will then attempt to initialize an OpenAI client via the factory.

    mock_openai_client_instance = MagicMock()
    mock_create_openai.return_value = mock_openai_client_instance

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_dummy_key"}):
        try:
            summarizer = Summarizer(repo=mock_repo)  # No config provided
            assert isinstance(summarizer.config, OpenAIConfig), "Config should default to OpenAIConfig"
            # The factory should be called with the API key
            mock_create_openai.assert_called_once_with("test_dummy_key", None)
        except ValueError as e:
            pytest.fail(f"Summarizer initialization with dummy API key failed unexpectedly: {e}")


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


def test_summarizer_init_invalid_config_type(mock_repo):
    class InvalidConfig:
        pass

    config = InvalidConfig()
    with pytest.raises(TypeError, match="Unsupported LLM configuration"):  # As per Summarizer.__init__
        Summarizer(repo=mock_repo, config=config)


def test_summarizer_init_openai_config_with_base_url(mock_repo):
    """Test Summarizer correctly initializes OpenAI client with a custom base_url."""
    custom_api_key = "test_openrouter_key"
    custom_base_url = "https://openrouter.ai/api/v1/test"
    custom_model = "openrouter/some-model"

    config = OpenAIConfig(api_key=custom_api_key, base_url=custom_base_url, model=custom_model)

    with patch("openai.OpenAI", create=True) as mock_openai_constructor:
        mock_openai_client_instance = MagicMock()
        mock_openai_constructor.return_value = mock_openai_client_instance

        summarizer = Summarizer(repo=mock_repo, config=config)

        mock_openai_constructor.assert_called_once_with(api_key=custom_api_key, base_url=custom_base_url)
        assert summarizer._llm_client == mock_openai_client_instance


# --- Test _get_llm_client ---


@patch("openai.OpenAI", create=True)
def test_get_llm_client_openai(mock_openai_constructor, mock_repo):
    """Test _get_llm_client returns the client created in __init__."""
    mock_openai_instance = MagicMock()
    mock_openai_constructor.return_value = mock_openai_instance

    config = OpenAIConfig(api_key="test_openai_key")
    with patch("openai.OpenAI", new=mock_openai_constructor):
        summarizer = Summarizer(repo=mock_repo, config=config)
        mock_openai_constructor.assert_called_once_with(api_key="test_openai_key")

        client = summarizer._get_llm_client()
        assert client is summarizer._llm_client

    client2 = summarizer._get_llm_client()
    mock_openai_constructor.assert_called_once()
    assert client2 == client


def test_openai_config_reads_base_url_from_env():
    """Test OpenAIConfig reads OPENAI_BASE_URL from environment."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "OPENAI_BASE_URL": "https://proxy.example.com/v1"}):
        config = OpenAIConfig()
        assert config.base_url == "https://proxy.example.com/v1"


def test_openai_config_base_url_default_is_none():
    """Test OpenAIConfig base_url is None when env var not set."""
    env = {"OPENAI_API_KEY": "test-key"}
    # Ensure OPENAI_BASE_URL is not set
    with patch.dict(os.environ, env, clear=True):
        config = OpenAIConfig()
        assert config.base_url is None


@patch("openai.OpenAI", create=True)
def test_get_llm_client_openai_with_base_url_lazy_load(mock_openai_lazy_constructor, mock_repo):
    """Test _get_llm_client lazy loads OpenAI client with base_url if not already initialized."""
    custom_api_key = "test_lazy_key"
    custom_base_url = "http://lazy_load_url.com/v1"
    config = OpenAIConfig(api_key=custom_api_key, base_url=custom_base_url)

    with patch("openai.OpenAI", new=mock_openai_lazy_constructor) as patched_constructor_for_lazy:
        summarizer = Summarizer(repo=mock_repo, config=config, llm_client=None)
        patched_constructor_for_lazy.assert_called_once_with(api_key=custom_api_key, base_url=custom_base_url)

        summarizer._llm_client = None
        mock_openai_lazy_constructor.reset_mock()

        client = summarizer._get_llm_client()

        patched_constructor_for_lazy.assert_called_once_with(api_key=custom_api_key, base_url=custom_base_url)
        assert client is not None


@patch("kit.llm_client_factory.create_anthropic_client")
def test_get_llm_client_anthropic(mock_create_anthropic, mock_repo):
    """Test _get_llm_client returns the client created in __init__."""
    mock_anthropic_instance = MagicMock()
    mock_create_anthropic.return_value = mock_anthropic_instance

    config = AnthropicConfig(api_key="test_anthropic_key")
    summarizer = Summarizer(repo=mock_repo, config=config)

    # The factory should have been called
    mock_create_anthropic.assert_called_once_with("test_anthropic_key")

    # _get_llm_client should return the already created client
    client = summarizer._get_llm_client()
    assert client is summarizer._llm_client

    # Call again to check caching
    client2 = summarizer._get_llm_client()
    mock_create_anthropic.assert_called_once()  # Should not be called again
    assert client2 == client


@patch("google.genai.Client", create=True)  # New mock for google.genai.Client
def test_get_llm_client_google(mock_google_client_constructor, mock_repo):
    """Test _get_llm_client returns and caches Google client."""
    if kit_s_genai is None:
        pytest.skip("google.genai not available to kit.summaries")

    # Set up the mock before creating the Summarizer
    mock_client_instance = MagicMock()
    mock_google_client_constructor.return_value = mock_client_instance

    config = GoogleConfig(api_key="test_google_key", model="gemini-test")
    summarizer = Summarizer(repo=mock_repo, config=config)

    # First call: client should be created and cached
    client1 = summarizer._get_llm_client()
    assert client1 == mock_client_instance
    mock_google_client_constructor.assert_called_once_with(api_key="test_google_key")

    # Second call: cached client should be returned
    client2 = summarizer._get_llm_client()
    assert client2 == mock_client_instance
    mock_google_client_constructor.assert_called_once()  # Still called only once


# --- Test summarize_file ---


@patch("openai.OpenAI", create=True)  # To mock the client obtained via _get_llm_client
def test_summarize_file_openai(mock_openai_constructor, mock_repo, temp_code_file):
    """Test summarize_file with OpenAIConfig."""
    mock_file_content = "# A simple Python script\nprint('Hello, world!')"
    mock_repo.get_file_content.return_value = mock_file_content  # Mock repo method

    # Mock the OpenAI client and its response
    mock_openai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "This is an OpenAI summary."
    mock_openai_client.chat.completions.create.return_value = mock_response
    mock_openai_constructor.return_value = mock_openai_client

    config = OpenAIConfig(api_key="test_openai_key", model="gpt-test", max_tokens=100)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_to_summarize = "sample_code.py"
    summary = summarizer.summarize_file(file_to_summarize)

    mock_repo.get_abs_path.assert_called_once_with(file_to_summarize)
    mock_repo.get_file_content.assert_called_once_with(f"/abs/path/to/{file_to_summarize}")

    expected_system_prompt = "You are an expert assistant skilled in creating concise and informative code summaries."
    expected_user_prompt = f"Summarize the following code from the file '{file_to_summarize}'. Provide a high-level overview of its purpose, key components, and functionality. Focus on what the code does, not just how it's written. The code is:\n\n```\n{mock_file_content}\n```"

    mock_openai_client.chat.completions.create.assert_called_once_with(
        model="gpt-test",
        messages=[
            {"role": "system", "content": expected_system_prompt},
            {"role": "user", "content": expected_user_prompt},
        ],
        max_tokens=100,
    )

    assert summary == "This is an OpenAI summary."


def test_summarize_file_not_found(mock_repo):
    """Test summarize_file raises FileNotFoundError if file does not exist."""
    abs_path_to_non_existent_file = "/abs/path/to/non_existent.py"
    mock_repo.get_abs_path.return_value = abs_path_to_non_existent_file
    mock_repo.get_file_content.side_effect = FileNotFoundError(
        f"File not found: {abs_path_to_non_existent_file}"
    )  # Actual error from get_file_content

    summarizer = Summarizer(repo=mock_repo, config=OpenAIConfig(api_key="dummy"))

    # The error message re-raised by summarize_file will include 'File not found via repo: '
    expected_error_message = f"File not found via repo: {abs_path_to_non_existent_file}"
    with pytest.raises(FileNotFoundError, match=re.escape(expected_error_message)):
        summarizer.summarize_file("non_existent.py")

    mock_repo.get_abs_path.assert_called_once_with("non_existent.py")
    mock_repo.get_file_content.assert_called_once_with(abs_path_to_non_existent_file)


@patch("openai.OpenAI", create=True)
def test_summarize_file_llm_error_empty_summary(mock_openai_constructor, mock_repo, temp_code_file):
    """Test summarize_file raises LLMError if LLM returns an empty summary."""
    mock_repo.get_file_content.return_value = "def hello():\n    print('Hello, world!')"
    mock_openai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = ""  # Empty summary
    mock_openai_client.chat.completions.create.return_value = mock_response
    mock_openai_constructor.return_value = mock_openai_client

    config = OpenAIConfig(api_key="test_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(LLMError, match="LLM returned an empty summary."):
        summarizer.summarize_file(temp_code_file)


@patch("openai.OpenAI", create=True)
def test_summarize_file_llm_api_error(mock_openai_constructor, mock_repo, temp_code_file):
    """Test summarize_file raises LLMError on API communication failure."""
    mock_repo.get_file_content.return_value = "def hello():\n    print('Hello, world!')"
    mock_openai_client = MagicMock()
    mock_openai_client.chat.completions.create.side_effect = Exception("API Down")
    mock_openai_constructor.return_value = mock_openai_client

    config = OpenAIConfig(api_key="test_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(LLMError, match="Error communicating with LLM API: API Down"):
        summarizer.summarize_file(temp_code_file)


@patch("anthropic.Anthropic", create=True)  # Mock Anthropic client
def test_summarize_file_anthropic(mock_anthropic_constructor, mock_repo, temp_code_file):
    """Test summarize_file with AnthropicConfig."""
    mock_file_content = "# Another script for Anthropic\nprint('Claude is neat!')"
    mock_repo.get_file_content.return_value = mock_file_content  # Mock repo method

    mock_anthropic_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content[0].text = "This is an Anthropic summary."
    mock_anthropic_client.messages.create.return_value = mock_response
    mock_anthropic_constructor.return_value = mock_anthropic_client

    config = AnthropicConfig(api_key="test_anthropic_key", model="claude-test", max_tokens=150)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_to_summarize = "sample_anthropic_code.py"
    summary = summarizer.summarize_file(file_to_summarize)

    mock_repo.get_abs_path.assert_called_once_with(file_to_summarize)
    mock_repo.get_file_content.assert_called_once_with(f"/abs/path/to/{file_to_summarize}")

    expected_system_prompt = "You are an expert assistant skilled in creating concise and informative code summaries."
    expected_user_prompt = f"Summarize the following code from the file '{file_to_summarize}'. Provide a high-level overview of its purpose, key components, and functionality. Focus on what the code does, not just how it's written. The code is:\n\n```\n{mock_file_content}\n```"

    mock_anthropic_client.messages.create.assert_called_once_with(
        model="claude-test",
        system=expected_system_prompt,
        messages=[{"role": "user", "content": expected_user_prompt}],
        max_tokens=150,
    )

    assert summary == "This is an Anthropic summary."


@patch("google.genai.Client", create=True)  # New mock
def test_summarize_file_google(mock_google_client_constructor, mock_repo, temp_code_file):
    """Test summarize_file with GoogleConfig."""
    if kit_s_genai is None:
        pytest.skip("google.genai not available to kit.summaries")

    mock_file_content = "# A simple Python script\nprint('Google AI is fun!')"
    # Ensure get_abs_path returns a consistent path
    abs_path = f"/abs/path/to/{temp_code_file}"
    mock_repo.get_abs_path.return_value = abs_path
    mock_repo.get_file_content.return_value = mock_file_content

    mock_google_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a Google file summary."
    mock_response.prompt_feedback = None  # Assume no blocking for this test
    mock_google_client_instance.models.generate_content.return_value = mock_response
    mock_google_client_constructor.return_value = mock_google_client_instance

    config = GoogleConfig(api_key="test_google_key", model="gemini-file-test", max_output_tokens=110)
    summarizer = Summarizer(repo=mock_repo, config=config)

    summary = summarizer.summarize_file(temp_code_file)

    mock_repo.get_abs_path.assert_called_once_with(temp_code_file)
    mock_repo.get_file_content.assert_called_once_with(abs_path)
    mock_google_client_constructor.assert_called_once_with(api_key="test_google_key")

    # The actual implementation uses this format for Google clients
    expected_user_prompt = f"Summarize the following code from the file '{temp_code_file}'. Provide a high-level overview of its purpose, key components, and functionality. Focus on what the code does, not just how it's written. The code is:\n\n```\n{mock_file_content}\n```"

    # With the fix, we expect a GenerateContentConfig object to be created

    mock_google_client_instance.models.generate_content.assert_called_once()
    call_args = mock_google_client_instance.models.generate_content.call_args

    # Verify the correct parameters were passed
    assert call_args[1]["model"] == "gemini-file-test"
    assert call_args[1]["contents"] == expected_user_prompt

    # Verify that config parameter was used with GenerateContentConfig object
    assert "config" in call_args[1]
    # The config should be a GenerateContentConfig object (mocked)

    assert summary == "This is a Google file summary."


# --- Test summarize_function ---


@patch("openai.OpenAI", create=True)  # To mock the client obtained via _get_llm_client
def test_summarize_function_openai(mock_openai_constructor, mock_repo):
    """Test summarize_function with OpenAIConfig."""
    mock_func_code = "def my_func(a, b):\n    return a + b"
    mock_repo.extract_symbols.return_value = [{"name": "my_func", "type": "FUNCTION", "code": mock_func_code}]

    # Mock the OpenAI client and its response
    mock_openai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "This is an OpenAI function summary."
    mock_openai_client.chat.completions.create.return_value = mock_response
    mock_openai_constructor.return_value = mock_openai_client

    config = OpenAIConfig(api_key="test_openai_key", model="gpt-func-test", max_tokens=90)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_path = "src/module.py"
    func_name = "my_func"
    summary = summarizer.summarize_function(file_path, func_name)

    mock_repo.extract_symbols.assert_called_once_with(file_path)

    expected_system_prompt = "You are an expert assistant skilled in creating concise code summaries for functions."
    expected_user_prompt = f"Summarize the following function named '{func_name}' from the file '{file_path}'. Describe its purpose, parameters, and return value. The function definition is:\n\n```\n{mock_func_code}\n```"

    mock_openai_client.chat.completions.create.assert_called_once_with(
        model="gpt-func-test",
        messages=[
            {"role": "system", "content": expected_system_prompt},
            {"role": "user", "content": expected_user_prompt},
        ],
        max_tokens=90,
    )

    assert summary == "This is an OpenAI function summary."


def test_summarize_function_not_found(mock_repo):
    """Test summarize_function raises ValueError if function symbol is not found."""
    mock_repo.extract_symbols.return_value = []  # Simulate symbol not found
    config = OpenAIConfig(api_key="test_key")  # Can use any config for this test
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(ValueError, match="Could not find function 'non_existent_func' in 'some_file.py'."):
        summarizer.summarize_function("some_file.py", "non_existent_func")


@patch("openai.OpenAI", create=True)
def test_summarize_function_llm_error_empty_summary(mock_openai_constructor, mock_repo):
    """Test summarize_function raises LLMError if LLM returns an empty summary."""
    mock_repo.extract_symbols.return_value = [{"name": "my_func_empty", "type": "FUNCTION", "code": "def f(): pass"}]
    mock_openai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = ""  # Empty summary
    mock_openai_client.chat.completions.create.return_value = mock_response
    mock_openai_constructor.return_value = mock_openai_client

    config = OpenAIConfig(api_key="test_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(LLMError, match="LLM returned an empty summary for function my_func_empty."):
        summarizer.summarize_function("file.py", "my_func_empty")


@patch("openai.OpenAI", create=True)
def test_summarize_function_llm_api_error(mock_openai_constructor, mock_repo):
    """Test summarize_function raises LLMError on API communication failure."""
    mock_repo.extract_symbols.return_value = [{"name": "my_func_api_err", "type": "FUNCTION", "code": "def f(): pass"}]
    mock_openai_client = MagicMock()
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
    mock_openai_constructor.return_value = mock_openai_client

    config = OpenAIConfig(api_key="test_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(LLMError, match="Error communicating with LLM API for function my_func_api_err: API Error"):
        summarizer.summarize_function("file.py", "my_func_api_err")


@patch("anthropic.Anthropic", create=True)  # Mock Anthropic client
def test_summarize_function_anthropic(mock_anthropic_constructor, mock_repo):
    """Test summarize_function with AnthropicConfig."""
    mock_func_code = "def greet(name: str) -> str:\n    return f'Hello, {name}'"
    mock_repo.extract_symbols.return_value = [{"name": "greet", "type": "FUNCTION", "code": mock_func_code}]

    mock_anthropic_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content[0].text = "This is an Anthropic function summary."
    mock_anthropic_client.messages.create.return_value = mock_response
    mock_anthropic_constructor.return_value = mock_anthropic_client

    config = AnthropicConfig(api_key="test_anthropic_key", model="claude-func-test", max_tokens=100)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_path = "src/greetings.py"
    func_name = "greet"
    summary = summarizer.summarize_function(file_path, func_name)

    mock_repo.extract_symbols.assert_called_once_with(file_path)

    expected_system_prompt = "You are an expert assistant skilled in creating concise code summaries for functions."
    expected_user_prompt = f"Summarize the following function named '{func_name}' from the file '{file_path}'. Describe its purpose, parameters, and return value. The function definition is:\n\n```\n{mock_func_code}\n```"

    mock_anthropic_client.messages.create.assert_called_once_with(
        model="claude-func-test",
        system=expected_system_prompt,
        messages=[{"role": "user", "content": expected_user_prompt}],
        max_tokens=100,
    )

    assert summary == "This is an Anthropic function summary."


@patch("google.genai.Client", create=True)  # New mock
def test_summarize_function_google(mock_google_client_constructor, mock_repo):
    """Test summarize_function with GoogleConfig."""
    if kit_s_genai is None:
        pytest.skip("google.genai not available to kit.summaries")

    mock_func_code = "def calculate_sum(numbers: list[int]) -> int:\n    return sum(numbers)"
    mock_repo.extract_symbols.return_value = [{"name": "calculate_sum", "type": "FUNCTION", "code": mock_func_code}]

    mock_google_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a Google function summary."
    mock_response.prompt_feedback = None
    mock_google_client_instance.models.generate_content.return_value = mock_response
    mock_google_client_constructor.return_value = mock_google_client_instance

    config = GoogleConfig(api_key="test_google_key", model="gemini-func-test", max_output_tokens=100)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_path = "src/calculations.py"
    function_name = "calculate_sum"
    summary = summarizer.summarize_function(file_path, function_name)

    mock_repo.extract_symbols.assert_called_once_with(file_path)
    mock_google_client_constructor.assert_called_once_with(api_key="test_google_key")

    # The actual implementation only uses the user prompt for Google client
    expected_user_prompt = f"Summarize the following function named '{function_name}' from the file '{file_path}'. Describe its purpose, parameters, and return value. The function definition is:\n\n```\n{mock_func_code}\n```"

    # With the fix, we expect a GenerateContentConfig object to be created
    mock_google_client_instance.models.generate_content.assert_called_once()
    call_args = mock_google_client_instance.models.generate_content.call_args

    # Verify the correct parameters were passed
    assert call_args[1]["model"] == "gemini-func-test"
    assert call_args[1]["contents"] == expected_user_prompt

    # Verify that config parameter was used instead of generation_config
    assert "config" in call_args[1]

    assert summary == "This is a Google function summary."


# --- Test summarize_class ---


@patch("openai.OpenAI", create=True)  # To mock the client obtained via _get_llm_client
def test_summarize_class_openai(mock_openai_constructor, mock_repo):
    """Test summarize_class with OpenAIConfig."""
    mock_class_code = (
        "class MyClass:\n    def __init__(self, x):\n        self.x = x\n\n    def get_x(self):\n        return self.x"
    )
    mock_repo.extract_symbols.return_value = [{"name": "MyClass", "type": "CLASS", "code": mock_class_code}]

    # Mock the OpenAI client and its response
    mock_openai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "This is an OpenAI class summary."
    mock_openai_client.chat.completions.create.return_value = mock_response
    mock_openai_constructor.return_value = mock_openai_client

    config = OpenAIConfig(api_key="test_openai_key", model="gpt-class-test", max_tokens=110)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_path = "src/data_model.py"
    class_name = "MyClass"
    summary = summarizer.summarize_class(file_path, class_name)

    mock_repo.extract_symbols.assert_called_once_with(file_path)

    expected_system_prompt = "You are an expert assistant skilled in creating concise code summaries for classes."
    expected_user_prompt = f"Summarize the following class named '{class_name}' from the file '{file_path}'. Describe its purpose, key attributes, and main methods. The class definition is:\n\n```\n{mock_class_code}\n```"

    mock_openai_client.chat.completions.create.assert_called_once_with(
        model="gpt-class-test",
        messages=[
            {"role": "system", "content": expected_system_prompt},
            {"role": "user", "content": expected_user_prompt},
        ],
        max_tokens=110,
    )

    assert summary == "This is an OpenAI class summary."


def test_summarize_class_not_found(mock_repo):
    """Test summarize_class raises ValueError if class symbol is not found."""
    mock_repo.extract_symbols.return_value = []  # Simulate symbol not found
    config = OpenAIConfig(api_key="test_key")  # Can use any config
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(ValueError, match="Could not find class 'NonExistentClass' in 'another_file.py'."):
        summarizer.summarize_class("another_file.py", "NonExistentClass")


@patch("openai.OpenAI", create=True)
def test_summarize_class_llm_error_empty_summary(mock_openai_constructor, mock_repo):
    """Test summarize_class raises LLMError if LLM returns an empty summary."""
    mock_repo.extract_symbols.return_value = [{"name": "MyClass_empty", "type": "CLASS", "code": "class C: pass"}]
    mock_openai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = ""  # Empty summary
    mock_openai_client.chat.completions.create.return_value = mock_response
    mock_openai_constructor.return_value = mock_openai_client

    config = OpenAIConfig(api_key="test_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(LLMError, match="LLM returned an empty summary for class MyClass_empty."):
        summarizer.summarize_class("file.py", "MyClass_empty")


@patch("openai.OpenAI", create=True)
def test_summarize_class_llm_api_error(mock_openai_constructor, mock_repo):
    """Test summarize_class raises LLMError on API communication failure."""
    mock_repo.extract_symbols.return_value = [{"name": "MyClass_api_err", "type": "CLASS", "code": "class C: pass"}]
    mock_openai_client = MagicMock()
    mock_openai_client.chat.completions.create.side_effect = Exception("API Crash")
    mock_openai_constructor.return_value = mock_openai_client

    config = OpenAIConfig(api_key="test_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(LLMError, match="Error communicating with LLM API for class MyClass_api_err: API Crash"):
        summarizer.summarize_class("file.py", "MyClass_api_err")


@patch("anthropic.Anthropic", create=True)  # Mock Anthropic client
def test_summarize_class_anthropic(mock_anthropic_constructor, mock_repo):
    """Test summarize_class with AnthropicConfig."""
    mock_class_code = "class DataProcessor:\n    def __init__(self, data):\n        self.data = data\n\n    def process(self):\n        return len(self.data)"
    mock_repo.extract_symbols.return_value = [{"name": "DataProcessor", "type": "CLASS", "code": mock_class_code}]

    mock_anthropic_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content[0].text = "This is an Anthropic class summary."
    mock_anthropic_client.messages.create.return_value = mock_response
    mock_anthropic_constructor.return_value = mock_anthropic_client

    config = AnthropicConfig(api_key="test_anthropic_key", model="claude-class-test", max_tokens=120)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_path = "src/processing.py"
    class_name = "DataProcessor"
    summary = summarizer.summarize_class(file_path, class_name)

    mock_repo.extract_symbols.assert_called_once_with(file_path)

    expected_system_prompt = "You are an expert assistant skilled in creating concise code summaries for classes."
    expected_user_prompt = f"Summarize the following class named '{class_name}' from the file '{file_path}'. Describe its purpose, key attributes, and main methods. The class definition is:\n\n```\n{mock_class_code}\n```"

    mock_anthropic_client.messages.create.assert_called_once_with(
        model="claude-class-test",
        system=expected_system_prompt,
        messages=[{"role": "user", "content": expected_user_prompt}],
        max_tokens=120,
    )

    assert summary == "This is an Anthropic class summary."


@patch("google.genai.Client", create=True)  # New mock
def test_summarize_class_google(mock_google_client_constructor, mock_repo):
    """Test summarize_class with GoogleConfig."""
    if kit_s_genai is None:
        pytest.skip("google.genai not available to kit.summaries")
    mock_class_code = "class Logger:\n    def __init__(self, level='INFO'):\n        self.level = level\n\n    def log(self, message):\n        print(f'[{self.level}] {message}')"
    mock_repo.extract_symbols.return_value = [{"name": "Logger", "type": "CLASS", "code": mock_class_code}]

    mock_google_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a Google class summary."
    mock_response.prompt_feedback = None
    mock_google_client_instance.models.generate_content.return_value = mock_response
    mock_google_client_constructor.return_value = mock_google_client_instance

    config = GoogleConfig(api_key="test_google_key", model="gemini-class-test", max_output_tokens=130)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_path = "src/utils.py"
    class_name = "Logger"
    summary = summarizer.summarize_class(file_path, class_name)

    mock_repo.extract_symbols.assert_called_once_with(file_path)
    mock_google_client_constructor.assert_called_once_with(api_key="test_google_key")

    # The actual implementation only uses the user prompt for Google client
    expected_user_prompt = f"Summarize the following class named '{class_name}' from the file '{file_path}'. Describe its purpose, key attributes, and main methods. The class definition is:\n\n```\n{mock_class_code}\n```"

    # With the fix, we expect a GenerateContentConfig object to be created
    mock_google_client_instance.models.generate_content.assert_called_once()
    call_args = mock_google_client_instance.models.generate_content.call_args

    # Verify the correct parameters were passed
    assert call_args[1]["model"] == "gemini-class-test"
    assert call_args[1]["contents"] == expected_user_prompt

    # Verify that config parameter was used instead of generation_config
    assert "config" in call_args[1]

    assert summary == "This is a Google class summary."


# --- Test for Issue #137: generation_config parameter fix ---


@patch("google.genai.Client", create=True)
def test_google_gemini_generation_config_fix(mock_google_client_constructor, mock_repo):
    """Test that Google Gemini API is called with 'config' parameter instead of 'generation_config'.

    This test ensures issue #137 is fixed - the TypeError about unexpected 'generation_config'
    keyword argument should not occur with newer google-genai SDK versions.
    """
    if kit_s_genai is None:
        pytest.skip("google.genai not available to kit.summaries")

    # Setup mock client
    mock_google_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Test summary response"

    # Ensure prompt_feedback doesn't trigger blocking logic
    mock_response.prompt_feedback = None

    mock_google_client_instance.models.generate_content.return_value = mock_response
    mock_google_client_constructor.return_value = mock_google_client_instance

    # Setup mock repo
    mock_repo.get_file_content.return_value = "print('test code')"

    # Create config with max_output_tokens to trigger the config object creation
    config = GoogleConfig(api_key="test_api_key", model="gemini-2.0-flash-exp", max_output_tokens=150)
    summarizer = Summarizer(repo=mock_repo, config=config)

    # Call summarize_file which should use the fixed parameter name
    result = summarizer.summarize_file("test.py")

    # Verify the call was made
    mock_google_client_instance.models.generate_content.assert_called_once()
    call_args = mock_google_client_instance.models.generate_content.call_args

    # CRITICAL: Verify 'config' parameter is used, NOT 'generation_config'
    assert "config" in call_args[1], "Should use 'config' parameter"
    assert "generation_config" not in call_args[1], "Should NOT use 'generation_config' parameter (causes TypeError)"

    # Verify the config object is passed (should be the mocked GenerateContentConfig)
    config_param = call_args[1]["config"]
    assert config_param is not None, "config parameter should not be None when max_output_tokens is set"

    # Verify other expected parameters
    assert call_args[1]["model"] == "gemini-2.0-flash-exp"
    assert "contents" in call_args[1]

    assert result == "Test summary response"


# --- Test Helper for Mocking Summarizer ---


# --- Test Thinking Token Stripping ---


class TestThinkingTokenStripping:
    """Tests for the _strip_thinking_tokens function."""

    def test_strip_simple_think_tags(self):
        """Test stripping simple <think> tags."""
        from kit.summaries import _strip_thinking_tokens

        response = "<think>This is internal reasoning</think>\n\nThis is the actual response."
        expected = "This is the actual response."
        result = _strip_thinking_tokens(response)
        assert result == expected

    def test_strip_thinking_tags(self):
        """Test stripping <thinking> tags."""
        from kit.summaries import _strip_thinking_tokens

        response = "<thinking>\nLet me analyze this...\nActually, I think...\n</thinking>\n\nHere's my analysis."
        expected = "Here's my analysis."
        result = _strip_thinking_tokens(response)
        assert result == expected

    def test_strip_thought_tags(self):
        """Test stripping <thought> tags."""
        from kit.summaries import _strip_thinking_tokens

        response = "<thought>Internal thoughts here</thought>\n\nFinal answer."
        expected = "Final answer."
        result = _strip_thinking_tokens(response)
        assert result == expected

    def test_strip_reason_tags(self):
        """Test stripping <reason> tags."""
        from kit.summaries import _strip_thinking_tokens

        response = "<reason>Because X leads to Y</reason>\n\nTherefore, the solution is Z."
        expected = "Therefore, the solution is Z."
        result = _strip_thinking_tokens(response)
        assert result == expected

    def test_strip_multiple_patterns(self):
        """Test stripping multiple different thinking token patterns."""
        from kit.summaries import _strip_thinking_tokens

        response = """<thinking>
First, let me think about this...
</thinking>

Here's my initial analysis.

<think>Wait, I need to reconsider...</think>

Actually, the correct approach is:

<reason>The logic should be X because Y</reason>

Final recommendation."""

        expected = "Here's my initial analysis.\n\nActually, the correct approach is:\n\nFinal recommendation."
        result = _strip_thinking_tokens(response)
        assert result == expected

    def test_case_insensitive_stripping(self):
        """Test that thinking token stripping is case insensitive."""
        from kit.summaries import _strip_thinking_tokens

        response = "<THINK>Upper case thinking</THINK>\n\n<Think>Mixed case</Think>\n\nActual content."
        expected = "Actual content."
        result = _strip_thinking_tokens(response)
        assert result == expected

    def test_no_thinking_tokens(self):
        """Test that text without thinking tokens is unchanged."""
        from kit.summaries import _strip_thinking_tokens

        response = "This is a normal response with no thinking tokens."
        result = _strip_thinking_tokens(response)
        assert result == response

    def test_empty_input(self):
        """Test handling of empty input."""
        from kit.summaries import _strip_thinking_tokens

        assert _strip_thinking_tokens("") == ""
        assert _strip_thinking_tokens(None) is None

    def test_only_thinking_tokens(self):
        """Test input that contains only thinking tokens."""
        from kit.summaries import _strip_thinking_tokens

        response = "<think>Only internal thoughts here</think>"
        result = _strip_thinking_tokens(response)
        assert result == ""

    def test_nested_content_preservation(self):
        """Test that thinking tokens with nested content are fully removed."""
        from kit.summaries import _strip_thinking_tokens

        response = """<thinking>
I need to consider:
1. Option A because of X
2. Option B because of Y
3. Option C because of Z

Let me weigh the pros and cons...
Actually, option B seems best.
</thinking>

Based on my analysis, I recommend option B."""

        expected = "Based on my analysis, I recommend option B."
        result = _strip_thinking_tokens(response)
        assert result == expected

    def test_malformed_tags_ignored(self):
        """Test that malformed tags are not stripped."""
        from kit.summaries import _strip_thinking_tokens

        response = "<think>Valid thinking</think>\n\n<think unclosed tag\n\nSome content with <think but not closed."
        # Only the properly formed tag should be removed
        expected = "<think unclosed tag\n\nSome content with <think but not closed."
        result = _strip_thinking_tokens(response)
        assert result == expected

    def test_multiple_blank_lines_cleanup(self):
        """Test that multiple blank lines left by tag removal are cleaned up."""
        from kit.summaries import _strip_thinking_tokens

        response = """First paragraph.

<think>Internal reasoning</think>



<thinking>More thinking</thinking>




Second paragraph."""

        expected = "First paragraph.\n\nSecond paragraph."
        result = _strip_thinking_tokens(response)
        assert result == expected

    def test_deepseek_r1_style_response(self):
        """Test a realistic DeepSeek R1 style response with thinking tokens."""
        from kit.summaries import _strip_thinking_tokens

        response = """<think>
The user is asking about code review. I need to analyze:
1. The function structure
2. Error handling
3. Performance implications
4. Security considerations

Let me think through each aspect...
</think>

## Code Review

The function has several issues that need attention:

<think>
Actually, let me be more specific about the error handling issue...
</think>

### Issues Found

1. **Missing Error Handling**: The function doesn't handle edge cases properly
2. **Performance**: The nested loops could be optimized

### Recommendations

- Add try-catch blocks around risky operations
- Consider using a more efficient algorithm"""

        expected = """## Code Review

The function has several issues that need attention:

### Issues Found

1. **Missing Error Handling**: The function doesn't handle edge cases properly
2. **Performance**: The nested loops could be optimized

### Recommendations

- Add try-catch blocks around risky operations
- Consider using a more efficient algorithm"""

        result = _strip_thinking_tokens(response)
        assert result == expected

    def test_whitespace_only_after_stripping(self):
        """Test handling when only whitespace remains after stripping."""
        from kit.summaries import _strip_thinking_tokens

        response = "   <think>Only thinking content</think>   \n\n  "
        result = _strip_thinking_tokens(response)
        assert result == ""

    def test_thinking_tokens_at_boundaries(self):
        """Test thinking tokens at the start and end of content."""
        from kit.summaries import _strip_thinking_tokens

        response = "<think>Start thinking</think>Middle content<think>End thinking</think>"
        expected = "Middle content"
        result = _strip_thinking_tokens(response)
        assert result == expected
