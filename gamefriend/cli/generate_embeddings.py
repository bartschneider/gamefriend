"""
CLI tool to generate embeddings for all guides.
"""
import argparse
import logging
from pathlib import Path
import sys
import os

# Add parent directory to path so we can import gamefriend
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

from gamefriend.guide_manager import FileSystemGuideManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("gamefriend.cli.generate_embeddings")

def main():
    """Generate embeddings for all guides."""
    parser = argparse.ArgumentParser(description="Generate embeddings for game guides")
    parser.add_argument("--guides-dir", default="guides", help="Directory containing game guides")
    parser.add_argument("--embeddings-dir", default="data/embeddings", help="Directory to store embeddings")
    parser.add_argument("--game", help="Generate embeddings for a specific game only")
    parser.add_argument("--platform", help="Generate embeddings for a specific platform only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Set up logging
    if args.verbose:
        logging.getLogger("gamefriend").setLevel(logging.DEBUG)
    
    # Initialize guide manager
    logger.info(f"Initializing guide manager with guides directory: {args.guides_dir}")
    guide_manager = FileSystemGuideManager(
        base_path=args.guides_dir,
        embeddings_dir=args.embeddings_dir
    )
    
    # Generate embeddings for all games or a specific game
    if args.game and args.platform:
        logger.info(f"Generating embeddings for game: {args.game} on platform: {args.platform}")
        try:
            guide_manager._generate_embeddings(args.game, args.platform)
            logger.info(f"Successfully generated embeddings for {args.game}")
        except Exception as e:
            logger.error(f"Failed to generate embeddings for {args.game}: {e}")
            return 1
    else:
        logger.info("Generating embeddings for all games")
        results = guide_manager.generate_embeddings_for_all_games()
        
        logger.info(f"Successfully processed {results['processed']} games")
        if results['failed']:
            logger.warning(f"Failed to process {len(results['failed'])} games:")
            for failed in results['failed']:
                logger.warning(f"  - {failed}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())