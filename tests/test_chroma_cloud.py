"""Tests for Chroma Cloud integration."""

import os
import unittest
from unittest.mock import MagicMock, patch

import pytest

# Try to import chromadb to check if it's available
try:
    import chromadb  # noqa: F401

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Only import these if chromadb is available
if CHROMADB_AVAILABLE:
    from kit.vector_searcher import ChromaCloudBackend, get_default_backend


@pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb is not installed")
class TestChromaCloudBackend(unittest.TestCase):
    """Test Chroma Cloud backend functionality."""

    @patch("kit.vector_searcher.CloudClient")
    @patch.dict(
        os.environ,
        {
            "CHROMA_API_KEY": "test-api-key",
            "CHROMA_TENANT": "3893b771-b971-4f45-8e30-7aac7837ad7f",
            "CHROMA_DATABASE": "test-db",
        },
    )
    def test_init_with_env_vars(self, mock_cloud_client):
        """Test initialization with environment variables."""
        mock_client_instance = MagicMock()
        mock_cloud_client.return_value = mock_client_instance

        ChromaCloudBackend()

        mock_cloud_client.assert_called_once_with(
            tenant="3893b771-b971-4f45-8e30-7aac7837ad7f",
            database="test-db",
            api_key="test-api-key",
        )
        mock_client_instance.get_or_create_collection.assert_called_once_with("kit_code_chunks")

    @patch("kit.vector_searcher.CloudClient")
    def test_init_with_explicit_params(self, mock_cloud_client):
        """Test initialization with explicit parameters."""
        mock_client_instance = MagicMock()
        mock_cloud_client.return_value = mock_client_instance

        ChromaCloudBackend(
            collection_name="my_collection",
            api_key="explicit-key",
            tenant="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            database="my-db",
        )

        mock_cloud_client.assert_called_once_with(
            tenant="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            database="my-db",
            api_key="explicit-key",
        )
        mock_client_instance.get_or_create_collection.assert_called_once_with("my_collection")

    def test_init_without_api_key_raises(self):
        """Test that initialization without API key raises ValueError."""
        with patch.dict(
            os.environ,
            {"CHROMA_TENANT": "3893b771-b971-4f45-8e30-7aac7837ad7f", "CHROMA_DATABASE": "test-db"},
            clear=True,
        ):
            with self.assertRaises(ValueError) as cm:
                ChromaCloudBackend()
            self.assertIn("Chroma Cloud API key not found", str(cm.exception))

    def test_init_with_invalid_tenant_uuid_raises(self):
        """Test that initialization with invalid tenant UUID raises ValueError."""
        with patch.dict(
            os.environ,
            {"CHROMA_API_KEY": "test-key", "CHROMA_TENANT": "not-a-uuid", "CHROMA_DATABASE": "test-db"},
            clear=True,
        ):
            with self.assertRaises(ValueError) as cm:
                ChromaCloudBackend()
            self.assertIn("Invalid tenant format", str(cm.exception))
            self.assertIn("not-a-uuid", str(cm.exception))
            self.assertIn("valid UUID", str(cm.exception))

    @patch("kit.vector_searcher.CloudClient")
    @patch.dict(
        os.environ,
        {
            "CHROMA_API_KEY": "test-api-key",
            "CHROMA_TENANT": "3893b771-b971-4f45-8e30-7aac7837ad7f",
            "CHROMA_DATABASE": "test-db",
        },
    )
    def test_add_embeddings(self, mock_cloud_client):
        """Test adding embeddings to cloud backend."""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client_instance = MagicMock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_cloud_client.return_value = mock_client_instance

        backend = ChromaCloudBackend()
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        metadatas = [{"file": "test1.py"}, {"file": "test2.py"}]

        backend.add(embeddings, metadatas)

        mock_collection.add.assert_called_once_with(embeddings=embeddings, metadatas=metadatas, ids=["0", "1"])

    @patch("kit.vector_searcher.CloudClient")
    @patch.dict(
        os.environ,
        {
            "CHROMA_API_KEY": "test-api-key",
            "CHROMA_TENANT": "3893b771-b971-4f45-8e30-7aac7837ad7f",
            "CHROMA_DATABASE": "test-db",
        },
    )
    def test_query(self, mock_cloud_client):
        """Test querying the cloud backend."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "metadatas": [[{"file": "test1.py"}, {"file": "test2.py"}]],
            "distances": [[0.1, 0.2]],
        }
        mock_client_instance = MagicMock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_cloud_client.return_value = mock_client_instance

        backend = ChromaCloudBackend()
        results = backend.query([0.1, 0.2], top_k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["file"], "test1.py")
        self.assertEqual(results[0]["score"], 0.1)
        self.assertEqual(results[1]["file"], "test2.py")
        self.assertEqual(results[1]["score"], 0.2)

    @patch("kit.vector_searcher.CloudClient")
    @patch.dict(
        os.environ,
        {
            "CHROMA_API_KEY": "test-api-key",
            "CHROMA_TENANT": "3893b771-b971-4f45-8e30-7aac7837ad7f",
            "CHROMA_DATABASE": "test-db",
        },
    )
    def test_delete(self, mock_cloud_client):
        """Test deleting vectors from cloud backend."""
        mock_collection = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_cloud_client.return_value = mock_client_instance

        backend = ChromaCloudBackend()
        backend.delete(["id1", "id2"])

        mock_collection.delete.assert_called_once_with(ids=["id1", "id2"])


@pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb is not installed")
class TestGetDefaultBackend(unittest.TestCase):
    """Test the get_default_backend factory function."""

    @patch("kit.vector_searcher.ChromaCloudBackend")
    @patch.dict(
        os.environ,
        {
            "KIT_USE_CHROMA_CLOUD": "true",
            "CHROMA_API_KEY": "test-api-key",
            "CHROMA_TENANT": "3893b771-b971-4f45-8e30-7aac7837ad7f",
            "CHROMA_DATABASE": "test-db",
        },
    )
    def test_returns_cloud_backend_when_explicitly_enabled(self, mock_cloud_backend):
        """Test that cloud backend is returned when explicitly enabled."""
        backend = get_default_backend(persist_dir="/some/path", collection_name="test_collection")

        mock_cloud_backend.assert_called_once_with(collection_name="test_collection")
        self.assertEqual(backend, mock_cloud_backend.return_value)

    @patch.dict(os.environ, {"KIT_USE_CHROMA_CLOUD": "true"}, clear=True)
    def test_raises_when_cloud_enabled_but_no_api_key(self):
        """Test that ValueError is raised when cloud is enabled but no API key."""
        with self.assertRaises(ValueError) as cm:
            get_default_backend(persist_dir="/some/path", collection_name="test_collection")
        self.assertIn("KIT_USE_CHROMA_CLOUD is set to true but CHROMA_API_KEY is not found", str(cm.exception))

    @patch("kit.vector_searcher.ChromaDBBackend")
    @patch.dict(os.environ, {"CHROMA_API_KEY": "test-api-key"}, clear=True)
    def test_returns_local_backend_when_api_key_set_but_cloud_not_enabled(self, mock_local_backend):
        """Test that local backend is returned even with API key if cloud not explicitly enabled."""
        backend = get_default_backend(persist_dir="/some/path", collection_name="test_collection")

        mock_local_backend.assert_called_once_with("/some/path", "test_collection")
        self.assertEqual(backend, mock_local_backend.return_value)

    @patch("kit.vector_searcher.ChromaDBBackend")
    @patch.dict(os.environ, {}, clear=True)
    def test_returns_local_backend_by_default(self, mock_local_backend):
        """Test that local backend is returned by default."""
        backend = get_default_backend(persist_dir="/some/path", collection_name="test_collection")

        mock_local_backend.assert_called_once_with("/some/path", "test_collection")
        self.assertEqual(backend, mock_local_backend.return_value)

    @patch.dict(os.environ, {}, clear=True)
    def test_raises_when_no_persist_dir_for_local(self):
        """Test that ValueError is raised when no persist_dir for local backend."""
        with self.assertRaises(ValueError) as cm:
            get_default_backend(collection_name="test_collection")
        self.assertIn("persist_dir is required", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
