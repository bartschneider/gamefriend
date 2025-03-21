import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

logger = logging.getLogger(__name__)


class MistralClientWrapper:
    def __init__(self):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable is not set")
        self.client = MistralClient(api_key=api_key)
        self.model = "mistral-small"  # Using mistral-small instead of mistral-tiny

    def create_embeddings(self, text: str) -> List[float]:
        """Create embeddings for a piece of text."""
        try:
            response = self.client.embeddings(
                model="mistral-embed", input=text  # Using mistral-embed for embeddings
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            raise

    def chat_with_context(
        self, question: str, context: str, chat_history: str = ""
    ) -> str:
        """Generate a response using the provided context and chat history."""
        try:
            # Construct the system prompt with context and chat history
            system_prompt = f"""You are a helpful gaming assistant. Use the following guide content to answer the user's question.
            If the answer cannot be found in the guide, say so. Do not make up information.
            
            Guide content:
            {context}
            
            Previous conversation:
            {chat_history}
            
            Instructions:
            1. Use the guide content to provide accurate information about the game
            2. If the information isn't in the guide, say so
            3. Keep your responses concise but informative
            4. If the user is asking about game progress or state, help track that
            5. If the user is asking about specific items, locations, or strategies, provide detailed guidance
            """

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=question),
            ]

            response = self.client.chat(model=self.model, messages=messages)

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error in chat_with_context: {str(e)}")
            raise
