"""Entry point of the realistic fixture repo.
Demonstrates simple usage of utils and AuthService."""

from services.auth import AuthService
from utils import greet


def main() -> None:
    """Run a demo workflow."""
    name = "Alice"
    print(greet(name))

    auth = AuthService()
    token = auth.login(username=name, password="secret")
    print(f"Logged in with token: {token}")

    assert auth.is_valid(token)

    auth.logout(token)
    assert not auth.is_valid(token)
    print("Logged out.")


if __name__ == "__main__":
    main()
