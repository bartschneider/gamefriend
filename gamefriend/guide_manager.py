"""
Guide management implementation.
"""
from pathlib import Path
from typing import List, Dict, Optional, Union
from .interfaces import GuideManager
from .scraper import GameFAQsScraper
from .embeddings_manager import EmbeddingsManager
import logging
import os

logger = logging.getLogger(__name__)

class FileSystemGuideManager(GuideManager):
    """Manages game guides in the filesystem."""
    
    def __init__(self, base_path: str = "guides", embeddings_dir: Optional[str] = None):
        """Initialize the guide manager.
        
        Args:
            base_path: Base directory for storing guides
            embeddings_dir: Directory for storing guide embeddings
        """
        self.base_path = Path(base_path)
        self.scraper = GameFAQsScraper()
        self.embeddings_dir = Path(embeddings_dir) if embeddings_dir else Path("data/embeddings")
        self.embeddings_manager = EmbeddingsManager(embeddings_dir=self.embeddings_dir)
        
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
        logger.info(f"Downloading guide from URL: {url}")
        content, path = self.scraper.download_guide(url)
        logger.info(f"Successfully downloaded guide to: {path}")
        
        # Extract game name and platform from the path
        try:
            platform_dir = Path(path).parent.parent
            game_dir = Path(path).parent
            game_name = game_dir.name
            platform = platform_dir.name
            
            # Generate embeddings for the newly downloaded guide
            self._generate_embeddings(game_name, platform)
            
        except Exception as e:
            logger.warning(f"Failed to generate embeddings for downloaded guide: {e}")
        
        return str(path)
    
    def _generate_embeddings(self, game_name: str, platform: str) -> None:
        """Generate embeddings for a game's guides.
        
        Args:
            game_name: Name of the game
            platform: Platform of the game
        """
        try:
            logger.info(f"Generating embeddings for {game_name} on {platform}")
            self.embeddings_manager.process_game_guides(
                game_name=game_name,
                platform=platform,
                guides_dir=self.base_path
            )
            logger.info(f"Successfully generated embeddings for {game_name}")
        except Exception as e:
            logger.error(f"Failed to generate embeddings for {game_name}: {e}")
            raise
        
    def list_games(self) -> List[Dict[str, str]]:
        """List all games that have guides available.
        
        Returns:
            List of dictionaries containing game information
            Each dict has keys: name, platform
        """
        games = []
        if not self.base_path.exists():
            return games
            
        for platform_dir in self.base_path.iterdir():
            if not platform_dir.is_dir():
                continue
                
            for game_dir in platform_dir.iterdir():
                if not game_dir.is_dir():
                    continue
                    
                # Check if there's a guide file in the game directory
                guide_files = list(game_dir.glob("guide_*.md"))
                if guide_files:
                    games.append({
                        "name": game_dir.name,
                        "platform": platform_dir.name
                    })
                    
        return games
    
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
        try:
            # Normalize game name for consistency
            normalized_name = game_name.lower().replace(" ", "-")
            
            # Get context using embeddings manager
            return self.embeddings_manager.get_context_for_query(
                normalized_name, 
                query, 
                top_k=top_k
            )
        except FileNotFoundError:
            logger.warning(f"No embeddings found for {game_name}, generating them...")
            
            # Try to find the game and generate embeddings
            for platform_dir in self.base_path.iterdir():
                if not platform_dir.is_dir():
                    continue
                    
                for game_dir in platform_dir.iterdir():
                    if game_dir.is_dir() and normalized_name in game_dir.name.lower().replace(" ", "-"):
                        # Found the game, generate embeddings
                        self._generate_embeddings(game_dir.name, platform_dir.name)
                        
                        # Try again to get context
                        return self.embeddings_manager.get_context_for_query(
                            normalized_name, 
                            query, 
                            top_k=top_k
                        )
            
            # If we get here, we couldn't find the game
            raise FileNotFoundError(f"No guides found for game: {game_name}")
    
    def generate_embeddings_for_all_games(self) -> Dict[str, Union[int, List[str]]]:
        """Generate embeddings for all games with guides.
        
        Returns:
            Dictionary with count of processed games and failures
        """
        results = {
            "processed": 0,
            "failed": [],
        }
        
        games = self.list_games()
        logger.info(f"Generating embeddings for {len(games)} games")
        
        for game in games:
            try:
                self._generate_embeddings(game["name"], game["platform"])
                results["processed"] += 1
            except Exception as e:
                logger.error(f"Failed to generate embeddings for {game['name']}: {e}")
                results["failed"].append(f"{game['name']} ({str(e)})")
        
        return results 