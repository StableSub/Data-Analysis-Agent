from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


PreprocessOpType = Literal[
    "drop_missing",
    "impute",
    "drop_columns",
    "rename_columns",
    "scale",
    "derived_column",
]

class PreprocessOperation(BaseModel):
    """단일 전처리 작업 정의."""

    op: PreprocessOpType
    params: Dict[str, Any] = Field(default_factory=dict)

class PreprocessApplyRequest(BaseModel):
    """전처리 적용 요청."""

    dataset_id: int
    operations: List[PreprocessOperation] = Field(min_length=1)

class PreprocessApplyResponse(BaseModel):
    """전처리 적용 결과."""

    dataset_id: int
