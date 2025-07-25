"""Configuration management for PR review functionality."""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class LLMProvider(Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    GOOGLE = "google"


class ReviewDepth(Enum):
    """Review analysis depth levels."""

    QUICK = "quick"
    STANDARD = "standard"
    THOROUGH = "thorough"


def _detect_provider_from_model(model_name: str) -> Optional[LLMProvider]:
    """Detect LLM provider from model name."""
    model_lower = model_name.lower()

    # Strip common prefixes first
    prefixes_to_strip = [
        "vertex_ai/",
        "openrouter/",
        "together/",
        "groq/",
        "fireworks/",
        "perplexity/",
        "replicate/",
        "bedrock/",
        "azure/",
    ]

    stripped_model = model_lower
    for prefix in prefixes_to_strip:
        if stripped_model.startswith(prefix):
            stripped_model = stripped_model[len(prefix) :]
            break

    # OpenAI model patterns
    openai_patterns = ["gpt-", "o1-", "text-davinci", "text-curie", "text-babbage", "text-ada"]
    if any(pattern in stripped_model for pattern in openai_patterns):
        return LLMProvider.OPENAI

    # Anthropic model patterns
    anthropic_patterns = ["claude-", "haiku", "sonnet", "opus"]
    if any(pattern in stripped_model for pattern in anthropic_patterns):
        return LLMProvider.ANTHROPIC

    # Google model patterns
    google_patterns = ["gemini-", "gemini", "bison", "gecko", "palm"]
    if any(pattern in stripped_model for pattern in google_patterns):
        return LLMProvider.GOOGLE

    # Ollama model patterns - popular models available in Ollama
    ollama_patterns = [
        "llama",
        "mistral",
        "codellama",
        "deepseek",
        "qwen",
        "phi",
        "gemma",
        "wizardcoder",
        "starcoder",
        "codegemma",
        "solar",
        "nous-hermes",
        "openchat",
        "zephyr",
        "orca",
        "vicuna",
        "alpaca",
        "devstral",
    ]
    if any(pattern in stripped_model for pattern in ollama_patterns):
        return LLMProvider.OLLAMA

    return None


def _is_placeholder_token(token: Optional[str]) -> bool:
    """Check if a token is a placeholder that should be ignored."""
    if not token:
        return True

    # Common placeholder patterns
    placeholder_patterns = [
        "your_token_here",
        "your_api_key_here",
        "your_key_here",
        "replace_with_your_token",
        "sk-your_api_key_here",
        "ghp_your_token_here",
        "sk-ant-your_key",
    ]

    token_lower = token.lower()
    return any(pattern in token_lower for pattern in placeholder_patterns)


@dataclass
class GitHubConfig:
    """GitHub configuration."""

    token: str
    base_url: str = "https://api.github.com"


@dataclass
class LLMConfig:
    """LLM configuration."""

    provider: LLMProvider
    model: str
    api_key: str
    max_tokens: int = 4000
    temperature: float = 0.1
    api_base_url: Optional[str] = None  # For local LLMs or custom OpenAI endpoints


@dataclass
class ReviewConfig:
    """Complete review configuration."""

    github: GitHubConfig
    llm: LLMConfig
    max_files: int = 50
    include_recent_prs: bool = True
    analysis_depth: ReviewDepth = ReviewDepth.STANDARD
    post_as_comment: bool = True
    clone_for_analysis: bool = True
    cache_repos: bool = True
    cache_directory: str = "~/.kit/repo-cache"
    cache_ttl_hours: int = 24
    custom_pricing: Optional[Dict] = None
    # Agentic reviewer settings
    agentic_max_turns: int = 20
    agentic_finalize_threshold: int = 15  # Start encouraging finalization at this turn
    # Output control
    quiet: bool = False  # Suppress status output for plain mode
    # Priority filtering
    priority_filter: Optional[List[str]] = None  # ["high", "medium", "low"] or subset
    max_review_size_mb: float = 5.0  # Default 5MB limit (was 1MB hardcoded)
    # Custom context profile
    profile: Optional[str] = None  # Profile name to use
    profile_context: Optional[str] = None  # Loaded profile context
    # Existing repository path (skips cloning when provided)
    repo_path: Optional[str] = None  # Path to existing repository to use for analysis
    # Local review settings
    save_reviews: bool = False  # Save local reviews to .kit/reviews/
    llm_provider: Optional[str] = None  # Convenience accessor for llm.provider
    llm_model: Optional[str] = None  # Convenience accessor for llm.model
    llm_api_key: Optional[str] = None  # Convenience accessor for llm.api_key
    llm_api_base_url: Optional[str] = None  # Convenience accessor for llm.api_base_url
    llm_temperature: Optional[float] = None  # Convenience accessor for llm.temperature
    llm_max_tokens: Optional[int] = None  # Convenience accessor for llm.max_tokens

    @classmethod
    def from_file(
        cls,
        config_path: Optional[str] = None,
        profile: Optional[str] = None,
        repo_path: Optional[str] = None,
        model_hint: Optional[str] = None,
    ) -> "ReviewConfig":
        """Load configuration from file or environment variables.

        Args:
            config_path: Path to config file
            profile: Profile name to load custom context from
            repo_path: Path to existing repository to use for analysis
            model_hint: Model name to help auto-detect provider
        """
        if config_path is None:
            config_path = os.path.expanduser("~/.kit/review-config.yaml")

        config_data: Dict = {}

        # Try to load from file
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f) or {}

        # Override with environment variables
        config_github_token = config_data.get("github", {}).get("token")
        if _is_placeholder_token(config_github_token):
            config_github_token = None  # Treat placeholder as missing

        github_token = config_github_token or os.getenv("KIT_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")

        if not github_token:
            raise ValueError(
                "GitHub token required. Set KIT_GITHUB_TOKEN environment variable or "
                "add 'github.token' to ~/.kit/review-config.yaml"
            )

        github_config = GitHubConfig(
            token=github_token,
            base_url=config_data.get("github", {}).get("base_url", "https://api.github.com"),
        )

        # LLM configuration
        llm_data = config_data.get("llm", {}) or {}  # Handle None or empty llm section

        # Try to detect provider from model hint first
        detected_provider = None
        if model_hint:
            detected_provider = _detect_provider_from_model(model_hint)

        # Get provider from config, environment, detected, or default
        provider_str = (
            llm_data.get("provider")
            or os.getenv("LLM_PROVIDER")
            or (detected_provider.value if detected_provider else None)
            or "anthropic"
        )

        try:
            provider = LLMProvider(provider_str)
        except ValueError:
            raise ValueError(f"Unsupported LLM provider: {provider_str}. Use: {[p.value for p in LLMProvider]}")

        # Default models and API key environment variables
        if provider == LLMProvider.ANTHROPIC:
            default_model = "claude-sonnet-4-20250514"
            api_key_env = "KIT_ANTHROPIC_TOKEN or ANTHROPIC_API_KEY"
            config_api_key = llm_data.get("api_key")
            if _is_placeholder_token(config_api_key):
                config_api_key = None  # Treat placeholder as missing
            api_key = config_api_key or os.getenv("KIT_ANTHROPIC_TOKEN") or os.getenv("ANTHROPIC_API_KEY")
        elif provider == LLMProvider.GOOGLE:
            default_model = "gemini-2.5-flash"  # Updated to latest model
            api_key_env = "KIT_GOOGLE_API_KEY or GOOGLE_API_KEY"
            config_api_key = llm_data.get("api_key")
            if _is_placeholder_token(config_api_key):
                config_api_key = None  # Treat placeholder as missing
            api_key = config_api_key or os.getenv("KIT_GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
        elif provider == LLMProvider.OLLAMA:
            default_model = "qwen2.5-coder:latest"  # Latest code-specialized model
            api_key_env = "None (Ollama doesn't require API keys)"
            # Ollama doesn't need an API key, but we'll use a placeholder for consistency
            api_key = llm_data.get("api_key", "ollama")
        else:  # OpenAI
            default_model = "gpt-4.1-2025-04-14"
            api_key_env = "KIT_OPENAI_TOKEN or OPENAI_API_KEY"
            config_api_key = llm_data.get("api_key")
            if _is_placeholder_token(config_api_key):
                config_api_key = None  # Treat placeholder as missing
            api_key = config_api_key or os.getenv("KIT_OPENAI_TOKEN") or os.getenv("OPENAI_API_KEY")

        # Ollama doesn't require API keys, so skip validation for it
        if not api_key and provider != LLMProvider.OLLAMA:
            # Provide a more helpful error message based on the provider
            if provider == LLMProvider.ANTHROPIC and not (config_data.get("llm") or {}).get("provider"):
                # User didn't specify a provider, defaulted to Anthropic
                raise ValueError(
                    f"LLM API key required. To use Anthropic (default), set {api_key_env} environment variable. "
                    f"To use a different provider, set 'llm.provider' to 'openai', 'google', or 'ollama' in ~/.kit/review-config.yaml"
                )
            else:
                # User explicitly chose this provider
                raise ValueError(
                    f"LLM API key required for {provider.value}. Set {api_key_env} environment variable or "
                    f"add 'llm.api_key' to ~/.kit/review-config.yaml"
                )

        llm_config = LLMConfig(
            provider=provider,
            model=llm_data.get("model", default_model),
            api_key=str(api_key),
            max_tokens=llm_data.get("max_tokens", 4000),
            temperature=llm_data.get("temperature", 0.1),
            api_base_url=llm_data.get("api_base_url"),
        )

        # Set default base URLs for local providers
        if llm_config.provider == LLMProvider.OLLAMA and not llm_config.api_base_url:
            llm_config.api_base_url = "http://localhost:11434"  # Default Ollama API endpoint

        # Review settings
        review_data = config_data.get("review", {})
        try:
            depth = ReviewDepth(review_data.get("analysis_depth", "standard"))
        except ValueError:
            depth = ReviewDepth.STANDARD

        # Validate priority_filter if present in config
        priority_filter = review_data.get("priority_filter", None)
        if priority_filter is not None:
            try:
                from .priority_utils import Priority

                priority_filter = Priority.validate_priorities(priority_filter)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid priority_filter in config file: {e}. Valid priorities: high, medium, low")

        # Load profile context if profile is specified
        profile_context = None
        if profile:
            try:
                from .profile_manager import ProfileManager

                profile_manager = ProfileManager()
                profile_obj = profile_manager.get_profile(profile)
                profile_context = profile_obj.context
            except Exception as e:
                raise ValueError(f"Failed to load profile '{profile}': {e}")

        return cls(
            github=github_config,
            llm=llm_config,
            max_files=review_data.get("max_files", 50),
            include_recent_prs=review_data.get("include_recent_prs", True),
            analysis_depth=depth,
            post_as_comment=review_data.get("post_as_comment", True),
            clone_for_analysis=review_data.get("clone_for_analysis", True),
            cache_repos=review_data.get("cache_repos", True),
            cache_directory=review_data.get("cache_directory", "~/.kit/repo-cache"),
            cache_ttl_hours=review_data.get("cache_ttl_hours", 24),
            custom_pricing=review_data.get("custom_pricing", None),
            agentic_max_turns=review_data.get("agentic_max_turns", 20),
            agentic_finalize_threshold=review_data.get("agentic_finalize_threshold", 15),
            quiet=review_data.get("quiet", False),
            priority_filter=priority_filter,
            max_review_size_mb=review_data.get("max_review_size_mb", 5.0),
            profile=profile,
            profile_context=profile_context,
            repo_path=repo_path,
            save_reviews=review_data.get("save_reviews", False),
            # Convenience accessors for LLM config
            llm_provider=llm_config.provider.value,
            llm_model=llm_config.model,
            llm_api_key=llm_config.api_key,
            llm_api_base_url=llm_config.api_base_url,
            llm_temperature=llm_config.temperature,
            llm_max_tokens=llm_config.max_tokens,
        )

    def create_default_config_file(self, config_path: Optional[str] = None) -> str:
        """Create a default configuration file."""
        if config_path is None:
            config_path = os.path.expanduser("~/.kit/review-config.yaml")

        config_dir = Path(config_path).parent
        config_dir.mkdir(parents=True, exist_ok=True)

        default_config = {
            "github": {"token": "ghp_your_token_here", "base_url": "https://api.github.com"},
            "llm": {
                "provider": "anthropic",  # or "openai", "google"
                "model": "claude-sonnet-4-20250514",  # or "gpt-4o", "gemini-2.5-flash"
                "api_key": "sk-your_api_key_here",
                "max_tokens": 4000,
                "temperature": 0.1,
                # For custom OpenAI compatible providers (e.g., Together AI, OpenRouter, etc.)
                # "api_base_url": "https://api.together.xyz/v1",  # Example: Together AI
                # "api_base_url": "https://openrouter.ai/api/v1",  # Example: OpenRouter
                # "api_base_url": "http://localhost:8000/v1",      # Example: Local OpenAI API server
            },
            "review": {
                "max_files": 50,
                "include_recent_prs": True,
                "analysis_depth": "standard",  # quick, standard, thorough
                "post_as_comment": True,
                "clone_for_analysis": True,
                "cache_repos": True,
                "cache_directory": "~/.kit/repo-cache",
                "cache_ttl_hours": 24,
                # Priority filtering (can also be set via --priority CLI flag)
                # "priority_filter": ["high", "medium"],  # Only show high and medium priority issues
                # "priority_filter": ["high"],            # Only show high priority issues
                # Performance and safety limits
                "max_review_size_mb": 5.0,  # Maximum review text size in MB (prevents DoS)
                # Agentic reviewer settings (for multi-turn analysis)
                "agentic_max_turns": 20,  # Maximum number of analysis turns
                "agentic_finalize_threshold": 15,  # Start encouraging finalization at this turn
                # "custom_pricing": {
                #     "anthropic": {
                #         "claude-3-7-sonnet-latest": {
                #             "input_per_million": 3.00,
                #             "output_per_million": 15.00
                #         }
                #     },
                #     "openai": {
                #         "gpt-4o": {
                #             "input_per_million": 2.50,
                #             "output_per_million": 10.00
                #         }
                #     }
                # }
            },
        }

        with open(config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)

        # Add a commented-out example for local Ollama usage
        local_ollama_example = """\
# Example Ollama configuration (completely free local AI):
# llm:
#   provider: ollama
#   model: "qwen2.5-coder:latest"  # Or deepseek-r1:latest, gemma3:latest, etc.
#   api_base_url: "http://localhost:11434"  # Default Ollama endpoint
#   api_key: "ollama"  # Placeholder (Ollama doesn't use API keys)
#   max_tokens: 2000
#   temperature: 0.1

# Example Google Gemini configuration:
# llm:
#   provider: google
#   model: "gemini-2.5-flash"  # Or "gemini-2.5-pro" for more complex reasoning, "gemini-2.0-flash-lite" for speed
#   api_key: "AIzaSy..."  # Get from https://aistudio.google.com/apikey
#   max_tokens: 4000
#   temperature: 0.1

# Example OpenAI compatible provider configurations:
#
# Together AI (https://together.ai/):
# llm:
#   provider: openai
#   model: "meta-llama/Llama-3.3-70B-Instruct-Turbo"
#   api_key: "your_together_api_key"
#   api_base_url: "https://api.together.xyz/v1"
#   max_tokens: 4000
#   temperature: 0.1
#
# OpenRouter (https://openrouter.ai/):
# llm:
#   provider: openai
#   model: "anthropic/claude-3.5-sonnet"
#   api_key: "your_openrouter_api_key"
#   api_base_url: "https://openrouter.ai/api/v1"
#   max_tokens: 4000
#   temperature: 0.1
#
# Local OpenAI API server (e.g., text-generation-webui, vLLM):
# llm:
#   provider: openai
#   model: "local-model-name"
#   api_key: "not-used"  # Local servers often don't require API keys
#   api_base_url: "http://localhost:8000/v1"
#   max_tokens: 4000
#   temperature: 0.1
#
# Groq (https://groq.com/):
# llm:
#   provider: openai
#   model: "llama-3.3-70b-versatile"
#   api_key: "your_groq_api_key"
#   api_base_url: "https://api.groq.com/openai/v1"
#   max_tokens: 4000
#   temperature: 0.1
"""

        with open(config_path, "a") as f:
            f.write("\n" + local_ollama_example)

        return config_path
