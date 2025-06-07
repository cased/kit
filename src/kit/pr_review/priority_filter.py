"""Priority filtering for PR review output."""

import re
from typing import List, Optional

from .priority_utils import Priority

# Pre-compiled regex patterns for better performance
PRIORITY_SECTION_PATTERNS = [
    re.compile(r"^#{1,4}\s*priority\s*issues?", re.IGNORECASE),
    re.compile(r"^#{1,4}\s*issues?\s*by\s*priority", re.IGNORECASE),
]

MAJOR_SECTION_PATTERN = re.compile(r"^#{1,3}\s+[A-Z]")

PRIORITY_HEADER_PATTERNS = [
    re.compile(r"^#{3,4}\s+(High|Medium|Low)\s*Priority", re.IGNORECASE),
    re.compile(r"^#{3,4}\s+(High|Medium|Low)\s*:", re.IGNORECASE),
    re.compile(r"^\*\*\s*(High|Medium|Low)\s*Priority", re.IGNORECASE),
    re.compile(r"^\*\*(High|Medium|Low)\*\*", re.IGNORECASE),
    re.compile(r"^(High|Medium|Low)\s*Priority\s*[:\-]?\s*$", re.IGNORECASE),
]

# Constants for meaningful content detection and performance limits
# MIN_MEANINGFUL_LENGTH: Minimum character threshold for considering a line as meaningful content.
# Set to 10 based on analysis of typical code review comments - this length filters out:
# - Very short words ("ok", "fix", "todo") that aren't substantial feedback
# - Punctuation-only lines ("...", "---")
# - Single identifiers ("user", "config") without context
# While preserving meaningful content like "Add error handling" (18 chars)
MIN_MEANINGFUL_LENGTH = 10

# MAX_LINES: Maximum number of lines to process to prevent excessive memory usage
# Set to 50,000 lines - allows very large PRs while preventing abuse
MAX_LINES = 50_000


def filter_review_by_priority(
    review_text: str, allowed_priorities: Optional[List[str]], max_review_size_mb: float = 5.0
) -> str:
    """
    Filter review text to only show specified priority levels.

    Args:
        review_text: The full review text from the LLM
        allowed_priorities: List of allowed priority levels (e.g., ["high", "medium"])
                           If None or empty, returns original text
        max_review_size_mb: Maximum allowed review text size in MB (default: 5.0)

    Returns:
        Filtered review text with only the specified priority levels

    Raises:
        ValueError: If any priority level is invalid or text is too large
        TypeError: If review_text is not a string type
    """
    # Strict input validation to prevent security issues
    if review_text is None:
        return ""

    if not isinstance(review_text, str):
        raise TypeError(f"review_text must be a string, got {type(review_text).__name__}")

    if not review_text.strip():
        return review_text

    # Validate max_review_size_mb parameter
    if not isinstance(max_review_size_mb, (int, float)) or max_review_size_mb <= 0:
        raise ValueError(f"max_review_size_mb must be a positive number, got {max_review_size_mb}")

    if max_review_size_mb > 1000:  # Reasonable upper limit of 1GB
        raise ValueError(f"max_review_size_mb too large ({max_review_size_mb}MB), maximum allowed: 1000MB")

    # Performance safeguards to prevent timeouts and excessive memory usage
    max_size_bytes = int(max_review_size_mb * 1024 * 1024)  # Convert MB to bytes

    # Efficient UTF-8 byte size check with early optimization for ASCII-heavy text
    # For most ASCII text, character count ≈ byte count, so we can optimize common cases
    char_count = len(review_text)
    if char_count <= max_size_bytes * 0.25:  # Conservative safety margin for worst-case Unicode (4x expansion)
        # Skip expensive encoding for clearly safe cases (75% safety margin for 4-byte UTF-8 chars)
        pass
    else:
        # For larger texts or texts that might have Unicode, do accurate byte counting
        text_bytes = len(review_text.encode("utf-8"))  # Count actual bytes for accuracy
        if text_bytes > max_size_bytes:
            raise ValueError(
                f"Review text too large ({text_bytes:,} bytes). Maximum allowed: {max_size_bytes:,} bytes ({max_review_size_mb}MB)"
            )

    line_count = review_text.count("\n") + 1
    if line_count > MAX_LINES:
        raise ValueError(f"Review text has too many lines ({line_count:,}). Maximum allowed: {MAX_LINES:,} lines")

    if not allowed_priorities:
        return review_text

    # Validate and normalize priority levels using centralized validation
    normalized_priorities = Priority.validate_priorities(allowed_priorities)

    # Parse the review and extract priority sections
    filtered_content = _filter_priority_content(review_text, normalized_priorities)

    # Add priority filter note
    if set(normalized_priorities) != {Priority.HIGH.value, Priority.MEDIUM.value, Priority.LOW.value}:
        priority_note = f"*Note: Showing only {', '.join(normalized_priorities)} priority issues*\n\n"
        # Insert after the main title but before content
        lines = filtered_content.split("\n")
        title_line = 0
        for i, line in enumerate(lines):
            if line.startswith("#"):
                title_line = i
                break
        lines.insert(title_line + 1, priority_note)
        filtered_content = "\n".join(lines)

    return filtered_content


def _filter_priority_content(review_text: str, allowed_priorities: List[str]) -> str:
    """Filter the review content to only include allowed priority sections using optimized single-pass parsing."""
    lines = review_text.split("\n")
    filtered_lines = []

    # State tracking for single-pass processing
    in_priority_section = False
    was_ever_in_priority_section = False
    current_priority = None
    skip_current_section = False
    allowed_set = set(allowed_priorities)  # O(1) lookup

    for line in lines:
        # More flexible matching for Priority Issues section
        if _is_priority_section_header(line):
            in_priority_section = True
            was_ever_in_priority_section = True
            filtered_lines.append(line)
            continue

        # Check if we're leaving the Priority Issues section (any other major section)
        elif in_priority_section and _is_major_section_header(line):
            in_priority_section = False
            current_priority = None
            skip_current_section = False
            # Apply intelligent filtering to Summary and Recommendations sections
            if _is_summary_or_recommendations_section(line):
                filtered_lines.append(line)
                # We'll filter the content of these sections
                continue
            else:
                filtered_lines.append(line)
                continue

        # If we're in the priority section, handle subsections
        elif in_priority_section:
            # Check for priority subsection headers - more flexible matching
            priority_level = _extract_priority_level(line)
            if priority_level:
                current_priority = priority_level.lower()
                skip_current_section = current_priority not in allowed_set
                if not skip_current_section:
                    filtered_lines.append(line)
                continue

            # Handle content under priority subsections
            if not skip_current_section:
                filtered_lines.append(line)
            continue

        # For all other lines (outside priority section), filter intelligently
        else:
            # Apply intelligent filtering to Summary and Recommendations
            if _should_filter_line_content(line, allowed_set):
                continue  # Skip this line
            filtered_lines.append(line)

    # Check if we need to add a "no issues found" note
    if was_ever_in_priority_section and not _has_priority_content_optimized(filtered_lines, allowed_set):
        # Find the Priority Issues section and add a note
        for i, line in enumerate(filtered_lines):
            if _is_priority_section_header(line):
                # Look for the end of the Priority Issues section or end of content
                insert_pos = len(filtered_lines)
                for j in range(i + 1, len(filtered_lines)):
                    if _is_major_section_header(filtered_lines[j]):
                        insert_pos = j
                        break

                # Insert the message before the next major section
                filtered_lines.insert(insert_pos, "")
                filtered_lines.insert(insert_pos + 1, f"*No {', '.join(allowed_priorities)} priority issues found.*")
                break

    return "\n".join(filtered_lines)


def _is_priority_section_header(line: str) -> bool:
    """Check if line is a Priority Issues section header with flexible matching."""
    line_clean = line.strip()
    # Use pre-compiled patterns for better performance
    return any(pattern.match(line_clean) for pattern in PRIORITY_SECTION_PATTERNS)


def _is_major_section_header(line: str) -> bool:
    """Check if line is a major section header (not priority subsection)."""
    line_clean = line.strip()
    # Use pre-compiled pattern and check it's not a priority level
    return bool(MAJOR_SECTION_PATTERN.match(line_clean) and not _extract_priority_level(line_clean))


def _extract_priority_level(line: str) -> Optional[str]:
    """Extract priority level from a line if it's a priority subsection header."""
    line_clean = line.strip()
    # Use pre-compiled patterns for better performance
    for pattern in PRIORITY_HEADER_PATTERNS:
        match = pattern.match(line_clean)
        if match:
            return match.group(1)
    return None


def _has_priority_content_optimized(lines: List[str], allowed_set: set) -> bool:
    """Optimized check for priority content using set lookup."""
    in_priority_section = False
    current_priority = None
    found_content = False

    for line in lines:
        if _is_priority_section_header(line):
            in_priority_section = True
            continue
        elif in_priority_section and _is_major_section_header(line):
            break
        elif in_priority_section:
            # Check for priority subsection headers
            priority_level = _extract_priority_level(line)
            if priority_level:
                current_priority = priority_level.lower()
                continue
            # Check for actual content (list items, meaningful text)
            elif current_priority and current_priority in allowed_set and _is_meaningful_content(line):
                found_content = True

    # If we're in a priority section but found no priority subsections at all,
    # or if we found subsections but no meaningful content in allowed priorities, return False
    return found_content


def _is_meaningful_content(line: str) -> bool:
    """Check if a line contains meaningful content (not just whitespace or empty)."""
    line_clean = line.strip()
    # Check for list items, meaningful text, code blocks, etc.
    return bool(
        line_clean
        and (
            line_clean.startswith("-")  # List items
            or line_clean.startswith("*")  # Bullet points
            or line_clean.startswith("1.")  # Numbered lists
            or (len(line_clean) > MIN_MEANINGFUL_LENGTH and not line_clean.startswith("#"))
        )  # Meaningful sentences
    )


def _is_summary_or_recommendations_section(line: str) -> bool:
    """Check if line is a Summary or Recommendations section header."""
    line_clean = line.strip().lower()
    return any(
        section in line_clean for section in ["## summary", "## recommendations", "### summary", "### recommendations"]
    )


def _should_filter_line_content(line: str, allowed_priorities: set) -> bool:
    """Determine if a line should be filtered out based on priority references."""
    line_lower = line.strip().lower()

    # Skip empty lines and non-content lines
    if not line_lower or line_lower.startswith("#"):
        return False

    # Only filter lines that explicitly mention specific priority levels
    for priority in ["high", "medium", "low"]:
        if priority not in allowed_priorities:
            # Look for explicit priority mentions, not just related words
            priority_patterns = [
                f"{priority} priority",
                f"**{priority}**:",
                f"- **{priority}**:",
                "**immediate**:" if priority == "high" else None,
                "**before merge**:" if priority == "medium" else None,
                "**follow-up**:" if priority == "low" else None,
            ]

            # Filter None values and check for matches
            patterns = [p for p in priority_patterns if p is not None]
            if any(pattern in line_lower for pattern in patterns):
                return True

    return False


def count_filtered_issues(review_text: str, priority_filter: Optional[List[str]]) -> dict:
    """
    Count how many issues were filtered out for transparency.

    Returns:
        Dict with counts like {"shown": 5, "filtered": 10, "total": 15}
    """
    if not priority_filter:
        return {"shown": "all", "filtered": 0, "total": "all"}

    shown_count = 0
    total_count = 0

    lines = review_text.split("\n")
    in_priority_section = False
    current_priority = None

    for line in lines:
        # Track if we're in Priority Issues section
        if _is_priority_section_header(line):
            in_priority_section = True
            continue
        elif in_priority_section and _is_major_section_header(line):
            break
        elif in_priority_section:
            # Check for priority subsection headers
            priority_level = _extract_priority_level(line)
            if priority_level:
                current_priority = priority_level.lower()
                continue

            # Count meaningful content items under priority sections
            if current_priority and _is_meaningful_content(line):
                total_count += 1
                if current_priority in [p.lower() for p in priority_filter]:
                    shown_count += 1

    filtered_count = total_count - shown_count

    return {"shown": shown_count, "filtered": filtered_count, "total": total_count}
