from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .diff_parser import DiffParser


class LineRefFixer:
    """Utility to validate and auto-fix file:line references in an AI review comment."""

    # Match file references like path/to/file.ext:123 or file.ext:10-20
    # Extension 1–10 alphanum chars to avoid over-matching URLs.
    REF_PATTERN = re.compile(r"([\w./+-]+\.[a-zA-Z0-9]{1,10}):(\d+)(?:-(\d+))?")

    @classmethod
    def _build_valid_line_map(cls, diff_text: str) -> Dict[str, set[int]]:
        diff_files = DiffParser.parse_diff(diff_text)
        valid: Dict[str, set[int]] = {}
        for filename, fd in diff_files.items():
            line_set: set[int] = set()
            for hunk in fd.hunks:
                cur = hunk.new_start
                for raw in hunk.lines:
                    # Any line that exists in the *new* file (context or addition) is legal.
                    if not raw.startswith("-"):
                        line_set.add(cur)
                        cur += 1
            valid[filename] = line_set
        return valid

    @classmethod
    def fix_comment(cls, comment: str, diff_text: str) -> Tuple[str, List[Tuple[str, int, int]]]:
        """Return (fixed_comment, fixes).

        fixes list items are (filename, old_line, new_line).
        """
        valid_map = cls._build_valid_line_map(diff_text)
        fixes: List[Tuple[str, int, int]] = []

        def _nearest(file: str, line: int) -> int:
            lines = valid_map.get(file, set())
            return min(lines, key=lambda n: abs(n - line)) if lines else line

        def _replacer(match: re.Match[str]) -> str:
            file, start_s, end_s = match.groups()
            start = int(start_s)
            if end_s:
                end = int(end_s)
                new_start = _nearest(file, start)
                new_end = _nearest(file, end)
                if (new_start, new_end) != (start, end):
                    fixes.append((file, start, new_start))
                    fixes.append((file, end, new_end))
                return f"{file}:{new_start}-{new_end}"
            else:
                new_line = _nearest(file, start)
                if new_line != start:
                    fixes.append((file, start, new_line))
                return f"{file}:{new_line}"

        fixed_comment = cls.REF_PATTERN.sub(_replacer, comment)
        return fixed_comment, fixes
