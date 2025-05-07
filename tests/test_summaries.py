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

import sys
import types

# ---------------------------------------------------------
# Ensure external SDKs are importable even if not installed
# ---------------------------------------------------------
if 'openai' not in sys.modules:
    openai_dummy = types.ModuleType('openai')
    openai_dummy.OpenAI = MagicMock()
    sys.modules['openai'] = openai_dummy

if 'anthropic' not in sys.modules:
    anthropic_dummy = types.ModuleType('anthropic')
    anthropic_dummy.Anthropic = MagicMock()
    sys.modules['anthropic'] = anthropic_dummy

if 'google' not in sys.modules:
    google_dummy = types.ModuleType('google')
    sys.modules['google'] = google_dummy

if 'google.generativeai' not in sys.modules:
    generativeai_dummy = types.ModuleType('generativeai')
    generativeai_dummy.configure = MagicMock()
    generativeai_dummy.GenerativeModel = MagicMock()
    # Attach submodule to parent "google"
    sys.modules['google'].generativeai = generativeai_dummy
    sys.modules['google.generativeai'] = generativeai_dummy

# --- Fixtures ---

@pytest.fixture
def mock_repo():
    """Provides a MagicMock instance of the Repository with required methods."""
    repo = MagicMock()  # Do not enforce spec to allow arbitrary attributes
    repo.get_abs_path = MagicMock(side_effect=lambda x: f"/abs/path/to/{x}")  # Mock get_abs_path
    repo.get_symbol_text = MagicMock()
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

@patch('openai.OpenAI', create=True)
def test_get_llm_client_openai(mock_openai_constructor, mock_repo):
    """Test _get_llm_client returns and caches OpenAI client."""
    config = OpenAIConfig(api_key="test_openai_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    mock_openai_instance = MagicMock()
    mock_openai_constructor.return_value = mock_openai_instance

    client = summarizer._get_llm_client()
    mock_openai_constructor.assert_called_once_with(api_key="test_openai_key")
    assert client == mock_openai_instance

    # Call again to check caching
    client2 = summarizer._get_llm_client()
    mock_openai_constructor.assert_called_once() # Should not be called again
    assert client2 == client

@patch('anthropic.Anthropic', create=True)
def test_get_llm_client_anthropic(mock_anthropic_constructor, mock_repo):
    """Test _get_llm_client returns and caches Anthropic client."""
    config = AnthropicConfig(api_key="test_anthropic_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    mock_anthropic_instance = MagicMock()
    mock_anthropic_constructor.return_value = mock_anthropic_instance

    client = summarizer._get_llm_client()
    mock_anthropic_constructor.assert_called_once_with(api_key="test_anthropic_key")
    assert client == mock_anthropic_instance

    # Call again to check caching
    client2 = summarizer._get_llm_client()
    mock_anthropic_constructor.assert_called_once() # Should not be called again
    assert client2 == client

@patch('google.generativeai.configure', create=True)
@patch('google.generativeai.GenerativeModel', create=True)
def test_get_llm_client_google(mock_google_generativemodel_constructor, mock_google_configure, mock_repo):
    """Test _get_llm_client returns and caches Google client."""
    config = GoogleConfig(api_key="test_google_key", model="gemini-test")
    summarizer = Summarizer(repo=mock_repo, config=config)
    mock_model_instance = MagicMock()
    mock_google_generativemodel_constructor.return_value = mock_model_instance

    client = summarizer._get_llm_client()
    mock_google_configure.assert_called_once_with(api_key="test_google_key")
    mock_google_generativemodel_constructor.assert_called_once_with("gemini-test")
    assert client == mock_model_instance

    # Call again to check caching
    client2 = summarizer._get_llm_client()
    mock_google_configure.assert_called_once() # Should not be called again
    mock_google_generativemodel_constructor.assert_called_once() # Should not be called again
    assert client2 == client

# --- Test summarize_file ---

@patch('kit.summaries.os.path.exists')
@patch('builtins.open')
@patch('openai.OpenAI', create=True) # To mock the client obtained via _get_llm_client
def test_summarize_file_openai(mock_openai_constructor, mock_open_file, mock_path_exists, mock_repo, temp_code_file):
    """Test summarize_file with OpenAIConfig."""
    mock_path_exists.return_value = True
    mock_file_content = "def hello():\n    print('Hello, world!')"
    mock_open_file.return_value.__enter__.return_value.read.return_value = mock_file_content

    # Mock the OpenAI client and its response
    mock_openai_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "This is an OpenAI summary."
    mock_openai_client_instance.chat.completions.create.return_value = mock_response
    mock_openai_constructor.return_value = mock_openai_client_instance # Mock the constructor

    config = OpenAIConfig(api_key="test_openai_key", model="gpt-test", temperature=0.5, max_tokens=100)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_to_summarize = "sample_code.py"
    summary = summarizer.summarize_file(file_to_summarize)

    abs_file_path = f"/abs/path/to/{file_to_summarize}"
    mock_repo.get_abs_path.assert_called_once_with(file_to_summarize)
    mock_path_exists.assert_called_once_with(abs_file_path)
    mock_open_file.assert_called_once_with(abs_file_path, 'r', encoding='utf-8')

    expected_system_prompt = "You are an expert assistant skilled in creating concise and informative code summaries."
    expected_user_prompt = f"Summarize the following code from the file '{file_to_summarize}'. Provide a high-level overview of its purpose, key components, and functionality. Focus on what the code does, not just how it's written. The code is:\n\n```\n{mock_file_content}\n```"

    mock_openai_client_instance.chat.completions.create.assert_called_once_with(
        model="gpt-test",
        messages=[
            {"role": "system", "content": expected_system_prompt},
            {"role": "user", "content": expected_user_prompt}
        ],
        temperature=0.5,
        max_tokens=100,
    )

    assert summary == "This is an OpenAI summary."

def test_summarize_file_not_found(mock_repo):
    """Test summarize_file raises FileNotFoundError if file does not exist."""
    with patch('kit.summaries.os.path.exists', return_value=False):
        config = OpenAIConfig(api_key="test_key") # Any config will do
        summarizer = Summarizer(repo=mock_repo, config=config)
        with pytest.raises(FileNotFoundError):
            summarizer.summarize_file("non_existent_file.py")

@patch('openai.OpenAI', create=True)
def test_summarize_file_llm_error_empty_summary(mock_openai_constructor, mock_repo, temp_code_file):
    """Test summarize_file raises LLMError if LLM returns an empty summary."""
    with patch('kit.summaries.os.path.exists', return_value=True):
        with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="code")))))):
            mock_openai_client_instance = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "" # Empty summary
            mock_openai_client_instance.chat.completions.create.return_value = mock_response
            mock_openai_constructor.return_value = mock_openai_client_instance

            config = OpenAIConfig(api_key="test_key")
            summarizer = Summarizer(repo=mock_repo, config=config)
            with pytest.raises(LLMError, match="LLM returned an empty summary."):
                summarizer.summarize_file(temp_code_file)

@patch('openai.OpenAI', create=True)
def test_summarize_file_llm_api_error(mock_openai_constructor, mock_repo, temp_code_file):
    """Test summarize_file raises LLMError on API communication failure."""
    with patch('kit.summaries.os.path.exists', return_value=True):
        with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="code")))))):
            mock_openai_client_instance = MagicMock()
            mock_openai_client_instance.chat.completions.create.side_effect = Exception("API Down")
            mock_openai_constructor.return_value = mock_openai_client_instance

            config = OpenAIConfig(api_key="test_key")
            summarizer = Summarizer(repo=mock_repo, config=config)
            with pytest.raises(LLMError, match="Error communicating with LLM API: API Down"):
                summarizer.summarize_file(temp_code_file)

@patch('kit.summaries.os.path.exists')
@patch('builtins.open')
@patch('anthropic.Anthropic', create=True) # Mock Anthropic client
def test_summarize_file_anthropic(mock_anthropic_constructor, mock_open_file, mock_path_exists, mock_repo, temp_code_file):
    """Test summarize_file with AnthropicConfig."""
    mock_path_exists.return_value = True
    mock_file_content = "class Simple:\n    pass"
    mock_open_file.return_value.__enter__.return_value.read.return_value = mock_file_content

    # Mock the Anthropic client and its response
    mock_anthropic_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.content[0].text = "This is an Anthropic summary."
    mock_anthropic_client_instance.messages.create.return_value = mock_response
    mock_anthropic_constructor.return_value = mock_anthropic_client_instance

    config = AnthropicConfig(api_key="test_anthropic_key", model="claude-test", temperature=0.6, max_tokens=150)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_to_summarize = "sample_anthropic_code.py"
    summary = summarizer.summarize_file(file_to_summarize)

    abs_file_path = f"/abs/path/to/{file_to_summarize}"
    mock_repo.get_abs_path.assert_called_once_with(file_to_summarize)
    mock_path_exists.assert_called_once_with(abs_file_path)
    mock_open_file.assert_called_once_with(abs_file_path, 'r', encoding='utf-8')

    expected_system_prompt = "You are an expert assistant skilled in creating concise and informative code summaries."
    expected_user_prompt = f"Summarize the following code from the file '{file_to_summarize}'. Provide a high-level overview of its purpose, key components, and functionality. Focus on what the code does, not just how it's written. The code is:\n\n```\n{mock_file_content}\n```"

    mock_anthropic_client_instance.messages.create.assert_called_once_with(
        model="claude-test",
        system=expected_system_prompt,
        messages=[
            {"role": "user", "content": expected_user_prompt}
        ],
        temperature=0.6,
        max_tokens=150,
    )

    assert summary == "This is an Anthropic summary."

@patch('kit.summaries.os.path.exists')
@patch('builtins.open')
@patch('google.generativeai.configure', create=True) # Mock Google SDK
@patch('google.generativeai.GenerativeModel', create=True) # Mock Google SDK
def test_summarize_file_google(mock_google_generativemodel_constructor, mock_google_configure, mock_open_file, mock_path_exists, mock_repo, temp_code_file):
    """Test summarize_file with GoogleConfig."""
    mock_path_exists.return_value = True
    mock_file_content = "# A simple Python script\nprint('Google AI is fun!')"
    mock_open_file.return_value.__enter__.return_value.read.return_value = mock_file_content

    # Mock the Google client (GenerativeModel instance) and its response
    mock_google_model_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a Google summary."
    mock_google_model_instance.generate_content.return_value = mock_response
    mock_google_generativemodel_constructor.return_value = mock_google_model_instance # Mock the constructor of GenerativeModel

    config = GoogleConfig(api_key="test_google_key", model="gemini-pro-test", temperature=0.7, max_output_tokens=200)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_to_summarize = "sample_google_code.py"
    summary = summarizer.summarize_file(file_to_summarize)

    abs_file_path = f"/abs/path/to/{file_to_summarize}"
    mock_repo.get_abs_path.assert_called_once_with(file_to_summarize)
    mock_path_exists.assert_called_once_with(abs_file_path)
    mock_open_file.assert_called_once_with(abs_file_path, 'r', encoding='utf-8')

    expected_system_prompt = "You are an expert assistant skilled in creating concise and informative code summaries."
    expected_user_prompt = f"Summarize the following code from the file '{file_to_summarize}'. Provide a high-level overview of its purpose, key components, and functionality. Focus on what the code does, not just how it's written. The code is:\n\n```\n{mock_file_content}\n```"
    expected_full_prompt = f"{expected_system_prompt}\n\n{expected_user_prompt}"

    mock_google_configure.assert_called_once_with(api_key="test_google_key")
    mock_google_generativemodel_constructor.assert_called_once_with("gemini-pro-test")
    
    mock_google_model_instance.generate_content.assert_called_once_with(
        contents=[expected_full_prompt],
        generation_config={
            'temperature': 0.7,
            'max_output_tokens': 200,
            'candidate_count': 1
        }
    )

    assert summary == "This is a Google summary."

# --- Test summarize_function ---

@patch('openai.OpenAI', create=True) # To mock the client obtained via _get_llm_client
def test_summarize_function_openai(mock_openai_constructor, mock_repo):
    """Test summarize_function with OpenAIConfig."""
    mock_function_code = "def my_func(a, b):\n    return a + b"
    mock_repo.get_symbol_text.return_value = mock_function_code

    # Mock the OpenAI client and its response
    mock_openai_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "This is an OpenAI function summary."
    mock_openai_client_instance.chat.completions.create.return_value = mock_response
    mock_openai_constructor.return_value = mock_openai_client_instance

    config = OpenAIConfig(api_key="test_openai_key", model="gpt-func-test", temperature=0.4, max_tokens=90)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_path = "src/module.py"
    function_name = "my_func"
    summary = summarizer.summarize_function(file_path, function_name)

    mock_repo.get_symbol_text.assert_called_once_with(file_path, function_name)

    expected_system_prompt = "You are an expert assistant skilled in creating concise code summaries for functions."
    expected_user_prompt = f"Summarize the following Python function named '{function_name}' from the file '{file_path}'. Describe its purpose, parameters, and return value. The function code is:\n\n```python\n{mock_function_code}\n```"

    mock_openai_client_instance.chat.completions.create.assert_called_once_with(
        model="gpt-func-test",
        messages=[
            {"role": "system", "content": expected_system_prompt},
            {"role": "user", "content": expected_user_prompt}
        ],
        temperature=0.4,
        max_tokens=90,
    )

    assert summary == "This is an OpenAI function summary."

def test_summarize_function_not_found(mock_repo):
    """Test summarize_function raises ValueError if function symbol is not found."""
    mock_repo.get_symbol_text.return_value = None # Simulate symbol not found
    config = OpenAIConfig(api_key="test_key") # Can use any config for this test
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(ValueError, match="Could not find function 'non_existent_func' in 'some_file.py'."):
        summarizer.summarize_function("some_file.py", "non_existent_func")

@patch('openai.OpenAI', create=True)
def test_summarize_function_llm_error_empty_summary(mock_openai_constructor, mock_repo):
    """Test summarize_function raises LLMError if LLM returns an empty summary."""
    mock_repo.get_symbol_text.return_value = "def f(): pass"
    mock_openai_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "" # Empty summary
    mock_openai_client_instance.chat.completions.create.return_value = mock_response
    mock_openai_constructor.return_value = mock_openai_client_instance

    config = OpenAIConfig(api_key="test_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(LLMError, match="LLM returned an empty summary for function my_func_empty."):
        summarizer.summarize_function("file.py", "my_func_empty")

@patch('openai.OpenAI', create=True)
def test_summarize_function_llm_api_error(mock_openai_constructor, mock_repo):
    """Test summarize_function raises LLMError on API communication failure."""
    mock_repo.get_symbol_text.return_value = "def f(): pass"
    mock_openai_client_instance = MagicMock()
    mock_openai_client_instance.chat.completions.create.side_effect = Exception("API Error")
    mock_openai_constructor.return_value = mock_openai_client_instance

    config = OpenAIConfig(api_key="test_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(LLMError, match="Error communicating with LLM API for function my_func_api_err: API Error"):
        summarizer.summarize_function("file.py", "my_func_api_err")

@patch('anthropic.Anthropic', create=True) # Mock Anthropic client
def test_summarize_function_anthropic(mock_anthropic_constructor, mock_repo):
    """Test summarize_function with AnthropicConfig."""
    mock_function_code = "def greet(name: str) -> str:\n    return f'Hello, {name}'"
    mock_repo.get_symbol_text.return_value = mock_function_code

    mock_anthropic_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.content[0].text = "This is an Anthropic function summary."
    mock_anthropic_client_instance.messages.create.return_value = mock_response
    mock_anthropic_constructor.return_value = mock_anthropic_client_instance

    config = AnthropicConfig(api_key="test_anthropic_key", model="claude-func-test", temperature=0.5, max_tokens=100)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_path = "src/greetings.py"
    function_name = "greet"
    summary = summarizer.summarize_function(file_path, function_name)

    mock_repo.get_symbol_text.assert_called_once_with(file_path, function_name)

    expected_system_prompt = "You are an expert assistant skilled in creating concise code summaries for functions."
    expected_user_prompt = f"Summarize the following Python function named '{function_name}' from the file '{file_path}'. Describe its purpose, parameters, and return value. The function code is:\n\n```python\n{mock_function_code}\n```"

    mock_anthropic_client_instance.messages.create.assert_called_once_with(
        model="claude-func-test",
        system=expected_system_prompt,
        messages=[
            {"role": "user", "content": expected_user_prompt}
        ],
        temperature=0.5,
        max_tokens=100,
    )

    assert summary == "This is an Anthropic function summary."

@patch('google.generativeai.configure', create=True) # Mock Google SDK
@patch('google.generativeai.GenerativeModel', create=True) # Mock Google SDK
def test_summarize_function_google(mock_google_generativemodel_constructor, mock_google_configure, mock_repo):
    """Test summarize_function with GoogleConfig."""
    mock_function_code = "def calculate_sum(numbers: list[int]) -> int:\n    return sum(numbers)"
    mock_repo.get_symbol_text.return_value = mock_function_code

    mock_google_model_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a Google function summary."
    mock_google_model_instance.generate_content.return_value = mock_response
    mock_google_generativemodel_constructor.return_value = mock_google_model_instance

    config = GoogleConfig(api_key="test_google_key", model="gemini-func-test", temperature=0.6, max_output_tokens=120)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_path = "src/calculator.py"
    function_name = "calculate_sum"
    summary = summarizer.summarize_function(file_path, function_name)

    mock_repo.get_symbol_text.assert_called_once_with(file_path, function_name)

    expected_system_prompt = "You are an expert assistant skilled in creating concise code summaries for functions."
    expected_user_prompt = f"Summarize the following Python function named '{function_name}' from the file '{file_path}'. Describe its purpose, parameters, and return value. The function code is:\n\n```python\n{mock_function_code}\n```"
    expected_full_prompt = f"{expected_system_prompt}\n\n{expected_user_prompt}"

    mock_google_configure.assert_called_once_with(api_key="test_google_key")
    mock_google_generativemodel_constructor.assert_called_once_with("gemini-func-test")
    
    mock_google_model_instance.generate_content.assert_called_once_with(
        contents=[expected_full_prompt],
        generation_config={
            'temperature': 0.6,
            'max_output_tokens': 120,
            'candidate_count': 1
        }
    )

    assert summary == "This is a Google function summary."

# --- Test summarize_class ---

@patch('openai.OpenAI', create=True) # To mock the client obtained via _get_llm_client
def test_summarize_class_openai(mock_openai_constructor, mock_repo):
    """Test summarize_class with OpenAIConfig."""
    mock_class_code = "class MyClass:\n    def __init__(self, x):\n        self.x = x\n\n    def get_x(self):\n        return self.x"
    mock_repo.get_symbol_text.return_value = mock_class_code

    # Mock the OpenAI client and its response
    mock_openai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "This is an OpenAI class summary."
    mock_openai_client.chat.completions.create.return_value = mock_response
    mock_openai_constructor.return_value = mock_openai_client

    config = OpenAIConfig(api_key="test_openai_key", model="gpt-class-test", temperature=0.3, max_tokens=110)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_path = "src/data_model.py"
    class_name = "MyClass"
    summary = summarizer.summarize_class(file_path, class_name)

    mock_repo.get_symbol_text.assert_called_once_with(file_path, class_name)

    expected_system_prompt = "You are an expert assistant skilled in creating concise code summaries for classes."
    expected_user_prompt = f"Summarize the following Python class named '{class_name}' from the file '{file_path}'. Describe its purpose, key attributes, and main methods. The class code is:\n\n```python\n{mock_class_code}\n```"

    mock_openai_client.chat.completions.create.assert_called_once_with(
        model="gpt-class-test",
        messages=[
            {"role": "system", "content": expected_system_prompt},
            {"role": "user", "content": expected_user_prompt}
        ],
        temperature=0.3,
        max_tokens=110,
    )

    assert summary == "This is an OpenAI class summary."

def test_summarize_class_not_found(mock_repo):
    """Test summarize_class raises ValueError if class symbol is not found."""
    mock_repo.get_symbol_text.return_value = None # Simulate symbol not found
    config = OpenAIConfig(api_key="test_key") # Can use any config
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(ValueError, match="Could not find class 'NonExistentClass' in 'another_file.py'."):
        summarizer.summarize_class("another_file.py", "NonExistentClass")

@patch('openai.OpenAI', create=True)
def test_summarize_class_llm_error_empty_summary(mock_openai_constructor, mock_repo):
    """Test summarize_class raises LLMError if LLM returns an empty summary."""
    mock_repo.get_symbol_text.return_value = "class C: pass"
    mock_openai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "" # Empty summary
    mock_openai_client.chat.completions.create.return_value = mock_response
    mock_openai_constructor.return_value = mock_openai_client

    config = OpenAIConfig(api_key="test_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(LLMError, match="LLM returned an empty summary for class MyClass_empty."):
        summarizer.summarize_class("file.py", "MyClass_empty")

@patch('openai.OpenAI', create=True)
def test_summarize_class_llm_api_error(mock_openai_constructor, mock_repo):
    """Test summarize_class raises LLMError on API communication failure."""
    mock_repo.get_symbol_text.return_value = "class C: pass"
    mock_openai_client = MagicMock()
    mock_openai_client.chat.completions.create.side_effect = Exception("API Crash")
    mock_openai_constructor.return_value = mock_openai_client

    config = OpenAIConfig(api_key="test_key")
    summarizer = Summarizer(repo=mock_repo, config=config)
    with pytest.raises(LLMError, match="Error communicating with LLM API for class MyClass_api_err: API Crash"):
        summarizer.summarize_class("file.py", "MyClass_api_err")

@patch('anthropic.Anthropic', create=True) # Mock Anthropic client
def test_summarize_class_anthropic(mock_anthropic_constructor, mock_repo):
    """Test summarize_class with AnthropicConfig."""
    mock_class_code = "class DataProcessor:\n    def __init__(self, data):\n        self.data = data\n\n    def process(self):\n        return len(self.data)"
    mock_repo.get_symbol_text.return_value = mock_class_code

    mock_anthropic_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content[0].text = "This is an Anthropic class summary."
    mock_anthropic_client.messages.create.return_value = mock_response
    mock_anthropic_constructor.return_value = mock_anthropic_client

    config = AnthropicConfig(api_key="test_anthropic_key", model="claude-class-test", temperature=0.4, max_tokens=120)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_path = "src/processing.py"
    class_name = "DataProcessor"
    summary = summarizer.summarize_class(file_path, class_name)

    mock_repo.get_symbol_text.assert_called_once_with(file_path, class_name)

    expected_system_prompt = "You are an expert assistant skilled in creating concise code summaries for classes."
    expected_user_prompt = f"Summarize the following Python class named '{class_name}' from the file '{file_path}'. Describe its purpose, key attributes, and main methods. The class code is:\n\n```python\n{mock_class_code}\n```"

    mock_anthropic_client.messages.create.assert_called_once_with(
        model="claude-class-test",
        system=expected_system_prompt,
        messages=[
            {"role": "user", "content": expected_user_prompt}
        ],
        temperature=0.4,
        max_tokens=120,
    )

    assert summary == "This is an Anthropic class summary."

@patch('google.generativeai.configure', create=True) # Mock Google SDK
@patch('google.generativeai.GenerativeModel', create=True) # Mock Google SDK
def test_summarize_class_google(mock_google_generativemodel_constructor, mock_google_configure, mock_repo):
    """Test summarize_class with GoogleConfig."""
    mock_class_code = "class Logger:\n    def __init__(self, level='INFO'):\n        self.level = level\n\n    def log(self, message):\n        print(f'[{self.level}] {message}')"
    mock_repo.get_symbol_text.return_value = mock_class_code

    mock_google_model_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a Google class summary."
    mock_google_model_instance.generate_content.return_value = mock_response
    mock_google_generativemodel_constructor.return_value = mock_google_model_instance

    config = GoogleConfig(api_key="test_google_key", model="gemini-class-test", temperature=0.5, max_output_tokens=130)
    summarizer = Summarizer(repo=mock_repo, config=config)

    file_path = "src/utils.py"
    class_name = "Logger"
    summary = summarizer.summarize_class(file_path, class_name)

    mock_repo.get_symbol_text.assert_called_once_with(file_path, class_name)

    expected_system_prompt = "You are an expert assistant skilled in creating concise code summaries for classes."
    expected_user_prompt = f"Summarize the following Python class named '{class_name}' from the file '{file_path}'. Describe its purpose, key attributes, and main methods. The class code is:\n\n```python\n{mock_class_code}\n```"
    expected_full_prompt = f"{expected_system_prompt}\n\n{expected_user_prompt}"

    mock_google_configure.assert_called_once_with(api_key="test_google_key")
    mock_google_generativemodel_constructor.assert_called_once_with("gemini-class-test")
    
    mock_google_model_instance.generate_content.assert_called_once_with(
        contents=[expected_full_prompt],
        generation_config={
            'temperature': 0.5,
            'max_output_tokens': 130,
            'candidate_count': 1
        }
    )

    assert summary == "This is a Google class summary."
