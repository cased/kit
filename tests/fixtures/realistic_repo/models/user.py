"""User dataclass for the realistic fixture repo."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..utils import is_valid_email


@dataclass
class User:
    id: int
    name: str
    email: str
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    last_login_at: Optional[float] = None
    preferences: Dict[str, Any] = field(default_factory=dict)

    def display(self) -> str:
        """Return a human readable representation."""
        status = "active" if self.is_active else "inactive"
        return f"<{self.id}> {self.name} <{self.email}> ({status})"

    def update_email(self, new_email: str) -> bool:
        """Updates the user's email address after validating it.

        Args:
            new_email: The new email address.

        Returns:
            True if the email was updated, False otherwise.
        """
        if is_valid_email(new_email):
            self.email = new_email
            return True
        return False

    def deactivate(self) -> None:
        """Deactivates the user's account."""
        self.is_active = False
        print(f"User {self.name} deactivated.")

    def record_login(self) -> None:
        """Updates the last_login_at timestamp to the current time."""
        self.last_login_at = time.time()

    def set_preference(self, key: str, value: Any) -> None:
        """Sets a user preference.

        Args:
            key: The preference key.
            value: The preference value.
        """
        self.preferences[key] = value

    def get_preference(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Gets a user preference.

        Args:
            key: The preference key.
            default: The default value to return if the key is not found.

        Returns:
            The preference value or the default.
        """
        return self.preferences.get(key, default)
