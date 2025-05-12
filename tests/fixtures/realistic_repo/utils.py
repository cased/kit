"""Utility helpers for the fixture repo."""

import datetime
import re


def greet(name: str) -> str:
    """Return a friendly greeting."""
    return f"Hello, {name}!"


def format_timestamp(ts: float, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Formats a Unix timestamp into a human-readable string.

    Args:
        ts: The Unix timestamp (float).
        format_string: The strftime format string.

    Returns:
        A string representing the formatted timestamp.
    """
    dt_object = datetime.datetime.fromtimestamp(ts)
    return dt_object.strftime(format_string)


def is_valid_email(email: str) -> bool:
    """Checks if the provided string is a valid email address (basic check).

    Args:
        email: The email string to validate.

    Returns:
        True if the email format is valid, False otherwise.
    """
    # A simple regex for email validation
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, email):
        return True
    return False
