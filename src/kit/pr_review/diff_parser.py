"""Diff parsing utilities for accurate line number mapping."""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class DiffHunk:
    """Represents a single diff hunk with line mappings."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str]

    def get_new_line_number(self, diff_line_offset: int) -> Optional[int]:
        """Get the absolute line number in the new file for a given offset within this hunk."""
        if diff_line_offset < 0 or diff_line_offset >= len(self.lines):
            return None

        # If the line at this offset is a deletion, it doesn't exist in the new file
        target_line = self.lines[diff_line_offset]
        if target_line.startswith("-"):
            return None

        # Count how many non-deletion lines come before this offset
        lines_before = 0
        for i in range(diff_line_offset):
            if not self.lines[i].startswith("-"):
                lines_before += 1

        return self.new_start + lines_before

    def contains_line_change(self, content: str) -> List[int]:
        """Find line numbers where the given content appears in changes."""
        matches = []
        current_new_line = self.new_start

        for line in self.lines:
            if line.startswith("+") and content.lower() in line.lower():
                matches.append(current_new_line)

            if not line.startswith("-"):  # Count context and added lines
                current_new_line += 1

        return matches


@dataclass
class FileDiff:
    """Represents diff information for a single file."""

    filename: str
    hunks: List[DiffHunk]

    def find_line_for_content(self, content: str) -> List[int]:
        """Find line numbers where content appears in the diff."""
        all_matches = []
        for hunk in self.hunks:
            all_matches.extend(hunk.contains_line_change(content))
        return all_matches

    def get_changed_line_ranges(self) -> List[Tuple[int, int]]:
        """Get ranges of lines that were modified in this file."""
        ranges = []
        for hunk in self.hunks:
            start = hunk.new_start
            end = hunk.new_start + hunk.new_count - 1
            ranges.append((start, end))
        return ranges


class DiffParser:
    """Parser for git diff output to extract accurate line number mappings."""

    @staticmethod
    def parse_diff(diff_content: str) -> Dict[str, FileDiff]:
        """
        Parse a git diff and return file diff information.

        Args:
            diff_content: Raw git diff output

        Returns:
            Dict mapping filename to FileDiff objects
        """
        files: Dict[str, FileDiff] = {}
        current_file = None
        current_hunks: List[DiffHunk] = []
        current_hunk_lines: List[str] = []
        current_hunk_header = None

        def save_current_hunk():
            """Helper to save the current hunk if it exists."""
            if current_hunk_header and current_hunk_lines:
                hunk = DiffParser._parse_hunk_header(current_hunk_header)
                if hunk:
                    hunk.lines = current_hunk_lines.copy()
                    current_hunks.append(hunk)

        def save_current_file():
            """Helper to save the current file if it has hunks."""
            if current_file and current_hunks:
                files[current_file] = FileDiff(current_file, current_hunks)

        for line in diff_content.split("\n"):
            # File header
            if line.startswith("diff --git"):
                # Save previous hunk and file
                save_current_hunk()
                save_current_file()

                # Extract filename
                match = re.search(r"diff --git a/(.+?) b/(.+)", line)
                if match:
                    current_file = match.group(2)  # Use the "b/" version (new file)
                current_hunks = []
                current_hunk_lines = []
                current_hunk_header = None

            # Hunk header: @@ -old_start,old_count +new_start,new_count @@
            elif line.startswith("@@"):
                # Save previous hunk if exists
                save_current_hunk()

                current_hunk_header = line
                current_hunk_lines = []

            # Hunk content
            elif current_hunk_header is not None and (
                line.startswith(" ") or line.startswith("+") or line.startswith("-")
            ):
                current_hunk_lines.append(line)

            # Empty line or other content - might end a hunk
            elif current_hunk_header is not None and line.strip() == "":
                # Only add empty line if we're still in hunk content (not between files)
                current_hunk_lines.append(line)

            # Skip other lines (index, ---, +++, etc.)

        # Save final hunk and file
        save_current_hunk()
        save_current_file()

        return files

    @staticmethod
    def _parse_hunk_header(header: str) -> Optional[DiffHunk]:
        """Parse a hunk header line like '@@ -10,5 +12,7 @@'."""
        match = re.search(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", header)
        if not match:
            return None

        old_start = int(match.group(1))
        old_count = int(match.group(2)) if match.group(2) else 1
        new_start = int(match.group(3))
        new_count = int(match.group(4)) if match.group(4) else 1

        return DiffHunk(old_start=old_start, old_count=old_count, new_start=new_start, new_count=new_count, lines=[])

    @staticmethod
    def generate_line_number_context(
        diff_files: Dict[str, FileDiff],
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        sha: Optional[str] = None,
    ) -> str:
        """Generate context about line number ranges for AI consumption."""
        context = "**Accurate Line Number Reference:**\n"

        for filename, file_diff in diff_files.items():
            context += f"\n{filename}:\n"
            for i, hunk in enumerate(file_diff.hunks):
                # Calculate actual changed lines, not just the hunk range
                added_lines = []
                current_line = hunk.new_start

                for line in hunk.lines:
                    if line.startswith("+"):
                        added_lines.append(current_line)
                    elif line.startswith(" "):
                        # Context line - increment but don't mark as changed
                        pass
                    # Deletions don't increment current_line

                    if not line.startswith("-"):
                        current_line += 1

                # Show both the hunk range and specific changed lines
                hunk_range = f"{hunk.new_start}-{hunk.new_start + hunk.new_count - 1}"
                context += f"  Hunk {i + 1}: Lines {hunk_range}"

                if added_lines:
                    if len(added_lines) == 1:
                        context += f" (actual change: line {added_lines[0]})"
                    else:
                        context += f" (actual changes: lines {', '.join(map(str, added_lines))})"
                else:
                    context += " (deletions only)"

                context += "\n"

        context += (
            "\n**IMPORTANT**: Reference the *exact* lines shown below—not the hunk header.\n"
            "**REMINDER**: The red '-' lines are deletions and no longer exist. Only reference the green '+' lines (actual additions) when citing line numbers.\n"
        )

        # Generate proper GitHub links if we have repository information
        if owner and repo and sha:
            context += f"**GitHub links**: reference lines with the format `[file.py:123](https://github.com/{owner}/{repo}/blob/{sha}/file.py#L123)`\n"
        else:
            context += "**GitHub links**: reference lines with clickable file:line format when possible\n"

        return context
