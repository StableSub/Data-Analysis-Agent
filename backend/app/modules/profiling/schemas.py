from typing import Literal

from pydantic import BaseModel, Field


ColumnProfileType = Literal["numerical", "categorical", "datetime"]


class ColumnProfile(BaseModel):
    name: str
    raw_dtype: str
    inferred_type: ColumnProfileType
    missing_rate: float = Field(ge=0.0, le=1.0)
    sample_values: list[object] = Field(default_factory=list)


class DatasetProfile(BaseModel):
    source_id: str
    available: bool
    row_count: int = 0
    column_count: int = 0
    columns: list[str] = Field(default_factory=list)
    dtypes: dict[str, str] = Field(default_factory=dict)
    missing_rates: dict[str, float] = Field(default_factory=dict)
    sample_rows: list[dict[str, object]] = Field(default_factory=list)
    numeric_columns: list[str] = Field(default_factory=list)
    datetime_columns: list[str] = Field(default_factory=list)
    categorical_columns: list[str] = Field(default_factory=list)
    column_profiles: list[ColumnProfile] = Field(default_factory=list)
