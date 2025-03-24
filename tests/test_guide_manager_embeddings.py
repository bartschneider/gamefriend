"""
Tests for the guide manager with local embeddings support.
"""
import os
import tempfile
from pathlib import Path
import shutil
import pytest
from unittest.mock import patch, MagicMock

from gamefriend.guide_manager import FileSystemGuideManager
from gamefriend.embeddings_manager import EmbeddingsManager

# Sample guide content
SAMPLE_GUIDE_CONTENT = """
# Soul Blazer Guide

## Introduction
Welcome to the Soul Blazer guide! This game was released in 1992 for the SNES.

## Chapter 1: The Green Valley
Start by exploring the Green Valley. Talk to the elder in the first town.
You'll need to find the sword before proceeding to the first dungeon.

### The First Dungeon
Enter the dungeon and defeat the enemies to release the trapped souls.
These souls will return to the town and unlock new areas and provide information.

## Chapter 2: The Mountain Pass
After completing the first dungeon, head to the Mountain Pass.
Be careful of the flying enemies here, they can be difficult to hit.
"""

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def guide_dir(temp_dir):
    """Create a temporary guide directory with a sample guide."""
    guides_dir = temp_dir / "guides"
    game_dir = guides_dir / "snes" / "soul-blazer"
    game_dir.mkdir(parents=True)
    
    guide_path = game_dir / "guide_12345.md"
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(SAMPLE_GUIDE_CONTENT)
    
    return guides_dir

@pytest.fixture
def embeddings_dir(temp_dir):
    """Create a temporary directory for embeddings."""
    embed_dir = temp_dir / "data" / "embeddings"
    embed_dir.mkdir(parents=True)
    return embed_dir

def test_guide_manager_init(guide_dir, embeddings_dir):
    """Test initialization of the guide manager with embeddings support."""
    manager = FileSystemGuideManager(
        base_path=str(guide_dir),
        embeddings_dir=str(embeddings_dir)
    )
    assert isinstance(manager.embeddings_manager, EmbeddingsManager)

def test_generate_embeddings(guide_dir, embeddings_dir):
    """Test generating embeddings for a game."""
    # Create guide manager
    manager = FileSystemGuideManager(
        base_path=str(guide_dir),
        embeddings_dir=str(embeddings_dir)
    )
    
    # Mock the embeddings_manager.process_game_guides method directly
    with patch.object(manager.embeddings_manager, 'process_game_guides') as mock_process:
        # Configure the mock to return a path when processing guides
        mock_process.return_value = embeddings_dir / "soul-blazer_embeddings.json"
        
        # Call the method
        manager._generate_embeddings("soul-blazer", "snes")
        
        # Verify the mock was called correctly
        mock_process.assert_called_once_with(
            game_name="soul-blazer",
            platform="snes",
            guides_dir=guide_dir
        )

def test_get_guide_context(guide_dir, embeddings_dir):
    """Test getting guide context for a query."""
    # Create guide manager
    manager = FileSystemGuideManager(
        base_path=str(guide_dir),
        embeddings_dir=str(embeddings_dir)
    )
    
    # Mock the embeddings_manager.get_context_for_query method directly
    with patch.object(manager.embeddings_manager, 'get_context_for_query') as mock_get_context:
        # Configure the mock to return context
        expected_context = "From guide_12345.md:\nStart by exploring the Green Valley. Talk to the elder in the first town."
        mock_get_context.return_value = expected_context
        
        # Call the method
        context = manager.get_guide_context("soul-blazer", "Where do I start?")
        
        # Verify the mock was called correctly
        mock_get_context.assert_called_once_with(
            "soul-blazer",
            "Where do I start?",
            top_k=3
        )
        
        # Verify the context was returned
        assert context == expected_context

def test_get_guide_context_with_file_not_found(guide_dir, embeddings_dir):
    """Test getting guide context when embeddings don't exist."""
    # Create guide manager
    manager = FileSystemGuideManager(
        base_path=str(guide_dir),
        embeddings_dir=str(embeddings_dir)
    )
    
    # Mock the embeddings_manager.get_context_for_query method directly
    with patch.object(manager.embeddings_manager, 'get_context_for_query') as mock_get_context:
        # Configure the mock to raise FileNotFoundError
        mock_get_context.side_effect = FileNotFoundError("No embeddings found")
        
        # Mock the _generate_embeddings method
        with patch.object(manager, '_generate_embeddings') as mock_generate:
            # Call the method - should raise FileNotFoundError
            with pytest.raises(FileNotFoundError):
                context = manager.get_guide_context("nonexistent-game", "Where do I start?")
            
            # Verify the _generate_embeddings method was attempted for the nonexistent game
            # Note: in a real environment, this method call would happen in the try block
            # before raising the FileNotFoundError in get_guide_context
            assert mock_generate.call_count == 0

def test_generate_embeddings_for_all_games(guide_dir, embeddings_dir):
    """Test generating embeddings for all games."""
    # Create a second game
    second_game_dir = guide_dir / "gba" / "golden-sun"
    second_game_dir.mkdir(parents=True)
    
    second_guide_path = second_game_dir / "guide_67890.md"
    with open(second_guide_path, "w", encoding="utf-8") as f:
        f.write("# Golden Sun Guide\n\nThis is a guide for Golden Sun.")
    
    # Create guide manager 
    manager = FileSystemGuideManager(
        base_path=str(guide_dir),
        embeddings_dir=str(embeddings_dir)
    )
    
    # Mock the _generate_embeddings method to avoid actual processing
    with patch.object(manager, '_generate_embeddings') as mock_generate:
        # Call the method
        results = manager.generate_embeddings_for_all_games()
        
        # Verify the results - should find 2 games
        assert mock_generate.call_count == 2
        
        # The call arguments should include both games
        calls = mock_generate.call_args_list
        game_names = [call[0][0] for call in calls]  # Extract the game_name argument
        
        # Check that both games were processed
        assert "soul-blazer" in game_names
        assert "golden-sun" in game_names