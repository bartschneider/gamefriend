"""
Chat session implementation.
"""
from typing import Optional
from .interfaces import ChatSession
from .chat.companion import GameCompanion
import logging

logger = logging.getLogger(__name__)

class InteractiveChatSession(ChatSession):
    """Interactive chat session with GameFriend."""
    
    def __init__(self, game_name: str, api_key: str, verbose: bool = False):
        """Initialize the chat session.
        
        Args:
            game_name: Name of the game to chat about
            api_key: Mistral API key
            verbose: Enable verbose logging
        """
        self.game_name = game_name
        self.companion = GameCompanion(game_name, api_key, verbose)
        
    def start(self) -> None:
        """Start the chat session."""
        print(f"\nGameFriend - Your AI Gaming Companion for {self.game_name}")
        print("Type 'quit' or 'exit' to end the chat\n")
        
        while True:
            try:
                message = self._get_input()
                if self._should_exit(message):
                    break
                    
                response = self.send_message(message)
                self._display_response(response)
            except KeyboardInterrupt:
                break
            except Exception as e:
                self._handle_error(e)
                
    def send_message(self, message: str) -> str:
        """Send a message and get response.
        
        Args:
            message: The user's message
            
        Returns:
            The AI's response
            
        Raises:
            Exception: If chat fails
        """
        return self.companion.chat(message)
        
    def _get_input(self) -> str:
        """Get input from the user."""
        return input("\nYou: ").strip()
        
    def _should_exit(self, message: str) -> bool:
        """Check if the user wants to exit."""
        return message.lower() in ["quit", "exit"]
        
    def _display_response(self, response: str) -> None:
        """Display the AI's response."""
        print("\nGameFriend:")
        print(response)
        
    def _handle_error(self, error: Exception) -> None:
        """Handle errors during chat."""
        logger.error(f"Error in chat session: {str(error)}")
        print(f"\nError: {str(error)}") 