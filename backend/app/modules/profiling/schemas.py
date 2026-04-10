from typing import Literal

from pydantic import BaseModel, Field


ColumnProfileType = Literal[
    "numerical",
    "categorical",
    "identifier",
    "datetime",
    "boolean",
    "group_key",
]


class ColumnProfile(BaseModel):
    name: str
    raw_dtype: str
    inferred_type: ColumnProfileType
    null_count: int = 0
    missing_rate: float = Field(ge=0.0, le=1.0)
    unique_count: int = 0
    unique_ratio: float = Field(ge=0.0, le=1.0)
    sample_values: list[object] = Field(default_factory=list)


class DatasetProfile(BaseModel):
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


class TopMissingColumn(BaseModel):
    column: str
    missing_count: int = 0
    missing_rate: float = Field(ge=0.0, le=1.0)


class DatasetQualitySummary(BaseModel):
    missing_total: int = 0
    missing_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    top_missing_columns: list[TopMissingColumn] = Field(default_factory=list)


class DatasetContext(BaseModel):
    source_id: str
    filename: str = ""
    available: bool
    row_count_total: int = 0
    row_count_sample: int = 0
    column_count: int = 0
    columns: list[str] = Field(default_factory=list)
    dtypes: dict[str, str] = Field(default_factory=dict)
    logical_types: dict[str, ColumnProfileType] = Field(default_factory=dict)
    type_columns: dict[str, list[str]] = Field(default_factory=dict)
    numeric_columns: list[str] = Field(default_factory=list)
    datetime_columns: list[str] = Field(default_factory=list)
    categorical_columns: list[str] = Field(default_factory=list)
    boolean_columns: list[str] = Field(default_factory=list)
    identifier_columns: list[str] = Field(default_factory=list)
    group_key_columns: list[str] = Field(default_factory=list)
    sample_rows: list[dict[str, object]] = Field(default_factory=list)
    missing_rates: dict[str, float] = Field(default_factory=dict)
    quality_summary: DatasetQualitySummary = Field(default_factory=DatasetQualitySummary)
