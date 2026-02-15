from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

class StrictModel(BaseModel):
    """구조화 출력/요청 스키마 공통 베이스."""

    model_config = ConfigDict(extra="forbid")

class DropMissingOperation(StrictModel):
    """누락값 제거 연산."""

    op: Literal["drop_missing"]
    columns: list[str] = Field(default_factory=list)
    how: Literal["any", "all"] = "any"

class ImputeOperation(StrictModel):
    """결측값 대체 연산."""

    op: Literal["impute"]
    columns: list[str]
    method: Literal["mean", "median", "mode", "value"]
    value: str | float | int | bool | None = None

class DropColumnsOperation(StrictModel):
    """컬럼 삭제 연산."""

    op: Literal["drop_columns"]
    columns: list[str]

class RenameColumnsOperation(StrictModel):
    """컬럼명 변경 연산."""

    op: Literal["rename_columns"]
    rename_from: list[str] = Field(default_factory=list)
    rename_to: list[str] = Field(default_factory=list)

class ScaleOperation(StrictModel):
    """스케일링 연산."""

    op: Literal["scale"]
    columns: list[str]
    method: Literal["standardize", "normalize"]

class DerivedColumnOperation(StrictModel):
    """파생 컬럼 생성 연산."""

    op: Literal["derived_column"]
    name: str
    expression: str

PreprocessOperation = Annotated[
    Union[
        DropMissingOperation,
        ImputeOperation,
        DropColumnsOperation,
        RenameColumnsOperation,
        ScaleOperation,
        DerivedColumnOperation,
    ],
    Field(discriminator="op"),
]

class PreprocessApplyRequest(StrictModel):
    """전처리 적용 요청."""

    source_id: str
    operations: list[PreprocessOperation] = Field(default_factory=list)

class PreprocessApplyResponse(StrictModel):
    """전처리 적용 결과."""

    source_id: str
