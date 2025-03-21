"""
Tests for game companion implementation.
"""
import pytest
from unittest.mock import Mock, patch
from gamefriend.companion import GameCompanion
from mistralai.models.chat_completion import ChatMessage

@pytest.fixture
def mock_mistral_client():
    with patch("gamefriend.companion.MistralClient") as mock:
        instance = mock.return_value
        instance.chat.return_value.choices = [
            Mock(message=Mock(content="Test response"))
        ]
        yield instance

@pytest.fixture
def companion(mock_mistral_client):
    return GameCompanion("test_game", "test_key")

def test_chat(companion, mock_mistral_client):
    """Test chat functionality."""
    response = companion.chat("test message")
    assert response == "Test response"
    
    # Verify chat history
    assert len(companion.chat_history) == 2
    assert companion.chat_history[0].role == "user"
    assert companion.chat_history[0].content == "test message"
    assert companion.chat_history[1].role == "assistant"
    assert companion.chat_history[1].content == "Test response"
    
    # Verify Mistral client call
    mock_mistral_client.chat.assert_called_once_with(
        model="mistral-tiny",
        messages=companion.chat_history
    )

def test_chat_error(companion, mock_mistral_client):
    """Test error handling in chat."""
    mock_mistral_client.chat.side_effect = Exception("Test error")
    
    with pytest.raises(Exception) as exc_info:
        companion.chat("test message")
    assert str(exc_info.value) == "Test error" 