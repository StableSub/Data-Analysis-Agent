from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from backend.app.modules.chat_fast_path.decision import CommonAnalyticsFastPathDecision
from backend.app.modules.chat_fast_path.executor import execute_common_analytics
from backend.app.modules.datasets.service import DatasetReader
from backend.app.modules.planner.schemas import PlanningResult
from backend.app.modules.profiling.schemas import (
    DatasetContext,
    DatasetQualitySummary,
    TopMissingColumn,
)
from backend.app.orchestration.builder import build_main_workflow


class _StaticDatasetContextService:
    def build_context(self, source_id: str) -> DatasetContext:
        return DatasetContext(
            source_id=source_id,
            filename="labels.csv",
            available=True,
            row_count_total=100,
            row_count_sample=5,
            column_count=2,
            columns=["PassOrFail", "Reason"],
            dtypes={"PassOrFail": "int64", "Reason": "object"},
            categorical_columns=["PassOrFail", "Reason"],
            missing_rates={"Reason": 0.98},
            quality_summary=DatasetQualitySummary(
                missing_total=98,
                missing_ratio=0.49,
                top_missing_columns=[
                    TopMissingColumn(column="Reason", missing_count=98, missing_rate=0.98)
                ],
            ),
            sample_rows=[
                {"PassOrFail": 0, "Reason": None},
                {"PassOrFail": 0, "Reason": None},
                {"PassOrFail": 0, "Reason": None},
                {"PassOrFail": 1, "Reason": "short shot"},
                {"PassOrFail": 1, "Reason": "scratch"},
            ],
        )


class _PlannerMustNotRun:
    dataset_context_service = _StaticDatasetContextService()

    def plan(self, **_: object) -> PlanningResult:
        raise AssertionError("handled chat fast-path must not reach planner")


class _StaticDatasetRepository:
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path

    def get_by_source_id(self, source_id: str) -> SimpleNamespace:
        return SimpleNamespace(source_id=source_id, storage_path=str(self._storage_path))


class _NoopRagService:
    def ensure_index_for_source(self, source_id: str) -> dict[str, str]:
        return {"status": "no_source", "source_id": source_id}

    def query_for_source(self, *, query: str, top_k: int, source_id: str) -> list[object]:
        return []

    def build_context(self, retrieved: list[object]) -> str:
        return ""


class _NoopGuidelineService:
    def get_active_guideline(self) -> None:
        return None

    def get_guideline_by_source_id(self, source_id: str) -> None:
        return None


class _NoopGuidelineRagService:
    def ensure_index_for_guideline(self, guideline: object) -> dict[str, str]:
        return {"status": "no_active_guideline"}

    def query_for_source(
        self,
        *,
        query: str,
        source_id: str,
        top_k: int,
    ) -> list[object]:
        return []

    def build_context(self, retrieved: list[object]) -> str:
        return ""


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


def test_common_analytics_fast_path_emits_meaningful_evidence_package(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "labels.csv"
    dataset_path.write_text(
        "PassOrFail\n" + "\n".join(["0"] * 98 + ["1"] * 2) + "\n",
        encoding="utf-8",
    )
    workflow = build_main_workflow(
        planner_service=_PlannerMustNotRun(),
        analysis_service=SimpleNamespace(
            dataset_repository=_StaticDatasetRepository(dataset_path),
        ),
        preprocess_service=object(),
        eda_service=SimpleNamespace(reader=DatasetReader()),
        rag_service=_NoopRagService(),
        guideline_service=_NoopGuidelineService(),
        guideline_rag_service=_NoopGuidelineRagService(),
        visualization_service=object(),
        report_service=object(),
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": "PassOrFail 분포를 알려줘",
            "source_id": "dataset-source",
            "model_id": "test-model",
        }
    )

    assert result["output"]["type"] == "fast_common_analytics"
    assert result["analysis_result"]["execution_status"] == "success"
    assert result["analysis_result"]["used_columns"] == ["PassOrFail"]
    assert result["analysis_result"]["raw_metrics"]["defect_count"] == 2
    assert result["evidence_package"]["filename"] == "labels.csv"
    assert result["evidence_package"]["used_columns"] == ["PassOrFail"]
    assert result["evidence_package"]["analysis_metrics"]["total"] == 100
    assert result["evidence_package"]["analysis_metrics"]["defect_rate_pct"] == 2.0
    assert result["answer_quality"]["answerable"] is True
    assert "analysis" in result["merged_context"]["applied_steps"]
