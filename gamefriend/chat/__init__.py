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

from .mistral_client import MistralClientWrapper

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: datetime


class ChatManager:
    def __init__(self):
        self.guides_dir = Path("guides")
        self.mistral = MistralClientWrapper()
        self.chat_history: Dict[str, List[ChatMessage]] = {}
        self.section_embeddings: Dict[str, List[float]] = {}
        self.max_chunk_length = 8000  # Keep under Mistral's 8192 limit
        self.current_game_id: Optional[str] = None

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
        if (
            not game_context
            or not game_context.get("name")
            or not game_context.get("platform")
        ):
            logger.warning(f"Invalid game context: {game_context}")
            return None

        try:
            # Construct the game directory path from platform and name
            game_path = (
                self.guides_dir / game_context["platform"] / game_context["name"]
            )
            logger.info(f"Looking for guides in: {game_path}")

            # Look for any guide file in the game directory
            guide_files = list(game_path.glob("guide_*.md"))

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
        self, guide_content: str, question: str, top_k: int = 3
    ) -> List[str]:
        """Find the most relevant sections using embeddings."""
        # Split guide into sections if not already done
        sections = self.split_into_sections(guide_content)

        # Get embeddings for all sections if not already cached
        if not self.section_embeddings:
            for section in sections:
                if section not in self.section_embeddings:
                    # Split long sections into chunks
                    chunks = self.chunk_text(section)
                    # Get embeddings for each chunk
                    chunk_embeddings = []
                    for chunk in chunks:
                        try:
                            embedding = self.mistral.create_embeddings(chunk)
                            chunk_embeddings.append(embedding)
                        except Exception as e:
                            logger.error(
                                f"Error creating embeddings for chunk: {str(e)}"
                            )
                            continue

                    if chunk_embeddings:
                        # Average the embeddings of all chunks
                        avg_embedding = np.mean(chunk_embeddings, axis=0)
                        self.section_embeddings[section] = avg_embedding.tolist()

        # Get embedding for the question
        question_embedding = self.mistral.create_embeddings(question)

        # Calculate cosine similarity between question and each section
        similarities = []
        for section, embedding in self.section_embeddings.items():
            similarity = np.dot(question_embedding, embedding) / (
                np.linalg.norm(question_embedding) * np.linalg.norm(embedding)
            )
            similarities.append((similarity, section))

        # Sort by similarity and get top k sections
        similarities.sort(reverse=True)
        return [section for _, section in similarities[:top_k]]

    def process_message(
        self, message: str, game_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process a chat message and return a response."""
        if not game_context:
            return "Please select a game first to start chatting about it."

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

        guide_content = self.get_guide_content(game_context)
        if not guide_content:
            return f"I couldn't find the guide for {game_context.get('name', 'this game')}. Please try importing a guide first."

        try:
            # Find relevant sections based on the question
            relevant_sections = self.find_relevant_sections(guide_content, message)

            if not relevant_sections:
                return f"I couldn't find specific information about that in the guide. Could you try rephrasing your question about {game_context.get('name', 'the game')}?"

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

            # Use Mistral to generate a response based on the context and chat history
            response = self.mistral.chat_with_context(message, context, chat_history)

            # Add assistant response to history
            self.chat_history[game_id].append(
                ChatMessage(
                    role="assistant", content=response, timestamp=datetime.now()
                )
            )

            return response

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return "I encountered an error while processing your question. Please try again."

__all__ = ["ChatManager", "ChatMessage", "MistralClientWrapper"]
