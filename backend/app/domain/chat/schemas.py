from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessageSchema(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True


class ChatRequest(BaseModel):
    question: str = Field(..., description="The natural language question from the user.")
    session_id: Optional[int] = Field(default=None, description="Existing chat session identifier.")


class ChatResponse(BaseModel):
    answer: str
    session_id: int


class ChatHistoryResponse(BaseModel):
    session_id: int
    messages: List[ChatMessageSchema]
