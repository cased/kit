from __future__ import annotations

import abc
import logging
from typing import Dict

# Type alias for the cache structure: Maps doc_id -> {"hash": content_hash}
CacheData = Dict[str, Dict[str, str]]

logger = logging.getLogger(__name__)


class CacheBackend(abc.ABC):
    """Abstract base class for DocstringIndexer cache storage backends."""

    @abc.abstractmethod
    def load(self) -> CacheData:
        """Load the cache data from the backend storage.

        Returns:
            A dictionary containing the cached data (doc_id -> {hash: content_hash}).
            Returns an empty dictionary if the cache doesn't exist or is empty.
        """
        pass

    @abc.abstractmethod
    def save(self, cache_data: CacheData) -> None:
        """Save the cache data to the backend storage.

        Args:
            cache_data: The dictionary containing the cache data to save.
        """
        pass


# The FilesystemCacheBackend class has been moved to src/kit/cache_backends/filesystem.py
