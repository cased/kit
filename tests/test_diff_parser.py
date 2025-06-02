"""Tests for diff parsing utilities."""

from src.kit.pr_review.diff_parser import DiffHunk, DiffParser, FileDiff


def test_parse_hunk_header():
    """Test parsing of diff hunk headers."""
    # Standard hunk header
    header = "@@ -10,5 +12,7 @@"
    hunk = DiffParser._parse_hunk_header(header)

    assert hunk is not None
    assert hunk.old_start == 10
    assert hunk.old_count == 5
    assert hunk.new_start == 12
    assert hunk.new_count == 7

    # Single line change
    header = "@@ -42 +42 @@"
    hunk = DiffParser._parse_hunk_header(header)

    assert hunk is not None
    assert hunk.old_start == 42
    assert hunk.old_count == 1
    assert hunk.new_start == 42
    assert hunk.new_count == 1


def test_parse_simple_diff():
    """Test parsing a simple git diff."""
    diff_content = """diff --git a/src/test.py b/src/test.py
index abc123..def456 100644
--- a/src/test.py
+++ b/src/test.py
@@ -10,5 +10,7 @@ def main():
     print("hello")
     # This is a comment
+    print("new line")
     if True:
         pass
+    print("another new line")
     return 0"""

    diff_files = DiffParser.parse_diff(diff_content)

    assert "src/test.py" in diff_files
    file_diff = diff_files["src/test.py"]

    assert len(file_diff.hunks) == 1
    hunk = file_diff.hunks[0]

    assert hunk.old_start == 10
    assert hunk.old_count == 5
    assert hunk.new_start == 10
    assert hunk.new_count == 7

    # Check that the hunk lines were captured
    assert len(hunk.lines) > 0
    assert any(line.startswith("+") for line in hunk.lines)


def test_multiple_files_diff():
    """Test parsing diff with multiple files."""
    diff_content = """diff --git a/file1.py b/file1.py
index abc123..def456 100644
--- a/file1.py
+++ b/file1.py
@@ -1,3 +1,4 @@
 def func1():
+    print("added")
     pass


diff --git a/file2.py b/file2.py
index xyz789..uvw012 100644
--- a/file2.py
+++ b/file2.py
@@ -10,2 +10,3 @@ class Test:
     def method(self):
+        print("method change")
         return True"""

    diff_files = DiffParser.parse_diff(diff_content)

    assert len(diff_files) == 2
    assert "file1.py" in diff_files
    assert "file2.py" in diff_files

    # Check file1
    file1 = diff_files["file1.py"]
    assert len(file1.hunks) == 1
    assert file1.hunks[0].new_start == 1

    # Check file2
    file2 = diff_files["file2.py"]
    assert len(file2.hunks) == 1
    assert file2.hunks[0].new_start == 10


def test_line_number_context_generation():
    """Test generation of line number context for AI."""
    diff_content = """diff --git a/test.py b/test.py
index abc123..def456 100644
--- a/test.py
+++ b/test.py
@@ -10,5 +10,7 @@ def main():
     print("hello")
+    print("new line")
     if True:
         pass
     return 0
@@ -50,3 +52,4 @@ def other():
     x = 1
+    y = 2
     return x"""

    diff_files = DiffParser.parse_diff(diff_content)
    context = DiffParser.generate_line_number_context(diff_files)

    assert "test.py:" in context
    assert "Lines 10-16" in context  # First hunk: start=10, count=7
    assert "Lines 52-55" in context  # Second hunk: start=52, count=4
    assert "REMINDER" in context
    assert "GitHub links" in context


def test_hunk_line_finding():
    """Test finding specific content in diff hunks."""
    hunk = DiffHunk(
        old_start=10,
        old_count=3,
        new_start=10,
        new_count=4,
        lines=[" existing_line", "+new_function_call()", " another_existing", "+print('debug')"],
    )

    # Should find line numbers where content appears in additions
    matches = hunk.contains_line_change("function_call")
    assert len(matches) == 1
    assert matches[0] == 11  # Second line (new_start=10, so +1)

    matches = hunk.contains_line_change("debug")
    assert len(matches) == 1
    assert matches[0] == 13  # Fourth line


def test_file_diff_changed_ranges():
    """Test getting changed line ranges from file diff."""
    hunks = [
        DiffHunk(old_start=10, old_count=3, new_start=10, new_count=5, lines=[]),
        DiffHunk(old_start=50, old_count=2, new_start=52, new_count=3, lines=[]),
    ]

    file_diff = FileDiff("test.py", hunks)
    ranges = file_diff.get_changed_line_ranges()

    assert len(ranges) == 2
    assert ranges[0] == (10, 14)  # start=10, count=5, so end=14
    assert ranges[1] == (52, 54)  # start=52, count=3, so end=54


def test_empty_diff():
    """Test handling of empty or malformed diff."""
    diff_files = DiffParser.parse_diff("")
    assert len(diff_files) == 0

    diff_files = DiffParser.parse_diff("not a valid diff")
    assert len(diff_files) == 0
