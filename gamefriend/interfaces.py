"""
Core interfaces for GameFriend components.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict

class GuideManager(ABC):
    """Interface for managing game guides."""
    
    @abstractmethod
    def download(self, url: str, output_path: Optional[str] = None) -> str:
        """Download a guide from GameFAQs.
        
        Args:
            url: The GameFAQs guide URL
            output_path: Optional path to save the guide
            
        Returns:
            The path where the guide was saved
            
        Raises:
            ValueError: If the URL is invalid
            Exception: If download fails
        """
        pass

    @abstractmethod
    def list_games(self) -> List[Dict[str, str]]:
        """List all games that have guides available.
        
        Returns:
            List of dictionaries containing game information
            Each dict has keys: name, platform
        """
        pass
        
    @abstractmethod
    def get_guide_context(self, game_name: str, query: str, top_k: int = 3) -> str:
        """Get relevant guide context for a query.
        
        Args:
            game_name: Name of the game
            query: The query to find relevant context for
            top_k: Number of top chunks to return
            
        Returns:
            Formatted string with relevant guide excerpts
            
        Raises:
            FileNotFoundError: If no embeddings found for the game
        """
        pass

class ChatSession(ABC):
    """Interface for chat sessions with GameFriend."""
    
    @abstractmethod
    def start(self) -> None:
        """Start the chat session."""
        pass

    @abstractmethod
    def send_message(self, message: str) -> str:
        """Send a message and get response.
        
        Args:
            message: The user's message
            
        Returns:
            The AI's response
            
        Raises:
            Exception: If chat fails
        """
        pass 