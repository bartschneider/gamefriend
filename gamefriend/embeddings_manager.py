"""
Embeddings management for guide retrieval.

This module provides functionality for:
1. Loading and managing embedding models
2. Processing and chunking guide text
3. Generating embeddings locally with sentence-transformers
4. Storing and loading pre-computed embeddings
5. Performing similarity search with FAISS
"""

import os
import json
import logging
from typing import List, Dict, Optional, Union, Tuple, Any
from pathlib import Path
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from .models import GameRoadmap

logger = logging.getLogger(__name__)

class EmbeddingsManager:
    """Manages guide embeddings generation and retrieval."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        embeddings_dir: Optional[Path] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 32,
        verbose: bool = False
    ):
        """Initialize the embeddings manager.
        
        Args:
            model_name: Name of the sentence-transformers model to use
            embeddings_dir: Directory to store embeddings
            chunk_size: Maximum size of text chunks in tokens/characters
            chunk_overlap: Number of tokens/characters to overlap between chunks
            batch_size: Number of text chunks to embed in a single batch
            verbose: Whether to print debug information
        """
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.batch_size = batch_size
        self.verbose = verbose
        
        # Set up directories
        self.embeddings_dir = embeddings_dir or Path("data/embeddings")
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded with dimension: {self.embedding_dim}")
        
        # Index cache for loaded games
        self.index_cache: Dict[str, faiss.Index] = {}
        self.chunks_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    def _chunk_text(self, text: str, source: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks.
        
        Args:
            text: The text to chunk
            source: Source identifier (e.g., file path)
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        # Break text into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[Dict[str, Any]] = []
        
        current_chunk: List[str] = []
        current_length = 0
        current_start = 0
        
        for i, paragraph in enumerate(paragraphs):
            # If adding this paragraph would exceed chunk size and we already have content
            if current_length + len(paragraph) > self.chunk_size and current_chunk:
                # Store the current chunk
                chunk_text = "\n\n".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "source": source,
                    "start_idx": current_start,
                    "end_idx": current_start + len(chunk_text),
                    "paragraphs": list(range(current_start, current_start + len(current_chunk)))
                })
                
                # Start a new chunk with overlap
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:]
                current_start = current_start + overlap_start
                current_length = sum(len(p) for p in current_chunk)
            
            # Add the paragraph to the current chunk
            current_chunk.append(paragraph)
            current_length += len(paragraph)
        
        # Add the last chunk if it has content
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "source": source,
                "start_idx": current_start,
                "end_idx": current_start + len(chunk_text),
                "paragraphs": list(range(current_start, current_start + len(current_chunk)))
            })
        
        return chunks
    
    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> np.ndarray:
        """Generate embeddings for a list of text chunks.
        
        Args:
            chunks: List of chunk dictionaries with text field
            
        Returns:
            Numpy array of embeddings
        """
        texts = [chunk["text"] for chunk in chunks]
        
        # Use batching for efficiency
        all_embeddings: List[np.ndarray] = []
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            
            if self.verbose:
                logger.info(f"Embedding batch {i//self.batch_size + 1}/{(len(texts) + self.batch_size - 1)//self.batch_size}")
            
            # Generate embeddings
            batch_embeddings = self.model.encode(batch_texts, show_progress_bar=self.verbose)
            all_embeddings.append(batch_embeddings)
        
        # Combine all batched embeddings
        if not all_embeddings:
            return np.array([])
        return np.vstack(all_embeddings)
    
    def process_guide_file(self, file_path: Union[str, Path]) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        """Process a guide file and generate embeddings.
        
        Args:
            file_path: Path to the guide file
            
        Returns:
            Tuple of (chunks, embeddings)
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise ValueError(f"Guide file not found: {file_path}")
        
        logger.info(f"Processing guide file: {file_path}")
        
        # Read and chunk the guide
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        chunks = self._chunk_text(text, str(file_path))
        logger.info(f"Created {len(chunks)} chunks from guide")
        
        # Generate embeddings
        embeddings = self.generate_embeddings(chunks)
        logger.info(f"Generated embeddings with shape: {embeddings.shape}")
        
        return chunks, embeddings
    
    def save_embeddings(self, game_name: str, chunks: List[Dict[str, Any]], embeddings: np.ndarray) -> Path:
        """Save embeddings to disk.
        
        Args:
            game_name: Name of the game
            chunks: List of text chunks with metadata
            embeddings: Numpy array of embeddings
            
        Returns:
            Path where embeddings were saved
        """
        # Normalize game name
        game_name = game_name.lower().replace(" ", "-")
        embeddings_file = self.embeddings_dir / f"{game_name}_embeddings.json"
        
        # Create data structure
        data = {
            "game_name": game_name,
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "chunks": chunks,
            "embeddings": embeddings.tolist()
        }
        
        # Save to file
        with open(embeddings_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        
        logger.info(f"Saved {len(chunks)} chunks with embeddings to {embeddings_file}")
        return embeddings_file
    
    def load_embeddings(self, game_name: str) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        """Load embeddings from disk.
        
        Args:
            game_name: Name of the game
            
        Returns:
            Tuple of (chunks, embeddings)
            
        Raises:
            FileNotFoundError: If embeddings file doesn't exist
        """
        # Normalize game name
        game_name = game_name.lower().replace(" ", "-")
        embeddings_file = self.embeddings_dir / f"{game_name}_embeddings.json"
        
        if not embeddings_file.exists():
            raise FileNotFoundError(f"No embeddings found for game: {game_name}")
        
        # Load from file
        with open(embeddings_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        chunks = data["chunks"]
        embeddings = np.array(data["embeddings"])
        
        logger.info(f"Loaded {len(chunks)} chunks with embeddings for {game_name}")
        return chunks, embeddings
    
    def build_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """Build a FAISS index for fast similarity search.
        
        Args:
            embeddings: Numpy array of embeddings
            
        Returns:
            FAISS index
        """
        # Create an L2 (Euclidean distance) index
        index = faiss.IndexFlatL2(self.embedding_dim)
        
        # Add embeddings to index
        if len(embeddings) > 0:
            index.add(embeddings.astype(np.float32))
            
        logger.info(f"Built FAISS index with {index.ntotal} vectors")
        return index
    
    def load_or_create_index(self, game_name: str) -> Tuple[faiss.Index, List[Dict[str, Any]]]:
        """Load or create FAISS index for a game.
        
        Args:
            game_name: Name of the game
            
        Returns:
            Tuple of (index, chunks)
            
        Raises:
            FileNotFoundError: If embeddings file doesn't exist
        """
        # Normalize game name
        game_name = game_name.lower().replace(" ", "-")
        
        # Check if already cached
        if game_name in self.index_cache:
            return self.index_cache[game_name], self.chunks_cache[game_name]
        
        # Load embeddings
        chunks, embeddings = self.load_embeddings(game_name)
        
        # Build index
        index = self.build_faiss_index(embeddings)
        
        # Cache for future use
        self.index_cache[game_name] = index
        self.chunks_cache[game_name] = chunks
        
        return index, chunks
    
    def search(self, game_name: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant chunks for a query.
        
        Args:
            game_name: Name of the game
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of relevant chunks with metadata
        """
        # Load or create index
        index, chunks = self.load_or_create_index(game_name)
        
        # Generate query embedding
        query_embedding = self.model.encode([query])[0].reshape(1, -1).astype(np.float32)
        
        # Search
        distances, indices = index.search(query_embedding, top_k)
        
        # Get results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(chunks):  # Ensure valid index
                chunk = chunks[idx].copy()
                chunk["score"] = float(1.0 / (1.0 + distances[0][i]))  # Convert distance to similarity score
                results.append(chunk)
        
        return results
    
    def process_game_guides(self, game_name: str, platform: str, guides_dir: Optional[Path] = None) -> Path:
        """Process all guides for a game and save embeddings.
        
        Args:
            game_name: Name of the game
            platform: Game platform
            guides_dir: Directory containing game guides
            
        Returns:
            Path where embeddings were saved
            
        Raises:
            ValueError: If no guides found for the game
        """
        # Normalize game name
        normalized_name = game_name.lower().replace(" ", "-")
        
        # Set up guides directory
        guides_dir = guides_dir or Path("guides")
        
        # Find all guide files for this game
        game_dir = guides_dir / platform.lower() / normalized_name
        if not game_dir.exists():
            raise ValueError(f"No guide directory found for {game_name} on {platform}")
        
        guide_files = list(game_dir.glob("guide_*.md"))
        if not guide_files:
            raise ValueError(f"No guides found for {game_name} on {platform}")
        
        logger.info(f"Found {len(guide_files)} guides for {game_name}")
        
        # Process all guides
        all_chunks: List[Dict[str, Any]] = []
        all_embeddings: Optional[np.ndarray] = None
        
        for guide_file in guide_files:
            chunks, embeddings = self.process_guide_file(guide_file)
            all_chunks.extend(chunks)
            if all_embeddings is None:
                all_embeddings = embeddings
            else:
                all_embeddings = np.vstack([all_embeddings, embeddings])
        
        # Save combined embeddings
        if all_embeddings is None:
            all_embeddings = np.array([])
        
        return self.save_embeddings(normalized_name, all_chunks, all_embeddings)
    
    def get_context_for_query(self, game_name: str, query: str, top_k: int = 3) -> str:
        """Get formatted context from relevant chunks for a query.
        
        Args:
            game_name: Name of the game
            query: The query to find relevant context for
            top_k: Number of top results to return
            
        Returns:
            Formatted string containing relevant context
        """
        relevant_chunks = self.search(game_name, query, top_k)
        
        context_parts = []
        for chunk in relevant_chunks:
            source = chunk["source"]
            text = chunk["text"]
            score = chunk.get("score", 0.0)
            
            # Format context with source and relevance information
            context_parts.append(f"From {source} (relevance: {score:.2f}):\n{text}\n")
        
        return "\n".join(context_parts)