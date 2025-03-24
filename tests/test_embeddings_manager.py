"""
Tests for the embeddings manager.
"""
import os
import json
import tempfile
from pathlib import Path
import shutil
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from gamefriend.embeddings_manager import EmbeddingsManager

# Sample test data
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
def guide_file(temp_dir):
    """Create a temporary guide file for testing."""
    guide_dir = temp_dir / "guides" / "snes" / "soul-blazer"
    guide_dir.mkdir(parents=True)
    
    guide_path = guide_dir / "guide_12345.md"
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(SAMPLE_GUIDE_CONTENT)
    
    return guide_path

@pytest.fixture
def embeddings_dir(temp_dir):
    """Create a temporary directory for embeddings."""
    embed_dir = temp_dir / "data" / "embeddings"
    embed_dir.mkdir(parents=True)
    return embed_dir

def test_init_embeddings_manager():
    """Test initialization of the embeddings manager."""
    manager = EmbeddingsManager(verbose=False)
    assert manager.model_name == "all-MiniLM-L6-v2"
    assert manager.chunk_size == 500
    assert manager.chunk_overlap == 50
    assert manager.embedding_dim > 0

def test_chunk_text():
    """Test text chunking functionality."""
    manager = EmbeddingsManager(chunk_size=500, chunk_overlap=50)  # Use a larger chunk size for the test
    chunks = manager._chunk_text(SAMPLE_GUIDE_CONTENT, "test.md")
    
    assert len(chunks) > 0
    assert all("text" in chunk for chunk in chunks)
    assert all("source" in chunk for chunk in chunks)

def test_process_guide_file(guide_file):
    """Test processing a guide file."""
    manager = EmbeddingsManager()
    chunks, embeddings = manager.process_guide_file(guide_file)
    
    assert len(chunks) > 0
    assert embeddings.shape[0] == len(chunks)
    assert embeddings.shape[1] == manager.embedding_dim

def test_save_and_load_embeddings(embeddings_dir):
    """Test saving and loading embeddings."""
    manager = EmbeddingsManager(embeddings_dir=embeddings_dir)
    
    # Create sample data
    chunks = [{"text": "Sample text", "source": "test.md"}]
    embeddings = np.random.random((1, manager.embedding_dim))
    
    # Save embeddings
    saved_path = manager.save_embeddings("test-game", chunks, embeddings)
    assert saved_path.exists()
    
    # Load embeddings
    loaded_chunks, loaded_embeddings = manager.load_embeddings("test-game")
    assert len(loaded_chunks) == len(chunks)
    assert np.array_equal(loaded_embeddings, embeddings)

def test_build_and_search_index(embeddings_dir):
    """Test building a FAISS index and searching."""
    manager = EmbeddingsManager(embeddings_dir=embeddings_dir)
    
    # Create sample data
    chunks = [
        {"text": "This is about a sword and magic", "source": "test1.md"},
        {"text": "Information about the mountain area", "source": "test2.md"},
        {"text": "How to defeat the boss in the dungeon", "source": "test3.md"}
    ]
    
    # Get the actual embedding dimension from the model
    embed_dim = manager.embedding_dim
    
    # Mock the encode method to return predictable embeddings with correct dimension
    with patch.object(manager.model, 'encode') as mock_encode:
        # Create embeddings that will match "sword" query to first chunk with correct dimension
        embeddings = np.zeros((3, embed_dim))
        # Make the first embedding have high values in first few dimensions
        embeddings[0, 0:3] = [0.9, 0.1, 0.1]  # Sword chunk
        embeddings[1, 0:3] = [0.1, 0.9, 0.1]  # Mountain chunk
        embeddings[2, 0:3] = [0.1, 0.1, 0.9]  # Dungeon chunk
        
        query_embedding = np.zeros((1, embed_dim))
        query_embedding[0, 0:3] = [0.9, 0.1, 0.1]  # Similar to sword chunk
        
        mock_encode.side_effect = [
            embeddings,  # For initial encoding
            query_embedding  # For query "sword"
        ]
        
        # Save embeddings
        manager.save_embeddings("test-game", chunks, embeddings)
        
        # Mock load_embeddings to return our test data
        with patch.object(manager, 'load_embeddings') as mock_load:
            mock_load.return_value = (chunks, embeddings)
            
            # Test search
            results = manager.search("test-game", "sword")
            assert len(results) > 0
            assert "sword" in results[0]["text"].lower()

def test_process_game_guides(temp_dir):
    """Test processing all guides for a game."""
    # Create multiple guide files
    guides_dir = temp_dir / "guides"
    game_dir = guides_dir / "snes" / "soul-blazer"
    game_dir.mkdir(parents=True)
    
    guide1 = game_dir / "guide_12345.md"
    guide2 = game_dir / "guide_67890.md"
    
    with open(guide1, "w", encoding="utf-8") as f:
        f.write(SAMPLE_GUIDE_CONTENT)
    
    with open(guide2, "w", encoding="utf-8") as f:
        f.write(SAMPLE_GUIDE_CONTENT + "\n\n## Additional Content\nThis is a different guide.")
    
    # Create embeddings manager with the temp directory
    embeddings_dir = temp_dir / "data" / "embeddings"
    manager = EmbeddingsManager(embeddings_dir=embeddings_dir)
    
    # Process guides
    result_path = manager.process_game_guides("Soul Blazer", "SNES", guides_dir=guides_dir)
    
    # Check that embeddings were saved
    assert result_path.exists()
    
    # Load the saved data
    with open(result_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Verify content
    assert "chunks" in data
    assert "embeddings" in data
    assert len(data["chunks"]) > 0
    assert len(data["embeddings"]) == len(data["chunks"])

def test_get_context_for_query(embeddings_dir):
    """Test getting formatted context for a query."""
    manager = EmbeddingsManager(embeddings_dir=embeddings_dir)
    
    # Create sample data with different relevance scores
    chunks = [
        {"text": "This is about a sword and magic", "source": "test1.md"},
        {"text": "Information about the mountain area", "source": "test2.md"},
        {"text": "How to defeat the boss in the dungeon", "source": "test3.md"}
    ]
    
    # Mock the search method
    with patch.object(manager, 'search') as mock_search:
        # Return chunks with added score
        mock_results = [
            {**chunks[0], "score": 0.95},
            {**chunks[2], "score": 0.75},
            {**chunks[1], "score": 0.60}
        ]
        mock_search.return_value = mock_results
        
        # Get context
        context = manager.get_context_for_query("test-game", "sword and dungeon")
        
        # Verify context format
        assert "test1.md" in context
        assert "test3.md" in context
        assert "relevance: 0.95" in context
        assert "sword and magic" in context
        assert "boss in the dungeon" in context