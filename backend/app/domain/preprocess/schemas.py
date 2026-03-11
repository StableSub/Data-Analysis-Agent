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

class EncodeCategoricalOperation(StrictModel):
    """범주형 인코딩 연산 (One-Hot / Label Encoding)."""

    op: Literal["encode_categorical"]
    columns: list[str]
    method: Literal["one_hot", "label"]


class ParseDatetimeOperation(StrictModel):
    """Datetime 파싱/형 변환 연산."""

    op: Literal["parse_datetime"]
    columns: list[str]
    format: str | None = None  # None 이면 pandas 자동 추론


class OutlierOperation(StrictModel):
    """이상치 탐지 및 처리 연산 (Z-score / IQR)."""

    op: Literal["outlier"]
    columns: list[str]
    method: Literal["zscore", "iqr"]
    strategy: Literal["drop", "clip"]
    z_threshold: float = 3.0      # zscore 전용
    iqr_multiplier: float = 1.5   # iqr 전용

# 요약 통계
class NumericDistribution(StrictModel):
    """수치형 컬럼 분포 통계."""

    model_config = ConfigDict(extra="forbid")

    min: float | None = None
    max: float | None = None
    mean: float | None = None
    std: float | None = None
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None


class DataSummary(StrictModel):
    """데이터프레임 요약 통계."""

    model_config = ConfigDict(extra="forbid")

    row_count: int
    column_count: int
    missing_total: int
    missing_by_column: dict[str, int]
    numeric_distribution: dict[str, NumericDistribution]
    dtypes: dict[str, str]


class SummaryDiff(StrictModel):
    """전처리 전후 변화량."""

    model_config = ConfigDict(extra="forbid")

    row_count_delta: int
    column_count_delta: int
    missing_total_delta: int
    missing_by_column_delta: dict[str, int]
    dtype_changes: dict[str, dict[str, str]]  # {col: {"before": dtype, "after": dtype}}

PreprocessOperation = Annotated[
    Union[
        DropMissingOperation,
        ImputeOperation,
        DropColumnsOperation,
        RenameColumnsOperation,
        ScaleOperation,
        DerivedColumnOperation,
        EncodeCategoricalOperation,
        ParseDatetimeOperation,
        OutlierOperation,
    ],
    Field(discriminator="op"),
]

class PreprocessApplyRequest(StrictModel):
    """전처리 적용 요청."""

    source_id: str
    operations: list[PreprocessOperation] = Field(default_factory=list)

class PreprocessApplyResponse(StrictModel):
    """전처리 적용 결과."""

    input_source_id: str
    output_source_id: str
    output_filename: str
    summary_before: DataSummary | None = None
    summary_after: DataSummary | None = None
    summary_diff: SummaryDiff | None = None
