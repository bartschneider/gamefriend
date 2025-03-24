"""
Chat functionality for GameFriend.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import json
from pathlib import Path

from .mistral_client import MistralClientWrapper
from ..guide_manager import FileSystemGuideManager
import os

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: datetime


class ChatManager:
    def __init__(self):
        self.guides_dir = Path("guides")
        self.roadmaps_dir = Path("data/roadmaps")
        self.embeddings_dir = Path("data/embeddings")
        self.mistral = MistralClientWrapper()
        self.chat_history: Dict[str, List[ChatMessage]] = {}
        self.max_chunk_length = 8000  # Keep under Mistral's 8192 limit
        self.current_game_id: Optional[str] = None
        
        # Get API key from environment
        api_key = os.environ.get("MISTRAL_API_KEY", "")
        
        # Initialize guide manager with embeddings support
        self.guide_manager = FileSystemGuideManager(
            base_path=str(self.guides_dir),
            embeddings_dir=str(self.embeddings_dir)
        )

    def get_roadmap_for_game(self, game_name: str, platform: str) -> Optional[Dict]:
        """Get the roadmap for a game if it exists."""
        if not game_name:
            return None
            
        # Sanitize game name for filename
        sanitized_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in game_name)
        roadmap_path = self.roadmaps_dir / f"{platform}_{sanitized_name}_roadmap.json"
        
        if not roadmap_path.exists():
            logger.info(f"No roadmap found at {roadmap_path}")
            return None
            
        try:
            with open(roadmap_path, "r") as f:
                roadmap_data = json.load(f)
            logger.info(f"Loaded roadmap for {game_name}")
            return roadmap_data
        except Exception as e:
            logger.error(f"Error loading roadmap: {e}")
            return None
    
    def reset_context(self, game_context: Dict[str, Any]) -> None:
        """Reset the context when switching games."""
        if not game_context or not game_context.get("name") or not game_context.get("platform"):
            return

        game_id = f"{game_context['platform']}/{game_context['name']}"
        
        # Only reset if we're switching to a different game
        if game_id != self.current_game_id:
            # Clear embeddings for the new game
            self.section_embeddings = {}
            self.current_game_id = game_id

    def get_guide_content(self, game_context: Dict[str, Any]) -> Optional[str]:
        """Get the content of the guide for the given game."""
        if not game_context:
            logger.warning("Game context is missing")
            return None
            
        # Handle case where game_context might be a string
        if isinstance(game_context, str):
            game_name = game_context
            platform = "unknown"
            logger.info(f"Converting string game context '{game_name}' to dictionary")
            game_context = {"name": game_name, "platform": platform}
            
        if not game_context.get("name"):
            logger.warning(f"Game name is missing in context: {game_context}")
            return None
            
        # Set a default platform if missing
        if not game_context.get("platform"):
            game_context["platform"] = "unknown"
            logger.info(f"Using default platform 'unknown' for {game_context['name']}")

        try:
            # Construct the game directory path from platform and name
            # Normalize the platform: look for common platforms like snes, nes, pc, etc.
            platform = game_context["platform"].lower()
            if platform != "snes" and platform != "pc":
                # Check if path exists with current platform, otherwise use existing ones
                possible_platforms = [p.name for p in self.guides_dir.iterdir() if p.is_dir()]
                logger.info(f"Available platforms: {possible_platforms}")
                
                # If original platform isn't in the list, default to first available
                if platform not in possible_platforms and possible_platforms:
                    platform = possible_platforms[0]
                    logger.info(f"Using first available platform: {platform}")
            
            # Check for guides directory
            if not self.guides_dir.exists():
                logger.error(f"Guides directory not found: {self.guides_dir}")
                return None
                
            # List available games in all platforms
            all_games = []
            for platform_dir in self.guides_dir.iterdir():
                if platform_dir.is_dir():
                    for game_dir in platform_dir.iterdir():
                        if game_dir.is_dir():
                            all_games.append((platform_dir.name, game_dir.name))
            
            logger.info(f"All available games: {all_games}")
                
            # Construct the path
            game_name = game_context["name"]
            game_path = self.guides_dir / platform / game_name
            logger.info(f"Looking for guides in: {game_path}")

            # Look for any guide file in the game directory
            guide_files = list(game_path.glob("guide_*.md"))

            if not guide_files:
                logger.warning(f"No guide files found for exact path: {game_path}")
                
                # Try fallback: search for any game directory that contains the name
                game_name_lower = game_name.lower()
                logger.info(f"Trying fallback search for name: {game_name_lower}")
                
                for platform_dir, game_dir_name in all_games:
                    if game_name_lower in game_dir_name.lower() or game_dir_name.lower() in game_name_lower:
                        logger.info(f"Found similar game: {platform_dir}/{game_dir_name}")
                        fallback_path = self.guides_dir / platform_dir / game_dir_name
                        fallback_files = list(fallback_path.glob("guide_*.md"))
                        
                        if fallback_files:
                            logger.info(f"Using fallback guide files: {fallback_files}")
                            guide_files = fallback_files
                            game_path = fallback_path
                            break
                
                if not guide_files:
                    logger.warning(f"No guide files found for game: {game_path}")
                    return None

            # Read all guide files and combine their content
            all_content = []
            for guide_file in guide_files:
                content = guide_file.read_text(encoding="utf-8")
                all_content.append(content)

            combined_content = "\n\n".join(all_content)
            logger.info(f"Successfully loaded guide content for game: {game_path}")
            return combined_content

        except Exception as e:
            logger.error(f"Error loading guide content: {str(e)}")
            return None

    def split_into_sections(self, guide_content: str) -> List[str]:
        """Split guide content into meaningful sections."""
        # Split on headers and other major section breaks
        sections = re.split(
            r"^#{1,6}\s+|^Q\.|^A\.|^\[.*?\]", guide_content, flags=re.MULTILINE
        )

        # Clean up sections
        sections = [s.strip() for s in sections if s.strip()]

        # Combine very short sections with their neighbors
        combined_sections = []
        current_section = ""

        for section in sections:
            if (
                len(section.split()) < 10 and current_section
            ):  # If section is very short
                current_section += "\n" + section
            else:
                if current_section:
                    combined_sections.append(current_section)
                current_section = section

        if current_section:
            combined_sections.append(current_section)

        return combined_sections

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks that are under the maximum length."""
        chunks = []
        current_chunk = []
        current_length = 0

        # Split into sentences to avoid breaking mid-sentence
        sentences = re.split(r"(?<=[.!?])\s+", text)

        for sentence in sentences:
            sentence_length = len(sentence)

            if current_length + sentence_length > self.max_chunk_length:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def find_relevant_sections(
        self, game_name: str, question: str, top_k: int = 3
    ) -> List[str]:
        """Find the most relevant sections using local embeddings.
        
        Args:
            game_name: Name of the game
            question: The question to find relevant context for
            top_k: Number of top results to return
            
        Returns:
            List of relevant sections
        """
        try:
            # Use the guide manager to get relevant context
            context = self.guide_manager.get_guide_context(game_name, question, top_k=top_k)
            
            # Split context into sections if it's a single string
            if isinstance(context, str):
                # Each section in the context is separated by "From [source]:" markers
                sections = re.split(r'From\s+[^:]+:', context)
                # Remove empty sections and clean up
                sections = [s.strip() for s in sections if s.strip()]
                return sections
            
            # If no sections found or context is empty
            if not sections:
                logger.warning(f"No relevant sections found for question: {question}")
                return []
                
            return sections
            
        except Exception as e:
            logger.error(f"Error finding relevant sections: {str(e)}")
            return []

    def process_message(
        self, message: str, game_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process a chat message and return a response."""
        if not game_context:
            return "Please select a game first to start chatting about it."

        # Handle case where game_context is a string (from frontend)
        if isinstance(game_context, str):
            game_context = {"name": game_context, "platform": "unknown"}
        elif isinstance(game_context, dict) and not game_context.get("platform"):
            game_context["platform"] = "unknown"
            
        logger.info(f"Processing message with game context: {game_context}")

        # Reset context if switching games
        self.reset_context(game_context)

        # Initialize chat history for this game if not exists
        game_id = f"{game_context['platform']}/{game_context['name']}"
        if game_id not in self.chat_history:
            self.chat_history[game_id] = []

        # Add user message to history
        self.chat_history[game_id].append(
            ChatMessage(role="user", content=message, timestamp=datetime.now())
        )

        try:
            # Use game name for finding relevant sections
            game_name = game_context.get('name', '')
            if not game_name:
                return "Please specify a game name to chat about."
                
            # Find relevant sections using local embeddings
            relevant_sections = self.find_relevant_sections(game_name, message)

            if not relevant_sections:
                # If no guide found, check if it exists in the filesystem
                try:
                    # This will try to find and generate embeddings if not exists
                    self.guide_manager.get_guide_context(game_name, message)
                    # Try again after generating embeddings
                    relevant_sections = self.find_relevant_sections(game_name, message)
                except FileNotFoundError:
                    return f"I couldn't find the guide for {game_name}. Please try importing a guide first."
            
            if not relevant_sections:
                return f"I couldn't find specific information about that in the guide. Could you try rephrasing your question about {game_name}?"

            # Combine relevant sections with chat history
            context = "\n\n".join(relevant_sections)
            chat_history = "\n".join(
                [
                    f"{msg.role}: {msg.content}"
                    for msg in self.chat_history[game_id][
                        -5:
                    ]  # Last 5 messages for context
                ]
            )

            # Get roadmap if available
            roadmap_data = self.get_roadmap_for_game(game_context.get("name"), game_context.get("platform", "unknown"))
            
            # Use Mistral to generate a response based on the context, roadmap and chat history
            response = self.mistral.chat_with_context(
                question=message, 
                context=context, 
                chat_history=chat_history,
                game_context=game_context
            )

            # Add assistant response to history
            self.chat_history[game_id].append(
                ChatMessage(
                    role="assistant", content=response, timestamp=datetime.now()
                )
            )

            return response

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return f"I encountered an error while processing your question: {str(e)}. Please try again."

__all__ = ["ChatManager", "ChatMessage", "MistralClientWrapper"]
