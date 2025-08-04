"""Tests for high-priority issue validation functionality."""

from unittest.mock import MagicMock, patch

import pytest

from kit.pr_review.config import LLMConfig, LLMProvider
from kit.pr_review.high_issue_validator import (
    HighIssueValidation,
    HighIssueValidator,
    apply_validation_results,
)


class TestHighIssueValidator:
    """Test high-priority issue validation."""

    @pytest.fixture
    def llm_config(self):
        """Create test LLM config."""
        return LLMConfig(
            provider=LLMProvider.ANTHROPIC, model="claude-3-sonnet", api_key="test-key", max_tokens=500, temperature=0.1
        )

    @pytest.fixture
    def validator(self, llm_config):
        """Create test validator."""
        return HighIssueValidator(llm_config, validation_threshold=0.7)

    def test_extract_high_priority_issues(self, validator):
        """Test extracting high-priority issues from review text."""
        review_text = """
## Priority Issues

### High Priority
- [auth.py:45](https://github.com/owner/repo/blob/sha/auth.py#L45) - SQL injection vulnerability in login function
- Missing input validation in user_input.py:123
- **Critical**: Buffer overflow in parser.c:89

### Medium Priority
- Code duplication in utils.py
"""

        issues = validator.extract_high_priority_issues(review_text)

        assert len(issues) == 3
        assert "SQL injection" in issues[0]["issue"]
        assert issues[0]["file"] == "auth.py"
        assert issues[0]["line"] == "45"

        assert "Missing input validation" in issues[1]["issue"]
        assert issues[1]["file"] == "user_input.py"
        assert issues[1]["line"] == "123"

        assert "Buffer overflow" in issues[2]["issue"]
        assert issues[2]["file"] == "parser.c"
        assert issues[2]["line"] == "89"

    def test_extract_high_priority_issues_different_format(self, validator):
        """Test extraction with different formatting."""
        review_text = """
## Code Review

## HIGH Priority

* Security issue in config.py line 22
* Potential memory leak at [memory.c:100]

## Low Priority
* Style issues
"""

        issues = validator.extract_high_priority_issues(review_text)

        assert len(issues) == 2
        assert "Security issue" in issues[0]["issue"]
        assert "memory leak" in issues[1]["issue"]

    @pytest.mark.asyncio
    async def test_validate_single_issue(self, validator):
        """Test validation of a single issue."""
        issue = {"issue": "SQL injection in auth.py:45", "file": "auth.py", "line": "45"}

        # Mock LLM response
        mock_response = """
VALID: true
CONFIDENCE: 0.9
REASONING: The code shows direct string interpolation of user input into SQL query without parameterization.
SUGGESTED_FIX: N/A
"""

        with patch.object(validator, "_call_llm", return_value=mock_response):
            validation = await validator._validate_single_issue(issue, "mock diff", {}, "PR context")

        assert validation.is_valid is True
        assert validation.confidence == 0.9
        assert "string interpolation" in validation.reasoning
        assert validation.suggested_fix is None

    @pytest.mark.asyncio
    async def test_validate_issues_batch(self, validator):
        """Test batch validation of multiple issues."""
        issues = [
            {"issue": "Issue 1", "file": "file1.py", "line": "10"},
            {"issue": "Issue 2", "file": "file2.py", "line": "20"},
        ]

        # Mock different responses
        responses = [
            "VALID: true\nCONFIDENCE: 0.8\nREASONING: Valid issue\nSUGGESTED_FIX: N/A",
            "VALID: false\nCONFIDENCE: 0.3\nREASONING: Not a real issue\nSUGGESTED_FIX: Remove this",
        ]

        with patch.object(validator, "_call_llm", side_effect=responses):
            validations = await validator.validate_issues(issues, "diff", {}, "context")

        assert len(validations) == 2
        assert validations[0].is_valid is True
        assert validations[0].confidence == 0.8
        assert validations[1].is_valid is False
        assert validations[1].confidence == 0.3
        assert validations[1].suggested_fix == "Remove this"

    def test_apply_validation_results(self):
        """Test applying validation results to filter review."""
        review_text = """
## Priority Issues

### High Priority
- Issue 1: Valid security issue
- Issue 2: False positive
- Issue 3: Another valid issue

### Medium Priority
- Some medium issue
"""

        validations = [
            HighIssueValidation(
                issue="Issue 1: Valid security issue", is_valid=True, confidence=0.9, reasoning="Confirmed"
            ),
            HighIssueValidation(
                issue="Issue 2: False positive", is_valid=False, confidence=0.2, reasoning="Not a real issue"
            ),
            HighIssueValidation(
                issue="Issue 3: Another valid issue", is_valid=True, confidence=0.8, reasoning="Confirmed"
            ),
        ]

        filtered_review, removed, total = apply_validation_results(review_text, validations, threshold=0.7)

        assert removed == 1
        assert total == 3
        assert "Issue 1: Valid security issue" in filtered_review
        assert "Issue 2: False positive" not in filtered_review
        assert "Issue 3: Another valid issue" in filtered_review
        assert "1 high-priority issue(s) removed after validation" in filtered_review

    def test_apply_validation_results_all_valid(self):
        """Test when all issues are valid."""
        review_text = """
### High Priority
- Issue 1
- Issue 2
"""

        validations = [
            HighIssueValidation("Issue 1", True, 0.9, "Valid"),
            HighIssueValidation("Issue 2", True, 0.8, "Valid"),
        ]

        filtered_review, removed, total = apply_validation_results(review_text, validations, threshold=0.7)

        assert removed == 0
        assert total == 2
        assert "Issue 1" in filtered_review
        assert "Issue 2" in filtered_review
        assert "removed after validation" not in filtered_review

    def test_parse_validation_response(self, validator):
        """Test parsing LLM validation response."""
        response = """
VALID: false
CONFIDENCE: 0.4
REASONING: The issue description doesn't match the actual code. The function has proper input validation.
SUGGESTED_FIX: Change to "Consider adding rate limiting" instead of "SQL injection"
"""

        validation = validator._parse_validation_response("Test issue", response)

        assert validation.issue == "Test issue"
        assert validation.is_valid is False
        assert validation.confidence == 0.4
        assert "doesn't match the actual code" in validation.reasoning
        assert "rate limiting" in validation.suggested_fix

    def test_parse_validation_response_malformed(self, validator):
        """Test parsing malformed response."""
        response = "This is not a properly formatted response"

        validation = validator._parse_validation_response("Test issue", response)

        # Should have defaults
        assert validation.is_valid is False
        assert validation.confidence == 0.5
        assert validation.reasoning == "No reasoning provided"
        assert validation.suggested_fix is None

    @pytest.mark.asyncio
    async def test_anthropic_call(self, validator):
        """Test Anthropic API call."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="VALID: true\nCONFIDENCE: 0.9")]
        mock_client.messages.create.return_value = mock_response

        validator._llm_client = mock_client

        result = await validator._call_anthropic("test prompt")

        assert result == "VALID: true\nCONFIDENCE: 0.9"
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_openai_call(self, validator):
        """Test OpenAI API call."""
        validator.llm_config.provider = LLMProvider.OPENAI

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="VALID: true"))]
        mock_client.chat.completions.create.return_value = mock_response

        validator._llm_client = mock_client

        result = await validator._call_openai("test prompt")

        assert result == "VALID: true"
        mock_client.chat.completions.create.assert_called_once()

    def test_extract_relevant_diff(self, validator):
        """Test extracting relevant diff context."""
        from kit.pr_review.diff_parser import DiffHunk, FileDiff

        # Create test diff
        hunk = DiffHunk(
            old_start=40,
            old_count=10,
            new_start=40,
            new_count=12,
            lines=[
                "  def login(self, username, password):",
                "-     query = f'SELECT * FROM users WHERE username = {username}'",
                "+     query = 'SELECT * FROM users WHERE username = ?'",
                "+     cursor.execute(query, (username,))",
                "      return cursor.fetchone()",
            ],
        )

        file_diff = FileDiff(filename="auth.py", hunks=[hunk])

        diff_files = {"auth.py": file_diff}

        result = validator._extract_relevant_diff("auth.py", "42", diff_files, "full diff")

        assert result is not None
        assert "@@ -40,10 +40,12 @@" in result
        assert "SELECT * FROM users" in result
