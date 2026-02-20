from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic import ConfigDict


class ChatMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    question: str = Field(..., description="The natural language question from the user.")
    session_id: Optional[int] = Field(default=None, description="Existing chat session identifier.")
    model_id: Optional[str] = Field(default=None, description="Optional model identifier.")
    source_id: Optional[str] = Field(default=None, description="Optional dataset source identifier.")


class ChatThoughtStep(BaseModel):
    phase: str
    message: str
    status: str = "completed"


class ChatResponse(BaseModel):
    answer: str
    session_id: int
    thought_steps: List[ChatThoughtStep] = Field(default_factory=list)


class ChatHistoryResponse(BaseModel):
    session_id: int
    messages: List[ChatMessage]
