from datetime import datetime
from typing import List

from pydantic import BaseModel


class GuidelineBase(BaseModel):
    """지침서 기본 응답 형태(단건/업로드/목록 아이템 공용)."""

    id: int
    source_id: str
    guideline_id: str
    filename: str
    storage_path: str
    filesize: int | None = None
    version: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True


class GuidelineListResponse(BaseModel):
    """지침서 목록 응답 형태."""

    total: int
    items: List[GuidelineBase]


class GuidelineActivateResponse(BaseModel):
    """지침서 활성화 응답 형태."""

    source_id: str
    is_active: bool
    message: str
