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
