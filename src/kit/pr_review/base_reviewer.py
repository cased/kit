"""Base reviewer class with shared functionality for PR reviewers."""

import re
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from kit import __version__

from .cache import RepoCache
from .config import ReviewConfig
from .cost_tracker import CostTracker
from .diff_parser import DiffParser, FileDiff


class BaseReviewer:
    """Base class for PR reviewers with common GitHub API and caching functionality.

    This class provides shared methods for:
    - PR URL parsing
    - GitHub API interactions (get PR details, files, diffs)
    - Repository caching for analysis
    - Diff caching
    """

    def __init__(self, config: ReviewConfig, user_agent: Optional[str] = None):
        """Initialize the base reviewer.

        Args:
            config: The review configuration
            user_agent: User-Agent string for GitHub API requests (defaults to kit-review/{version})
        """
        self.config = config
        self.github_session = requests.Session()
        self.github_session.headers.update(
            {
                "Authorization": f"token {config.github.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": user_agent or f"kit-review/{__version__}",
            }
        )
        self._llm_client: Optional[Any] = None
        # Pass quiet mode to repo cache if available
        quiet = getattr(config, "quiet", False)
        self.repo_cache = RepoCache(config, quiet=quiet)
        self.cost_tracker = CostTracker(config.custom_pricing)

        # Diff caching
        self._cached_diff_key: Optional[tuple[str, str, int]] = None
        self._cached_diff_text: Optional[str] = None
        self._cached_parsed_diff: Optional[Dict[str, FileDiff]] = None
        self._cached_parsed_key: Optional[tuple[str, str, int]] = None

    def parse_pr_url(self, pr_input: str) -> tuple[str, str, int]:
        """Parse PR URL or number to extract owner, repo, and PR number.

        Args:
            pr_input: GitHub PR URL or just PR number (if in repo directory)

        Returns:
            tuple of (owner, repo, pr_number)

        Raises:
            NotImplementedError: If only a PR number is provided
            ValueError: If the URL format is invalid
        """
        # If it's just a number, we'll need to detect repo from current directory
        if pr_input.isdigit():
            raise NotImplementedError(
                "PR number without repository URL is not yet supported. "
                "Please provide the full GitHub PR URL: https://github.com/owner/repo/pull/123"
            )

        # Parse GitHub URL
        # https://github.com/owner/repo/pull/123
        # Also supports enterprise GitHub: https://github.enterprise.com/owner/repo/pull/123
        url_pattern = r"https://(?:\w+\.)?github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(url_pattern, pr_input)

        if not match:
            raise ValueError(f"Invalid GitHub PR URL: {pr_input}")

        owner, repo, pr_number = match.groups()
        return owner, repo, int(pr_number)

    def get_pr_details(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get PR details from GitHub API.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            Dictionary with PR details from GitHub API
        """
        url = f"{self.config.github.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        response = self.github_session.get(url)
        response.raise_for_status()
        return response.json()

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[Dict[str, Any]]:
        """Get list of files changed in the PR.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            List of file change dictionaries from GitHub API
        """
        url = f"{self.config.github.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = self.github_session.get(url)
        response.raise_for_status()
        return response.json()

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Get the full diff for the PR.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            The full diff text for the PR
        """
        key = (owner, repo, pr_number)

        # Return cached diff text if we already fetched it
        if self._cached_diff_key == key and self._cached_diff_text is not None:
            return self._cached_diff_text

        url = f"{self.config.github.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = dict(self.github_session.headers)
        headers["Accept"] = "application/vnd.github.v3.diff"

        response = self.github_session.get(url, headers=headers)
        response.raise_for_status()

        # Cache the result
        self._cached_diff_key = key
        self._cached_diff_text = response.text

        # Invalidate parsed cache because diff may have changed
        self._cached_parsed_diff = None
        self._cached_parsed_key = None

        return response.text

    def get_parsed_diff(self, owner: str, repo: str, pr_number: int) -> Dict[str, FileDiff]:
        """Get the parsed diff for the PR.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            Dictionary mapping file paths to FileDiff objects
        """
        key = (owner, repo, pr_number)

        if self._cached_parsed_key == key and self._cached_parsed_diff is not None:
            return self._cached_parsed_diff

        diff_text = self.get_pr_diff(owner, repo, pr_number)
        parsed: Dict[str, FileDiff] = DiffParser.parse_diff(diff_text)
        self._cached_parsed_key = key
        self._cached_parsed_diff = parsed
        return parsed

    def get_repo_for_analysis(self, owner: str, repo: str, pr_details: Dict[str, Any]) -> str:
        """Get repository for analysis, using cache if available.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_details: PR details dictionary from GitHub API

        Returns:
            Path to the repository for analysis
        """
        # If a repo_path is configured, use the existing repository
        if self.config.repo_path:
            repo_path = Path(self.config.repo_path).expanduser().resolve()
            if not repo_path.exists():
                raise ValueError(f"Specified repository path does not exist: {repo_path}")
            if not (repo_path / ".git").exists():
                raise ValueError(f"Specified path is not a git repository: {repo_path}")
            return str(repo_path)

        # Default behavior: use cache
        head_sha = pr_details["head"]["sha"]
        return self.repo_cache.get_repo_path(owner, repo, head_sha)
