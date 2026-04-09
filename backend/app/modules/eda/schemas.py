from typing import Literal

from ..profiling.schemas import ColumnProfile, ColumnProfileType
from pydantic import BaseModel, Field, ConfigDict


class EDASummaryCounts(BaseModel):
    numerical: int = 0
    categorical: int = 0
    datetime: int = 0
    boolean: int = 0
    identifier: int = 0
    group_key: int = 0


class EDASummaryResponse(BaseModel):
    source_id: str
    row_count: int = 0
    column_count: int = 0
    sample_row_count: int = 0
    type_counts: EDASummaryCounts = Field(default_factory=EDASummaryCounts)
    columns: list[str] = Field(default_factory=list)


class EDAQualityColumn(BaseModel):
    column: str
    inferred_type: ColumnProfileType
    null_count: int = 0
    null_ratio: float = Field(default=0.0, ge=0.0, le=1.0)


class EDAQualityResponse(BaseModel):
    source_id: str
    row_count: int = 0
    column_count: int = 0
    missing_total: int = 0
    missing_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    top_missing_columns: list[EDAQualityColumn] = Field(default_factory=list)
    columns: list[EDAQualityColumn] = Field(default_factory=list)


class EDAColumnTypeItem(BaseModel):
    column: str
    raw_dtype: str
    inferred_type: ColumnProfileType
    null_count: int = 0
    null_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    unique_count: int = 0
    unique_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    sample_values: list[object] = Field(default_factory=list)


class EDAColumnTypesResponse(BaseModel):
    source_id: str
    column_count: int = 0
    type_columns: dict[str, list[str]] = Field(default_factory=dict)
    columns: list[EDAColumnTypeItem] = Field(default_factory=list)


class EDAStatsColumn(BaseModel):
    column: str
    mean: float | None = None
    min: float | None = None
    max: float | None = None
    median: float | None = None
    std: float | None = None
    q1: float | None = None
    q3: float | None = None
    skew: float | None = None


class EDAStatsResponse(BaseModel):
    source_id: str
    row_count: int = 0
    column_count: int = 0
    numeric_column_count: int = 0
    columns: list[EDAStatsColumn] = Field(default_factory=list)


class EDACorrelationItem(BaseModel):
    column_1: str
    column_2: str
    correlation: float


class EDACorrelationsResponse(BaseModel):
    source_id: str
    pairs: list[EDACorrelationItem] = Field(default_factory=list)


class EDAOutlierColumn(BaseModel):
    column: str
    outlier_count: int = 0
    outlier_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    q1: float | None = None
    q3: float | None = None
    iqr: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None


class EDAOutliersResponse(BaseModel):
    source_id: str
    numeric_column_count: int = 0
    columns: list[EDAOutlierColumn] = Field(default_factory=list)


class EDADistributionBin(BaseModel):
    label: str
    value: int
    lower: float | None = None
    upper: float | None = None


class EDADistributionResponse(BaseModel):
    source_id: str
    column: str
    inferred_type: ColumnProfileType
    chart_type: str
    total_count: int = 0
    other_count: int = 0
    truncated: bool = False
    bins: list[EDADistributionBin] = Field(default_factory=list)


class EDAAISummaryResponse(BaseModel):
    source_id: str
    structure_summary: str = ""
    quality_issues: list[str] = Field(default_factory=list)
    key_insights: list[str] = Field(default_factory=list)


class EDAProfileResponse(BaseModel):
    source_id: str
    available: bool
    row_count: int = 0
    sample_row_count: int = 0
    column_count: int = 0
    columns: list[str] = Field(default_factory=list)
    dtypes: dict[str, str] = Field(default_factory=dict)
    missing_rates: dict[str, float] = Field(default_factory=dict)
    sample_rows: list[dict[str, object]] = Field(default_factory=list)
    numeric_columns: list[str] = Field(default_factory=list)
    datetime_columns: list[str] = Field(default_factory=list)
    categorical_columns: list[str] = Field(default_factory=list)
    boolean_columns: list[str] = Field(default_factory=list)
    identifier_columns: list[str] = Field(default_factory=list)
    group_key_columns: list[str] = Field(default_factory=list)
    type_columns: dict[str, list[str]] = Field(default_factory=dict)
    logical_types: dict[str, ColumnProfileType] = Field(default_factory=dict)
    column_profiles: list[ColumnProfile] = Field(default_factory=list)

# 전처리 추천
class RecommendedOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal[
        "drop_missing",
        "impute",
        "drop_columns",
        "scale",
        "encode_categorical",
        "outlier",
        "parse_datetime",
        "derived_column",
    ]
    target_columns: list[str]
    reason: str
    priority: Literal["high", "medium", "low"]

class PreprocessRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operations: list[RecommendedOperation] = Field(default_factory=list)
    summary: str

class PreprocessRecommendationResponse(BaseModel):
    source_id: str
    recommendation: PreprocessRecommendation
    generation_mode: Literal["llm", "fallback", "none"]
    warning: str | None = None
