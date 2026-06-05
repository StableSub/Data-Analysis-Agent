from __future__ import annotations

from pathlib import Path

from backend.app.modules.chat_fast_path.decision import CommonAnalyticsFastPathDecision
from backend.app.modules.chat_fast_path.executor import execute_common_analytics
from backend.app.modules.datasets.service import DatasetReader


def _write_label_csv(path: Path) -> None:
    _ = path.write_text(
        "PassOrFail\n"
        + "\n".join(["0"] * 98 + ["1"] * 2)
        + "\n",
        encoding="utf-8",
    )


def test_value_counts_preserves_label_distribution_table(tmp_path: Path) -> None:
    dataset_path = tmp_path / "labels.csv"
    _write_label_csv(dataset_path)
    decision = CommonAnalyticsFastPathDecision(
        eligible=True,
        operation="basic_metric",
        metric="value_counts",
        columns=["PassOrFail"],
    )

    result = execute_common_analytics(
        decision=decision,
        storage_path=str(dataset_path),
        dataset_context={},
        reader=DatasetReader(),
    )

    assert result.table == [
        {"value": "0", "count": 98, "ratio": 0.98},
        {"value": "1", "count": 2, "ratio": 0.02},
    ]
    assert result.raw_metrics["total"] == 100


def test_pass_or_fail_distribution_explains_defect_analysis_sufficiency(tmp_path: Path) -> None:
    dataset_path = tmp_path / "labels.csv"
    _write_label_csv(dataset_path)
    decision = CommonAnalyticsFastPathDecision(
        eligible=True,
        operation="basic_metric",
        metric="value_counts",
        columns=["PassOrFail"],
    )

    result = execute_common_analytics(
        decision=decision,
        storage_path=str(dataset_path),
        dataset_context={},
        reader=DatasetReader(),
    )

    assert "정상 98건" in result.summary
    assert "불량 2건" in result.summary
    assert "불량 분석" in result.summary
    assert "세부 분석에는 부족할 수 있습니다" in result.summary
