"""User dataclass for the realistic fixture repo."""

from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
    email: str

    def display(self) -> str:
        """Return a human readable representation."""
        return f"<{self.id}> {self.name} <{self.email}>"
