"""Shared priority filtering utilities for PR review."""

from enum import Enum
from typing import List, Optional


class Priority(Enum):
    """Valid priority levels for PR review filtering.

    Examples:
        Basic validation:
        >>> Priority.validate_priorities(['high', 'medium'])
        ['high', 'medium']

        Case insensitive validation:
        >>> Priority.validate_priorities(['HIGH', 'Medium', 'low'])
        ['high', 'medium', 'low']

        Error on invalid priority:
        >>> Priority.validate_priorities(['critical'])  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ValueError: Invalid priority levels: ['critical']. Valid levels: ['high', 'medium', 'low']
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def validate_priorities(cls, priorities: List[str]) -> List[str]:
        """Validate and normalize priority levels.

        Args:
            priorities: List of priority level strings

        Returns:
            List of normalized priority levels

        Raises:
            ValueError: If any priority level is invalid
        """
        if not priorities:
            return []

        normalized = [p.lower().strip() for p in priorities]
        valid_priorities = {p.value for p in cls}
        invalid = [p for p in normalized if p not in valid_priorities]

        if invalid:
            raise ValueError(f"Invalid priority levels: {invalid}. Valid levels: {list(valid_priorities)}")

        return normalized


def build_priority_instructions(priority_filter: Optional[List[str]]) -> str:
    """Build simple priority instructions exactly like the original main branch."""
    return """## Priority Issues
- [High/Medium/Low priority] findings with [file.py:123](https://github.com/{owner}/{repo_name}/blob/{pr_details["head"]["sha"]}/file.py#L123) links"""


def get_recommendations_focus(priority_filter: Optional[List[str]]) -> str:
    """Get simple recommendations focus like the original main branch."""
    return "Security, performance, or logic issues with specific fixes; missing error handling or edge cases; cross-codebase impact concerns"
