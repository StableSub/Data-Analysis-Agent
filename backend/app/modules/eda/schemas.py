from ..profiling.schemas import ColumnProfile, ColumnProfileType
from pydantic import BaseModel, Field


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
