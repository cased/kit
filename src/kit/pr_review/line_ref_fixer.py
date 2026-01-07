from __future__ import annotations

import bisect
import re
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

from .diff_parser import DiffParser

if TYPE_CHECKING:
    from .diff_parser import FileDiff


class LineRefFixer:
    """Utility to validate and auto-fix file:line references in an AI review comment."""

    # Match file references like path/to/file.ext:123 or file.ext:10-20
    # Extension 1–10 alphanum chars to avoid over-matching URLs.
    REF_PATTERN = re.compile(r"([\w./+-]+\.[a-zA-Z0-9]{1,10}):(\d+)(?:-(\d+))?")

    @classmethod
    def _build_valid_line_map(
        cls,
        diff_text_or_parsed: Union[str, Dict[str, "FileDiff"]],
    ) -> Dict[str, set[int]]:
        """Build map of valid line numbers from diff.

        Args:
            diff_text_or_parsed: Either raw diff text (str) or pre-parsed diff dict.
                Passing pre-parsed diff avoids redundant parsing when caller
                has already parsed the diff.
        """
        if isinstance(diff_text_or_parsed, str):
            diff_files = DiffParser.parse_diff(diff_text_or_parsed)
        else:
            diff_files = diff_text_or_parsed

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
    def fix_comment(
        cls,
        comment: str,
        diff_text: str,
        parsed_diff: Optional[Dict[str, "FileDiff"]] = None,
    ) -> Tuple[str, List[Tuple[str, int, int]]]:
        """Return (fixed_comment, fixes).

        Args:
            comment: The review comment text to fix.
            diff_text: Raw diff text (used if parsed_diff not provided).
            parsed_diff: Pre-parsed diff dict. If provided, avoids re-parsing
                the diff which saves ~0.1ms per call.

        Returns:
            Tuple of (fixed_comment, fixes) where fixes is a list of
            (filename, old_line, new_line) tuples.
        """
        valid_map = cls._build_valid_line_map(parsed_diff if parsed_diff else diff_text)
        # Convert sets to sorted lists once for O(log n) lookups
        sorted_lines_cache: Dict[str, List[int]] = {}
        fixes: List[Tuple[str, int, int]] = []

        def _nearest(file: str, line: int) -> int:
            # Get or build sorted list for this file
            if file not in sorted_lines_cache:
                lines = valid_map.get(file, set())
                sorted_lines_cache[file] = sorted(lines) if lines else []

            sorted_lines = sorted_lines_cache[file]
            if not sorted_lines:
                return line

            # Binary search for nearest line - O(log n) instead of O(n)
            idx = bisect.bisect_left(sorted_lines, line)

            # Check candidates: idx and idx-1
            if idx == 0:
                return sorted_lines[0]
            if idx == len(sorted_lines):
                return sorted_lines[-1]

            # Compare distances to neighbors
            before = sorted_lines[idx - 1]
            after = sorted_lines[idx]
            return before if (line - before) <= (after - line) else after

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
