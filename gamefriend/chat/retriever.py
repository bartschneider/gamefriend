"""
Retrieval-Augmented Generation (RAG) implementation for game guides.
"""

from pathlib import Path
from typing import List, Dict, Optional
import json
import numpy as np
from mistralai.client import MistralClient
from mistralai.models.embeddings import EmbeddingResponse
import tiktoken

class GuideRetriever:
    """Handles retrieval of relevant guide content for RAG."""
    
    def __init__(
        self,
        game_name: str,
        api_key: str,
        guides_dir: Optional[Path] = None,
        embeddings_dir: Optional[Path] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        verbose: bool = False
    ):
        """Initialize the guide retriever.
        
        Args:
            game_name: Name of the game
            api_key: Mistral API key
            guides_dir: Directory containing game guides
            embeddings_dir: Directory to store embeddings
            chunk_size: Maximum size of text chunks in tokens
            chunk_overlap: Number of tokens to overlap between chunks
            verbose: Whether to print debug information
        """
        self.game_name = game_name.lower().replace(" ", "-")  # Normalize game name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.verbose = verbose
        
        # Set up directories
        self.guides_dir = guides_dir or Path("guides")
        self.embeddings_dir = embeddings_dir or Path("data/embeddings")
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Mistral client
        self.client = MistralClient(api_key=api_key)
        
        # Load or create embeddings
        self.embeddings_file = self.embeddings_dir / f"{self.game_name}_embeddings.json"
        self.chunks: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None
        self._load_or_create_embeddings()
    
    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        encoding = tiktoken.get_encoding("cl100k_base")  # Compatible with Mistral
        return len(encoding.encode(text))
    
    def _chunk_text(self, text: str, filepath: str) -> List[Dict]:
        """Split text into overlapping chunks."""
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        chunks = []
        
        i = 0
        while i < len(tokens):
            # Get chunk tokens
            chunk_tokens = tokens[i:i + self.chunk_size]
            
            # Decode chunk
            chunk_text = encoding.decode(chunk_tokens)
            
            # Store chunk with metadata
            chunks.append({
                "text": chunk_text,
                "source": filepath,
                "start_token": i,
                "end_token": i + len(chunk_tokens)
            })
            
            # Move to next chunk, accounting for overlap
            i += self.chunk_size - self.chunk_overlap
        
        return chunks
    
    def _find_guide_files(self) -> List[Path]:
        """Find all guide files for the game."""
        # First try the game-specific directory structure
        game_dir = self.guides_dir / "snes" / self.game_name  # TODO: Make platform configurable
        if game_dir.exists():
            guide_files = list(game_dir.glob("guide_*.md"))
            if guide_files:
                if self.verbose:
                    print(f"Found {len(guide_files)} guides in {game_dir}")
                return guide_files
        
        # Fallback to searching all directories
        guide_files = []
        for platform_dir in self.guides_dir.iterdir():
            if platform_dir.is_dir():
                for game_dir in platform_dir.iterdir():
                    if game_dir.is_dir() and self.game_name in game_dir.name.lower():
                        guide_files.extend(game_dir.glob("guide_*.md"))
        
        if guide_files:
            if self.verbose:
                print(f"Found {len(guide_files)} guides in various directories")
            return guide_files
        
        raise ValueError(f"No guides found for game: {self.game_name}")
    
    def _get_embeddings_batched(self, texts: List[str], batch_size: int = 8) -> np.ndarray:
        """Get embeddings for texts in batches to avoid token limits.
        
        Args:
            texts: List of text chunks to get embeddings for
            batch_size: Number of chunks to process in each batch
            
        Returns:
            Array of embeddings
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            if self.verbose:
                print(f"Getting embeddings for batch {i//batch_size + 1} of {(len(texts) + batch_size - 1)//batch_size}")
            
            response = self.client.embeddings(
                model="mistral-embed",
                input=batch
            )
            
            all_embeddings.extend([e.embedding for e in response.data])
        
        return np.array(all_embeddings)
    
    def _load_or_create_embeddings(self):
        """Load existing embeddings or create new ones from guides."""
        if self.embeddings_file.exists():
            # Load existing embeddings
            with open(self.embeddings_file, "r") as f:
                data = json.load(f)
                self.chunks = data["chunks"]
                self.embeddings = np.array(data["embeddings"])
            if self.verbose:
                print(f"Loaded {len(self.chunks)} existing chunks with embeddings")
            return
        
        # Find all guide files for this game
        guide_files = self._find_guide_files()
        
        # Process each guide
        all_chunks = []
        for guide_file in guide_files:
            if self.verbose:
                print(f"Processing guide: {guide_file}")
            
            # Read and chunk the guide
            with open(guide_file, "r") as f:
                text = f.read()
            chunks = self._chunk_text(text, str(guide_file))
            all_chunks.extend(chunks)
        
        if not all_chunks:
            raise ValueError(f"No content found in guides for game: {self.game_name}")
        
        # Get embeddings for all chunks in batches
        texts = [chunk["text"] for chunk in all_chunks]
        if self.verbose:
            print(f"Generating embeddings for {len(texts)} chunks...")
        
        self.embeddings = self._get_embeddings_batched(texts)
        self.chunks = all_chunks
        
        # Save to file
        with open(self.embeddings_file, "w") as f:
            json.dump({
                "chunks": self.chunks,
                "embeddings": self.embeddings.tolist()
            }, f)
        
        if self.verbose:
            print(f"Created and saved {len(self.chunks)} chunks with embeddings")
    
    def get_relevant_chunks(self, query: str, n_results: int = 3) -> List[Dict]:
        """Get the most relevant chunks for a query.
        
        Args:
            query: The query to find relevant chunks for
            n_results: Number of chunks to return
            
        Returns:
            List of relevant chunks with their text and metadata
        """
        # Get query embedding
        query_embedding_response = self.client.embeddings(
            model="mistral-embed",
            input=[query]
        )
        query_embedding = np.array(query_embedding_response.data[0].embedding)
        
        # Calculate similarities
        similarities = np.dot(self.embeddings, query_embedding)
        
        # Get top chunks
        top_indices = np.argsort(similarities)[-n_results:][::-1]
        
        return [self.chunks[i] for i in top_indices]
    
    def get_context_for_query(self, query: str, max_tokens: int = 2000) -> str:
        """Get formatted context from relevant chunks for a query.
        
        Args:
            query: The query to find relevant context for
            max_tokens: Maximum number of tokens to include in context
            
        Returns:
            Formatted string containing relevant context
        """
        chunks = self.get_relevant_chunks(query)
        context_parts = []
        total_tokens = 0
        
        for chunk in chunks:
            chunk_tokens = self._count_tokens(chunk["text"])
            if total_tokens + chunk_tokens > max_tokens:
                break
                
            context_parts.append(f"From {chunk['source']}:\n{chunk['text']}\n")
            total_tokens += chunk_tokens
        
        return "\n".join(context_parts) 