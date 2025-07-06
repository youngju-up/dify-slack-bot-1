"""
Unit tests for dify-slack-bot.
"""
import pytest
from unittest.mock import Mock, patch
from src.config import Config
from src.dify_client import DifyClient
from src.utils import (
    extract_text_from_event,
    format_dify_response,
    ConversationCache,
    parse_streaming_response,
    truncate_text
)


class TestUtils:
    """Test utility functions."""

    def test_extract_text_from_event(self):
        """Test text extraction from Slack events."""
        # Test with bot mention
        event = {"text": "<@U123456> hello world"}
        assert extract_text_from_event(event) == "hello world"

        # Test without mention
        event = {"text": "just a message"}
        assert extract_text_from_event(event) == "just a message"

        # Test with multiple mentions
        event = {"text": "<@U123456> <@U789012> test"}
        assert extract_text_from_event(event) == "test"

    def test_format_dify_response(self):
        """Test Dify response formatting."""
        # Test basic response
        response = {"answer": "Test answer"}
        assert format_dify_response(response) == "Test answer"

        # Test with citations
        response = {
            "answer": "Test answer",
            "metadata": {
                "retriever_resources": [
                    {
                        "dataset_name": "Test Dataset",
                        "document_name": "Test Doc",
                        "score": 0.95
                    }
                ]
            }
        }
        formatted = format_dify_response(response)
        assert "Test answer" in formatted
        assert "Sources:" in formatted
        assert "Test Doc" in formatted

    def test_conversation_cache(self):
        """Test conversation cache functionality."""
        cache = ConversationCache(ttl_seconds=60)

        # Test set and get
        cache.set("user1", "channel1", "conv1")
        assert cache.get("user1", "channel1") == "conv1"

        # Test with thread
        cache.set("user1", "channel1", "conv2", "thread1")
        assert cache.get("user1", "channel1", "thread1") == "conv2"

        # Test non-existent
        assert cache.get("user2", "channel2") is None

    def test_parse_streaming_response(self):
        """Test streaming response parsing."""
        # Valid line
        line = 'data: {"event": "message", "answer": "Hello"}'
        result = parse_streaming_response(line)
        assert result["event"] == "message"
        assert result["answer"] == "Hello"

        # Invalid line
        line = 'not a valid line'
        assert parse_streaming_response(line) is None

        # Invalid JSON
        line = 'data: not json'
        assert parse_streaming_response(line) is None

    def test_truncate_text(self):
        """Test text truncation."""
        # Short text
        text = "Short text"
        assert truncate_text(text, 20) == text

        # Long text
        text = "a" * 100
        truncated = truncate_text(text, 50)
        assert len(truncated) == 50
        assert truncated.endswith("...")


class TestDifyClient:
    """Test Dify API client."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        with patch.object(Config, 'DIFY_API_KEY', 'test-key'):
            with patch.object(Config, 'DIFY_BASE_URL', 'http://test.com'):
                return DifyClient()

    @patch('requests.post')
    def test_send_message_blocking(self, mock_post, client):
        """Test sending message in blocking mode."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "answer": "Test response",
            "conversation_id": "conv123"
        }
        mock_post.return_value = mock_response

        with patch.object(Config, 'RESPONSE_MODE', 'blocking'):
            result = client.send_message("user1", "Hello")

        assert result["answer"] == "Test response"
        assert result["conversation_id"] == "conv123"

        # Verify request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["query"] == "Hello"
        assert call_args[1]["json"]["user"] == "user1"

    @patch('requests.post')
    def test_send_message_with_files(self, mock_post, client):
        """Test sending message with files."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"answer": "Response"}
        mock_post.return_value = mock_response

        files = [{
            "type": "image",
            "transfer_method": "local_file",
            "upload_file_id": "file123"
        }]

        with patch.object(Config, 'RESPONSE_MODE', 'blocking'):
            client.send_message("user1", "Check this", files=files)

        call_args = mock_post.call_args
        assert call_args[1]["json"]["files"] == files

    @patch('requests.post')
    def test_upload_file(self, mock_post, client):
        """Test file upload."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "file123",
            "name": "test.png",
            "size": 1024
        }
        mock_post.return_value = mock_response

        result = client.upload_file(b"test content", "test.png", "user1")

        assert result["id"] == "file123"
        assert result["name"] == "test.png"

    @patch('requests.get')
    def test_get_conversations(self, mock_get, client):
        """Test getting conversations."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "conv1", "name": "Test"}],
            "has_more": False
        }
        mock_get.return_value = mock_response

        result = client.get_conversations("user1")

        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "conv1"

    @patch('requests.post')
    def test_error_handling(self, mock_post, client):
        """Test error handling."""
        # API error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            with patch.object(Config, 'RESPONSE_MODE', 'blocking'):
                client.send_message("user1", "Hello")

        assert "400" in str(exc_info.value)

        # Connection error
        mock_post.side_effect = requests.exceptions.ConnectionError()

        with pytest.raises(Exception) as exc_info:
            with patch.object(Config, 'RESPONSE_MODE', 'blocking'):
                client.send_message("user1", "Hello")

        assert "Connection error" in str(exc_info.value)


class TestSlackBot:
    """Test Slack bot functionality."""

    @pytest.fixture
    def bot(self):
        """Create a test bot."""
        with patch('src.bot.App'):
            with patch('src.bot.SlackRequestHandler'):
                flask_app = Mock()
                return SlackBot(flask_app)

    def test_bot_initialization(self, bot):
        """Test bot initialization."""
        assert bot.dify is not None
        assert bot.app is not None
        assert bot.handler is not None


if __name__ == "__main__":
    pytest.main([__file__])
