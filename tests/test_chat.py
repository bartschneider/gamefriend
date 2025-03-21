import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from gamefriend.chat import ChatManager, ChatMessage
from gamefriend.chat.mistral_client import MistralClientWrapper


@pytest.fixture
def mock_mistral_client():
    with patch('gamefriend.chat.mistral_client.MistralClient') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def chat_manager(mock_mistral_client):
    with patch('gamefriend.chat.mistral_client.MistralClientWrapper') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        manager = ChatManager()
        manager.mistral = mock_instance
        return manager


@pytest.fixture
def sample_guide_content():
    return """
    # Game Guide
    This is a guide for a game.

    ## Getting Started
    Here's how to start the game.

    ## Items
    * Sword
    * Shield
    * Potion

    ## Code Example
    ```python
    def example():
        print("Hello")
    ```
    """


def test_chat_message_creation():
    """Test creating a ChatMessage instance."""
    message = ChatMessage(
        role="user",
        content="Hello",
        timestamp=datetime.now()
    )
    assert message.role == "user"
    assert message.content == "Hello"
    assert isinstance(message.timestamp, datetime)


def test_get_guide_content(chat_manager, tmp_path):
    """Test getting guide content from a file."""
    # Create a temporary guide file
    guides_dir = tmp_path / "guides" / "gba" / "test-game"
    guides_dir.mkdir(parents=True)
    guide_file = guides_dir / "guide_123.md"
    guide_file.write_text("# Test Guide\nSome content")

    # Patch the guides_dir in chat_manager
    chat_manager.guides_dir = tmp_path / "guides"

    # Test with valid game context
    game_context = {"platform": "gba", "name": "test-game"}
    content = chat_manager.get_guide_content(game_context)
    assert content is not None
    assert "# Test Guide" in content
    assert "Some content" in content

    # Test with invalid game context
    assert chat_manager.get_guide_content({}) is None
    assert chat_manager.get_guide_content({"platform": "invalid"}) is None
    assert chat_manager.get_guide_content({"name": "invalid"}) is None


def test_split_into_sections(chat_manager, sample_guide_content):
    """Test splitting guide content into sections."""
    sections = chat_manager.split_into_sections(sample_guide_content)
    assert len(sections) > 0
    assert any("Getting Started" in section for section in sections)
    assert any("Items" in section for section in sections)
    assert any("Code Example" in section for section in sections)


def test_chunk_text(chat_manager):
    """Test splitting text into chunks."""
    text = "First sentence. Second sentence. Third sentence."
    chunks = chat_manager.chunk_text(text)
    assert len(chunks) > 0
    assert all(len(chunk) <= chat_manager.max_chunk_length for chunk in chunks)


def test_find_relevant_sections(chat_manager, sample_guide_content):
    """Test finding relevant sections using embeddings."""
    # Mock the embeddings creation
    chat_manager.mistral.create_embeddings.side_effect = [
        np.random.rand(384),  # Question embedding
        np.random.rand(384),  # Section 1 embedding
        np.random.rand(384),  # Section 2 embedding
        np.random.rand(384),  # Section 3 embedding
    ]

    sections = chat_manager.find_relevant_sections(sample_guide_content, "How do I start?")
    assert len(sections) > 0
    assert len(sections) <= 3  # Default top_k is 3


def test_process_message(chat_manager, sample_guide_content):
    """Test processing a chat message."""
    # Mock guide content retrieval
    chat_manager.get_guide_content = MagicMock(return_value=sample_guide_content)
    
    # Mock finding relevant sections
    chat_manager.find_relevant_sections = MagicMock(return_value=["Getting Started section"])
    
    # Mock Mistral response
    chat_manager.mistral.chat_with_context.return_value = "Here's how to start..."

    # Test with valid game context
    game_context = {"platform": "gba", "name": "test-game"}
    response = chat_manager.process_message("How do I start?", game_context)
    assert response == "Here's how to start..."

    # Test without game context
    assert "Please select a game first" in chat_manager.process_message("Hello", None)

    # Test with no guide content
    chat_manager.get_guide_content.return_value = None
    assert "I couldn't find the guide" in chat_manager.process_message("Hello", game_context)


def test_mistral_client_wrapper(mock_mistral_client):
    """Test MistralClientWrapper functionality."""
    with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
        client = MistralClientWrapper()
        
        # Test creating embeddings
        mock_mistral_client.embeddings.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2, 0.3])]
        )
        embeddings = client.create_embeddings("test text")
        assert len(embeddings) == 3
        assert all(isinstance(x, float) for x in embeddings)

        # Test chat with context
        mock_mistral_client.chat.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="test response"))]
        )
        response = client.chat_with_context(
            "test question",
            "test context",
            "test history"
        )
        assert response == "test response"


def test_mistral_client_wrapper_no_api_key():
    """Test MistralClientWrapper initialization without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="MISTRAL_API_KEY environment variable is not set"):
            MistralClientWrapper()


def test_chat_context_switching(chat_manager, tmp_path):
    """Test that chat context is properly reset when switching games."""
    # Create temporary guide files for two different games
    guides_dir = tmp_path / "guides"
    chat_manager.guides_dir = guides_dir

    # Create guide for first game
    game1_dir = guides_dir / "gba" / "game1"
    game1_dir.mkdir(parents=True)
    game1_guide = game1_dir / "guide_1.md"
    game1_guide.write_text("# Game 1 Guide\nThis is about game 1")

    # Create guide for second game
    game2_dir = guides_dir / "snes" / "game2"
    game2_dir.mkdir(parents=True)
    game2_guide = game2_dir / "guide_2.md"
    game2_guide.write_text("# Game 2 Guide\nThis is about game 2")

    # Mock guide content retrieval
    chat_manager.get_guide_content = MagicMock(side_effect=[
        "# Game 1 Guide\nThis is about game 1",  # First game
        "# Game 2 Guide\nThis is about game 2",  # Second game
    ])

    # Mock finding relevant sections
    chat_manager.find_relevant_sections = MagicMock(side_effect=[
        ["Game 1 section"],  # First game
        ["Game 2 section"],  # Second game
    ])

    # Mock Mistral response
    chat_manager.mistral.chat_with_context.return_value = "Test response"

    # Start chat with first game
    game1_context = {"platform": "gba", "name": "game1"}
    response1 = chat_manager.process_message("Tell me about game 1", game1_context)
    assert response1 == "Test response"

    # Verify chat history for first game
    game1_id = "gba/game1"
    assert game1_id in chat_manager.chat_history
    assert len(chat_manager.chat_history[game1_id]) == 2  # User message + assistant response

    # Switch to second game
    game2_context = {"platform": "snes", "name": "game2"}
    response2 = chat_manager.process_message("Tell me about game 2", game2_context)
    assert response2 == "Test response"

    # Verify chat history for second game
    game2_id = "snes/game2"
    assert game2_id in chat_manager.chat_history
    assert len(chat_manager.chat_history[game2_id]) == 2  # User message + assistant response

    # Verify that the first game's history is still preserved
    assert game1_id in chat_manager.chat_history
    assert len(chat_manager.chat_history[game1_id]) == 2

    # Verify that get_guide_content was called with correct contexts
    from unittest.mock import call
    chat_manager.get_guide_content.assert_has_calls([
        call(game1_context),
        call(game2_context),
    ])

    # Verify that find_relevant_sections was called with correct content and messages
    chat_manager.find_relevant_sections.assert_has_calls([
        call("# Game 1 Guide\nThis is about game 1", "Tell me about game 1"),
        call("# Game 2 Guide\nThis is about game 2", "Tell me about game 2"),
    ])

    # Verify that chat_with_context was called with correct parameters
    chat_manager.mistral.chat_with_context.assert_has_calls([
        call("Tell me about game 1", "Game 1 section", "user: Tell me about game 1"),
        call("Tell me about game 2", "Game 2 section", "user: Tell me about game 2"),
    ])

    # Verify that section_embeddings were cleared when switching games
    assert chat_manager.current_game_id == game2_id
    assert not chat_manager.section_embeddings  # Should be empty after switching games 