"""Entry point of the realistic fixture repo.
Demonstrates expanded usage of AuthService, User model, and utils."""

from services.auth import AuthService
from utils import greet


def main() -> None:
    """Run an expanded demo workflow showcasing more features."""
    print("Kit Realistic Repo Demo\n" + "=" * 30)

    auth_service = AuthService()

    # 1. Register users
    print("\n--- Registering Users ---")
    user_alice_details = {"username": "alice", "email": "alice@example.com", "password": "password"}
    user_bob_details = {"username": "bob", "email": "bob@example.com", "password": "password"}

    alice = auth_service.register_user(**user_alice_details)
    if alice:
        print(f"Registered: {alice.display()}")
    else:
        print(f"Failed to register {user_alice_details['username']}")

    bob = auth_service.register_user(**user_bob_details)
    if bob:
        print(f"Registered: {bob.display()}")
    else:
        print(f"Failed to register {user_bob_details['username']}")

    # Attempt to register Alice again (should fail)
    print("\n--- Attempting to re-register Alice ---")
    alice_again = auth_service.register_user(**user_alice_details)
    if not alice_again:
        print(f"Successfully prevented re-registration of {user_alice_details['username']}.")
    else:
        print(f"ERROR: Re-registration of {user_alice_details['username']} was allowed.")

    # 2. Login Alice
    print("\n--- Logging in Alice ---")
    alice_token = auth_service.login(username="alice", password="password")
    if alice_token:
        print(f"Alice logged in. Token: {alice_token[:8]}...")
        assert auth_service.is_valid_token(alice_token), "Alice's token should be valid"
        print("Token is valid.")

        # 3. Get user from token and demonstrate User methods
        current_user = auth_service.get_user_from_token(alice_token)
        if current_user:
            print(f"\n--- User details for {current_user.name} (from token) ---")
            print(f"Initial display: {current_user.display()}")
            print(f"Last login timestamp: {current_user.last_login_at}")

            new_email = "alice.updated@example.com"
            print(f"Attempting to update email to: {new_email}")
            if current_user.update_email(new_email):
                print(f"Email updated. New display: {current_user.display()}")
            else:
                print(f"Failed to update email to {new_email}.")

            current_user.set_preference("theme", "dark_mode_pro")
            current_user.set_preference("notifications_level", "critical")
            print(f"Preferences set. Theme: {current_user.get_preference('theme')}")
            print(f"All preferences: {current_user.preferences}")
        else:
            print("Could not retrieve user from Alice's token.")

        # 4. Logout Alice
        print("\n--- Logging out Alice ---")
        auth_service.logout(alice_token)
        assert not auth_service.is_valid_token(alice_token), "Alice's token should be invalid after logout"
        print("Alice logged out. Token is now invalid.")
    else:
        print("Alice login failed.")

    # 5. Demonstrate deactivation with Bob
    print("\n--- Operations with Bob ---")
    bob_token = auth_service.login(username="bob", password="password")
    if bob_token and bob:
        print(f"Bob logged in. Token: {bob_token[:8]}...")
        retrieved_bob = auth_service.get_user_from_token(bob_token)
        if retrieved_bob:
            print(f"Deactivating Bob ({retrieved_bob.name})...")
            retrieved_bob.deactivate()
            print(f"Bob's account status: {'active' if retrieved_bob.is_active else 'inactive'}")

            print("Attempting to log in deactivated Bob...")
            bob_deactivated_token = auth_service.login(username="bob", password="password")
            if not bob_deactivated_token:
                print("Login for deactivated Bob correctly failed.")
            else:
                print("ERROR: Deactivated Bob was able to log in.")
        else:
            print("Could not retrieve Bob from token for deactivation.")

        # Logout Bob if he was logged in
        auth_service.logout(bob_token)
        print("Bob logged out.")

    else:
        print("Bob login failed or Bob object not found.")

    print(f"\n{greet('Developer')}! Demo finished.")


if __name__ == "__main__":
    main()
