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


def _execute_pass_or_fail_value_counts(dataset_path: Path):
    decision = CommonAnalyticsFastPathDecision(
        eligible=True,
        operation="basic_metric",
        metric="value_counts",
        columns=["PassOrFail"],
    )
    return execute_common_analytics(
        decision=decision,
        storage_path=str(dataset_path),
        dataset_context={},
        reader=DatasetReader(),
    )


def test_value_counts_preserves_label_distribution_table(tmp_path: Path) -> None:
    dataset_path = tmp_path / "labels.csv"
    _write_label_csv(dataset_path)
    result = _execute_pass_or_fail_value_counts(dataset_path)

    assert result.table == [
        {"value": "0", "count": 98, "ratio": 0.98},
        {"value": "1", "count": 2, "ratio": 0.02},
    ]
    assert result.raw_metrics["total"] == 100


def test_pass_or_fail_distribution_explains_defect_analysis_sufficiency(tmp_path: Path) -> None:
    dataset_path = tmp_path / "labels.csv"
    _write_label_csv(dataset_path)
    result = _execute_pass_or_fail_value_counts(dataset_path)

    assert "정상 98건" in result.summary
    assert "불량 2건" in result.summary
    assert "불량 분석" in result.summary
    assert "세부 분석에는 부족할 수 있습니다" in result.summary


def test_pass_or_fail_distribution_names_answerable_parts_and_uncertainty(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "labels.csv"
    _write_label_csv(dataset_path)

    result = _execute_pass_or_fail_value_counts(dataset_path)

    assert "현재 데이터로 정확히 답할 수 있는 부분" in result.summary
    assert "전체 정상/불량 건수와 비율" in result.summary
    assert "전체 불량률은 2.00%" in result.summary
    assert "비전문가 관점" in result.summary
    assert "불량 원인이나 제품별/날짜별 차이" in result.summary
    assert "정보가 부족하여 이 부분은 정확하지 않을 수 있습니다" in result.summary


def test_pass_or_fail_distribution_explains_zero_defect_boundary(tmp_path: Path) -> None:
    dataset_path = tmp_path / "labels.csv"
    _ = dataset_path.write_text("PassOrFail\n" + "\n".join(["0"] * 12) + "\n", encoding="utf-8")

    result = _execute_pass_or_fail_value_counts(dataset_path)

    assert "정상 12건" in result.summary
    assert "불량 0건" in result.summary
    assert "현재 데이터에서는 불량 사례가 발견되지 않았습니다" in result.summary
    assert "불량 원인이나 불량 조건" in result.summary
    assert "정보가 부족하여 이 부분은 정확하지 않을 수 있습니다" in result.summary


def test_pass_or_fail_distribution_supports_yes_no_labels(tmp_path: Path) -> None:
    dataset_path = tmp_path / "labels.csv"
    _ = dataset_path.write_text("PassOrFail\n" + "\n".join(["Y"] * 9 + ["N"]) + "\n", encoding="utf-8")

    result = _execute_pass_or_fail_value_counts(dataset_path)

    assert "정상 9건" in result.summary
    assert "불량 1건" in result.summary
    assert result.raw_metrics["normal_label"] == "Y"
    assert result.raw_metrics["defect_label"] == "N"
