"""
Guide management implementation.
"""
from pathlib import Path
from typing import List, Dict, Optional
from .interfaces import GuideManager
from .scraper import GameFAQsScraper
import logging

logger = logging.getLogger(__name__)

class FileSystemGuideManager(GuideManager):
    """Manages game guides in the filesystem."""
    
    def __init__(self, base_path: str = "guides"):
        """Initialize the guide manager.
        
        Args:
            base_path: Base directory for storing guides
        """
        self.base_path = Path(base_path)
        self.scraper = GameFAQsScraper()
        
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
        return str(path)
        
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