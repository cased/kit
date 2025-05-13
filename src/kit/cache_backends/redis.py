from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis  # Import directly as it's now a required dependency

from ..cache_backend import CacheBackend, CacheData

logger = logging.getLogger(__name__)

# Remove the try...except ImportError block
# try:
#     import redis
# except ImportError:
#     redis = None  # type: ignore
#     logger.info(
#         "The 'redis' library is not installed. RedisCacheBackend will not be available. "
#         "Install with: pip install kit[redis-cache] or pip install redis"
#     )


class RedisCacheBackend(CacheBackend):
    """Cache backend using Redis to store cache data.

    The cache is stored as a JSON string in a single Redis key.
    """

    DEFAULT_REDIS_KEY = "kit_docstring_indexer_cache"

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        redis_url: Optional[str] = None,
        cache_key: Optional[str] = None,
        **redis_connection_kwargs: Any,
    ):
        """Initializes the RedisCacheBackend.

        Args:
            redis_client: An existing redis.Redis client instance.
            redis_url: URL for the Redis instance (e.g., "redis://localhost:6379/0").
                       If provided, a new client will be created.
            cache_key: The Redis key to use for storing the cache data.
                       Defaults to DEFAULT_REDIS_KEY.
            **redis_connection_kwargs: Additional arguments for redis.Redis.from_url()
                                       if redis_url is provided and redis_client is None.
        Raises:
            # Remove ImportError from raises as redis is required
            ValueError: If neither redis_client nor redis_url is provided.
        """
        # Remove the check for redis is None
        # if redis is None:
        #     raise ImportError(
        #         "The 'redis' library is required to use RedisCacheBackend. "
        #         "Please install it (e.g., 'pip install kit[redis-cache]' or 'pip install redis')."
        #     )

        if redis_client:
            self.redis_client = redis_client
        elif redis_url:
            try:
                self.redis_client = redis.Redis.from_url(redis_url, **redis_connection_kwargs)
            except Exception as e:
                logger.error(f"Failed to connect to Redis using URL {redis_url}: {e}", exc_info=True)
                raise
        else:
            raise ValueError("Either 'redis_client' or 'redis_url' must be provided for RedisCacheBackend.")

        self.cache_key = cache_key or self.DEFAULT_REDIS_KEY
        logger.debug(f"RedisCacheBackend initialized. Cache key: {self.cache_key}")

    def load(self) -> CacheData:
        """Loads cache data from the Redis key."""
        try:
            cached_data_json = self.redis_client.get(self.cache_key)
            if cached_data_json:
                content = cached_data_json.decode("utf-8")
                if not content.strip():
                    logger.warning(f"Cache key '{self.cache_key}' is empty in Redis.")
                    return {}
                return json.loads(content)
            else:
                logger.debug(f"Cache key '{self.cache_key}' not found in Redis. Starting fresh.")
                return {}
        except redis.RedisError as e:
            logger.error(
                f"Redis error while loading cache key '{self.cache_key}': {e}. Returning empty cache.", exc_info=True
            )
            return {}
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to decode JSON from Redis cache key '{self.cache_key}': {e}. Returning empty cache.",
                exc_info=True,
            )
            return {}
        except Exception as e:  # Catch any other unexpected errors
            logger.error(
                f"Unexpected error loading cache from Redis key '{self.cache_key}': {e}. Returning empty cache.",
                exc_info=True,
            )
            return {}

    def save(self, cache_data: CacheData) -> None:
        """Saves cache data to the Redis key as a JSON string."""
        try:
            json_data = json.dumps(cache_data, indent=2)
            self.redis_client.set(self.cache_key, json_data)
            logger.debug(f"Cache data saved successfully to Redis key '{self.cache_key}'.")
        except redis.RedisError as e:
            logger.error(f"Redis error while saving cache key '{self.cache_key}': {e}", exc_info=True)
            # Decide if we should raise here
        except TypeError as e:
            logger.error(f"Failed to serialize cache data to JSON for Redis key '{self.cache_key}': {e}", exc_info=True)
        except Exception as e:  # Catch any other unexpected errors
            logger.error(f"Unexpected error saving cache to Redis key '{self.cache_key}': {e}", exc_info=True)
