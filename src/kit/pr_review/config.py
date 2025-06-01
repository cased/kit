"""Configuration management for PR review functionality."""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

import yaml


class LLMProvider(Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class ReviewDepth(Enum):
    """Review analysis depth levels."""

    QUICK = "quick"
    STANDARD = "standard"
    THOROUGH = "thorough"


def _detect_provider_from_model(model_name: str) -> Optional[LLMProvider]:
    """Detect LLM provider from model name."""
    model_lower = model_name.lower()

    # OpenAI model patterns
    openai_patterns = ["gpt-", "o1-", "text-davinci", "text-curie", "text-babbage", "text-ada"]
    if any(pattern in model_lower for pattern in openai_patterns):
        return LLMProvider.OPENAI

    # Anthropic model patterns
    anthropic_patterns = ["claude-", "haiku", "sonnet", "opus"]
    if any(pattern in model_lower for pattern in anthropic_patterns):
        return LLMProvider.ANTHROPIC

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

    @classmethod
    def from_file(cls, config_path: Optional[str] = None) -> "ReviewConfig":
        """Load configuration from file or environment variables."""
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
        llm_data = config_data.get("llm", {})
        provider_str = llm_data.get("provider") or os.getenv("LLM_PROVIDER", "anthropic")

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
        else:  # OpenAI
            default_model = "gpt-4.1-2025-04-14"
            api_key_env = "KIT_OPENAI_TOKEN or OPENAI_API_KEY"
            config_api_key = llm_data.get("api_key")
            if _is_placeholder_token(config_api_key):
                config_api_key = None  # Treat placeholder as missing
            api_key = config_api_key or os.getenv("KIT_OPENAI_TOKEN") or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                f"LLM API key required. Set {api_key_env} environment variable or "
                f"add 'llm.api_key' to ~/.kit/review-config.yaml"
            )

        llm_config = LLMConfig(
            provider=provider,
            model=llm_data.get("model", default_model),
            api_key=api_key,
            max_tokens=llm_data.get("max_tokens", 4000),
            temperature=llm_data.get("temperature", 0.1),
        )

        # Review settings
        review_data = config_data.get("review", {})
        try:
            depth = ReviewDepth(review_data.get("analysis_depth", "standard"))
        except ValueError:
            depth = ReviewDepth.STANDARD

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
                "provider": "anthropic",  # or "openai"
                "model": "claude-sonnet-4-20250514",  # or "gpt-4o"
                "api_key": "sk-your_api_key_here",
                "max_tokens": 4000,
                "temperature": 0.1,
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

        return config_path
