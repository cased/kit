from kit.pr_review.line_ref_fixer import LineRefFixer

SIMPLE_DIFF = """diff --git a/foo.py b/foo.py
@@ -10,3 +10,4 @@ def func():
     a = 1
-    b = 2
+    b = 3
+    c = 4
"""

BAD_COMMENT = "Issue at foo.py:10 is wrong. Another range foo.py:10-11 is wrong too."


def test_line_ref_fix_simple():
    fixed, fixes = LineRefFixer.fix_comment(BAD_COMMENT, SIMPLE_DIFF)

    # Both referenced lines 10 and 10-11 are now legal; fixer should make no changes
    assert fixed == BAD_COMMENT
    assert fixes == []


# --- Edge case tests for binary search nearest-line algorithm ---

MULTI_HUNK_DIFF = """diff --git a/bar.py b/bar.py
@@ -10,4 +10,4 @@ def first():
     a = 1
     b = 2
+    c = 3
     d = 4
@@ -50,3 +51,4 @@ def second():
     x = 1
+    y = 2
+    z = 3
"""


def test_line_ref_fix_snaps_to_nearest_below():
    """When target is between valid lines, snap to nearest (prefer lower on tie)."""
    # Valid lines in bar.py: 10, 11, 12, 13, 51, 52, 53
    comment = "See bar.py:25"  # 25 is between 13 and 51; closer to 13
    fixed, fixes = LineRefFixer.fix_comment(comment, MULTI_HUNK_DIFF)
    assert fixed == "See bar.py:13"
    assert len(fixes) == 1
    assert fixes[0] == ("bar.py", 25, 13)


def test_line_ref_fix_snaps_to_nearest_above():
    """When target is closer to line above, snap there."""
    # Valid lines: 10, 11, 12, 13, 51, 52, 53
    comment = "See bar.py:48"  # 48 is closer to 51 than to 13
    fixed, fixes = LineRefFixer.fix_comment(comment, MULTI_HUNK_DIFF)
    assert fixed == "See bar.py:51"
    assert fixes[0] == ("bar.py", 48, 51)


def test_line_ref_fix_before_all_valid_lines():
    """When target is before all valid lines, snap to first."""
    comment = "See bar.py:1"  # 1 is before 10 (first valid)
    fixed, fixes = LineRefFixer.fix_comment(comment, MULTI_HUNK_DIFF)
    assert fixed == "See bar.py:10"
    assert fixes[0] == ("bar.py", 1, 10)


def test_line_ref_fix_after_all_valid_lines():
    """When target is after all valid lines, snap to last."""
    # Valid lines: 10, 11, 12, 13, 51, 52, 53, 54
    comment = "See bar.py:999"  # 999 is after 54 (last valid)
    fixed, fixes = LineRefFixer.fix_comment(comment, MULTI_HUNK_DIFF)
    assert fixed == "See bar.py:54"
    assert fixes[0] == ("bar.py", 999, 54)


def test_line_ref_fix_exact_match():
    """When target exactly matches a valid line, no change needed."""
    comment = "See bar.py:52"
    fixed, fixes = LineRefFixer.fix_comment(comment, MULTI_HUNK_DIFF)
    assert fixed == "See bar.py:52"
    assert fixes == []


def test_line_ref_fix_equidistant_prefers_lower():
    """When equidistant between two lines, prefer the lower one."""
    # Valid lines include 12 and 13
    # If we reference 12.5 (not possible), but 32 is equidistant from 13 and 51
    # (32 - 13 = 19, 51 - 32 = 19)
    comment = "See bar.py:32"
    fixed, fixes = LineRefFixer.fix_comment(comment, MULTI_HUNK_DIFF)
    # Should prefer 13 (lower) when equidistant
    assert fixed == "See bar.py:13"


def test_line_ref_fix_range_both_endpoints():
    """Range endpoints are fixed independently."""
    # Valid lines: 10, 11, 12, 13, 51, 52, 53, 54
    comment = "See bar.py:1-999"
    fixed, fixes = LineRefFixer.fix_comment(comment, MULTI_HUNK_DIFF)
    assert fixed == "See bar.py:10-54"
    assert len(fixes) == 2


def test_line_ref_fix_unknown_file():
    """References to files not in diff are unchanged."""
    comment = "See unknown.py:42"
    fixed, fixes = LineRefFixer.fix_comment(comment, MULTI_HUNK_DIFF)
    assert fixed == "See unknown.py:42"
    assert fixes == []
