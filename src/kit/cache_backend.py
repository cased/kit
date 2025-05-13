from __future__ import annotations

import abc
import json
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Type alias for the cache structure: Maps doc_id -> {"hash": content_hash}
CacheData = Dict[str, Dict[str, str]]

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


class FilesystemCacheBackend(CacheBackend):
    """Default cache backend using a local filesystem JSON file."""

    DEFAULT_FILENAME = "meta.json"

    def __init__(self, persist_dir: str):
        """Initializes the backend.

        Args:
            persist_dir: The directory where the cache file should be stored.
        """
        if not persist_dir:
            raise ValueError("persist_dir must be provided for FilesystemCacheBackend")
        self.persist_dir = persist_dir
        # Construct the full path to the cache file
        self.cache_file_path = os.path.join(self.persist_dir, self.DEFAULT_FILENAME)
        # Ensure the directory exists so we can write the file later
        os.makedirs(self.persist_dir, exist_ok=True)
        logger.debug(f"FilesystemCacheBackend initialized. Cache file path: {self.cache_file_path}")


    def load(self) -> CacheData:
        """Loads cache data from the JSON file."""
        if os.path.exists(self.cache_file_path):
            try:
                # Open and read the file content
                with open(self.cache_file_path, "r", encoding="utf-8") as fp:
                    content = fp.read()
                # Handle empty file case - return empty dict, not error
                if not content.strip():
                    logger.warning(f"Cache file is empty: {self.cache_file_path}")
                    return {}
                # Parse the JSON content
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from cache file {self.cache_file_path}: {e}. Returning empty cache.", exc_info=True)
                # If JSON is invalid, treat as empty cache to allow rebuild
                return {}
            except OSError as e:
                logger.error(f"Failed to read cache file {self.cache_file_path}: {e}. Returning empty cache.", exc_info=True)
                 # If file read error occurs, treat as empty cache
                return {}
        else:
            # File doesn't exist, so return an empty cache
            logger.debug(f"Cache file not found, starting fresh: {self.cache_file_path}")
            return {}

    def save(self, cache_data: CacheData) -> None:
        """Saves cache data to the JSON file."""
        try:
            # Write the cache data dictionary to the file as JSON
            with open(self.cache_file_path, "w", encoding="utf-8") as fp:
                json.dump(cache_data, fp, indent=2) # Use indent for readability
            logger.debug(f"Cache data saved successfully to {self.cache_file_path}")
        except OSError as e:
            logger.error(f"Failed to write cache file {self.cache_file_path}: {e}", exc_info=True)
            # Consider if raising an exception here is more appropriate
            # For now, log the error and continue
        except TypeError as e:
            logger.error(f"Failed to serialize cache data to JSON for {self.cache_file_path}: {e}", exc_info=True)
            # This might happen if cache_data is not JSON serializable 