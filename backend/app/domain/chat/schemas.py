from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic import ConfigDict


class ChatMessageSchema(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    question: str = Field(..., description="The natural language question from the user.")
    session_id: Optional[int] = Field(default=None, description="Existing chat session identifier.")
    context: Optional[str] = Field(default=None, description="Optional extra context string.")
    data_source_id: Optional[str] = Field(
        default=None,
        description="Optional dataset source_id to load file content as context.",
    )


class ChatResponse(BaseModel):
    answer: str
    session_id: int


class ChatHistoryResponse(BaseModel):
    session_id: int
    messages: List[ChatMessageSchema]
