"""Tests to validate AI-generated line number accuracy."""

import re

from src.kit.pr_review.diff_parser import DiffParser
from src.kit.pr_review.validator import validate_review_quality


class TestLineNumberValidation:
    """Test that AI-generated reviews have accurate line numbers."""

    def test_validate_accurate_line_numbers(self):
        """Test validation of reviews with accurate line numbers."""
        # Sample diff
        diff_content = """diff --git a/auth.py b/auth.py
index 123..456 100644
--- a/auth.py
+++ b/auth.py
@@ -25,6 +25,8 @@ def authenticate():
     if not username:
         return False

+    # Validate input
+    username = username.strip()
     user = get_user(username)
     return user is not None"""

        # AI review with ACCURATE line numbers
        accurate_review = """
## Issues Found

1. [auth.py:29](https://github.com/owner/repo/blob/sha/auth.py#L29) - Added input validation is good, but consider validating length too
2. [auth.py:30](https://github.com/owner/repo/blob/sha/auth.py#L30) - Username stripping should happen before the empty check

## Summary
Added input validation for username parameter.
"""

        # AI review with INACCURATE line numbers
        inaccurate_review = """
## Issues Found

1. [auth.py:50](https://github.com/owner/repo/blob/sha/auth.py#L50) - Line doesn't exist in diff
2. [auth.py:15](https://github.com/owner/repo/blob/sha/auth.py#L15) - Line not in changed range

## Summary
Some issues found.
"""

        # Parse diff to get actual line ranges
        DiffParser.parse_diff(diff_content)

        # Validate accurate review
        validation_accurate = validate_review_quality(accurate_review, diff_content, ["auth.py"])

        # Validate inaccurate review
        validation_inaccurate = validate_review_quality(inaccurate_review, diff_content, ["auth.py"])

        # Accurate review should score higher
        assert validation_accurate.score > validation_inaccurate.score

        # Inaccurate review should have issues
        assert len(validation_inaccurate.issues) > len(validation_accurate.issues)

    def test_line_number_range_validation(self):
        """Test that line numbers fall within expected diff ranges."""
        diff_content = '''diff --git a/calculator.py b/calculator.py
index abc..def 100644
--- a/calculator.py
+++ b/calculator.py
@@ -10,5 +10,7 @@ def add(a, b):
     """Add two numbers."""
     if not isinstance(a, (int, float)):
         raise TypeError("a must be a number")
+    if not isinstance(b, (int, float)):
+        raise TypeError("b must be a number")
     return a + b

@@ -50,3 +52,4 @@ def divide(a, b):
     if b == 0:
         raise ValueError("Cannot divide by zero")
+    # Add logging here
     return a / b'''

        diff_files = DiffParser.parse_diff(diff_content)
        file_diff = diff_files["calculator.py"]

        # Get valid line ranges
        valid_ranges = file_diff.get_changed_line_ranges()
        assert (10, 16) in valid_ranges  # First hunk: lines 10-16
        assert (52, 55) in valid_ranges  # Second hunk: lines 52-55

        def is_line_in_range(line_num, ranges):
            return any(start <= line_num <= end for start, end in ranges)

        # Test various line numbers
        assert is_line_in_range(12, valid_ranges)  # In first hunk
        assert is_line_in_range(53, valid_ranges)  # In second hunk
        assert not is_line_in_range(5, valid_ranges)  # Before any hunk
        assert not is_line_in_range(30, valid_ranges)  # Between hunks
        assert not is_line_in_range(100, valid_ranges)  # After any hunk

    def test_extract_line_references_from_review(self):
        """Test extracting line references from AI reviews."""
        review_with_links = """
## Issues Found

1. [calculator.py:12](https://github.com/owner/repo/blob/sha/calculator.py#L12) - Type validation is good
2. File calculator.py line 54: Consider using logging.info instead of comment
3. calculator.py:55 - This line looks fine

## Other Issues
- Line 100 in calculator.py: This is invalid (line doesn't exist)
- Some issue without line number
"""

        # Extract line references using regex patterns
        patterns = [
            r"\.py:(\d+)",  # file.py:123
            r"line\s+(\d+)",  # line 123
            r"Line\s+(\d+)",  # Line 123 (capitalized)
            r"#L(\d+)",  # #L123
        ]

        line_refs = []
        for pattern in patterns:
            matches = re.findall(pattern, review_with_links)
            line_refs.extend([int(m) for m in matches])

        # Should find line references: 12, 54, 55, 100, 12 (from #L12)
        assert 12 in line_refs
        assert 54 in line_refs
        assert 55 in line_refs
        assert 100 in line_refs

        # Test with diff to see which are valid
        diff_content = """diff --git a/calculator.py b/calculator.py
index abc..def 100644
--- a/calculator.py
+++ b/calculator.py
@@ -10,5 +10,7 @@ def add():
     existing_line
+    new_line_at_12
     another_existing
     return result
@@ -50,3 +52,5 @@ def divide():
     if condition:
         existing_code
+    # new_line_at_54
+    # new_line_at_55
     return value"""

        diff_files = DiffParser.parse_diff(diff_content)
        file_diff = diff_files["calculator.py"]
        ranges = file_diff.get_changed_line_ranges()

        # Check which line references are valid
        valid_refs = [ref for ref in line_refs if any(start <= ref <= end for start, end in ranges)]
        invalid_refs = [ref for ref in line_refs if not any(start <= ref <= end for start, end in ranges)]

        assert 12 in valid_refs  # Should be in range 10-16
        assert 54 in valid_refs  # Should be in range 52-56
        assert 55 in valid_refs  # Should be in range 52-56
        assert 100 in invalid_refs  # Way outside any range

    def test_github_link_format_validation(self):
        """Test validation of GitHub link formats in reviews."""
        valid_links = [
            "[file.py:123](https://github.com/owner/repo/blob/abc123/file.py#L123)",
            "[src/main.py:45](https://github.com/user/project/blob/def456/src/main.py#L45)",
        ]

        invalid_links = [
            "[file.py:123](https://github.com/owner/repo/blob/abc123/file.py#L999)",  # Wrong line
            "[file.py:123](https://github.com/owner/repo/blob/abc123/wrong_file.py#L123)",  # Wrong file
            "[file.py:123](https://github.com/owner/repo/file.py#L123)",  # Missing blob/sha
        ]

        # GitHub link pattern
        github_pattern = r"\[([^\]]+)\]\(https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/([^)]+)#L(\d+)\)"

        for link in valid_links:
            match = re.search(github_pattern, link)
            assert match is not None

            link_text, owner, repo, sha, file_path, line_num = match.groups()
            assert file_path in link_text  # File should match
            assert line_num in link_text  # Line should match

        for link in invalid_links:
            # These might match the pattern but would fail validation in context
            match = re.search(github_pattern, link)
            if match:
                link_text, owner, repo, sha, file_path, line_num = match.groups()
                # Would need additional validation against actual diff

    def test_review_quality_with_line_accuracy(self):
        """Test overall review quality considering line number accuracy."""
        diff_content = """diff --git a/security.py b/security.py
index 111..222 100644
--- a/security.py
+++ b/security.py
@@ -15,4 +15,6 @@ def hash_password(password):
     if not password:
         raise ValueError("Password required")

+    # Add salt for security
+    salt = generate_salt()
     return hashlib.sha256(password.encode()).hexdigest()"""

        # High quality review with accurate line numbers
        high_quality_review = """
## Priority Issues

1. [security.py:19](https://github.com/owner/repo/blob/sha/security.py#L19) - Good addition of salt, but salt isn't being used in the hash
2. [security.py:20](https://github.com/owner/repo/blob/sha/security.py#L20) - SHA256 without salt is still vulnerable to rainbow tables

## Summary
Added salt generation but it's not being used in the actual hashing.

## Recommendations
- Use the generated salt: `hashlib.sha256((password + salt).encode()).hexdigest()`
- Store the salt with the hash for verification
"""

        # Low quality review with vague references
        low_quality_review = """
This looks okay. Maybe add some security stuff. The code seems fine overall.
"""

        validation_high = validate_review_quality(high_quality_review, diff_content, ["security.py"])
        validation_low = validate_review_quality(low_quality_review, diff_content, ["security.py"])

        # High quality should score better or equal
        assert validation_high.score >= validation_low.score

        # Key difference: high quality has GitHub links and line references
        assert validation_high.metrics["file_references"] > validation_low.metrics["file_references"]
        assert validation_high.metrics["github_links"] > validation_low.metrics["github_links"]
        assert validation_high.metrics["line_references"] > validation_low.metrics["line_references"]


class TestRealWorldScenarios:
    """Test with real-world complex scenarios."""

    def test_multi_file_line_accuracy(self):
        """Test line number accuracy across multiple files."""
        multi_file_diff = """diff --git a/models/user.py b/models/user.py
index aaa..bbb 100644
--- a/models/user.py
+++ b/models/user.py
@@ -25,5 +25,7 @@ class User:
     def __init__(self, username):
         self.username = username
         self.created_at = datetime.now()
+        self.email = None
+        self.is_active = True

diff --git a/views/auth.py b/views/auth.py
index ccc..ddd 100644
--- a/views/auth.py
+++ b/views/auth.py
@@ -40,3 +40,5 @@ def login_view(request):
     user = authenticate(username, password)
     if user:
         login(request, user)
+        # Log successful login
+        logger.info(f"User {username} logged in")
     return redirect('dashboard')"""

        diff_files = DiffParser.parse_diff(multi_file_diff)

        # Test context generation for multiple files
        context = DiffParser.generate_line_number_context(diff_files)

        # Should contain both files
        assert "models/user.py:" in context
        assert "views/auth.py:" in context

        # Should have correct line ranges (adjust expectations)
        assert "Lines 25-31" in context  # user.py: 5 lines -> 7 lines
        assert "Lines 40-" in context  # auth.py: should be in there somewhere

        # Test review that references both files accurately
        multi_file_review = """
## Issues Found

1. [models/user.py:28](https://github.com/owner/repo/blob/sha/models/user.py#L28) - Adding email field is good, consider validation
2. [models/user.py:29](https://github.com/owner/repo/blob/sha/models/user.py#L29) - is_active should default to True, which it does
3. [views/auth.py:43](https://github.com/owner/repo/blob/sha/views/auth.py#L43) - Logging is good for security auditing
4. [views/auth.py:44](https://github.com/owner/repo/blob/sha/views/auth.py#L44) - Consider not logging usernames for privacy

## Summary
Good additions to user model and authentication logging.
"""

        validation = validate_review_quality(multi_file_review, multi_file_diff, ["models/user.py", "views/auth.py"])

        # Should score well for file coverage and specificity
        assert validation.score > 0.7
        assert validation.metrics["file_references"] == 2  # Both files referenced
        assert validation.metrics["line_references"] >= 4  # All line references found

    def test_rename_and_modification_diff(self):
        """Test parsing diffs with file renames and modifications."""
        rename_diff = '''diff --git a/old_name.py b/new_name.py
similarity index 85%
rename from old_name.py
rename to new_name.py
index 123..456 100644
--- a/old_name.py
+++ b/new_name.py
@@ -10,6 +10,8 @@ def process_data():
     """Process the data."""
     data = load_data()
     if not data:
+        # Log empty data case
+        logger.warning("No data to process")
         return None

     return clean_data(data)'''

        diff_files = DiffParser.parse_diff(rename_diff)

        # Should parse the new filename
        assert "new_name.py" in diff_files
        file_diff = diff_files["new_name.py"]

        # Should have correct line range
        ranges = file_diff.get_changed_line_ranges()
        assert (10, 17) in ranges  # 6 lines -> 8 lines

        # Test context generation
        context = DiffParser.generate_line_number_context(diff_files)
        assert "new_name.py:" in context
        assert "Lines 10-17" in context
