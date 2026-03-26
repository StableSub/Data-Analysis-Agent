from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


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


class PendingApproval(BaseModel):
    stage: Literal["preprocess", "visualization", "report"]
    kind: Literal["plan_review", "draft_review"]
    title: str
    summary: str
    source_id: str
    plan: dict[str, Any] = Field(default_factory=dict)
    draft: str = ""
    review: dict[str, Any] = Field(default_factory=dict)


class ResumeRunRequest(BaseModel):
    decision: Literal["approve", "revise", "cancel"]
    stage: Literal["preprocess", "visualization", "report"]
    instruction: Optional[str] = None


class PendingApprovalResponse(BaseModel):
    session_id: int
    run_id: str
    pending_approval: PendingApproval


class ChatHistoryResponse(BaseModel):
    session_id: int
    messages: List[ChatMessage]
