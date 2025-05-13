from __future__ import annotations

import json

import pytest

# Check if fakeredis is installed, skip tests if not
try:
    import fakeredis
    import redis

    SKIP_TESTS = False
except ImportError:
    SKIP_TESTS = True

# Only import the backend if fakeredis is available
if not SKIP_TESTS:
    from kit.cache_backend import CacheData
    from kit.cache_backends.redis import RedisCacheBackend


@pytest.mark.skipif(SKIP_TESTS, reason="fakeredis or redis library not installed")
def test_redis_save_and_load():
    """Test saving and loading data using RedisCacheBackend."""
    fake_redis_client = fakeredis.FakeStrictRedis()
    cache_key = "test_cache_key"
    backend = RedisCacheBackend(redis_client=fake_redis_client, cache_key=cache_key)

    # 1. Test loading from empty cache
    loaded_empty = backend.load()
    assert loaded_empty == {}

    # 2. Test saving data
    test_data: CacheData = {
        "file1.py::func_a": {"hash": "hash1"},
        "file2.py::ClassB": {"hash": "hash2"},
    }
    backend.save(test_data)

    # 3. Verify data was saved correctly in Redis (as JSON string)
    raw_data = fake_redis_client.get(cache_key)
    assert raw_data is not None
    saved_json = raw_data.decode("utf-8")
    assert json.loads(saved_json) == test_data

    # 4. Test loading the saved data
    loaded_data = backend.load()
    assert loaded_data == test_data

    # 5. Test overwriting data
    new_data: CacheData = {"file3.py::func_c": {"hash": "hash3"}}
    backend.save(new_data)
    loaded_new_data = backend.load()
    assert loaded_new_data == new_data


@pytest.mark.skipif(SKIP_TESTS, reason="fakeredis or redis library not installed")
def test_redis_init_with_url():
    """Test initializing RedisCacheBackend with a URL."""

    # fakeredis doesn't directly support from_url in the same way, but we can test the path
    # We expect it to raise if redis isn't installed, or potentially connect if a real URL is given
    # Here, we just check that it *tries* to use from_url implicitly by not passing a client
    # We need to mock redis.Redis.from_url to avoid actual connection attempts
    class MockRedisClient:
        def get(self, key):
            return None

        def set(self, key, value):
            pass

    try:
        original_from_url = redis.Redis.from_url
        redis.Redis.from_url = lambda url, **kwargs: MockRedisClient()

        backend = RedisCacheBackend(redis_url="redis://dummy:6379/0")
        assert isinstance(backend.redis_client, MockRedisClient)
        assert backend.cache_key == RedisCacheBackend.DEFAULT_REDIS_KEY

        # Test loading (should use the mocked client)
        assert backend.load() == {}

    finally:
        # Restore original method
        if "original_from_url" in locals():
            redis.Redis.from_url = original_from_url


@pytest.mark.skipif(SKIP_TESTS, reason="fakeredis or redis library not installed")
def test_redis_init_errors():
    """Test initialization errors."""
    # Test ValueError if neither client nor URL is provided
    with pytest.raises(ValueError, match="Either 'redis_client' or 'redis_url' must be provided"):
        RedisCacheBackend()


# Add more tests as needed, e.g., for connection errors, JSON decode errors, etc.
# but mocking these within fakeredis might be tricky.
