"""Auth service that issues and validates in-memory tokens."""

import uuid

class AuthService:
    """Very small auth demo."""

    def __init__(self):
        self._tokens: set[str] = set()

    def login(self, *, username: str, password: str) -> str:
        # DO NOT use in real life! Just demo.
        token = str(uuid.uuid4())
        self._tokens.add(token)
        return token

    def logout(self, token: str) -> None:
        self._tokens.discard(token)

    def is_valid(self, token: str) -> bool:
        return token in self._tokens
