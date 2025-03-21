"""
Tests for core interfaces.
"""
import pytest
from typing import List, Dict
from gamefriend.interfaces import GuideManager, ChatSession

def test_guide_manager_interface():
    """Test that GuideManager interface is properly defined."""
    class TestGuideManager(GuideManager):
        def download(self, url: str, output_path: str = None) -> str:
            return "test/path"
            
        def list_games(self) -> List[Dict[str, str]]:
            return [{"name": "test", "platform": "test"}]
    
    manager = TestGuideManager()
    assert manager.download("test") == "test/path"
    assert len(manager.list_games()) == 1
    assert manager.list_games()[0]["name"] == "test"

def test_chat_session_interface():
    """Test that ChatSession interface is properly defined."""
    class TestChatSession(ChatSession):
        def start(self) -> None:
            pass
            
        def send_message(self, message: str) -> str:
            return "test response"
    
    session = TestChatSession()
    assert session.send_message("test") == "test response"
    session.start()  # Should not raise any exceptions 