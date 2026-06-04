from __future__ import annotations

import pandas as pd
import pytest
from pandas.api.types import is_numeric_dtype

from backend.app.modules.preprocess.processor import PreprocessProcessor
from backend.app.modules.preprocess.schemas import (
    DerivedColumnOperation,
    DropColumnsOperation,
    ImputeOperation,
    RenameColumnsOperation,
)


def test_numeric_impute_preserves_numeric_dtype_for_numeric_strings() -> None:
    processor = PreprocessProcessor()
    df = pd.DataFrame({"value": ["1", None, "3"]})

    result = processor.apply_operations(
        df,
        [ImputeOperation(op="impute", columns=["value"], method="median")],
    )

    assert result["value"].tolist() == [1.0, 2.0, 3.0]
    assert is_numeric_dtype(result["value"])


def test_drop_columns_rejects_missing_columns() -> None:
    processor = PreprocessProcessor()
    df = pd.DataFrame({"kept": [1, 2]})

    with pytest.raises(ValueError, match="Column not found: missing"):
        processor.apply_operations(
            df,
            [DropColumnsOperation(op="drop_columns", columns=["missing"])],
        )


def test_rename_columns_rejects_blank_pairs() -> None:
    processor = PreprocessProcessor()
    df = pd.DataFrame({"raw": [1, 2]})

    with pytest.raises(ValueError, match="rename_columns requires non-empty column pairs"):
        processor.apply_operations(
            df,
            [RenameColumnsOperation(op="rename_columns", rename_from=[""], rename_to=["clean"])],
        )


def test_derived_sum_rejects_non_numeric_source_columns() -> None:
    processor = PreprocessProcessor()
    df = pd.DataFrame({"left": ["1", "not-a-number"], "right": [2, 3]})

    with pytest.raises(ValueError, match="derived_column.sum requires a numeric column: left"):
        processor.apply_operations(
            df,
            [
                DerivedColumnOperation(
                    op="derived_column",
                    name="total",
                    source_columns=["left", "right"],
                    transform_type="sum",
                )
            ],
        )
