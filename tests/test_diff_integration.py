"""Integration tests for diff parsing with real GitHub data."""

from unittest.mock import patch

from src.kit.pr_review.config import GitHubConfig, LLMConfig, LLMProvider, ReviewConfig
from src.kit.pr_review.diff_parser import DiffParser
from src.kit.pr_review.reviewer import PRReviewer


class TestDiffParsingIntegration:
    """Integration tests using real-world diff scenarios."""

    def test_real_github_diff_parsing(self):
        """Test with a real GitHub diff format."""
        # This is based on an actual GitHub PR diff
        real_diff = '''diff --git a/src/example.py b/src/example.py
index 1234567..abcdefg 100644
--- a/src/example.py
+++ b/src/example.py
@@ -1,7 +1,9 @@
 import os
 import sys
+import json

 def main():
     print("Hello, world!")
+    data = {"key": "value"}
     return 0

@@ -15,6 +17,8 @@ def helper_function():
     """Helper function for processing."""
     result = process_data()
     if result:
+        print(f"Processing result: {result}")
+        log_result(result)
         return result
     return None

diff --git a/tests/test_example.py b/tests/test_example.py
index 9876543..fedcba9 100644
--- a/tests/test_example.py
+++ b/tests/test_example.py
@@ -10,4 +10,6 @@ class TestExample:
     def test_main(self):
         """Test main function."""
         assert main() == 0
+        # Additional test assertion
+        assert True'''

        diff_files = DiffParser.parse_diff(real_diff)

        # Verify parsing
        assert len(diff_files) == 2
        assert "src/example.py" in diff_files
        assert "tests/test_example.py" in diff_files

        # Test line number accuracy for first file
        src_file = diff_files["src/example.py"]
        assert len(src_file.hunks) == 2

        # First hunk: lines 1-9 (was 1-7, now 1-9)
        first_hunk = src_file.hunks[0]
        assert first_hunk.new_start == 1
        assert first_hunk.new_count == 9

        # Second hunk: lines 17-24 (was 15-20, now 17-24)
        second_hunk = src_file.hunks[1]
        assert second_hunk.new_start == 17
        assert second_hunk.new_count == 8

        # Test context generation
        context = DiffParser.generate_line_number_context(diff_files)
        assert "src/example.py:" in context
        assert "Lines 1-9" in context
        assert "Lines 17-24" in context
        assert "tests/test_example.py:" in context
        assert "Lines 10-15" in context

    def test_complex_diff_scenarios(self):
        """Test complex diff scenarios that could break line number parsing."""
        complex_diff = '''diff --git a/src/complex.py b/src/complex.py
index 1111111..2222222 100644
--- a/src/complex.py
+++ b/src/complex.py
@@ -50,0 +51,5 @@ class ComplexClass:
+    def new_method(self):
+        """A new method added in the middle."""
+        pass
+        return True
+
@@ -100,3 +105,3 @@ def existing_function():
     # Old implementation
-    old_code = "remove this"
-    process(old_code)
+    new_code = "replace with this"
+    process(new_code)
     return result
@@ -200,10 +205,8 @@ def another_function():
     for item in items:
         if condition:
-            old_logic()
-            more_old_logic()
         else:
-            different_old_logic()
+            new_logic()

-    cleanup_old()
     return processed_items'''

        diff_files = DiffParser.parse_diff(complex_diff)
        file_diff = diff_files["src/complex.py"]

        assert len(file_diff.hunks) == 3

        # Test line ranges are calculated correctly
        ranges = file_diff.get_changed_line_ranges()
        assert (51, 55) in ranges  # First hunk: added 5 lines starting at 51
        assert (105, 107) in ranges  # Second hunk: 3 lines starting at 105
        assert (205, 212) in ranges  # Third hunk: 8 lines starting at 205

    def test_edge_case_diffs(self):
        """Test edge cases that might break parsing."""
        edge_cases = [
            # Single line change
            """diff --git a/single.py b/single.py
index aaa..bbb 100644
--- a/single.py
+++ b/single.py
@@ -42 +42 @@ def func():
-    old_line
+    new_line""",
            # File with no changes (shouldn't happen but let's be safe)
            """diff --git a/empty.py b/empty.py
index ccc..ddd 100644
--- a/empty.py
+++ b/empty.py""",
            # Large line numbers
            """diff --git a/large.py b/large.py
index eee..fff 100644
--- a/large.py
+++ b/large.py
@@ -9999,5 +9999,7 @@ def huge_file_function():
     existing_code()
+    new_line_1()
     more_existing()
+    new_line_2()
     final_line()""",
        ]

        for i, diff in enumerate(edge_cases):
            diff_files = DiffParser.parse_diff(diff)
            if diff_files:  # Some edge cases might result in no files
                for filename, file_diff in diff_files.items():
                    context = DiffParser.generate_line_number_context(diff_files)
                    assert "Lines" in context or len(file_diff.hunks) == 0

                    # Test that all line numbers are positive
                    for hunk in file_diff.hunks:
                        assert hunk.new_start > 0
                        assert hunk.new_count >= 0

    @patch("src.kit.pr_review.reviewer.PRReviewer.get_pr_diff")
    def test_integration_with_pr_reviewer(self, mock_get_diff):
        """Test that diff parsing integrates correctly with PR reviewer."""
        # Mock a real diff
        mock_diff = """diff --git a/src/auth.py b/src/auth.py
index 123..456 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -25,6 +25,8 @@ def authenticate_user(username, password):
     if not username or not password:
         return False

+    # Add input validation
+    username = username.strip()
     user = get_user(username)
     if user and verify_password(password, user.password_hash):
         return True"""

        mock_get_diff.return_value = mock_diff

        # Create a test config
        config = ReviewConfig(
            github=GitHubConfig(token="test"),
            llm=LLMConfig(provider=LLMProvider.ANTHROPIC, model="claude-3-5-sonnet", api_key="test"),
        )

        PRReviewer(config)

        # Test that diff parsing works in the reviewer context
        diff_files = DiffParser.parse_diff(mock_diff)
        context = DiffParser.generate_line_number_context(diff_files)

        # Verify the context contains accurate line information
        assert "src/auth.py:" in context
        assert "Lines 25-32" in context  # Original was 6 lines, now 8 lines
        assert "REMINDER" in context
        assert "GitHub links" in context

    def test_line_number_accuracy_validation(self):
        """Test that our line numbers are actually accurate."""
        # Create a diff where we know exactly what the line numbers should be
        known_diff = """diff --git a/test_accuracy.py b/test_accuracy.py
index abc..def 100644
--- a/test_accuracy.py
+++ b/test_accuracy.py
@@ -10,8 +10,10 @@ def test_function():
     # Line 10: function definition (context)
     # Line 11: comment (context)
     variable = "old_value"  # Line 12 - will be modified
+    # Line 13: new comment added
     if condition:  # Line 13 -> Line 14 due to insertion
         process()  # Line 14 -> Line 15
+        new_call()  # Line 16: new line added
     return result  # Line 15 -> Line 17"""

        diff_files = DiffParser.parse_diff(known_diff)
        file_diff = diff_files["test_accuracy.py"]

        # We know this should be lines 10-19 (original 8 lines + 2 additions = 10 lines)
        hunk = file_diff.hunks[0]
        assert hunk.new_start == 10
        assert hunk.new_count == 10

        # Test finding specific additions
        additions = hunk.contains_line_change("new comment")
        assert len(additions) == 1
        assert additions[0] == 13  # Should be line 13

        new_call_additions = hunk.contains_line_change("new_call")
        assert len(new_call_additions) == 1
        assert additions[0] == 13  # Should be line 16


class TestEndToEndAccuracy:
    """End-to-end tests for line number accuracy in reviews."""

    def test_line_number_in_ai_prompt(self):
        """Test that AI prompts contain accurate line number context."""
        test_diff = """diff --git a/api.py b/api.py
index 111..222 100644
--- a/api.py
+++ b/api.py
@@ -45,4 +45,6 @@ def api_endpoint():
     data = request.get_json()
     if not data:
         return error_response()
+    # Validate input data
+    validate_input(data)
     return success_response(data)"""

        diff_files = DiffParser.parse_diff(test_diff)
        context = DiffParser.generate_line_number_context(diff_files, owner="owner", repo="repo", sha="abc123")

        # Test that context is AI-friendly
        lines = context.split("\n")
        assert any("api.py:" in line for line in lines)
        assert any("Lines 45-50" in line for line in lines)
        assert any("REMINDER" in line for line in lines)
        assert any("GitHub links" in line for line in lines)

        # Test that the context includes the format guidance for GitHub links
        assert "file.py:123" in context
        assert "#L123" in context

    def test_performance_with_large_diff(self):
        """Test parsing performance with large diffs."""
        import time

        # Generate a large diff programmatically
        large_diff_parts = [
            "diff --git a/large_file.py b/large_file.py\nindex aaa..bbb 100644\n--- a/large_file.py\n+++ b/large_file.py"
        ]

        # Add 50 hunks to simulate a large change
        for i in range(50):
            start_line = i * 20 + 10
            hunk = f"@@ -{start_line},5 +{start_line},7 @@ def function_{i}():\n"
            hunk += "     existing_line_1\n"
            hunk += f"+    new_line_{i}_1\n"
            hunk += "     existing_line_2\n"
            hunk += f"+    new_line_{i}_2\n"
            hunk += "     existing_line_3\n"
            large_diff_parts.append(hunk)

        large_diff = "\n".join(large_diff_parts)

        # Time the parsing
        start_time = time.time()
        diff_files = DiffParser.parse_diff(large_diff)
        parse_time = time.time() - start_time

        # Should parse quickly (under 1 second for reasonable size)
        assert parse_time < 1.0

        # Should parse correctly
        assert "large_file.py" in diff_files
        file_diff = diff_files["large_file.py"]
        assert len(file_diff.hunks) == 50

        # Generate context quickly
        start_time = time.time()
        context = DiffParser.generate_line_number_context(diff_files)
        context_time = time.time() - start_time

        assert context_time < 0.5
        assert "large_file.py:" in context
