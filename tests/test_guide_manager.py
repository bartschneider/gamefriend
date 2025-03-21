"""
Tests for guide manager implementation.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from gamefriend.guide_manager import FileSystemGuideManager

@pytest.fixture
def mock_scraper():
    with patch("gamefriend.guide_manager.GameFAQsScraper") as mock:
        instance = mock.return_value
        instance.download_guide.return_value = ("content", Path("guides/test/game/guide.md"))
        yield instance

@pytest.fixture
def guide_manager(tmp_path, mock_scraper):
    return FileSystemGuideManager(str(tmp_path))

def test_download_guide(guide_manager, mock_scraper):
    """Test guide download functionality."""
    url = "https://example.com/guide"
    path = guide_manager.download(url)
    assert path == "guides/test/game/guide.md"
    mock_scraper.download_guide.assert_called_once_with(url)

def test_list_games_empty(guide_manager):
    """Test listing games when no guides exist."""
    games = guide_manager.list_games()
    assert len(games) == 0

def test_list_games_with_guides(tmp_path):
    """Test listing games with existing guides."""
    # Create test directory structure
    platform_dir = tmp_path / "test_platform"
    game_dir = platform_dir / "test_game"
    game_dir.mkdir(parents=True)
    (game_dir / "guide_1.md").touch()
    
    manager = FileSystemGuideManager(str(tmp_path))
    games = manager.list_games()
    
    assert len(games) == 1
    assert games[0]["name"] == "test_game"
    assert games[0]["platform"] == "test_platform" 