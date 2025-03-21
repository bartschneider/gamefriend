from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
from ..models import ChatSession, ChatMessage
from ..chat.retriever import GuideRetriever
from ..chat.mistral_client import MistralClientWrapper

router = APIRouter()
chat_sessions: Dict[str, ChatSession] = {}
mistral_client = MistralClientWrapper()

class ChatRequest(BaseModel):
    message: str
    game_context: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    message: str
    messages: List[ChatMessage]

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        print(f"Received request: {request}")  # Debug log
        
        # Get or create session
        session_id = request.session_id
        if not session_id or session_id not in chat_sessions:
            session = ChatSession()
            chat_sessions[session.id] = session
            session_id = session.id

        session = chat_sessions[session_id]
        
        # Add user message
        session.add_message("user", request.message)
        
        # Get AI response using Mistral client
        response = mistral_client.chat_with_context(
            question=request.message,
            context=request.game_context,
            chat_history=session.get_messages_text()
        )
        
        # Add AI response
        session.add_message("assistant", response)
        
        return ChatResponse(
            session_id=session_id,
            message=response,
            messages=session.get_messages()
        )
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/sessions/{session_id}", response_model=ChatResponse)
async def get_session(session_id: str):
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = chat_sessions[session_id]
    return ChatResponse(
        session_id=session_id,
        message="",  # No current message for GET request
        messages=session.get_messages()
    ) 