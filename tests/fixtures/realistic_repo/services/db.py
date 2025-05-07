"""In-memory DB connector used by AuthService (toy)."""

def connect(url: str = "sqlite://:memory:") -> str:
    """Pretend to open a DB connection and return a connection ID."""
    return f"conn-{url}"
