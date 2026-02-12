"""Tests for pr_review.error_utils – non-actionable error classification."""

from unittest.mock import MagicMock, patch

import pytest

from kit.pr_review.error_utils import is_non_actionable_error


# ---------------------------------------------------------------------------
# is_non_actionable_error – unit tests
# ---------------------------------------------------------------------------

class TestIsNonActionableError:
    """Unit tests for the is_non_actionable_error helper."""

    # -- Token / context-length errors --

    def test_anthropic_context_length_exceeded(self):
        msg = "Error during enhanced LLM analysis: context_length_exceeded: the prompt is too long"
        assert is_non_actionable_error(msg) is True

    def test_openai_maximum_context_length(self):
        msg = (
            "Error during enhanced LLM analysis: This model's maximum context length "
            "is 128000 tokens. However, your messages resulted in 200000 tokens."
        )
        assert is_non_actionable_error(msg) is True

    def test_google_resource_exhausted(self):
        msg = "Error during enhanced LLM analysis: 400 RESOURCE_EXHAUSTED: Request too large"
        assert is_non_actionable_error(msg) is True

    def test_generic_token_limit(self):
        msg = "Error during enhanced LLM analysis: token limit exceeded for this model"
        assert is_non_actionable_error(msg) is True

    def test_prompt_too_long(self):
        msg = "Error during enhanced LLM analysis: prompt is too long"
        assert is_non_actionable_error(msg) is True

    def test_max_tokens_error(self):
        msg = "Error during enhanced LLM analysis: max_tokens must be less than input size"
        assert is_non_actionable_error(msg) is True

    # -- HTTP 5xx errors --

    def test_502_bad_gateway(self):
        msg = "Error during enhanced LLM analysis: 502 Bad Gateway"
        assert is_non_actionable_error(msg) is True

    def test_503_service_unavailable(self):
        msg = "Error during enhanced LLM analysis: 503 Service Unavailable"
        assert is_non_actionable_error(msg) is True

    def test_500_internal_server_error(self):
        msg = "Error during enhanced LLM analysis: 500 Internal Server Error"
        assert is_non_actionable_error(msg) is True

    def test_504_gateway_timeout(self):
        msg = "Error during enhanced LLM analysis: 504 Gateway Timeout"
        assert is_non_actionable_error(msg) is True

    def test_overloaded_error(self):
        msg = "Error during enhanced LLM analysis: overloaded_error: the API is overloaded"
        assert is_non_actionable_error(msg) is True

    # -- Rate-limit errors --

    def test_rate_limit(self):
        msg = "Error during enhanced LLM analysis: rate_limit_exceeded: too many requests"
        assert is_non_actionable_error(msg) is True

    def test_429_status(self):
        msg = "Error during enhanced LLM analysis: 429 Too Many Requests"
        assert is_non_actionable_error(msg) is True

    # -- Ollama error prefix --

    def test_ollama_prefix_5xx(self):
        msg = "Error during enhanced Ollama analysis: 502 Bad Gateway"
        assert is_non_actionable_error(msg) is True

    # -- Agentic error prefix --

    def test_agentic_prefix_token_limit(self):
        msg = "Error during agentic analysis turn 3: maximum context length exceeded"
        assert is_non_actionable_error(msg) is True

    def test_agentic_prefix_5xx(self):
        msg = "Error during agentic analysis turn 7: 503 Service Unavailable"
        assert is_non_actionable_error(msg) is True

    # -- Negative cases (should NOT be flagged) --

    def test_empty_string(self):
        assert is_non_actionable_error("") is False

    def test_none(self):
        assert is_non_actionable_error(None) is False

    def test_normal_review_text(self):
        review = (
            "## Priority Issues\n\n"
            "- [High] SQL injection risk in user_input handler at app.py:42\n\n"
            "## Summary\n\nThis PR adds a new endpoint."
        )
        assert is_non_actionable_error(review) is False

    def test_review_mentioning_500_in_content(self):
        """A legitimate review that mentions HTTP 500 should NOT be flagged."""
        review = (
            "## Priority Issues\n\n"
            "- [Medium] The handler returns a 500 Internal Server Error when "
            "the database connection fails.\n"
        )
        assert is_non_actionable_error(review) is False

    def test_review_mentioning_token_in_content(self):
        """A legitimate review that discusses tokens should NOT be flagged."""
        review = (
            "## Priority Issues\n\n"
            "- [Low] The token limit constant is hardcoded; consider making it configurable.\n"
        )
        assert is_non_actionable_error(review) is False

    def test_non_infra_error(self):
        """An LLM error that is NOT an infra failure should NOT be flagged."""
        msg = "Error during enhanced LLM analysis: Invalid API key"
        assert is_non_actionable_error(msg) is False

    def test_analysis_failed_fallback(self):
        """Fallback messages from clone/analysis failures are NOT infra errors."""
        msg = (
            "Analysis failed (clone error). Reviewing based on GitHub API data only.\n\n"
            "Files changed: 3 files with 42 additions and 10 deletions."
        )
        assert is_non_actionable_error(msg) is False

    def test_wrapped_in_review_comment(self):
        """Error wrapped in the Kit review markdown header should still be caught."""
        msg = (
            "## Kit AI Code Review\n\n"
            "Error during enhanced LLM analysis: 502 Bad Gateway\n\n"
            "---\n*Generated by cased kit*"
        )
        assert is_non_actionable_error(msg) is True


# ---------------------------------------------------------------------------
# Integration-style tests: verify post_pr_comment is NOT called
# ---------------------------------------------------------------------------

class TestReviewerSkipsPostOnNonActionableError:
    """Ensure PRReviewer.review_pr does not post when LLM returns a non-actionable error."""

    def _make_config(self, post_as_comment=True):
        from kit.pr_review.config import GitHubConfig, LLMConfig, LLMProvider, ReviewConfig

        return ReviewConfig(
            github=GitHubConfig(token="ghp_test"),
            llm=LLMConfig(provider=LLMProvider.OPENAI, api_key="sk-test", model="gpt-4"),
            post_as_comment=post_as_comment,
            quiet=True,
        )

    @patch("kit.pr_review.reviewer.PRReviewer.get_pr_details")
    @patch("kit.pr_review.reviewer.PRReviewer.get_pr_files")
    @patch("kit.pr_review.reviewer.PRReviewer.get_pr_diff")
    @patch("kit.pr_review.reviewer.PRReviewer.get_parsed_diff")
    @patch("kit.pr_review.reviewer.PRReviewer.get_repo_for_analysis")
    @patch("kit.pr_review.reviewer.PRReviewer.post_pr_comment")
    @patch("kit.pr_review.reviewer.asyncio.run")
    def test_5xx_error_not_posted(
        self,
        mock_asyncio_run,
        mock_post,
        mock_get_repo,
        mock_parsed_diff,
        mock_get_diff,
        mock_get_files,
        mock_get_details,
    ):
        mock_get_details.return_value = {
            "title": "Test PR",
            "user": {"login": "testuser"},
            "base": {"ref": "main", "repo": {"owner": {"login": "owner"}, "name": "repo"}},
            "head": {"ref": "feature", "sha": "abc123", "repo": {"owner": {"login": "owner"}, "name": "repo"}},
            "number": 1,
        }
        mock_get_files.return_value = [{"filename": "test.py", "additions": 1, "deletions": 0, "changes": 1}]
        mock_get_diff.return_value = "diff"
        mock_parsed_diff.return_value = {}
        mock_get_repo.return_value = "/tmp/repo"

        # Simulate LLM returning a 502 error
        mock_asyncio_run.return_value = "Error during enhanced LLM analysis: 502 Bad Gateway"

        config = self._make_config(post_as_comment=True)
        config.repo_path = "/tmp/repo"

        with patch("kit.pr_review.reviewer.validate_review_quality"):
            from kit.pr_review.reviewer import PRReviewer

            reviewer = PRReviewer(config)
            result = reviewer.review_pr("https://github.com/owner/repo/pull/1")

        # post_pr_comment must NOT have been called
        mock_post.assert_not_called()
        # The review text should still be returned locally
        assert "502 Bad Gateway" in result

    @patch("kit.pr_review.reviewer.PRReviewer.get_pr_details")
    @patch("kit.pr_review.reviewer.PRReviewer.get_pr_files")
    @patch("kit.pr_review.reviewer.PRReviewer.get_pr_diff")
    @patch("kit.pr_review.reviewer.PRReviewer.get_parsed_diff")
    @patch("kit.pr_review.reviewer.PRReviewer.get_repo_for_analysis")
    @patch("kit.pr_review.reviewer.PRReviewer.post_pr_comment")
    @patch("kit.pr_review.reviewer.asyncio.run")
    def test_token_limit_error_not_posted(
        self,
        mock_asyncio_run,
        mock_post,
        mock_get_repo,
        mock_parsed_diff,
        mock_get_diff,
        mock_get_files,
        mock_get_details,
    ):
        mock_get_details.return_value = {
            "title": "Test PR",
            "user": {"login": "testuser"},
            "base": {"ref": "main", "repo": {"owner": {"login": "owner"}, "name": "repo"}},
            "head": {"ref": "feature", "sha": "abc123", "repo": {"owner": {"login": "owner"}, "name": "repo"}},
            "number": 1,
        }
        mock_get_files.return_value = [{"filename": "test.py", "additions": 1, "deletions": 0, "changes": 1}]
        mock_get_diff.return_value = "diff"
        mock_parsed_diff.return_value = {}
        mock_get_repo.return_value = "/tmp/repo"

        # Simulate LLM returning a context-length error
        mock_asyncio_run.return_value = (
            "Error during enhanced LLM analysis: This model's maximum context length "
            "is 128000 tokens. However, your messages resulted in 200000 tokens."
        )

        config = self._make_config(post_as_comment=True)
        config.repo_path = "/tmp/repo"

        with patch("kit.pr_review.reviewer.validate_review_quality"):
            from kit.pr_review.reviewer import PRReviewer

            reviewer = PRReviewer(config)
            result = reviewer.review_pr("https://github.com/owner/repo/pull/1")

        mock_post.assert_not_called()
        assert "maximum context length" in result

    @patch("kit.pr_review.reviewer.PRReviewer.get_pr_details")
    @patch("kit.pr_review.reviewer.PRReviewer.get_pr_files")
    @patch("kit.pr_review.reviewer.PRReviewer.get_pr_diff")
    @patch("kit.pr_review.reviewer.PRReviewer.get_parsed_diff")
    @patch("kit.pr_review.reviewer.PRReviewer.get_repo_for_analysis")
    @patch("kit.pr_review.reviewer.PRReviewer.post_pr_comment")
    @patch("kit.pr_review.reviewer.asyncio.run")
    def test_successful_review_still_posted(
        self,
        mock_asyncio_run,
        mock_post,
        mock_get_repo,
        mock_parsed_diff,
        mock_get_diff,
        mock_get_files,
        mock_get_details,
    ):
        mock_get_details.return_value = {
            "title": "Test PR",
            "user": {"login": "testuser"},
            "base": {"ref": "main", "repo": {"owner": {"login": "owner"}, "name": "repo"}},
            "head": {"ref": "feature", "sha": "abc123", "repo": {"owner": {"login": "owner"}, "name": "repo"}},
            "number": 1,
        }
        mock_get_files.return_value = [{"filename": "test.py", "additions": 1, "deletions": 0, "changes": 1}]
        mock_get_diff.return_value = "diff"
        mock_parsed_diff.return_value = {}
        mock_get_repo.return_value = "/tmp/repo"

        # Simulate a successful LLM review
        mock_asyncio_run.return_value = (
            "## Priority Issues\n\n"
            "- [High] SQL injection risk at app.py:42\n\n"
            "## Summary\nThis PR adds a new endpoint."
        )
        mock_post.return_value = {"html_url": "https://github.com/owner/repo/pull/1#issuecomment-123"}

        config = self._make_config(post_as_comment=True)
        config.repo_path = "/tmp/repo"

        with patch("kit.pr_review.reviewer.validate_review_quality"):
            from kit.pr_review.reviewer import PRReviewer

            reviewer = PRReviewer(config)
            reviewer.review_pr("https://github.com/owner/repo/pull/1")

        # A normal review SHOULD be posted
        mock_post.assert_called_once()
