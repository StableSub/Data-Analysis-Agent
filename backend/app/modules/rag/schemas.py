from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query.")
    top_k: int = Field(default=3, ge=1, le=20)
    source_filter: Optional[List[str]] = Field(
        default=None,
        description="Optional list of source_id values to limit the search scope.",
    )


class RagRetrievedChunk(BaseModel):
    source_id: str
    chunk_id: int
    score: float
    snippet: str


class RagQueryResponse(BaseModel):
    answer: str
    retrieved_chunks: List[RagRetrievedChunk]
    executed_at: datetime


class RagDeleteResponse(BaseModel):
    success: bool
