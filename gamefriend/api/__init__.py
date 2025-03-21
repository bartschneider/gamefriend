import logging
import os
import traceback
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gamefriend.chat import ChatManager
from gamefriend.scraper import GameFAQsScraper
from gamefriend.database import get_db
from gamefriend.models import ChatSession, ChatMessage as DBChatMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter()

class GuideImportRequest(BaseModel):
    url: str


class ChatRequest(BaseModel):
    message: str
    game_context: dict | None = None
    session_id: int | None = None


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: str

    class Config:
        from_attributes = True


class ChatSessionResponse(BaseModel):
    id: int
    created_at: str
    updated_at: str
    game_context: dict | None
    messages: List[ChatMessageResponse]

    class Config:
        from_attributes = True


# Initialize chat manager
chat_manager = ChatManager()


@router.get("/games")
async def list_games():
    """List all games that have guides available."""
    try:
        games = []
        guides_dir = Path("guides")

        if not guides_dir.exists():
            return {"games": []}

        for platform_dir in guides_dir.iterdir():
            if not platform_dir.is_dir():
                continue

            for game_dir in platform_dir.iterdir():
                if not game_dir.is_dir():
                    continue

                # Check if there's a guide file in the game directory
                guide_files = list(game_dir.glob("guide_*.md"))
                if guide_files:
                    games.append(
                        {
                            "id": str(game_dir),
                            "name": game_dir.name,
                            "platform": platform_dir.name,
                            "hasGuide": True,
                        }
                    )

        return {"games": games}
    except Exception as e:
        logger.error(f"Error listing games: {str(e)}")
        logger.error("Traceback:")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/guides/import")
async def import_guide(request: GuideImportRequest):
    try:
        logger.info(f"Received guide import request for URL: {request.url}")

        # Create scraper instance
        scraper = GameFAQsScraper()
        logger.info("Created scraper instance")

        # Download guide
        content, output_path = scraper.download_guide(request.url)
        logger.info(f"Successfully downloaded guide to: {output_path}")

        # Convert Path to string and extract game info
        # Format: guides/platform/game-name/guide_ID.md
        path_str = str(output_path)
        path_parts = path_str.split(os.sep)

        if len(path_parts) < 4:
            raise ValueError(f"Invalid path structure: {path_str}")

        platform = path_parts[1]
        game_name = path_parts[2]

        logger.info(f"Extracted game info - Platform: {platform}, Game: {game_name}")

        return {
            "success": True,
            "game": game_name,
            "platform": platform,
            "message": f"Guide imported successfully for {game_name}",
            "path": path_str,
        }
    except ValueError as e:
        logger.error(f"ValueError in import_guide: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in import_guide: {str(e)}")
        logger.error("Traceback:")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Handle chat messages with session persistence."""
    try:
        logger.info(f"Received chat message: {request.message}")
        if request.game_context:
            logger.info(f"Game context: {request.game_context}")

        # Get or create chat session
        session = None
        if request.session_id:
            session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail="Chat session not found")
        else:
            session = ChatSession(game_context=request.game_context)
            db.add(session)
            db.commit()
            db.refresh(session)

        # Add user message to session
        user_message = DBChatMessage(
            session_id=session.id,
            role="user",
            content=request.message
        )
        db.add(user_message)

        # Process message with chat manager
        response = chat_manager.process_message(request.message, request.game_context)

        # Add assistant response to session
        assistant_message = DBChatMessage(
            session_id=session.id,
            role="assistant",
            content=response
        )
        db.add(assistant_message)
        db.commit()

        return {
            "session_id": session.id,
            "response": response,
            "messages": [
                {"role": msg.role, "content": msg.content, "created_at": msg.created_at.isoformat()}
                for msg in session.messages
            ]
        }

    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        logger.error("Traceback:")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/sessions/{session_id}")
async def get_chat_session(session_id: int, db: Session = Depends(get_db)):
    """Get a specific chat session by ID."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session
