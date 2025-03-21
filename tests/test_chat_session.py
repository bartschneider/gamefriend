"""
Tests for chat session implementation.
"""
import pytest
from unittest.mock import Mock, patch
from gamefriend.chat_session import InteractiveChatSession

@pytest.fixture
def mock_companion():
    with patch("gamefriend.chat_session.GameCompanion") as mock:
        instance = mock.return_value
        instance.chat.return_value = "Test response"
        yield instance

@pytest.fixture
def chat_session(mock_companion):
    return InteractiveChatSession("test_game", "test_key")

def test_send_message(chat_session, mock_companion):
    """Test sending a message."""
    response = chat_session.send_message("test message")
    assert response == "Test response"
    mock_companion.chat.assert_called_once_with("test message")

def test_should_exit(chat_session):
    """Test exit command detection."""
    assert chat_session._should_exit("quit")
    assert chat_session._should_exit("exit")
    assert not chat_session._should_exit("hello")

def test_chat_session_interaction(chat_session, mock_companion):
    """Test chat session interaction."""
    with patch("builtins.input", side_effect=["hello", "quit"]):
        with patch("builtins.print") as mock_print:
            chat_session.start()
    
    mock_companion.chat.assert_called_once_with("hello")
    assert any("GameFriend" in call.args[0] for call in mock_print.call_args_list)
    assert any("Test response" in call.args[0] for call in mock_print.call_args_list)

def test_chat_session_error_handling(chat_session, mock_companion):
    """Test error handling in chat session."""
    mock_companion.chat.side_effect = Exception("Test error")
    
    with patch("builtins.input", side_effect=["hello", "quit"]):
        with patch("builtins.print") as mock_print:
            chat_session.start()
    
    assert any("Error: Test error" in call.args[0] for call in mock_print.call_args_list) 