"""Tests that actually call LLMs to verify line number accuracy improvements."""

import os
import re

import pytest

from src.kit.pr_review.config import GitHubConfig, LLMConfig, LLMProvider, ReviewConfig
from src.kit.pr_review.diff_parser import DiffParser
from src.kit.pr_review.reviewer import PRReviewer


def is_ci_environment():
    """Check if we're running in a CI environment."""
    ci_indicators = [
        "CI",
        "CONTINUOUS_INTEGRATION",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "TRAVIS",
        "CIRCLECI",
        "JENKINS_URL",
        "BUILDKITE",
    ]
    return any(os.getenv(indicator) for indicator in ci_indicators)


class TestLLMLineAccuracy:
    """Test that LLMs actually produce more accurate line numbers with our improvements."""

    @pytest.fixture
    def config(self):
        """Create test config with real API keys if available."""
        # Skip in CI environments
        if is_ci_environment():
            pytest.skip("Skipping LLM tests in CI environment (no API keys, expensive)")

        # Try to get real API keys from environment
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if anthropic_key:
            return ReviewConfig(
                github=GitHubConfig(token="test"),
                llm=LLMConfig(
                    provider=LLMProvider.ANTHROPIC,
                    model="claude-3-5-haiku",  # Cheaper model for testing
                    api_key=anthropic_key,
                ),
            )
        elif openai_key:
            return ReviewConfig(
                github=GitHubConfig(token="test"),
                llm=LLMConfig(
                    provider=LLMProvider.OPENAI,
                    model="gpt-4o-mini",  # Cheaper model for testing
                    api_key=openai_key,
                ),
            )
        else:
            pytest.skip("No LLM API keys available for testing")

    @pytest.fixture
    def sample_diff(self):
        """Sample diff for testing."""
        return """diff --git a/auth.py b/auth.py
index 123..456 100644
--- a/auth.py
+++ b/auth.py
@@ -25,6 +25,8 @@ def authenticate_user(username, password):
     if not username or not password:
         return False

+    # Validate input length
+    username = username.strip()[:100]
     user = get_user(username)
     if user and verify_password(password, user.password_hash):
         return True"""

    @pytest.mark.integration
    @pytest.mark.llm
    @pytest.mark.skipif(is_ci_environment(), reason="Skip expensive LLM tests in CI")
    def test_llm_with_accurate_context(self, config, sample_diff):
        """Test that LLM produces accurate line numbers when given our context."""
        reviewer = PRReviewer(config)

        # Parse diff to get line context
        diff_files = DiffParser.parse_diff(sample_diff)
        line_context = DiffParser.generate_line_number_context(diff_files)

        # Create prompt with our line number context
        prompt = f"""Review this code change and provide specific feedback with accurate line numbers.

{line_context}

Diff:
```diff
{sample_diff}
```

IMPORTANT: Use the exact line numbers provided above when referencing code.
Format: [filename:line](https://github.com/owner/repo/blob/sha/filename#Lline)

Focus on the security improvement at line 28-29."""

        # Call LLM
        try:
            response = reviewer._call_llm(prompt)
        except Exception as e:
            pytest.skip(f"LLM call failed: {e}")

        # Extract line numbers from response
        line_refs = self._extract_line_numbers(response)

        # Verify line numbers are in the correct range (25-32 for our diff)
        valid_range = (25, 32)
        valid_refs = [ref for ref in line_refs if valid_range[0] <= ref <= valid_range[1]]
        invalid_refs = [ref for ref in line_refs if not (valid_range[0] <= ref <= valid_range[1])]

        # Most line references should be valid
        if line_refs:  # Only test if LLM actually provided line references
            accuracy_ratio = len(valid_refs) / len(line_refs)
            assert (
                accuracy_ratio >= 0.8
            ), f"Line accuracy too low: {accuracy_ratio}. Valid: {valid_refs}, Invalid: {invalid_refs}"

        # Response should mention the specific lines we highlighted
        assert any(28 <= ref <= 29 for ref in line_refs), f"LLM didn't reference lines 28-29: {line_refs}"

    @pytest.mark.integration
    @pytest.mark.llm
    @pytest.mark.skipif(is_ci_environment(), reason="Skip expensive LLM tests in CI")
    def test_llm_without_context_comparison(self, config, sample_diff):
        """Test LLM accuracy without our context vs with context."""
        reviewer = PRReviewer(config)

        # Test WITHOUT our context (old approach)
        prompt_without_context = f"""Review this code change:

```diff
{sample_diff}
```

Provide specific feedback with line numbers."""

        # Test WITH our context (new approach)
        diff_files = DiffParser.parse_diff(sample_diff)
        line_context = DiffParser.generate_line_number_context(diff_files)

        prompt_with_context = f"""Review this code change:

{line_context}

```diff
{sample_diff}
```

Use the exact line numbers provided above when referencing code."""

        try:
            response_without = reviewer._call_llm(prompt_without_context)
            response_with = reviewer._call_llm(prompt_with_context)
        except Exception as e:
            pytest.skip(f"LLM calls failed: {e}")

        # Extract line numbers from both responses
        refs_without = self._extract_line_numbers(response_without)
        refs_with = self._extract_line_numbers(response_with)

        # Calculate accuracy for both
        valid_range = (25, 32)

        if refs_without:
            accuracy_without = len([r for r in refs_without if valid_range[0] <= r <= valid_range[1]]) / len(
                refs_without
            )
        else:
            accuracy_without = 0

        if refs_with:
            accuracy_with = len([r for r in refs_with if valid_range[0] <= r <= valid_range[1]]) / len(refs_with)
        else:
            accuracy_with = 0

        # With context should be equal or better
        assert (
            accuracy_with >= accuracy_without
        ), f"Context didn't improve accuracy: {accuracy_with} vs {accuracy_without}"

        # If we have line references with context, accuracy should be high
        if refs_with:
            assert accuracy_with >= 0.7, f"Accuracy with context too low: {accuracy_with}"

    @pytest.mark.integration
    @pytest.mark.llm
    @pytest.mark.skipif(is_ci_environment(), reason="Skip expensive LLM tests in CI")
    def test_multi_file_llm_accuracy(self, config):
        """Test LLM accuracy with multi-file changes."""
        multi_diff = """diff --git a/models/user.py b/models/user.py
index aaa..bbb 100644
--- a/models/user.py
+++ b/models/user.py
@@ -15,4 +15,6 @@ class User:
     def __init__(self, username):
         self.username = username
         self.email = None
+        self.created_at = datetime.now()
+        self.is_active = True

diff --git a/views/auth.py b/views/auth.py
index ccc..ddd 100644
--- a/views/auth.py
+++ b/views/auth.py
@@ -30,3 +30,5 @@ def login_view(request):
     if user:
         login(request, user)
         return redirect('dashboard')
+    else:
+        logger.warning(f"Failed login attempt: {username}")"""

        reviewer = PRReviewer(config)

        # Generate context for multi-file diff
        diff_files = DiffParser.parse_diff(multi_diff)
        line_context = DiffParser.generate_line_number_context(diff_files)

        prompt = f"""Review this multi-file change:

{line_context}

```diff
{multi_diff}
```

Provide specific feedback for both files using exact line numbers."""

        try:
            response = reviewer._call_llm(prompt)
        except Exception as e:
            pytest.skip(f"LLM call failed: {e}")

        # Check that LLM references both files accurately
        user_py_refs = self._extract_line_numbers_for_file(response, "user.py")
        auth_py_refs = self._extract_line_numbers_for_file(response, "auth.py")

        # Validate ranges for each file
        user_py_range = (15, 20)  # Lines 15-20 for user.py
        auth_py_range = (30, 36)  # Lines 30-36 for auth.py

        if user_py_refs:
            user_accuracy = len([r for r in user_py_refs if user_py_range[0] <= r <= user_py_range[1]]) / len(
                user_py_refs
            )
            assert user_accuracy >= 0.7, f"User.py accuracy too low: {user_accuracy}"

        if auth_py_refs:
            auth_accuracy = len([r for r in auth_py_refs if auth_py_range[0] <= r <= auth_py_range[1]]) / len(
                auth_py_refs
            )
            assert auth_accuracy >= 0.7, f"Auth.py accuracy too low: {auth_accuracy}"

    @pytest.mark.integration
    @pytest.mark.llm
    @pytest.mark.expensive
    @pytest.mark.skipif(is_ci_environment(), reason="Skip expensive LLM tests in CI")
    def test_large_diff_llm_performance(self, config):
        """Test LLM performance and accuracy with larger diffs."""
        # Generate a larger diff
        large_diff = '''diff --git a/complex_service.py b/complex_service.py
index 111..222 100644
--- a/complex_service.py
+++ b/complex_service.py
@@ -45,8 +45,12 @@ class PaymentService:
     def process_payment(self, amount, card_token):
         """Process a payment transaction."""
         if not amount or amount <= 0:
             raise ValueError("Invalid amount")
+
+        # Add fraud detection
+        if self.is_suspicious_transaction(amount):
+            self.flag_for_review(amount, card_token)
+
         if not card_token:
             raise ValueError("Card token required")

@@ -67,6 +71,8 @@ class PaymentService:
         try:
             charge = self.stripe_client.create_charge(
                 amount=amount,
+                # Add idempotency key for safety
+                idempotency_key=self.generate_idempotency_key(),
                 source=card_token,
                 currency='usd'
             )
@@ -89,4 +95,7 @@ class PaymentService:
        """Log transaction for audit trail."""
        self.audit_logger.info(f"Transaction: {transaction_id}, Amount: {amount}")
        self.metrics.increment('payment.processed')
+
+        # Store transaction in database
+        self.db.store_transaction(transaction_id, amount, status)
        return True'''

        reviewer = PRReviewer(config)

        # Generate context
        diff_files = DiffParser.parse_diff(large_diff)
        line_context = DiffParser.generate_line_number_context(diff_files)

        prompt = f"""Review this payment service change:

{line_context}

```diff
{large_diff}
```

Focus on security and reliability improvements. Use exact line numbers."""

        try:
            response = reviewer._call_llm(prompt)
        except Exception as e:
            pytest.skip(f"LLM call failed: {e}")

        # Extract line references
        line_refs = self._extract_line_numbers(response)

        # Validate against the three changed ranges
        valid_ranges = [(45, 53), (71, 77), (95, 100)]
        valid_refs = []

        for ref in line_refs:
            if any(start <= ref <= end for start, end in valid_ranges):
                valid_refs.append(ref)

        if line_refs:
            accuracy = len(valid_refs) / len(line_refs)
            assert accuracy >= 0.6, f"Large diff accuracy too low: {accuracy}"

    def _extract_line_numbers(self, text: str) -> list[int]:
        """Extract line numbers from LLM response."""
        patterns = [
            r":(\d+)\]",  # [file.py:123]
            r"line\s+(\d+)",  # line 123
            r"Line\s+(\d+)",  # Line 123
            r"#L(\d+)",  # #L123
            r"\.py:(\d+)",  # file.py:123
        ]

        line_refs = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            line_refs.extend([int(m) for m in matches])

        return list(set(line_refs))  # Remove duplicates

    def _extract_line_numbers_for_file(self, text: str, filename: str) -> list[int]:
        """Extract line numbers specifically mentioned for a given file."""
        # Look for patterns like "user.py:123" or "in user.py line 123"
        patterns = [
            rf"{filename}:(\d+)",
            rf"in {filename}.*?line\s+(\d+)",
            rf"{filename}.*?#L(\d+)",
        ]

        line_refs = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            line_refs.extend([int(m) for m in matches])

        return list(set(line_refs))


class TestLLMContextEffectiveness:
    """Test that our line number context actually helps the LLM."""

    @pytest.fixture
    def config(self):
        """Create test config with real API keys if available."""
        # Skip in CI environments
        if is_ci_environment():
            pytest.skip("Skipping LLM tests in CI environment (no API keys, expensive)")

        # Try to get real API keys from environment
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if anthropic_key:
            return ReviewConfig(
                github=GitHubConfig(token="test"),
                llm=LLMConfig(
                    provider=LLMProvider.ANTHROPIC,
                    model="claude-3-5-haiku",  # Cheaper model for testing
                    api_key=anthropic_key,
                ),
            )
        elif openai_key:
            return ReviewConfig(
                github=GitHubConfig(token="test"),
                llm=LLMConfig(
                    provider=LLMProvider.OPENAI,
                    model="gpt-4o-mini",  # Cheaper model for testing
                    api_key=openai_key,
                ),
            )
        else:
            pytest.skip("No LLM API keys available for testing")

    @pytest.fixture
    def sample_diff(self):
        """Sample diff for testing."""
        return """diff --git a/auth.py b/auth.py
index 123..456 100644
--- a/auth.py
+++ b/auth.py
@@ -25,6 +25,8 @@ def authenticate_user(username, password):
     if not username or not password:
         return False

+    # Validate input length
+    username = username.strip()[:100]
     user = get_user(username)
     if user and verify_password(password, user.password_hash):
         return True"""

    @pytest.mark.integration
    @pytest.mark.llm
    @pytest.mark.skipif(is_ci_environment(), reason="Skip expensive LLM tests in CI")
    def test_context_improves_specificity(self, config, sample_diff):
        """Test that context makes LLM responses more specific."""
        reviewer = PRReviewer(config)

        # Test specificity without context
        vague_prompt = "Review this code change and give feedback."

        # Test with our detailed context
        diff_files = DiffParser.parse_diff(sample_diff)
        line_context = DiffParser.generate_line_number_context(diff_files)

        specific_prompt = f"""Review this code change with specific line references:

{line_context}

```diff
{sample_diff}
```

Provide detailed feedback using the exact line numbers shown above."""

        try:
            vague_response = reviewer._call_llm(vague_prompt)
            specific_response = reviewer._call_llm(specific_prompt)
        except Exception as e:
            pytest.skip(f"LLM calls failed: {e}")

        # Count specific indicators
        vague_specificity = self._count_specificity_indicators(vague_response)
        specific_specificity = self._count_specificity_indicators(specific_response)

        # Specific prompt should yield more specific responses
        assert (
            specific_specificity >= vague_specificity
        ), f"Context didn't improve specificity: {specific_specificity} vs {vague_specificity}"

    def _count_specificity_indicators(self, text: str) -> int:
        """Count indicators of specific feedback."""
        indicators = [
            r"line\s+\d+",  # "line 123"
            r"#L\d+",  # "#L123"
            r":\d+\]",  # ":123]"
            r"specific",  # word "specific"
            r"exactly",  # word "exactly"
            r"at line",  # "at line"
        ]

        count = 0
        for pattern in indicators:
            count += len(re.findall(pattern, text, re.IGNORECASE))

        return count
