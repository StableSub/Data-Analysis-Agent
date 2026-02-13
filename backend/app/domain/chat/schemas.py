from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic import ConfigDict


class ChatMessage(BaseModel):
    id: int
    role: str
    content: str

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    question: str = Field(..., description="The natural language question from the user.")
    session_id: Optional[int] = Field(default=None, description="Existing chat session identifier.")


class ChatResponse(BaseModel):
    answer: str
    session_id: int


class ChatHistoryResponse(BaseModel):
    session_id: int
    messages: List[ChatMessage]
