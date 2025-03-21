"""
Game companion class for CLI interactions.
"""

from typing import Optional

from . import ChatManager


class GameCompanion:
    """A wrapper around ChatManager for CLI interactions."""

    def __init__(self, game_name: str, api_key: str, verbose: bool = False):
        """Initialize the game companion."""
        self.game_name = game_name
        self.api_key = api_key
        self.verbose = verbose
        self.chat_manager = ChatManager()

    def chat(self, message: str) -> str:
        """Process a chat message and return a response."""
        # Create game context
        game_context = {
            "name": self.game_name,
            "platform": self._get_platform(),  # This would need to be determined somehow
        }

        try:
            response = self.chat_manager.process_message(message, game_context)
            return response
        except Exception as e:
            if self.verbose:
                return f"Error: {str(e)}\nTry asking something else."
            return "I encountered an error. Try asking something else."

    def _get_platform(self) -> str:
        """Get the platform for the current game."""
        # For now, we'll try to find the game in the guides directory
        guides_dir = self.chat_manager.guides_dir
        if not guides_dir.exists():
            return "unknown"

        # Look for the game in any platform directory
        for platform_dir in guides_dir.iterdir():
            if not platform_dir.is_dir():
                continue

            game_dir = platform_dir / self.game_name
            if game_dir.exists() and game_dir.is_dir():
                return platform_dir.name

        return "unknown" 