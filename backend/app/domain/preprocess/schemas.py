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
    op: PreprocessOpType
    params: Dict[str, Any] = Field(default_factory=dict)


class _DatasetReq(BaseModel):
    dataset_id: int


class PreprocessPreviewRequest(_DatasetReq):
    pass


class ColumnPreview(BaseModel):
    name: str
    dtype: str
    missing: int


class PreprocessPreviewResponse(BaseModel):
    dataset_id: int
    columns: List[ColumnPreview]
    sample_rows: List[Dict[str, Any]]


class PreprocessApplyRequest(_DatasetReq):
    operations: List[PreprocessOperation]


class PreprocessApplyResponse(BaseModel):
    dataset_id: int
    row_count: int
    col_count: int
