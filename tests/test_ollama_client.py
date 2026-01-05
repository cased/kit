"""Tests for the OllamaClient module."""

from unittest.mock import MagicMock, patch


class TestOllamaClient:
    """Tests for OllamaClient class."""

    def test_init_creates_own_session(self):
        """Test that OllamaClient creates its own session when none provided."""
        from kit.ollama_client import OllamaClient

        with patch("requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            client = OllamaClient("http://localhost:11434", "llama3")

            assert client.base_url == "http://localhost:11434"
            assert client.model == "llama3"
            assert client.session == mock_session
            assert client._owns_session is True
            mock_session_class.assert_called_once()

    def test_init_uses_provided_session(self):
        """Test that OllamaClient uses provided session."""
        from kit.ollama_client import OllamaClient

        mock_session = MagicMock()
        client = OllamaClient("http://localhost:11434", "llama3", session=mock_session)

        assert client.session == mock_session
        assert client._owns_session is False

    def test_generate_calls_api(self):
        """Test that generate makes correct API call."""
        from kit.ollama_client import OllamaClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Hello, world!"}
        mock_session.post.return_value = mock_response

        client = OllamaClient("http://localhost:11434", "llama3", session=mock_session)
        result = client.generate("Say hello")

        mock_session.post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": "Say hello", "stream": False},
        )
        assert result == "Hello, world!"

    def test_generate_with_kwargs(self):
        """Test that generate passes additional kwargs to API."""
        from kit.ollama_client import OllamaClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "test"}
        mock_session.post.return_value = mock_response

        client = OllamaClient("http://localhost:11434", "llama3", session=mock_session)
        client.generate("prompt", num_predict=100, temperature=0.7)

        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["num_predict"] == 100
        assert call_args[1]["json"]["temperature"] == 0.7

    def test_generate_handles_empty_response(self):
        """Test that generate handles missing response field."""
        from kit.ollama_client import OllamaClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_session.post.return_value = mock_response

        client = OllamaClient("http://localhost:11434", "llama3", session=mock_session)
        result = client.generate("prompt")

        assert result == ""

    def test_close_closes_owned_session(self):
        """Test that close() closes session when client owns it."""
        from kit.ollama_client import OllamaClient

        with patch("requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            client = OllamaClient("http://localhost:11434", "llama3")
            client.close()

            mock_session.close.assert_called_once()

    def test_close_does_not_close_injected_session(self):
        """Test that close() does not close injected session."""
        from kit.ollama_client import OllamaClient

        mock_session = MagicMock()
        client = OllamaClient("http://localhost:11434", "llama3", session=mock_session)
        client.close()

        mock_session.close.assert_not_called()

    def test_context_manager(self):
        """Test that OllamaClient works as context manager."""
        from kit.ollama_client import OllamaClient

        with patch("requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            with OllamaClient("http://localhost:11434", "llama3") as client:
                assert client.base_url == "http://localhost:11434"

            mock_session.close.assert_called_once()
