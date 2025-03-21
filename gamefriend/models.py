from datetime import datetime
from typing import List, Dict
import uuid
from pydantic import BaseModel

class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: datetime = datetime.utcnow()

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat()
        }

class ChatSession(BaseModel):
    id: str = str(uuid.uuid4())
    messages: List[ChatMessage] = []
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(ChatMessage(role=role, content=content))
        self.updated_at = datetime.utcnow()

    def get_messages(self) -> List[Dict]:
        return [msg.to_dict() for msg in self.messages]

    def get_messages_text(self) -> str:
        return "\n".join([f"{msg.role}: {msg.content}" for msg in self.messages]) 