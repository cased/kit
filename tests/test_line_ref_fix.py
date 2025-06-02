import pytest

from kit.pr_review.line_ref_fixer import LineRefFixer

SIMPLE_DIFF = """diff --git a/foo.py b/foo.py
@@ -10,3 +10,4 @@ def func():
     a = 1
-    b = 2
+    b = 3
+    c = 4
"""

BAD_COMMENT = (
    "Issue at foo.py:10 is wrong. Another range foo.py:10-11 is wrong too."
)


def test_line_ref_fix_simple():
    fixed, fixes = LineRefFixer.fix_comment(BAD_COMMENT, SIMPLE_DIFF)

    # The valid added lines are 11 and 12 (b=3 is 11, c=4 is 12)
    assert "foo.py:11" in fixed
    # 12 not referenced after auto-fix, so ensure 10 replaced
    # original 10 should be gone
    assert "foo.py:10" not in fixed
    # at least one fix recorded
    assert fixes 