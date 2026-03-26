from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict


class DatasetBase(BaseModel):
    """데이터셋 기본 응답 형태(단건/업로드/목록 아이템 공용)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: str
    filename: str
    storage_path: str
    filesize: int | None = None


class DatasetListResponse(BaseModel):
    """데이터셋 목록 응답 형태."""

    total: int
    items: List[DatasetBase]


class DatasetSampleResponse(BaseModel):
    """데이터셋 샘플 조회 응답 형태."""

    source_id: str
    columns: List[str]
    rows: List[Dict[str, Any]]
