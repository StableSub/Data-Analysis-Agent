from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from ..eda.schemas import PreprocessRecommendation


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DropMissingOperation(StrictModel):
    op: Literal["drop_missing"]
    columns: list[str] = Field(default_factory=list)
    how: Literal["any", "all"] = "any"


class ImputeOperation(StrictModel):
    op: Literal["impute"]
    columns: list[str]
    method: Literal["mean", "median", "mode", "value"]
    value: str | float | int | bool | None = None


class DropColumnsOperation(StrictModel):
    op: Literal["drop_columns"]
    columns: list[str]


class RenameColumnsOperation(StrictModel):
    op: Literal["rename_columns"]
    rename_from: list[str] = Field(default_factory=list)
    rename_to: list[str] = Field(default_factory=list)


class ScaleOperation(StrictModel):
    op: Literal["scale"]
    columns: list[str]
    method: Literal["standardize", "normalize"]


class DerivedColumnOperation(StrictModel):
    op: Literal["derived_column"]
    name: str
    expression: str

class EncodeCategoricalOperation(StrictModel):
    op: Literal["encode_categorical"]
    columns: list[str]
    method: Literal["one_hot", "label"]


class ParseDatetimeOperation(StrictModel):
    op: Literal["parse_datetime"]
    columns: list[str] = Field(default_factory=list)
    format: str | None = None


class OutlierOperation(StrictModel):
    op: Literal["outlier"]
    columns: list[str]
    method: Literal["zscore", "iqr"]
    strategy: Literal["drop", "clip"]
    z_threshold: float = 3.0
    iqr_multiplier: float = 1.5


class NumericDistribution(StrictModel):
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    std: float | None = None
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None


class DataSummary(StrictModel):
    row_count: int
    column_count: int
    missing_total: int
    missing_by_column: dict[str, int]
    numeric_distribution: dict[str, NumericDistribution]
    dtypes: dict[str, str]


class SummaryDiff(StrictModel):
    row_count_delta: int
    column_count_delta: int
    missing_total_delta: int
    missing_by_column_delta: dict[str, int]
    dtype_changes: dict[str, dict[str, str]]

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
    source_id: str
    operations: list[PreprocessOperation] = Field(default_factory=list)


class PreprocessApplyRecommendationRequest(StrictModel):
    source_id: str
    recommendation: PreprocessRecommendation


class PreprocessApplyResponse(StrictModel):
    input_source_id: str
    output_source_id: str
    output_filename: str
    summary_before: DataSummary | None = None
    summary_after: DataSummary | None = None
    summary_diff: SummaryDiff | None = None
