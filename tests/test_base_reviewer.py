"""Tests for the BaseReviewer class."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kit.pr_review.base_reviewer import BaseReviewer
from kit.pr_review.config import GitHubConfig, LLMConfig, LLMProvider, ReviewConfig


@pytest.fixture
def review_config():
    """Create a test ReviewConfig."""
    return ReviewConfig(
        github=GitHubConfig(token="test-token"),
        llm=LLMConfig(provider=LLMProvider.ANTHROPIC, api_key="test-key", model="claude-3"),
    )


@pytest.fixture
def mock_session():
    """Create a mock requests session."""
    with patch("kit.pr_review.base_reviewer.requests.Session") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        yield mock_session


class TestBaseReviewerInit:
    """Tests for BaseReviewer initialization."""

    def test_init_creates_github_session(self, review_config, mock_session):
        """Test that init creates GitHub session with correct headers."""
        from kit import __version__

        with patch("kit.pr_review.base_reviewer.RepoCache"):
            reviewer = BaseReviewer(review_config)

            assert reviewer.config == review_config
            mock_session.headers.update.assert_called_once()
            call_args = mock_session.headers.update.call_args[0][0]
            assert "Authorization" in call_args
            assert call_args["Authorization"] == "token test-token"
            assert call_args["User-Agent"] == f"kit-review/{__version__}"

    def test_init_with_custom_user_agent(self, review_config, mock_session):
        """Test that init accepts custom user agent."""
        with patch("kit.pr_review.base_reviewer.RepoCache"):
            BaseReviewer(review_config, user_agent="custom-agent/1.0")

            call_args = mock_session.headers.update.call_args[0][0]
            assert call_args["User-Agent"] == "custom-agent/1.0"


class TestParsePrUrl:
    """Tests for parse_pr_url method."""

    def test_parses_standard_github_url(self, review_config, mock_session):
        """Test parsing standard GitHub PR URL."""
        with patch("kit.pr_review.base_reviewer.RepoCache"):
            reviewer = BaseReviewer(review_config)

            owner, repo, pr_number = reviewer.parse_pr_url("https://github.com/owner/repo/pull/123")

            assert owner == "owner"
            assert repo == "repo"
            assert pr_number == 123

    def test_parses_enterprise_github_url(self, review_config, mock_session):
        """Test parsing enterprise GitHub PR URL."""
        with patch("kit.pr_review.base_reviewer.RepoCache"):
            reviewer = BaseReviewer(review_config)

            owner, repo, pr_number = reviewer.parse_pr_url("https://enterprise.github.com/org/project/pull/456")

            assert owner == "org"
            assert repo == "project"
            assert pr_number == 456

    def test_raises_for_invalid_url(self, review_config, mock_session):
        """Test that invalid URL raises ValueError."""
        with patch("kit.pr_review.base_reviewer.RepoCache"):
            reviewer = BaseReviewer(review_config)

            with pytest.raises(ValueError, match="Invalid GitHub PR URL"):
                reviewer.parse_pr_url("https://example.com/not/a/pr")

    def test_raises_for_pr_number_only(self, review_config, mock_session):
        """Test that PR number only raises NotImplementedError."""
        with patch("kit.pr_review.base_reviewer.RepoCache"):
            reviewer = BaseReviewer(review_config)

            with pytest.raises(NotImplementedError, match="PR number without repository URL"):
                reviewer.parse_pr_url("123")


class TestGetPrDetails:
    """Tests for get_pr_details method."""

    def test_fetches_pr_details(self, review_config, mock_session):
        """Test fetching PR details from GitHub API."""
        with patch("kit.pr_review.base_reviewer.RepoCache"):
            mock_response = MagicMock()
            mock_response.json.return_value = {"title": "Test PR", "number": 123}
            mock_session.get.return_value = mock_response

            reviewer = BaseReviewer(review_config)
            details = reviewer.get_pr_details("owner", "repo", 123)

            mock_session.get.assert_called_once_with("https://api.github.com/repos/owner/repo/pulls/123")
            assert details == {"title": "Test PR", "number": 123}


class TestGetPrFiles:
    """Tests for get_pr_files method."""

    def test_fetches_pr_files(self, review_config, mock_session):
        """Test fetching PR files from GitHub API."""
        with patch("kit.pr_review.base_reviewer.RepoCache"):
            mock_response = MagicMock()
            mock_response.json.return_value = [{"filename": "test.py", "status": "modified"}]
            mock_session.get.return_value = mock_response

            reviewer = BaseReviewer(review_config)
            files = reviewer.get_pr_files("owner", "repo", 123)

            mock_session.get.assert_called_once_with("https://api.github.com/repos/owner/repo/pulls/123/files")
            assert files == [{"filename": "test.py", "status": "modified"}]


class TestGetPrDiff:
    """Tests for get_pr_diff method."""

    def test_fetches_diff(self, review_config, mock_session):
        """Test fetching PR diff from GitHub API."""
        with patch("kit.pr_review.base_reviewer.RepoCache"):
            mock_response = MagicMock()
            mock_response.text = "diff --git a/test.py b/test.py\n..."
            mock_session.get.return_value = mock_response

            reviewer = BaseReviewer(review_config)
            diff = reviewer.get_pr_diff("owner", "repo", 123)

            assert diff == "diff --git a/test.py b/test.py\n..."
            # Check that Accept header was set for diff format
            call_args = mock_session.get.call_args
            assert call_args[1]["headers"]["Accept"] == "application/vnd.github.v3.diff"

    def test_caches_diff(self, review_config, mock_session):
        """Test that diff is cached."""
        with patch("kit.pr_review.base_reviewer.RepoCache"):
            mock_response = MagicMock()
            mock_response.text = "diff content"
            mock_session.get.return_value = mock_response

            reviewer = BaseReviewer(review_config)

            # First call
            diff1 = reviewer.get_pr_diff("owner", "repo", 123)
            # Second call should use cache
            diff2 = reviewer.get_pr_diff("owner", "repo", 123)

            assert diff1 == diff2
            assert mock_session.get.call_count == 1  # Only called once


class TestGetRepoForAnalysis:
    """Tests for get_repo_for_analysis method."""

    def test_uses_configured_repo_path(self, mock_session):
        """Test that configured repo_path is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake .git directory
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            config = ReviewConfig(
                github=GitHubConfig(token="test-token"),
                llm=LLMConfig(provider=LLMProvider.ANTHROPIC, api_key="test-key", model="claude-3"),
                repo_path=tmpdir,
            )

            with patch("kit.pr_review.base_reviewer.RepoCache"):
                reviewer = BaseReviewer(config)
                pr_details = {"head": {"sha": "abc123"}}

                result = reviewer.get_repo_for_analysis("owner", "repo", pr_details)

                assert result == str(Path(tmpdir).resolve())

    def test_raises_for_nonexistent_path(self, mock_session):
        """Test that nonexistent repo_path raises ValueError."""
        config = ReviewConfig(
            github=GitHubConfig(token="test-token"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, api_key="test-key", model="claude-3"),
            repo_path="/nonexistent/path",
        )

        with patch("kit.pr_review.base_reviewer.RepoCache"):
            reviewer = BaseReviewer(config)
            pr_details = {"head": {"sha": "abc123"}}

            with pytest.raises(ValueError, match="does not exist"):
                reviewer.get_repo_for_analysis("owner", "repo", pr_details)

    def test_raises_for_non_git_repo(self, mock_session):
        """Test that non-git directory raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReviewConfig(
                github=GitHubConfig(token="test-token"),
                llm=LLMConfig(provider=LLMProvider.ANTHROPIC, api_key="test-key", model="claude-3"),
                repo_path=tmpdir,
            )

            with patch("kit.pr_review.base_reviewer.RepoCache"):
                reviewer = BaseReviewer(config)
                pr_details = {"head": {"sha": "abc123"}}

                with pytest.raises(ValueError, match="not a git repository"):
                    reviewer.get_repo_for_analysis("owner", "repo", pr_details)

    def test_uses_cache_when_no_repo_path(self, review_config, mock_session):
        """Test that RepoCache is used when no repo_path configured."""
        with patch("kit.pr_review.base_reviewer.RepoCache") as mock_cache_class:
            mock_cache = MagicMock()
            mock_cache.get_repo_path.return_value = "/cached/repo/path"
            mock_cache_class.return_value = mock_cache

            reviewer = BaseReviewer(review_config)
            pr_details = {"head": {"sha": "abc123"}}

            result = reviewer.get_repo_for_analysis("owner", "repo", pr_details)

            mock_cache.get_repo_path.assert_called_once_with("owner", "repo", "abc123")
            assert result == "/cached/repo/path"
