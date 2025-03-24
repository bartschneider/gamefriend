import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

# Import from v1 Mistral client API
from mistralai import Mistral

logger = logging.getLogger(__name__)


class MistralClientWrapper:
    def __init__(self):
        # Get API key with better error handling
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            logger.error("MISTRAL_API_KEY environment variable is not set!")
            raise ValueError("MISTRAL_API_KEY environment variable is not set")
            
        # List of valid models in order of preference
        self.valid_models = [
            "mistral-medium-latest",  # Best option for complex tasks
            "mistral-small-latest",  # Latest version
            "mistral-small",  # Original version
            "open-mistral-7b"  # Open model version
        ]
        
        try:
            # Create the client using the new API
            self.client = Mistral(api_key=api_key)
            
            # Try to get available models
            available_models = []
            try:
                # In v1 API, list_models is a different endpoint
                models_response = self.client.models.list()
                
                # Extract model IDs
                available_models = [model.id for model in models_response.data]
                logger.info(f"Available Mistral models: {available_models}")
            except Exception as e:
                logger.warning(f"Could not retrieve available models: {e}")
                # Continue with default model
                
            # Choose the best available model
            self.model = None
            if available_models:
                for model in self.valid_models:
                    if model in available_models:
                        self.model = model
                        logger.info(f"Selected Mistral model: {self.model}")
                        break
                        
            # If no matching models found, use the default
            if not self.model:
                logger.warning("No preferred models found, defaulting to mistral-small-latest")
                self.model = "mistral-small-latest"
                
        except Exception as e:
            logger.error(f"Error initializing Mistral client: {e}")
            # Try a fallback initialization and model
            self.client = Mistral(api_key=api_key)
            self.model = "mistral-small-latest"

    def create_embeddings(self, text: str) -> List[float]:
        """Create embeddings for a piece of text."""
        try:
            # In v1 API, the parameter is 'inputs' (plural), not 'input'
            # And it expects a list of strings, even for a single text
            response = self.client.embeddings.create(
                model="mistral-embed", 
                inputs=[text]  # Note: Wrapped in a list as required by v1 API
            )
            
            # Log response type for debugging
            logger.info(f"Embeddings response type: {type(response)}")
            
            # Extract embeddings from v1 format
            # V1 API returns an array of embeddings in 'data'
            if hasattr(response, 'data') and len(response.data) > 0:
                if hasattr(response.data[0], 'embedding'):
                    return response.data[0].embedding
                elif hasattr(response.data[0], 'vector'):  # Some versions use 'vector' instead
                    return response.data[0].vector
                    
            # V1 typical format with direct access to embeddings
            if hasattr(response, 'embeddings') and response.embeddings:
                return response.embeddings[0]
                
            # Dictionary fallback approaches
            if isinstance(response, dict):
                # Try known dictionary structures
                if 'data' in response and len(response['data']) > 0:
                    if 'embedding' in response['data'][0]:
                        return response['data'][0]['embedding']
                    elif 'vector' in response['data'][0]:
                        return response['data'][0]['vector']
                
                # Direct embeddings array
                if 'embeddings' in response and len(response['embeddings']) > 0:
                    return response['embeddings'][0]
                    
                # Debug what we received
                logger.error(f"Unknown embeddings response format with keys: {list(response.keys())}")
                
            # If we get here, we couldn't parse the response
            logger.error(f"Failed to extract embeddings from response: {response}")
            raise ValueError(f"Could not extract embeddings from response: {response}")
                
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            raise

    def chat_with_context(
        self, question: str, context: str, chat_history: str = "", game_context: Any = None
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
            2. If the information isn't in the guide, say so clearly. DO NOT make up facts or invent content that isn't in the provided materials.
            3. Keep your responses concise but informative
            4. If the user is asking about game progress or state, help track that
            5. If the user is asking about specific items, locations, or strategies, provide detailed guidance
            6. Use markdown formatting to structure your responses clearly
            7. When discussing key game elements like locations, items or characters, use **bold** formatting
            """

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ]

            # Use the new chat completion API
            response = self.client.chat.complete(
                model=self.model, 
                messages=messages
            )

            # Log the response type and structure for debugging
            logger.info(f"Mistral API response type: {type(response)}")
            
            # Extract response content based on the Mistral API v1 format
            try:
                # Option 1: Direct content attribute (v1.x style)
                if hasattr(response, 'content') and response.content is not None:
                    return response.content
                
                # Option 2: Through choices.message.content (v0.x compatibility)
                if hasattr(response, 'choices') and hasattr(response.choices[0], 'message'):
                    message = response.choices[0].message
                    if hasattr(message, 'content'):
                        return message.content
                
                # Option 3: Dictionary with direct content
                if isinstance(response, dict):
                    if 'content' in response and response['content'] is not None:
                        return response['content']
                    
                    # Option 4: Dictionary via choices (v0.x compatibility)
                    if 'choices' in response and len(response['choices']) > 0:
                        message = response['choices'][0].get('message', {})
                        if 'content' in message:
                            return message['content']
                
                # Log the issue for debugging
                logger.warning(f"Unexpected response format: {type(response)}")
                if isinstance(response, dict):
                    logger.warning(f"Response keys: {list(response.keys())}")
                    logger.warning(f"Response sample: {str(response)[:200]}...")
                
                # Last resort - try to convert to string safely
                return str(response)
                
            except Exception as e:
                logger.error(f"Error parsing response: {e}")
                logger.error(f"Response type: {type(response)}")
                # Return placeholder when extraction fails
                return "Unable to extract response from Mistral API"

        except Exception as e:
            logger.error(f"Error in chat_with_context: {str(e)}")
            raise
