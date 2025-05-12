"""Auth service that issues and validates in-memory tokens, and manages users."""

import uuid
from typing import Dict, Optional

from ..models.user import User


class AuthService:
    """Manages user registration, login, and session tokens (in-memory demo)."""

    def __init__(self):
        self._users_by_username: Dict[str, User] = {}
        self._users_by_id: Dict[int, User] = {}
        self._active_tokens: Dict[str, int] = {}  # token_string -> user_id
        self._next_user_id: int = 1

    def register_user(self, username: str, email: str, password: str) -> Optional[User]:
        """Registers a new user.

        Args:
            username: The desired username.
            email: The user's email address.
            password: The user's password (ignored for this demo).

        Returns:
            The created User object, or None if username is taken.
        """
        if username in self._users_by_username:
            return None  # Username already taken

        # In a real app, hash the password!
        user_id = self._next_user_id
        new_user = User(id=user_id, name=username, email=email)
        self._next_user_id += 1

        self._users_by_username[username] = new_user
        self._users_by_id[user_id] = new_user
        return new_user

    def login(self, *, username: str, password: str) -> Optional[str]:
        """Logs in a user and returns a session token.

        Args:
            username: The username.
            password: The password.

        Returns:
            A session token string if login is successful, None otherwise.
        """
        user = self._users_by_username.get(username)
        # Demo: check if user exists and password is 'password' (DO NOT use in real life!)
        if user and user.is_active and password == "password":
            token = str(uuid.uuid4())
            self._active_tokens[token] = user.id
            user.record_login()  # Update last_login_at on the User model
            return token
        return None

    def logout(self, token: str) -> None:
        """Logs out a user by invalidating their token."""
        if token in self._active_tokens:
            del self._active_tokens[token]

    def is_valid_token(self, token: str) -> bool:
        """Checks if a token is currently valid."""
        return token in self._active_tokens

    def get_user_from_token(self, token: str) -> Optional[User]:
        """Retrieves the User object associated with a valid token.

        Args:
            token: The session token.

        Returns:
            The User object if the token is valid, None otherwise.
        """
        user_id = self._active_tokens.get(token)
        if user_id:
            return self._users_by_id.get(user_id)
        return None
