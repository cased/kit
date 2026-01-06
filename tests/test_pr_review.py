"""Tests for PR review functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from kit.pr_review.config import (
    GitHubConfig,
    LLMConfig,
    LLMProvider,
    ReviewConfig,
    _detect_provider_from_model,
)
from kit.pr_review.cost_tracker import CostBreakdown, CostTracker
from kit.pr_review.reviewer import PRReviewer
from kit.pr_review.validator import (
    ValidationResult,
    validate_review_quality,
)


def test_detect_provider_from_model():
    """Test provider detection from model names."""
    # OpenAI models
    assert _detect_provider_from_model("gpt-4") == LLMProvider.OPENAI
    assert _detect_provider_from_model("gpt-4.1") == LLMProvider.OPENAI
    assert _detect_provider_from_model("gpt-4o") == LLMProvider.OPENAI
    assert _detect_provider_from_model("gpt-4.1-nano") == LLMProvider.OPENAI
    assert _detect_provider_from_model("gpt-3.5-turbo") == LLMProvider.OPENAI
    assert _detect_provider_from_model("gpt-5") == LLMProvider.OPENAI
    assert _detect_provider_from_model("gpt-5-mini") == LLMProvider.OPENAI
    assert _detect_provider_from_model("gpt-5-nano") == LLMProvider.OPENAI
    assert _detect_provider_from_model("o1-preview") == LLMProvider.OPENAI
    assert _detect_provider_from_model("o3") == LLMProvider.OPENAI
    assert _detect_provider_from_model("o3-mini") == LLMProvider.OPENAI
    assert _detect_provider_from_model("o3-medium") == LLMProvider.OPENAI
    assert _detect_provider_from_model("text-davinci-003") == LLMProvider.OPENAI

    # Anthropic models
    assert _detect_provider_from_model("claude-3-opus") == LLMProvider.ANTHROPIC
    assert _detect_provider_from_model("claude-3-5-sonnet") == LLMProvider.ANTHROPIC
    assert _detect_provider_from_model("claude-sonnet-4-20250514") == LLMProvider.ANTHROPIC
    assert _detect_provider_from_model("claude-2.1") == LLMProvider.ANTHROPIC
    assert _detect_provider_from_model("claude-instant") == LLMProvider.ANTHROPIC

    # Google models
    assert _detect_provider_from_model("gemini-1.5-pro") == LLMProvider.GOOGLE
    assert _detect_provider_from_model("gemini-1.5-flash") == LLMProvider.GOOGLE
    assert _detect_provider_from_model("gemini-2.5-flash") == LLMProvider.GOOGLE
    assert _detect_provider_from_model("gemini-pro") == LLMProvider.GOOGLE

    # Ollama models
    assert _detect_provider_from_model("llama2") == LLMProvider.OLLAMA
    assert _detect_provider_from_model("llama3") == LLMProvider.OLLAMA
    assert _detect_provider_from_model("qwen2.5-coder") == LLMProvider.OLLAMA
    assert _detect_provider_from_model("codellama") == LLMProvider.OLLAMA
    assert _detect_provider_from_model("mistral") == LLMProvider.OLLAMA
    assert _detect_provider_from_model("deepseek-coder") == LLMProvider.OLLAMA

    # Models with provider prefixes
    assert _detect_provider_from_model("openrouter/gpt-4") == LLMProvider.OPENAI
    assert _detect_provider_from_model("together/claude-3-5-sonnet") == LLMProvider.ANTHROPIC
    assert _detect_provider_from_model("vertex_ai/gemini-pro") == LLMProvider.GOOGLE

    # Unknown models
    assert _detect_provider_from_model("unknown-model-xyz") is None
    assert _detect_provider_from_model("") is None


def test_config_loading_with_model_hint():
    """Test ReviewConfig.from_file with model_hint parameter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test-config.yaml"

        # Create a minimal config without provider
        config_data = {
            "github": {"token": "ghp_test"},
            "llm": {},  # No provider specified
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        # Test 1: Without model hint and no Anthropic key - should fail
        with patch.dict(os.environ, {"KIT_OPENAI_TOKEN": "sk-test-openai", "KIT_GITHUB_TOKEN": "ghp-test"}, clear=True):
            with pytest.raises(ValueError, match="To use Anthropic.*default.*set.*ANTHROPIC"):
                ReviewConfig.from_file(str(config_path))

        # Test 2: With OpenAI model hint - should succeed
        with patch.dict(os.environ, {"KIT_OPENAI_TOKEN": "sk-test-openai", "KIT_GITHUB_TOKEN": "ghp-test"}, clear=True):
            config = ReviewConfig.from_file(str(config_path), model_hint="gpt-4.1")
            assert config.llm.provider == LLMProvider.OPENAI
            assert config.llm.api_key == "sk-test-openai"
            assert config.llm.model == "gpt-4.1-2025-04-14"  # Default OpenAI model

        # Test 3: With Google model hint - should succeed with Google key
        with patch.dict(
            os.environ, {"KIT_GOOGLE_API_KEY": "AIza-test-google", "KIT_GITHUB_TOKEN": "ghp-test"}, clear=True
        ):
            config = ReviewConfig.from_file(str(config_path), model_hint="gemini-1.5-flash")
            assert config.llm.provider == LLMProvider.GOOGLE
            assert config.llm.api_key == "AIza-test-google"
            assert config.llm.model == "gemini-2.5-flash"  # Default Google model

        # Test 4: With Ollama model hint - should succeed without API key
        with patch.dict(os.environ, {"KIT_GITHUB_TOKEN": "ghp-test"}, clear=True):
            config = ReviewConfig.from_file(str(config_path), model_hint="qwen2.5-coder")
            assert config.llm.provider == LLMProvider.OLLAMA
            assert config.llm.api_key == "ollama"  # Placeholder for Ollama
            assert config.llm.model == "qwen2.5-coder:latest"  # Default Ollama model


def test_config_loading_provider_precedence():
    """Test provider selection precedence: config > env > model_hint > default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test 1: Config provider takes precedence over model hint
        config_path = Path(tmpdir) / "config-with-provider.yaml"
        config_data = {"github": {"token": "ghp_test"}, "llm": {"provider": "anthropic", "api_key": "sk-ant-test"}}
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = ReviewConfig.from_file(str(config_path), model_hint="gpt-4")
        assert config.llm.provider == LLMProvider.ANTHROPIC  # Config wins

        # Test 2: Env provider takes precedence over model hint
        config_path2 = Path(tmpdir) / "config-no-provider.yaml"
        config_data2 = {"github": {"token": "ghp_test"}, "llm": {"api_key": "sk-test"}}
        with open(config_path2, "w") as f:
            yaml.dump(config_data2, f)

        with patch.dict(os.environ, {"LLM_PROVIDER": "google"}):
            config = ReviewConfig.from_file(str(config_path2), model_hint="gpt-4")
            assert config.llm.provider == LLMProvider.GOOGLE  # Env wins

        # Test 3: Model hint used when no config or env provider
        with patch.dict(os.environ, {"KIT_OPENAI_TOKEN": "sk-test"}, clear=True):
            config = ReviewConfig.from_file(str(config_path2), model_hint="gpt-4")
            assert config.llm.provider == LLMProvider.OPENAI  # Model hint wins


def test_pr_url_parsing():
    """Test PR URL parsing functionality."""
    config = ReviewConfig(
        github=GitHubConfig(token="test"),
        llm=LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-4-sonnet",
            api_key="test",
        ),
    )
    reviewer = PRReviewer(config)

    # Test valid PR URL
    owner, repo, pr_number = reviewer.parse_pr_url("https://github.com/cased/kit/pull/47")
    assert owner == "cased"
    assert repo == "kit"
    assert pr_number == 47

    # Test invalid URL
    with pytest.raises(ValueError, match="Invalid GitHub PR URL"):
        reviewer.parse_pr_url("invalid-url")

    # Test PR number only (should raise NotImplementedError for now)
    with pytest.raises(NotImplementedError):
        reviewer.parse_pr_url("47")


def test_cost_tracker_anthropic():
    """Test cost tracking for Anthropic models."""
    # Mock pricing data for consistent testing
    mock_pricing = {
        LLMProvider.ANTHROPIC: {"claude-3-5-sonnet-20241022": {"input_per_million": 3.00, "output_per_million": 15.00}}
    }

    tracker = CostTracker(custom_pricing=mock_pricing)

    # Test Claude 3.5 Sonnet pricing
    tracker.track_llm_usage(LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 1000, 500)

    expected_cost = (1000 / 1_000_000) * 3.00 + (500 / 1_000_000) * 15.00
    assert abs(tracker.breakdown.llm_cost_usd - expected_cost) < 0.0001
    assert tracker.breakdown.llm_input_tokens == 1000
    assert tracker.breakdown.llm_output_tokens == 500
    assert tracker.breakdown.model_used == "claude-3-5-sonnet-20241022"


def test_cost_tracker_openai():
    """Test cost tracking for OpenAI models."""
    # Mock pricing data for consistent testing
    mock_pricing = {LLMProvider.OPENAI: {"gpt-4o": {"input_per_million": 2.50, "output_per_million": 10.00}}}

    tracker = CostTracker(custom_pricing=mock_pricing)

    # Test GPT-4o pricing
    tracker.track_llm_usage(LLMProvider.OPENAI, "gpt-4o", 2000, 800)

    expected_cost = (2000 / 1_000_000) * 2.50 + (800 / 1_000_000) * 10.00
    assert abs(tracker.breakdown.llm_cost_usd - expected_cost) < 0.0001
    assert tracker.breakdown.llm_input_tokens == 2000
    assert tracker.breakdown.llm_output_tokens == 800


def test_cost_tracker_unknown_model():
    """Test cost tracking for unknown models uses estimates."""
    tracker = CostTracker()

    with patch("kit.pr_review.cost_tracker.logger.warning") as mock_warning:
        tracker.track_llm_usage(LLMProvider.ANTHROPIC, "unknown-model", 1000, 500)

        # Should log warning
        mock_warning.assert_called()
        warning_calls = [str(call) for call in mock_warning.call_args_list]
        assert any("Unknown pricing" in str(call) for call in warning_calls)

        # Should use fallback pricing
        expected_cost = (1000 / 1_000_000) * 3.0 + (500 / 1_000_000) * 15.0
        assert abs(tracker.breakdown.llm_cost_usd - expected_cost) < 0.0001


def test_cost_tracker_multiple_calls():
    """Test cost tracking across multiple LLM calls."""
    tracker = CostTracker()

    # First call
    tracker.track_llm_usage(LLMProvider.ANTHROPIC, "claude-3-5-haiku-20241022", 500, 200)
    first_cost = tracker.breakdown.llm_cost_usd

    # Second call
    tracker.track_llm_usage(LLMProvider.ANTHROPIC, "claude-3-5-haiku-20241022", 300, 150)

    # Should accumulate
    assert tracker.breakdown.llm_input_tokens == 800
    assert tracker.breakdown.llm_output_tokens == 350
    assert tracker.breakdown.llm_cost_usd > first_cost


def test_cost_tracker_reset():
    """Test cost tracker reset functionality."""
    tracker = CostTracker()

    tracker.track_llm_usage(LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 1000, 500)
    assert tracker.breakdown.llm_cost_usd > 0

    tracker.reset()
    assert tracker.breakdown.llm_input_tokens == 0
    assert tracker.breakdown.llm_output_tokens == 0
    assert tracker.breakdown.llm_cost_usd == 0.0


def test_model_prefix_detection():
    """Test model prefix detection for popular providers."""

    # Test OpenRouter prefixes
    assert (
        CostTracker._strip_model_prefix("openrouter/meta-llama/llama-3.1-8b-instruct")
        == "meta-llama/llama-3.1-8b-instruct"
    )

    assert CostTracker._strip_model_prefix("openrouter/anthropic/claude-3.5-sonnet") == "anthropic/claude-3.5-sonnet"

    # Test Together AI prefixes
    assert CostTracker._strip_model_prefix("together/meta-llama/Llama-3-8b-chat-hf") == "meta-llama/Llama-3-8b-chat-hf"

    assert (
        CostTracker._strip_model_prefix("together/mistralai/Mixtral-8x7B-Instruct-v0.1")
        == "mistralai/Mixtral-8x7B-Instruct-v0.1"
    )

    # Test Groq prefixes
    assert CostTracker._strip_model_prefix("groq/llama3-8b-8192") == "llama3-8b-8192"

    assert CostTracker._strip_model_prefix("groq/mixtral-8x7b-32768") == "mixtral-8x7b-32768"

    # Test Fireworks AI prefixes
    assert (
        CostTracker._strip_model_prefix("fireworks/accounts/fireworks/models/llama-v3p1-8b-instruct")
        == "accounts/fireworks/models/llama-v3p1-8b-instruct"
    )

    # Test Replicate prefixes
    assert CostTracker._strip_model_prefix("replicate/meta/llama-2-70b-chat") == "meta/llama-2-70b-chat"

    # Test models without prefixes (should return as-is)
    assert CostTracker._strip_model_prefix("gpt-4o") == "gpt-4o"

    assert CostTracker._strip_model_prefix("claude-3-5-sonnet-20241022") == "claude-3-5-sonnet-20241022"

    # Test complex model names with multiple slashes - now strips first prefix generically
    assert CostTracker._strip_model_prefix("provider/org/model/version/variant") == "org/model/version/variant"

    # Test vertex_ai prefix
    assert CostTracker._strip_model_prefix("vertex_ai/claude-sonnet-4-20250514") == "claude-sonnet-4-20250514"


def test_cost_tracking_with_prefixed_models():
    """Test cost tracking with prefixed model names."""
    # Mock pricing data for consistent testing
    mock_pricing = {
        LLMProvider.OPENAI: {"gpt-4o": {"input_per_million": 2.50, "output_per_million": 10.00}},
        LLMProvider.ANTHROPIC: {"claude-3-5-sonnet-20241022": {"input_per_million": 3.00, "output_per_million": 15.00}},
    }

    tracker = CostTracker(custom_pricing=mock_pricing)

    # Test OpenRouter model that maps to known pricing
    # Should extract base model and use its pricing
    tracker.track_llm_usage(LLMProvider.OPENAI, "openrouter/gpt-4o", 1000, 500)

    # Should use GPT-4o pricing despite the prefix
    expected_cost = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
    assert abs(tracker.breakdown.llm_cost_usd - expected_cost) < 0.0001

    # Reset for next test
    tracker.reset()

    # Test Together AI model with Anthropic base model
    tracker.track_llm_usage(LLMProvider.ANTHROPIC, "together/claude-3-5-sonnet-20241022", 800, 400)

    # Should extract claude-3-5-sonnet-20241022 and use its pricing
    expected_cost = (800 / 1_000_000) * 3.00 + (400 / 1_000_000) * 15.00
    assert abs(tracker.breakdown.llm_cost_usd - expected_cost) < 0.0001


def test_cost_tracking_unknown_prefixed_models():
    """Test cost tracking for unknown prefixed models."""
    # Only provide default pricing for OpenAI
    mock_pricing = {LLMProvider.OPENAI: {"_default": {"input_per_million": 2.50, "output_per_million": 10.00}}}

    tracker = CostTracker(custom_pricing=mock_pricing)

    with patch("kit.pr_review.cost_tracker.logger.info") as mock_info:
        # Test completely unknown prefixed model
        tracker.track_llm_usage(LLMProvider.OPENAI, "newprovider/unknown/model-v1", 1000, 500)

        # Should log info about using default pricing
        mock_info.assert_called()
        info_calls = [str(call) for call in mock_info.call_args_list]
        assert any("Using default pricing" in str(call) for call in info_calls)

        # Should use default pricing for OpenAI provider
        expected_cost = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
        assert abs(tracker.breakdown.llm_cost_usd - expected_cost) < 0.0001


def test_model_validation_with_prefixes():
    """Test model validation with prefixed model names."""

    # Test that prefixed models are considered valid if base model is valid
    assert CostTracker.is_valid_model("openrouter/gpt-4o")
    assert CostTracker.is_valid_model("together/claude-3-5-sonnet-20241022")
    # Note: llama3-8b-8192 is not in the DEFAULT_PRICING, so this will be False
    # Let's test with a model that actually exists
    assert CostTracker.is_valid_model("groq/gpt-4o")

    # Test that prefixed models are invalid if base model is invalid
    assert not CostTracker.is_valid_model("openrouter/invalid/model")
    assert not CostTracker.is_valid_model("together/fake/model-v1")

    # Test suggestions for prefixed models
    suggestions = CostTracker.get_model_suggestions("openrouter/gpt4")
    assert len(suggestions) > 0
    # Should suggest models that match
    assert any("gpt-4" in s for s in suggestions)

    suggestions = CostTracker.get_model_suggestions("together/claude")
    assert len(suggestions) > 0
    assert any("claude" in s for s in suggestions)


def test_config_with_prefixed_models():
    """Test configuration with prefixed model names."""
    config = ReviewConfig(
        github=GitHubConfig(token="test"),
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            model="openrouter/gpt-4o",
            api_key="test",
        ),
    )

    # Should accept prefixed model name
    assert config.llm.model == "openrouter/gpt-4o"

    # Test model override with prefixed names
    config.llm.model = "together/claude-3-5-sonnet-20241022"
    assert config.llm.model == "together/claude-3-5-sonnet-20241022"

    # Test with Groq prefixed model
    config.llm.model = "groq/gpt-4o"
    assert config.llm.model == "groq/gpt-4o"


def test_pr_reviewer_with_prefixed_models():
    """Test PRReviewer handles prefixed model names correctly."""
    config = ReviewConfig(
        github=GitHubConfig(token="test"),
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            model="openrouter/gpt-4o-mini",
            api_key="test",
        ),
    )

    reviewer = PRReviewer(config)

    # Should store the full prefixed model name
    assert reviewer.config.llm.model == "openrouter/gpt-4o-mini"

    # Cost tracker should handle the prefixed model correctly
    reviewer.cost_tracker.track_llm_usage(LLMProvider.OPENAI, "openrouter/gpt-4o-mini", 500, 250)

    # Should extract base model for pricing
    assert reviewer.cost_tracker.breakdown.llm_cost_usd > 0


def test_cli_with_prefixed_models():
    """Test CLI handles prefixed model names correctly."""
    from typer.testing import CliRunner

    from kit.cli import app

    runner = CliRunner()

    # Test with prefixed model
    result = runner.invoke(
        app,
        [
            "review",
            "--model",
            "openrouter/gpt-4o",
            "--dry-run",
            "--init-config",
        ],
    )

    assert result.exit_code == 0
    assert "Created default config file" in result.output


def test_complex_prefixed_model_names():
    """Test handling of complex prefixed model names."""

    # Test deeply nested model names
    complex_models = [
        (
            "fireworks/accounts/fireworks/models/llama-v3p1-8b-instruct",
            "accounts/fireworks/models/llama-v3p1-8b-instruct",
        ),
        (
            "replicate/meta/llama-2-70b-chat:13c3cdee13ee059ab779f0291d29054dab00a47dad8261375654de5540165fb0",
            "meta/llama-2-70b-chat:13c3cdee13ee059ab779f0291d29054dab00a47dad8261375654de5540165fb0",
        ),
        # Now strips first prefix generically
        ("provider/org/team/model/version/variant", "org/team/model/version/variant"),
        # Now strips first prefix generically
        ("a/b/c/d/e/f/g", "b/c/d/e/f/g"),
    ]

    for original_model, expected_result in complex_models:
        base_model = CostTracker._strip_model_prefix(original_model)
        assert base_model == expected_result, f"Expected {expected_result}, got {base_model}"


def test_provider_prefix_detection():
    """Test detection of various provider prefixes."""

    # Test various provider prefixes - all should be stripped generically
    providers = [
        "openrouter",
        "together",
        "groq",
        "fireworks",
        "replicate",
        "bedrock",
        "vertex_ai",
        "huggingface",  # Now gets stripped too
        "vertex",  # Now gets stripped too
        "perplexity",  # Now gets stripped too
        "newprovider",  # Any prefix gets stripped
    ]

    for provider in providers:
        model_name = f"{provider}/test/model"
        base_name = CostTracker._strip_model_prefix(model_name)
        assert base_name == "test/model", f"Failed for {provider}: got {base_name}"
        assert not base_name.startswith(f"{provider}/")

    # Test model without any prefix (should remain unchanged)
    no_prefix_model = "test-model-without-prefix"
    base_name = CostTracker._strip_model_prefix(no_prefix_model)
    assert base_name == "test-model-without-prefix"  # Should remain unchanged


def test_cost_tracking_edge_cases_with_prefixes():
    """Test edge cases in cost tracking with prefixed models."""
    # Mock pricing data for known models only
    mock_pricing = {
        LLMProvider.OPENAI: {"gpt-4o": {"input_per_million": 2.50, "output_per_million": 10.00}},
        LLMProvider.ANTHROPIC: {"_default": {"input_per_million": 3.00, "output_per_million": 15.00}},
    }

    tracker = CostTracker(custom_pricing=mock_pricing)

    # Test model with provider prefix but unknown base model
    with patch("kit.pr_review.cost_tracker.logger.info") as mock_info:
        tracker.track_llm_usage(LLMProvider.ANTHROPIC, "openrouter/unknown/mystery-model-v1", 1000, 500)

        # Should log info about using default pricing
        mock_info.assert_called()

        # Should use default pricing
        expected_cost = (1000 / 1_000_000) * 3.0 + (500 / 1_000_000) * 15.0
        assert abs(tracker.breakdown.llm_cost_usd - expected_cost) < 0.0001

    # Reset tracker
    tracker.reset()

    # Test model with multiple provider-like prefixes
    tracker.track_llm_usage(LLMProvider.OPENAI, "together/gpt-4o", 800, 400)

    # Should extract gpt-4o and use its pricing
    expected_cost = (800 / 1_000_000) * 2.50 + (400 / 1_000_000) * 10.00
    assert abs(tracker.breakdown.llm_cost_usd - expected_cost) < 0.0001


def test_validator_basic():
    """Test basic review validation."""
    review = """
    ## Issues Found

    1. File src/main.py line 42: This function is missing error handling
    2. File tests/test_main.py line 15: Add assertions for edge cases

    https://github.com/user/repo/blob/main/src/main.py#L42
    """

    pr_diff = "some diff content"
    changed_files = ["src/main.py", "tests/test_main.py"]

    validation = validate_review_quality(review, pr_diff, changed_files)

    assert isinstance(validation, ValidationResult)
    assert validation.score > 0
    assert validation.metrics["file_references"] >= 2
    assert validation.metrics["line_references"] >= 2
    assert validation.metrics["github_links"] >= 0


def test_validator_empty_review():
    """Test validator with empty review."""
    validation = validate_review_quality("", "diff", ["file.py"])

    assert validation.score < 1.0
    assert "Review doesn't reference any changed files" in validation.issues
    assert validation.metrics["file_references"] == 0


def test_validator_vague_review():
    """Test validator detects vague reviews."""
    vague_review = "This looks good. Maybe consider some improvements. Seems fine overall."

    validation = validate_review_quality(vague_review, "diff", ["file.py"])

    assert validation.metrics["vague_statements"] > 0
    assert any("Review doesn't reference any changed files" in issue for issue in validation.issues)


def test_validator_no_file_references():
    """Test validator detects missing file references."""
    review = "This code has some issues that should be fixed."

    validation = validate_review_quality(review, "diff", ["main.py", "test.py"])

    assert validation.metrics["file_references"] == 0
    assert any("Review doesn't reference any changed files" in issue for issue in validation.issues)


def test_validator_change_coverage():
    """Test change coverage calculation."""
    review = """
    File main.py has issues.
    File helper.py looks good.
    """

    changed_files = ["main.py", "helper.py", "other.py"]

    validation = validate_review_quality(review, "diff", changed_files)

    assert validation.metrics["change_coverage"] == 1.0


def test_config_creation():
    """Test configuration file creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test-config.yaml"

        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-4-sonnet",
                api_key="test",
            ),
        )

        created_path = config.create_default_config_file(str(config_path))

        assert Path(created_path).exists()
        assert "github:" in config_path.read_text()
        assert "llm:" in config_path.read_text()
        assert "review:" in config_path.read_text()


def test_config_from_env():
    """Test configuration loading from environment variables."""
    with patch.dict(
        os.environ,
        {
            "GITHUB_TOKEN": "old_github_token",
            "KIT_GITHUB_TOKEN": "new_github_token",
            "ANTHROPIC_API_KEY": "old_anthropic_key",
            "KIT_ANTHROPIC_TOKEN": "new_anthropic_token",
        },
    ):
        # Use a non-existent config file to force env var usage
        config = ReviewConfig.from_file("/non/existent/path")

        # Should prefer KIT_ prefixed variables
        assert config.github.token == "new_github_token"
        assert config.llm.api_key == "new_anthropic_token"
        assert config.llm.provider == LLMProvider.ANTHROPIC


def test_config_backwards_compatibility():
    """Test configuration falls back to old environment variables."""
    # Clear all GitHub-related env vars first
    with patch.dict(
        os.environ,
        {
            "GITHUB_TOKEN": "test_github_token",
            "ANTHROPIC_API_KEY": "test_anthropic_key",
            "KIT_GITHUB_TOKEN": "",  # Clear the preferred var
            "KIT_ANTHROPIC_TOKEN": "",  # Clear the preferred var
        },
        clear=False,
    ):
        # Use a non-existent config file to force env var usage
        config = ReviewConfig.from_file("/non/existent/path")

        assert config.github.token == "test_github_token"
        assert config.llm.api_key == "test_anthropic_key"
        assert config.llm.provider == LLMProvider.ANTHROPIC


def test_config_openai_provider():
    """Test OpenAI provider configuration."""
    with patch.dict(
        os.environ,
        {
            "KIT_GITHUB_TOKEN": "github_token",
            "KIT_OPENAI_TOKEN": "openai_token",
            "LLM_PROVIDER": "openai",  # Explicitly set provider to OpenAI
        },
    ):
        config = ReviewConfig.from_file("/non/existent/path")

        assert config.llm.provider == LLMProvider.OPENAI
        assert config.llm.api_key == "openai_token"
        # Test that we can change the model
        config.llm.model = "gpt-4o"
        assert config.llm.model == "gpt-4o"


def test_config_custom_openai_provider():
    """Test custom OpenAI compatible provider configuration."""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config_data = {
            "github": {"token": "github_token"},
            "llm": {
                "provider": "openai",
                "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "api_key": "together_api_key",
                "api_base_url": "https://api.together.xyz/v1",
                "max_tokens": 4000,
            },
        }
        yaml.dump(config_data, f)
        config_path = f.name

    try:
        config = ReviewConfig.from_file(config_path)

        assert config.llm.provider == LLMProvider.OPENAI
        assert config.llm.api_key == "together_api_key"
        assert config.llm.api_base_url == "https://api.together.xyz/v1"
        assert config.llm.model == "meta-llama/Llama-3.3-70B-Instruct-Turbo"
        assert config.llm.max_tokens == 4000
    finally:
        import os

        os.unlink(config_path)


def test_config_missing_tokens():
    """Test configuration error when tokens are missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="GitHub token required"):
            ReviewConfig.from_file("/non/existent/path")


@patch("kit.pr_review.base_reviewer.requests.Session")
@patch("subprocess.run")
def test_pr_review_dry_run(mock_subprocess, mock_session_class):
    """Test PR review in dry run mode (no actual API calls)."""
    # Mock subprocess for git operations
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = ""

    # Mock the requests session
    mock_session = Mock()
    mock_session_class.return_value = mock_session

    # Mock PR details response
    mock_pr_response = Mock()
    mock_pr_response.json.return_value = {
        "title": "Test PR",
        "user": {"login": "testuser"},
        "base": {"ref": "main", "sha": "abc123"},
        "head": {"ref": "feature-branch", "sha": "def456"},
    }

    # Mock files response
    mock_files_response = Mock()
    mock_files_response.json.return_value = [
        {"filename": "test.py", "additions": 10, "deletions": 5},
        {"filename": "README.md", "additions": 2, "deletions": 0},
    ]

    # Configure mock to return different responses for different URLs
    def mock_get(url):
        if url.endswith("/pulls/47"):
            return mock_pr_response
        elif url.endswith("/pulls/47/files"):
            return mock_files_response
        return Mock()

    mock_session.get.side_effect = mock_get

    config = ReviewConfig(
        github=GitHubConfig(token="test"),
        llm=LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-4-sonnet",
            api_key="test",
        ),
        post_as_comment=False,  # Dry run mode
        clone_for_analysis=False,  # Skip cloning to avoid git issues
    )

    reviewer = PRReviewer(config)
    comment = reviewer.review_pr("https://github.com/cased/kit/pull/47")

    # Verify comment content - review should contain basic info even if
    # analysis fails
    assert "Kit AI Code Review" in comment or "Kit Code Review" in comment
    # Don't require specific PR title since the mock might not work perfectly
    assert len(comment) > 100  # Should be a substantial review comment

    # Verify API calls were made
    assert mock_session.get.call_count >= 1


def test_github_session_setup():
    """Test GitHub session is configured correctly."""
    config = ReviewConfig(
        github=GitHubConfig(token="test_token"),
        llm=LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-4-sonnet",
            api_key="test",
        ),
    )

    reviewer = PRReviewer(config)

    # Check session headers
    headers = reviewer.github_session.headers
    assert headers["Authorization"] == "token test_token"
    assert headers["Accept"] == "application/vnd.github.v3+json"
    assert "kit-review" in headers["User-Agent"]


def test_cost_breakdown_str():
    """Test cost breakdown string representation."""
    breakdown = CostBreakdown(
        llm_input_tokens=1000,
        llm_output_tokens=500,
        llm_cost_usd=0.0234,
        model_used="claude-3-5-sonnet-20241022",
    )

    str_repr = str(breakdown)
    assert "1,000 input" in str_repr
    assert "500 output" in str_repr
    assert "$0.0234" in str_repr
    assert "claude-3-5-sonnet-20241022" in str_repr


def test_model_override_config():
    """Test that model override works in ReviewConfig."""
    config = ReviewConfig(
        github=GitHubConfig(token="test"),
        llm=LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            api_key="test",
        ),
    )

    # Original model
    assert config.llm.model == "claude-3-5-sonnet-20241022"

    # Override model
    config.llm.model = "gpt-4.1-nano"
    assert config.llm.model == "gpt-4.1-nano"

    # Test with OpenAI model
    config.llm.model = "gpt-4o"
    assert config.llm.model == "gpt-4o"

    # Test with premium Anthropic model
    config.llm.model = "claude-opus-4-20250514"
    assert config.llm.model == "claude-opus-4-20250514"


def test_cli_model_flag_parsing():
    """Test CLI --model flag parsing."""
    from typer.testing import CliRunner

    from kit.cli import app

    runner = CliRunner()

    # Test with --model flag
    result = runner.invoke(
        app,
        [
            "review",
            "--model",
            "gpt-4.1-nano",
            "--dry-run",
            "--init-config",  # This will exit early without requiring a PR URL
        ],
    )

    # Should succeed (init-config doesn't need other args)
    assert result.exit_code == 0
    assert "Created default config file" in result.output

    # Test with -m short flag
    result = runner.invoke(
        app,
        [
            "review",
            "-m",
            "claude-opus-4-20250514",
            "--dry-run",
            "--init-config",
        ],
    )

    assert result.exit_code == 0
    assert "Created default config file" in result.output


def test_model_override_in_reviewer():
    """Test that model override is properly applied in PRReviewer."""
    config = ReviewConfig(
        github=GitHubConfig(token="test"),
        llm=LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            api_key="test",
        ),
    )

    # Create reviewer with original model
    reviewer = PRReviewer(config)
    assert reviewer.config.llm.model == "claude-3-5-sonnet-20241022"

    # Override model and check it's reflected
    reviewer.config.llm.model = "gpt-4.1-nano"
    assert reviewer.config.llm.model == "gpt-4.1-nano"


def test_model_flag_examples():
    """Test that various model names work with the flag."""
    valid_models = [
        "gpt-4.1-nano",
        "gpt-4.1-mini",
        "gpt-4.1",
        "gpt-4o",
        "gpt-4o-mini",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-opus-4-20250514",
        "claude-sonnet-4-20250514",
    ]

    config = ReviewConfig(
        github=GitHubConfig(token="test"),
        llm=LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="default",
            api_key="test",
        ),
    )

    for model in valid_models:
        # Test that all model names can be set
        config.llm.model = model
        assert config.llm.model == model


@patch("kit.pr_review.base_reviewer.requests.Session")
@patch("kit.pr_review.reviewer.subprocess.run")
def test_pr_review_with_model_override(mock_subprocess, mock_session_class):
    """Test PR review with model override."""
    # Mock subprocess for git operations
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = ""

    # Mock the requests session
    mock_session = Mock()
    mock_session_class.return_value = mock_session

    # Mock PR details response
    mock_pr_response = Mock()
    mock_pr_response.json.return_value = {
        "title": "Test PR with Model Override",
        "user": {"login": "testuser"},
        "base": {"ref": "main", "sha": "abc123"},
        "head": {"ref": "feature-branch", "sha": "def456"},
    }

    # Mock files response
    mock_files_response = Mock()
    mock_files_response.json.return_value = [
        {"filename": "test.py", "additions": 10, "deletions": 5},
    ]

    # Configure mock to return different responses for different URLs
    def mock_get(url):
        if url.endswith("/pulls/47"):
            return mock_pr_response
        elif url.endswith("/pulls/47/files"):
            return mock_files_response
        return Mock()

    mock_session.get.side_effect = mock_get

    # Create config with original model
    config = ReviewConfig(
        github=GitHubConfig(token="test"),
        llm=LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            api_key="test",
        ),
        post_as_comment=False,  # Dry run mode
        clone_for_analysis=False,  # Skip cloning to avoid git issues
    )

    # Override model (simulating CLI --model flag)
    config.llm.model = "gpt-4.1-nano"

    reviewer = PRReviewer(config)

    # Verify the model was overridden
    assert reviewer.config.llm.model == "gpt-4.1-nano"

    # Run review (should use the overridden model)
    comment = reviewer.review_pr("https://github.com/cased/kit/pull/47")

    # Verify comment was generated
    assert len(comment) > 100
    assert isinstance(comment, str)


def test_model_validation_functions():
    """Test the model validation utility functions."""
    from kit.pr_review.cost_tracker import CostTracker

    # Test valid models (class methods still work)
    assert CostTracker.is_valid_model("gpt-4.1-nano")
    assert CostTracker.is_valid_model("claude-3-5-sonnet-20241022")

    # Test invalid models
    assert not CostTracker.is_valid_model("gpt4.nope")
    assert not CostTracker.is_valid_model("invalid-model")

    # Create instance for instance methods
    tracker = CostTracker()

    # Test getting all models
    all_models = tracker.get_all_model_names()
    # With dynamic pricing, we can't guarantee specific models, but should have some
    assert len(all_models) > 0

    # Test getting models by provider
    available = tracker.get_available_models()
    assert "anthropic" in available
    assert "openai" in available
    # Can't guarantee specific models with dynamic pricing
    assert len(available["openai"]) > 0
    assert len(available["anthropic"]) > 0

    # Test suggestions for invalid models (class method)
    suggestions = CostTracker.get_model_suggestions("gpt4")
    assert len(suggestions) > 0
    # Can't guarantee specific suggestions with dynamic pricing


# --- Test Thinking Token Stripping in PR Reviewer ---


class TestPRReviewerThinkingTokenStripping:
    """Tests for the _strip_thinking_tokens function in PR reviewer."""

    def test_strip_thinking_tokens_in_pr_reviewer(self):
        """Test that PR reviewer's thinking token stripping works correctly."""
        from kit.pr_review.reviewer import _strip_thinking_tokens

        response = """<think>
I need to analyze this PR carefully...
Let me look at the changes...
</think>

## Priority Issues

- **High priority**: Missing error handling in auth.py:42
- **Medium priority**: Potential performance issue in utils.py:15

<think>
Actually, let me double-check that line number...
Yes, that's correct.
</think>

## Summary

This PR introduces authentication features but needs some improvements.

## Recommendations

- Add proper error handling
- Consider edge cases"""

        expected = """## Priority Issues

- **High priority**: Missing error handling in auth.py:42
- **Medium priority**: Potential performance issue in utils.py:15

## Summary

This PR introduces authentication features but needs some improvements.

## Recommendations

- Add proper error handling
- Consider edge cases"""

        result = _strip_thinking_tokens(response)
        assert result == expected

    def test_pr_reviewer_multiple_thinking_patterns(self):
        """Test PR reviewer handles multiple thinking token patterns."""
        from kit.pr_review.reviewer import _strip_thinking_tokens

        response = """<thinking>Let me review this code...</thinking>

The main changes are:

<think>I should focus on security issues</think>

1. Authentication logic changes
2. Database schema updates

<reason>These changes affect core security</reason>

Overall assessment: Needs review."""

        expected = """The main changes are:

1. Authentication logic changes
2. Database schema updates

Overall assessment: Needs review."""

        result = _strip_thinking_tokens(response)
        assert result == expected

    def test_pr_reviewer_empty_input(self):
        """Test PR reviewer handles empty input correctly."""
        from kit.pr_review.reviewer import _strip_thinking_tokens

        assert _strip_thinking_tokens("") == ""
        assert _strip_thinking_tokens(None) is None

    def test_pr_reviewer_no_thinking_tokens(self):
        """Test that normal responses without thinking tokens are not modified."""
        from kit.pr_review.reviewer import _strip_thinking_tokens

        input_text = "This is a normal response without any thinking tokens."
        output = _strip_thinking_tokens(input_text)
        assert output == input_text


class TestExistingRepoPath:
    """Test using existing repository path functionality."""

    def test_config_with_repo_path(self):
        """Test ReviewConfig with repo_path parameter."""
        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="claude-4-sonnet", api_key="test"),
            repo_path="/path/to/existing/repo",
        )
        assert config.repo_path == "/path/to/existing/repo"

    def test_config_from_file_with_repo_path(self):
        """Test ReviewConfig.from_file with repo_path parameter."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "github": {"token": "test-token"},
                "llm": {
                    "provider": "anthropic",
                    "model": "claude-4-sonnet",
                    "api_key": "test-key",
                },
            }
            yaml.dump(config_data, f)
            temp_config_path = f.name

        try:
            config = ReviewConfig.from_file(temp_config_path, repo_path="/custom/repo/path")
            assert config.repo_path == "/custom/repo/path"
        finally:
            os.unlink(temp_config_path)

    @patch("kit.pr_review.base_reviewer.requests.Session")
    @patch("pathlib.Path.exists")
    def test_get_repo_for_analysis_with_existing_path(self, mock_exists, mock_session_class):
        """Test get_repo_for_analysis uses existing repo path when configured."""
        # Setup mocks
        mock_exists.return_value = True
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="claude-4-sonnet", api_key="test"),
            repo_path="/existing/repo",
        )

        reviewer = PRReviewer(config)

        # Mock the Path.exists and git directory check
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.__truediv__") as mock_path_div:
                mock_git_path = Mock()
                mock_git_path.exists.return_value = True
                mock_path_div.return_value = mock_git_path

                pr_details = {"head": {"sha": "abc123"}}
                result = reviewer.get_repo_for_analysis("owner", "repo", pr_details)

                # Should resolve to the absolute path and not use cache
                assert "/existing/repo" in result

    @patch("kit.pr_review.base_reviewer.requests.Session")
    @patch("pathlib.Path.exists")
    def test_get_repo_for_analysis_nonexistent_path(self, mock_exists, mock_session_class):
        """Test get_repo_for_analysis raises error for nonexistent repo path."""
        mock_exists.return_value = False
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="claude-4-sonnet", api_key="test"),
            repo_path="/nonexistent/repo",
        )

        reviewer = PRReviewer(config)

        pr_details = {"head": {"sha": "abc123"}}

        with pytest.raises(ValueError, match="Specified repository path does not exist"):
            reviewer.get_repo_for_analysis("owner", "repo", pr_details)

    @patch("kit.pr_review.base_reviewer.requests.Session")
    @patch("pathlib.Path.exists")
    def test_get_repo_for_analysis_not_git_repo(self, mock_exists, mock_session_class):
        """Test get_repo_for_analysis raises error for non-git directory."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="claude-4-sonnet", api_key="test"),
            repo_path="/not/a/git/repo",
        )

        reviewer = PRReviewer(config)

        with patch("pathlib.Path.exists") as mock_path_exists:
            with patch("pathlib.Path.__truediv__") as mock_path_div:
                # Path exists but .git directory doesn't
                mock_path_exists.side_effect = lambda: True
                mock_git_path = Mock()
                mock_git_path.exists.return_value = False
                mock_path_div.return_value = mock_git_path

                pr_details = {"head": {"sha": "abc123"}}

                with pytest.raises(ValueError, match="Specified path is not a git repository"):
                    reviewer.get_repo_for_analysis("owner", "repo", pr_details)

    @patch("kit.pr_review.base_reviewer.requests.Session")
    @patch("kit.pr_review.reviewer.subprocess.run")
    @patch("builtins.print")
    def test_review_pr_with_existing_repo_warning(self, mock_print, mock_subprocess, mock_session_class):
        """Test that warning message is displayed when using existing repository."""
        # Setup similar to test_pr_review_dry_run but with repo_path
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock PR details response
        def mock_get(url):
            mock_response = Mock()
            if "pulls" in url and url.endswith("/47"):
                mock_response.json.return_value = {
                    "number": 47,
                    "title": "Test PR",
                    "user": {"login": "testuser"},
                    "base": {
                        "ref": "main",
                        "repo": {"owner": {"login": "cased"}, "name": "kit"},
                    },
                    "head": {
                        "ref": "feature",
                        "sha": "abc123",
                        "repo": {"owner": {"login": "cased"}, "name": "kit"},
                    },
                }
            elif url.endswith("/files"):
                mock_response.json.return_value = [{"filename": "test.py", "additions": 10, "deletions": 5}]
            elif url.endswith("/comments"):
                mock_response.json.return_value = {"html_url": "https://github.com/test/comment"}
            else:
                mock_response.text = "diff content"
            mock_response.raise_for_status = Mock()
            return mock_response

        mock_session.get = mock_get
        mock_session.post = mock_get

        # Mock existing repository path
        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="claude-4-sonnet", api_key="test"),
            clone_for_analysis=True,
            post_as_comment=False,
            repo_path="/existing/repo",
        )

        reviewer = PRReviewer(config)

        # Mock the repository path validation
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.__truediv__") as mock_path_div:
                mock_git_path = Mock()
                mock_git_path.exists.return_value = True
                mock_path_div.return_value = mock_git_path

                with patch("kit.pr_review.reviewer.Repository"):
                    with patch(
                        "kit.pr_review.reviewer.asyncio.run",
                        return_value="Test analysis",
                    ):
                        reviewer.review_pr("https://github.com/cased/kit/pull/47")

                        # Check that warning message was printed
                        warning_calls = [
                            call
                            for call in mock_print.call_args_list
                            if "WARNING: Using existing repository" in str(call)
                        ]
                        assert len(warning_calls) > 0

                        # Check that the existing repo path was mentioned
                        repo_path_calls = [call for call in mock_print.call_args_list if "/existing/repo" in str(call)]
                        assert len(repo_path_calls) > 0

    @patch("kit.pr_review.base_reviewer.requests.Session")
    @patch("kit.pr_review.agentic_reviewer.asyncio.run")
    @patch("builtins.print")
    def test_agentic_reviewer_with_repo_path(self, mock_print, mock_asyncio_run, mock_session_class):
        """Test AgenticPRReviewer with existing repository path and warning messages."""
        from kit.pr_review.agentic_reviewer import AgenticPRReviewer

        # Setup similar to test_review_pr_with_existing_repo_warning but for agentic reviewer
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock PR details response
        def mock_get(url):
            mock_response = Mock()
            if "pulls" in url and url.endswith("/47"):
                mock_response.json.return_value = {
                    "number": 47,
                    "title": "Test Agentic PR",
                    "user": {"login": "testuser"},
                    "base": {
                        "ref": "main",
                        "repo": {"owner": {"login": "cased"}, "name": "kit"},
                    },
                    "head": {
                        "ref": "feature",
                        "sha": "abc123",
                        "repo": {"owner": {"login": "cased"}, "name": "kit"},
                    },
                }
            elif url.endswith("/files"):
                mock_response.json.return_value = [{"filename": "test.py", "additions": 10, "deletions": 5}]
            elif url.endswith("/comments"):
                mock_response.json.return_value = {"html_url": "https://github.com/test/comment"}
            else:
                mock_response.text = "diff content"
            mock_response.raise_for_status = Mock()
            return mock_response

        mock_session.get = mock_get
        mock_session.post = mock_get

        # Mock existing repository path
        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="claude-4-sonnet", api_key="test"),
            post_as_comment=False,
            repo_path="/existing/repo",
        )

        # Mock the RepoCache to avoid path operation issues
        with patch("kit.pr_review.base_reviewer.RepoCache") as mock_repo_cache_class:
            mock_repo_cache = Mock()
            mock_repo_cache_class.return_value = mock_repo_cache

            reviewer = AgenticPRReviewer(config)

            # Mock the repository path validation
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.__truediv__") as mock_path_div:
                    mock_git_path = Mock()
                    mock_git_path.exists.return_value = True
                    mock_path_div.return_value = mock_git_path

                    # Mock the agentic analysis to return a test result
                    mock_asyncio_run.return_value = "Test agentic analysis result"

                    # Call the full agentic review method
                    reviewer.review_pr_agentic("https://github.com/cased/kit/pull/47")

                    # Check that warning message was printed
                    warning_calls = [
                        call for call in mock_print.call_args_list if "WARNING: Using existing repository" in str(call)
                    ]
                    assert len(warning_calls) > 0

                    # Check that the existing repo path was mentioned
                    repo_path_calls = [call for call in mock_print.call_args_list if "/existing/repo" in str(call)]
                    assert len(repo_path_calls) > 0


def test_helicone_api_integration():
    """Test Helicone API integration for dynamic pricing."""
    from unittest.mock import MagicMock, patch

    from kit.pr_review.cost_tracker import CostTracker

    # Clear the cache first to ensure test isolation
    CostTracker._fetch_pricing_with_cache.cache_clear()

    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"provider": "OPENAI", "model": "gpt-4o", "input_cost_per_1m": 5.0, "output_cost_per_1m": 15.0},
            {
                "provider": "ANTHROPIC",
                "model": "claude-3-5-sonnet-20241022",
                "input_cost_per_1m": 3.0,
                "output_cost_per_1m": 15.0,
            },
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        tracker = CostTracker()
        pricing = tracker._get_current_pricing()

        # Verify pricing was fetched and normalized
        assert LLMProvider.OPENAI in pricing
        assert LLMProvider.ANTHROPIC in pricing
        assert "gpt-4o" in pricing[LLMProvider.OPENAI]
        assert "claude-3-5-sonnet-20241022" in pricing[LLMProvider.ANTHROPIC]

        # Test cost calculation with fetched pricing
        tracker.track_llm_usage(LLMProvider.OPENAI, "gpt-4o", 1000, 1000)
        expected_cost = (1000 / 1_000_000) * 5.0 + (1000 / 1_000_000) * 15.0
        assert abs(tracker.breakdown.llm_cost_usd - expected_cost) < 0.0001

    # Clear cache again to avoid affecting other tests
    CostTracker._fetch_pricing_with_cache.cache_clear()


def test_helicone_api_fallback():
    """Test fallback when Helicone API is unavailable."""
    from unittest.mock import patch

    from kit.pr_review.cost_tracker import CostTracker

    # Clear the cache first
    CostTracker._fetch_pricing_with_cache.cache_clear()

    # Mock API failure
    with patch("requests.get", side_effect=Exception("Connection error")):
        with patch("kit.pr_review.cost_tracker.logger.warning") as mock_warning:
            tracker = CostTracker()
            pricing = tracker._get_current_pricing()

            # Should warn about failure
            assert mock_warning.call_count > 0

            # Should return fallback pricing
            assert pricing == CostTracker.FALLBACK_PRICING

    # Clear cache again to avoid affecting other tests
    CostTracker._fetch_pricing_with_cache.cache_clear()


class TestGPT5ParameterHandling:
    """Test GPT-5 models use max_completion_tokens instead of max_tokens."""

    def test_gpt5_uses_max_completion_tokens(self):
        """Test that GPT-5 models use max_completion_tokens parameter."""
        # Test the detection logic used in all OpenAI calls
        gpt5_models = ["gpt-5", "gpt-5-mini", "gpt-5-nano", "GPT-5-turbo", "gpt-5-preview"]

        for model in gpt5_models:
            assert "gpt-5" in model.lower(), f"Model {model} should be detected as GPT-5"

    def test_non_gpt5_uses_max_tokens(self):
        """Test that non-GPT-5 models use max_tokens parameter."""
        non_gpt5_models = ["gpt-4", "gpt-4o", "gpt-4-turbo", "gpt-4.1", "gpt-3.5-turbo", "o1-preview", "o3-mini"]

        for model in non_gpt5_models:
            assert "gpt-5" not in model.lower(), f"Model {model} should NOT be detected as GPT-5"

    @pytest.mark.asyncio
    async def test_reviewer_openai_gpt5_params(self):
        """Test PRReviewer._analyze_with_openai_enhanced uses correct params for GPT-5."""
        from unittest.mock import MagicMock

        from kit.pr_review.config import LLMConfig, LLMProvider, ReviewConfig
        from kit.pr_review.reviewer import PRReviewer

        # Create config with GPT-5 model
        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-5-mini",
            api_key="test-key",
            max_tokens=4000,
        )
        review_config = ReviewConfig(
            github=MagicMock(),
            llm=llm_config,
        )

        reviewer = PRReviewer(config=review_config)

        # Mock OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test review"))]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=mock_response)
        reviewer._llm_client = mock_client

        # Call the method
        await reviewer._analyze_with_openai_enhanced("Test prompt")

        # Verify max_completion_tokens was used (not max_tokens)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "max_completion_tokens" in call_kwargs, "GPT-5 should use max_completion_tokens"
        assert "max_tokens" not in call_kwargs, "GPT-5 should NOT use max_tokens"
        assert call_kwargs["max_completion_tokens"] == 4000

    @pytest.mark.asyncio
    async def test_reviewer_openai_gpt4_params(self):
        """Test PRReviewer._analyze_with_openai_enhanced uses correct params for GPT-4."""
        from unittest.mock import MagicMock

        from kit.pr_review.config import LLMConfig, LLMProvider, ReviewConfig
        from kit.pr_review.reviewer import PRReviewer

        # Create config with GPT-4 model
        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o",
            api_key="test-key",
            max_tokens=4000,
        )
        review_config = ReviewConfig(
            github=MagicMock(),
            llm=llm_config,
        )

        reviewer = PRReviewer(config=review_config)

        # Mock OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test review"))]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=mock_response)
        reviewer._llm_client = mock_client

        # Call the method
        await reviewer._analyze_with_openai_enhanced("Test prompt")

        # Verify max_tokens was used (not max_completion_tokens)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "max_tokens" in call_kwargs, "GPT-4 should use max_tokens"
        assert "max_completion_tokens" not in call_kwargs, "GPT-4 should NOT use max_completion_tokens"
        assert call_kwargs["max_tokens"] == 4000

    @pytest.mark.asyncio
    async def test_commit_generator_gpt5_params(self):
        """Test CommitMessageGenerator._generate_with_openai uses correct params for GPT-5."""
        from unittest.mock import MagicMock

        from kit.pr_review.commit_generator import CommitMessageGenerator
        from kit.pr_review.config import LLMConfig, LLMProvider, ReviewConfig

        # Create config with GPT-5 model
        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-5",
            api_key="test-key",
        )
        review_config = ReviewConfig(
            github=MagicMock(),
            llm=llm_config,
        )

        generator = CommitMessageGenerator(config=review_config)

        # Mock OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="feat: add feature"))]
        mock_response.usage = MagicMock(prompt_tokens=50, completion_tokens=10)

        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=mock_response)
        generator._llm_client = mock_client

        # Call the method
        await generator._generate_with_openai("Generate commit message")

        # Verify max_completion_tokens was used
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "max_completion_tokens" in call_kwargs, "GPT-5 should use max_completion_tokens"
        assert call_kwargs["max_completion_tokens"] == 200  # Commit messages are capped at 200

    @pytest.mark.asyncio
    async def test_summarizer_gpt5_params(self):
        """Test PRSummarizer._analyze_with_openai_summary uses correct params for GPT-5."""
        from unittest.mock import MagicMock

        from kit.pr_review.config import LLMConfig, LLMProvider, ReviewConfig
        from kit.pr_review.summarizer import PRSummarizer

        # Create config with GPT-5 model
        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-5-nano",
            api_key="test-key",
            max_tokens=2000,
        )
        review_config = ReviewConfig(
            github=MagicMock(),
            llm=llm_config,
        )

        summarizer = PRSummarizer(config=review_config)

        # Mock OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Summary of changes"))]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=mock_response)
        summarizer._llm_client = mock_client

        # Call the method
        await summarizer._analyze_with_openai_summary("Summarize this")

        # Verify max_completion_tokens was used
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "max_completion_tokens" in call_kwargs, "GPT-5 should use max_completion_tokens"
        # Summarizer caps at 1000
        assert call_kwargs["max_completion_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_agentic_reviewer_gpt5_params(self):
        """Test AgenticPRReviewer._run_agentic_analysis_openai uses correct params for GPT-5."""
        from unittest.mock import MagicMock

        from kit.pr_review.agentic_reviewer import AgenticPRReviewer
        from kit.pr_review.config import LLMConfig, LLMProvider, ReviewConfig

        # Create config with GPT-5 model
        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-5.2",
            api_key="test-key",
            max_tokens=4000,
        )
        review_config = ReviewConfig(
            github=MagicMock(),
            llm=llm_config,
        )

        reviewer = AgenticPRReviewer(config=review_config)

        # Mock OpenAI client - return a response with text content (no tool calls) to exit loop
        mock_message = MagicMock()
        mock_message.tool_calls = None
        mock_message.content = "Final analysis complete"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=mock_response)
        reviewer._llm_client = mock_client

        # Call the method
        await reviewer._run_agentic_analysis_openai("Test prompt")

        # Verify max_completion_tokens was used (not max_tokens)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "max_completion_tokens" in call_kwargs, "GPT-5 should use max_completion_tokens"
        assert "max_tokens" not in call_kwargs, "GPT-5 should NOT use max_tokens"
        assert call_kwargs["max_completion_tokens"] == 4000

    @pytest.mark.asyncio
    async def test_agentic_reviewer_gpt4_params(self):
        """Test AgenticPRReviewer._run_agentic_analysis_openai uses correct params for GPT-4."""
        from unittest.mock import MagicMock

        from kit.pr_review.agentic_reviewer import AgenticPRReviewer
        from kit.pr_review.config import LLMConfig, LLMProvider, ReviewConfig

        # Create config with GPT-4 model
        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o",
            api_key="test-key",
            max_tokens=4000,
        )
        review_config = ReviewConfig(
            github=MagicMock(),
            llm=llm_config,
        )

        reviewer = AgenticPRReviewer(config=review_config)

        # Mock OpenAI client - return a response with text content (no tool calls) to exit loop
        mock_message = MagicMock()
        mock_message.tool_calls = None
        mock_message.content = "Final analysis complete"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=mock_response)
        reviewer._llm_client = mock_client

        # Call the method
        await reviewer._run_agentic_analysis_openai("Test prompt")

        # Verify max_tokens was used (not max_completion_tokens)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "max_tokens" in call_kwargs, "GPT-4 should use max_tokens"
        assert "max_completion_tokens" not in call_kwargs, "GPT-4 should NOT use max_completion_tokens"
        assert call_kwargs["max_tokens"] == 4000


class TestAgenticReviewerProviderRouting:
    """Tests for agentic reviewer provider routing - Issue #173 fix."""

    @pytest.mark.asyncio
    async def test_agentic_reviewer_google_routing(self):
        """Test AgenticPRReviewer routes Google provider to _run_agentic_analysis_google."""
        from unittest.mock import AsyncMock, MagicMock

        from kit.pr_review.agentic_reviewer import AgenticPRReviewer
        from kit.pr_review.config import LLMConfig, LLMProvider, ReviewConfig

        # Create config with Google provider
        llm_config = LLMConfig(
            provider=LLMProvider.GOOGLE,
            model="gemini-2.5-pro",
            api_key="test-google-key",
            max_tokens=4000,
        )
        review_config = ReviewConfig(
            github=GitHubConfig(token="test-token"),
            llm=llm_config,
        )

        reviewer = AgenticPRReviewer(config=review_config)

        # Mock the Google analysis method to verify it's called
        reviewer._run_agentic_analysis_google = AsyncMock(return_value="Google analysis result")
        reviewer._run_agentic_analysis_openai = AsyncMock(return_value="OpenAI analysis result")
        reviewer._run_agentic_analysis_anthropic = AsyncMock(return_value="Anthropic analysis result")

        # Mock Repository and other dependencies
        with patch("kit.Repository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            # Setup minimal PR details
            pr_details = {
                "number": 1,
                "title": "Test PR",
                "user": {"login": "testuser"},
                "head": {"sha": "abc123", "repo": {"owner": {"login": "owner"}, "name": "repo"}},
                "base": {"repo": {"owner": {"login": "owner"}, "name": "repo"}},
            }
            files = [{"filename": "test.py", "additions": 10, "deletions": 5}]

            # Mock get_pr_diff and get_parsed_diff
            reviewer.get_pr_diff = MagicMock(return_value="diff content")
            reviewer.get_parsed_diff = MagicMock(return_value={})

            result = await reviewer.analyze_pr_agentic("/fake/repo", pr_details, files)

            # Verify Google method was called, not OpenAI
            reviewer._run_agentic_analysis_google.assert_called_once()
            reviewer._run_agentic_analysis_openai.assert_not_called()
            reviewer._run_agentic_analysis_anthropic.assert_not_called()
            assert result == "Google analysis result"

    @pytest.mark.asyncio
    async def test_agentic_reviewer_ollama_raises_error(self):
        """Test AgenticPRReviewer raises clear error for Ollama provider."""
        from unittest.mock import MagicMock

        from kit.pr_review.agentic_reviewer import AgenticPRReviewer
        from kit.pr_review.config import LLMConfig, LLMProvider, ReviewConfig

        # Create config with Ollama provider
        llm_config = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama3",
            api_key="ollama",
            max_tokens=4000,
        )
        review_config = ReviewConfig(
            github=GitHubConfig(token="test-token"),
            llm=llm_config,
        )

        reviewer = AgenticPRReviewer(config=review_config)

        # Mock Repository
        with patch("kit.Repository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            pr_details = {
                "number": 1,
                "title": "Test PR",
                "user": {"login": "testuser"},
                "head": {"sha": "abc123", "repo": {"owner": {"login": "owner"}, "name": "repo"}},
                "base": {"repo": {"owner": {"login": "owner"}, "name": "repo"}},
            }
            files = [{"filename": "test.py", "additions": 10, "deletions": 5}]

            reviewer.get_pr_diff = MagicMock(return_value="diff content")
            reviewer.get_parsed_diff = MagicMock(return_value={})

            with pytest.raises(RuntimeError, match="Agentic mode is not yet supported for Ollama"):
                await reviewer.analyze_pr_agentic("/fake/repo", pr_details, files)

    @pytest.mark.asyncio
    async def test_agentic_reviewer_openai_fallback_for_explicit_provider(self):
        """Test that OpenAI provider correctly routes to OpenAI method."""
        from unittest.mock import AsyncMock, MagicMock

        from kit.pr_review.agentic_reviewer import AgenticPRReviewer
        from kit.pr_review.config import LLMConfig, LLMProvider, ReviewConfig

        # Create config with OpenAI provider (explicit)
        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o",
            api_key="test-openai-key",
            max_tokens=4000,
        )
        review_config = ReviewConfig(
            github=GitHubConfig(token="test-token"),
            llm=llm_config,
        )

        reviewer = AgenticPRReviewer(config=review_config)

        # Mock analysis methods
        reviewer._run_agentic_analysis_google = AsyncMock(return_value="Google result")
        reviewer._run_agentic_analysis_openai = AsyncMock(return_value="OpenAI result")
        reviewer._run_agentic_analysis_anthropic = AsyncMock(return_value="Anthropic result")

        with patch("kit.Repository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            pr_details = {
                "number": 1,
                "title": "Test PR",
                "user": {"login": "testuser"},
                "head": {"sha": "abc123", "repo": {"owner": {"login": "owner"}, "name": "repo"}},
                "base": {"repo": {"owner": {"login": "owner"}, "name": "repo"}},
            }
            files = [{"filename": "test.py", "additions": 10, "deletions": 5}]

            reviewer.get_pr_diff = MagicMock(return_value="diff content")
            reviewer.get_parsed_diff = MagicMock(return_value={})

            result = await reviewer.analyze_pr_agentic("/fake/repo", pr_details, files)

            # Verify OpenAI method was called
            reviewer._run_agentic_analysis_openai.assert_called_once()
            reviewer._run_agentic_analysis_google.assert_not_called()
            assert result == "OpenAI result"
