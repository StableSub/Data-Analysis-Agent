from __future__ import annotations

import pytest

from eval_cases import RAW_DIR
from p1_dataset_oracles import (
    SCALED_COLUMNS,
    dataset_shape,
    header,
    is_scaled_like,
    label_counts,
    numeric_mean_std,
)
from runtime_assertions import assert_float_close

pytestmark = pytest.mark.skipif(
    not RAW_DIR.exists(),
    reason="evaluation/raw datasets are local benchmark artifacts",
)


def test_unlabeled_data_has_no_pass_or_fail_target() -> None:
    assert dataset_shape("unlabeled_data.csv") == {"row_count": 795315, "column_count": 46}
    assert "PassOrFail" not in header("unlabeled_data.csv")


def test_cn7_scaled_labeled_dataset_contract() -> None:
    assert dataset_shape("moldset_labeled_cn7.csv") == {"row_count": 1211, "column_count": 26}
    assert label_counts("moldset_labeled_cn7.csv") == {"0": 1194, "1": 17}
    stats = numeric_mean_std("moldset_labeled_cn7.csv", tuple(SCALED_COLUMNS))
    assert is_scaled_like(stats)
    for column in SCALED_COLUMNS:
        assert_float_close(stats[column]["mean"], 0.0, tolerance=0.05, context=column)


def test_rg3_scaled_labeled_dataset_contract() -> None:
    assert dataset_shape("moldset_labeled_rg3.csv") == {"row_count": 1182, "column_count": 26}
    assert label_counts("moldset_labeled_rg3.csv") == {"0": 1157, "1": 25}
    stats = numeric_mean_std("moldset_labeled_rg3.csv", tuple(SCALED_COLUMNS))
    assert is_scaled_like(stats)
    for column in SCALED_COLUMNS:
        assert_float_close(stats[column]["mean"], 0.0, tolerance=0.05, context=column)


def test_labeled_data_yn_target_distribution_contract() -> None:
    assert dataset_shape("labeled_data.csv") == {"row_count": 7996, "column_count": 45}
    assert label_counts("labeled_data.csv") == {"Y": 7925, "N": 71}
    assert_float_close(71 / 7996 * 100, 0.887943971985993, context="n_rate_pct")
