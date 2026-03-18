from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


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
    source_id: str
    operations: list[PreprocessOperation] = Field(default_factory=list)


class PreprocessApplyResponse(StrictModel):
    input_source_id: str
    output_source_id: str
    output_filename: str
