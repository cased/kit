"""
Base classes and protocols for LLM models.
"""

from typing import Protocol, runtime_checkable


# Define a Protocol for LLM clients to help with type checking
@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol defining the interface for LLM clients."""

    # This is a structural protocol - any object with compatible methods will be accepted
    pass


class LLMError(Exception):
    """Custom exception for LLM related errors."""

    pass
