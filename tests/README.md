# Test Suite Documentation

This directory contains comprehensive tests for the kit project, including unit tests, integration tests, and LLM accuracy tests.

## Test Categories

### 🚀 Fast Tests (Default)
These run in CI and don't require external dependencies:
```bash
# Run all fast tests (excludes LLM tests)
pytest

# Run specific test categories
pytest tests/test_pr_review.py           # PR review functionality 
pytest tests/test_diff_parser.py         # Diff parsing unit tests
pytest tests/test_diff_integration.py    # Diff parsing integration tests
```

### 🧪 Integration Tests
Tests that verify end-to-end functionality:
```bash
# Run integration tests
pytest -m integration

# Run integration tests excluding LLM calls
pytest -m "integration and not llm"
```

### 🤖 LLM Tests (Expensive)
Tests that actually call LLM APIs.

**Requirements:**
- API keys: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
- These tests cost money and are slow
- Automatically skipped in CI environments

```bash
# Run LLM tests (requires API keys)
pytest -m llm

# Run specific LLM test
pytest tests/test_llm_line_accuracy.py::TestLLMLineAccuracy::test_llm_with_accurate_context
```

### 💰 Expensive Tests
Large-scale tests that may be slow or costly:
```bash
# Run expensive tests (includes LLM tests)
pytest -m expensive
```

## Test Markers

| Marker | Description | Auto-skipped in CI |
|--------|-------------|-------------------|
| `integration` | Integration tests | No |
| `llm` | Tests that call LLM APIs | Yes |
| `expensive` | Slow/costly tests | Yes |

## Line Number Accuracy Tests


### What These Tests Do
1. **Before/After Comparison** - Test LLM accuracy with vs without our context
2. **Real API Calls** - Actually call Anthropic/OpenAI APIs
3. **Accuracy Measurement** - Validate that 70-80%+ of line references are correct
4. **Multi-file Testing** - Test accuracy across multiple changed files

### Running LLM Tests Locally

1. **Set up API keys:**
   ```bash
   export ANTHROPIC_API_KEY="your-key-here"
   # OR
   export OPENAI_API_KEY="your-key-here"
   ```

2. **Run tests:**
   ```bash
   # Run all LLM tests
   pytest tests/test_llm_line_accuracy.py -v
   
   # Run specific test
   pytest tests/test_llm_line_accuracy.py::TestLLMLineAccuracy::test_llm_without_context_comparison -v -s
   ```

3. **Expected costs:**
   - Uses cheaper models (`claude-3-5-haiku`, `gpt-4o-mini`)
   - ~$0.01-0.05 per test run
   - Total test suite: ~$0.20-0.50

## CI Behavior

- **GitHub Actions** and other CI environments automatically skip LLM tests
- Only fast unit and integration tests run in CI
- Developers can run LLM tests locally to verify improvements

## Troubleshooting

### Import Errors
If you see import errors when running tests:
```bash
# Install in development mode
pip install -e .

# Or install with test dependencies
pip install -e .[test-api]
```

### API Key Issues
LLM tests will be automatically skipped if:
- No API keys are found
- Running in CI environment
- API calls fail

### Test Performance
```bash
# Run fast tests only
pytest --ignore=tests/test_llm_line_accuracy.py

# Run with minimal output
pytest -q

# Run specific test file
pytest tests/test_diff_parser.py -v
``` 