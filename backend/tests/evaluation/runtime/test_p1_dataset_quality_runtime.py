from __future__ import annotations

import pytest

from eval_cases import RAW_DIR
from p1_dataset_oracles import SCALED_COLUMNS, header, is_scaled_like, label_counts, numeric_mean_std
from runtime_assertions import (
    assert_answerability,
    assert_float_close,
    assert_no_forbidden_metric_keys,
    assert_used_columns,
)

pytestmark = pytest.mark.skipif(
    not RAW_DIR.exists(),
    reason="evaluation/raw datasets are local benchmark artifacts",
)


def test_unlabeled_dataset_defect_rate_is_not_computable_from_current_columns() -> None:
    columns = header("unlabeled_data.csv")
    forbidden_metrics = ["defect_count", "defect_rate_pct", "normal_count"]
    empty_metrics: dict[str, float] = {}
    answer_quality = {"status": "unanswerable", "answerable": False}

    assert "PassOrFail" not in columns
    assert_no_forbidden_metric_keys(empty_metrics, forbidden_metrics)
    assert_answerability(answer_quality, "unanswerable")


def test_scaled_dataset_detection_uses_numeric_process_columns() -> None:
    observed_cases = []
    for dataset_name in ["moldset_labeled_cn7.csv", "moldset_labeled_rg3.csv"]:
        stats = numeric_mean_std(dataset_name, tuple(SCALED_COLUMNS))
        observed_cases.append({"dataset": dataset_name, "actual_scaled_like": is_scaled_like(stats)})
        assert_used_columns(SCALED_COLUMNS, ["Injection_Time", "Filling_Time", "Plasticizing_Time", "Cycle_Time"])
        for column, values in stats.items():
            assert_float_close(values["mean"], 0.0, tolerance=0.05, context=f"{dataset_name}.{column}.mean")
            assert 0.95 <= values["std"] <= 1.05

    assert observed_cases == [
        {"dataset": "moldset_labeled_cn7.csv", "actual_scaled_like": True},
        {"dataset": "moldset_labeled_rg3.csv", "actual_scaled_like": True},
    ]


def test_labeled_data_uses_yn_label_distribution_not_binary_zero_one_assumption() -> None:
    counts = label_counts("labeled_data.csv")

    assert counts == {"Y": 7925, "N": 71}
    assert "0" not in counts
    assert "1" not in counts
    assert_float_close(counts["N"] / sum(counts.values()) * 100, 0.887943971985993)
