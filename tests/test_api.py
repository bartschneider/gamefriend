from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from gamefriend.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_chat_endpoint_no_game_context(client):
    """Test chat endpoint without game context."""
    response = client.post("/api/chat", json={"message": "Hello"})
    assert response.status_code == 200
    assert "Please select a game first" in response.json()["response"]


def test_chat_endpoint_with_game_context(client):
    """Test chat endpoint with game context."""
    with patch("gamefriend.api.chat_manager.process_message") as mock_process:
        mock_process.return_value = "Test response"
        
        response = client.post(
            "/api/chat",
            json={
                "message": "Hello",
                "game_context": {"platform": "gba", "name": "test-game"}
            }
        )
        
        assert response.status_code == 200
        assert response.json()["response"] == "Test response"
        mock_process.assert_called_once_with(
            "Hello",
            {"platform": "gba", "name": "test-game"}
        )


def test_chat_endpoint_error_handling(client):
    """Test chat endpoint error handling."""
    with patch("gamefriend.api.chat_manager.process_message") as mock_process:
        mock_process.side_effect = Exception("Test error")
        
        response = client.post(
            "/api/chat",
            json={
                "message": "Hello",
                "game_context": {"platform": "gba", "name": "test-game"}
            }
        )
        
        assert response.status_code == 500
        assert "Test error" in response.json()["detail"]


def test_chat_endpoint_invalid_request(client):
    """Test chat endpoint with invalid request body."""
    response = client.post("/api/chat", json={})
    assert response.status_code == 422  # Validation error 