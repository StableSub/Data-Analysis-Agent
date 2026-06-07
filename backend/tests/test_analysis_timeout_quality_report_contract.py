from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.core.ai import llm_gateway
from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.sandbox import AnalysisSandbox
from backend.app.modules.analysis.schemas import (
    AnalysisPlan,
    ExpectedOutputSpec,
    MetadataSnapshot,
    MetricSpec,
    VisualizationHint,
)
from backend.app.modules.analysis.service import AnalysisService
from backend.app.modules.datasets.models import Dataset
from backend.app.modules.planner.service import PlannerService
from backend.app.modules.profiling.schemas import DatasetContext
from backend.app.modules.reports import service as report_service_module
from backend.app.modules.reports.service import ReportService


def _write_preprocessed_moldset_fixture(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "PassOrFail,PART_NO_86131AA000,PART_NO_86141AA000,PART_NO_86141T1000,Reason_가스,Reason_미성형,Reason_초기허용불량",
                "1,1,0,0,1,0,0",
                "1,0,1,0,0,1,0",
                "1,0,1,0,0,0,1",
                "1,0,0,1,1,0,0",
                "1,0,0,1,1,0,0",
            ]
        ),
        encoding="utf-8",
    )


def _metadata() -> MetadataSnapshot:
    columns = [
        "PassOrFail",
        "PART_NO_86131AA000",
        "PART_NO_86141AA000",
        "PART_NO_86141T1000",
        "Reason_가스",
        "Reason_미성형",
        "Reason_초기허용불량",
    ]
    return MetadataSnapshot(
        columns=columns,
        dtypes={column: "int64" for column in columns},
        numeric_columns=columns,
        row_count=5,
    )


def _quality_plan() -> AnalysisPlan:
    metadata = _metadata()
    return AnalysisPlan(
        analysis_type="quality_status_summary",
        objective="전체 품질 현황, 양품/불량 비율, 불량 사유, 제품별 생산량을 요약합니다.",
        required_columns=list(metadata.columns),
        used_columns=list(metadata.columns),
        filters=[],
        group_by=[],
        metrics=[
            MetricSpec(
                name="total_count",
                aggregation="count",
                column=None,
                alias="total_count",
            )
        ],
        derived_columns=[],
        sort_by=[],
        time_context=None,
        expected_output=ExpectedOutputSpec(
            require_summary=True,
            require_table=True,
            require_raw_metrics=True,
            expected_table_columns=["section", "label", "count", "rate"],
            allow_empty_table=False,
            minimum_rows=1,
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
        empty_result_policy="success_with_empty_summary",
        metadata_snapshot=metadata,
        codegen_strategy="llm_codegen",
    )


def _part_no_plan() -> AnalysisPlan:
    metadata = _metadata()
    part_columns = [
        "PART_NO_86131AA000",
        "PART_NO_86141AA000",
        "PART_NO_86141T1000",
    ]
    return AnalysisPlan(
        analysis_type="product_production_count",
        objective="PART_NO별 생산량을 계산합니다.",
        required_columns=part_columns,
        used_columns=part_columns,
        filters=[],
        group_by=["PART_NO"],
        metrics=[
            MetricSpec(
                name="production_count",
                aggregation="count",
                column=None,
                alias="production_count",
            )
        ],
        derived_columns=[],
        sort_by=[],
        time_context=None,
        expected_output=ExpectedOutputSpec(
            require_summary=True,
            require_table=True,
            require_raw_metrics=True,
            expected_table_columns=["PART_NO", "production_count"],
            allow_empty_table=False,
            minimum_rows=1,
            require_group_axis=True,
        ),
        visualization_hint=VisualizationHint(
            preferred_chart="bar",
            x="PART_NO",
            y="production_count",
        ),
        empty_result_policy="success_with_empty_summary",
        metadata_snapshot=metadata,
        codegen_strategy="llm_codegen",
    )


class _FailingRunService:
    def generate_analysis_code(self, **_: Any) -> str:
        raise TimeoutError("simulated LLM code generation timeout")

    def repair_analysis_code(self, **_: Any) -> str:
        raise TimeoutError("simulated LLM repair timeout")


def _analysis_service() -> AnalysisService:
    service: Any = object.__new__(AnalysisService)
    service.run_service = _FailingRunService()
    service.processor = AnalysisProcessor()
    service.sandbox = AnalysisSandbox(timeout_seconds=5)
    service.max_retries = 0
    return service


def test_quality_report_recovers_without_llm_codegen_when_provider_times_out(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "moldset_preprocessed.csv"
    _write_preprocessed_moldset_fixture(dataset_path)
    dataset = Dataset(
        source_id="moldset_labeled_전처리_4",
        filename="moldset_preprocessed.csv",
        storage_path=str(dataset_path),
    )

    bundle = _analysis_service()._run_code_generation_loop(
        question=(
            "이 데이터의 전체 품질 현황을 요약하는 리포트를 작성해줘. "
            "양품/불량 비율, 불량 사유, 제품별 생산량을 포함해줘."
        ),
        dataset=dataset,
        analysis_plan=_quality_plan(),
        model_id=None,
    )

    assert bundle["final_status"] == "success"
    result = bundle["analysis_result"]
    assert result.execution_status == "success"
    assert result.raw_metrics["total_count"] == 5
    assert result.raw_metrics["product_production"] == {
        "86131AA000": 1,
        "86141AA000": 2,
        "86141T1000": 2,
    }
    assert result.raw_metrics["defect_reasons"] == {
        "가스": 3,
        "미성형": 1,
        "초기허용불량": 1,
    }


def test_part_no_one_hot_group_count_returns_valid_json_without_llm(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "moldset_preprocessed.csv"
    _write_preprocessed_moldset_fixture(dataset_path)
    dataset = Dataset(
        source_id="moldset_labeled_전처리_4",
        filename="moldset_preprocessed.csv",
        storage_path=str(dataset_path),
    )

    bundle = _analysis_service()._run_code_generation_loop(
        question="PART_NO별 생산량을 계산해줘.",
        dataset=dataset,
        analysis_plan=_part_no_plan(),
        model_id=None,
    )

    assert bundle["final_status"] == "success"
    result = bundle["analysis_result"]
    assert result.execution_status == "success"
    assert result.table == [
        {"PART_NO": "86131AA000", "production_count": 1},
        {"PART_NO": "86141AA000", "production_count": 2},
        {"PART_NO": "86141T1000", "production_count": 2},
    ]
    assert result.used_columns == [
        "PART_NO_86131AA000",
        "PART_NO_86141AA000",
        "PART_NO_86141T1000",
    ]


def test_llm_gateway_has_no_default_provider_timeout(monkeypatch: Any) -> None:
    captured_kwargs: dict[str, Any] = {}

    def fake_init_chat_model(*_: Any, **kwargs: Any) -> object:
        captured_kwargs.update(kwargs)
        return object()

    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setattr(llm_gateway, "init_chat_model", fake_init_chat_model)

    llm_gateway.LLMGateway(default_model="test-model")._build_model(
        model_id=None,
        temperature=0,
    )

    assert captured_kwargs.get("timeout") is None


def _dataset_context() -> DatasetContext:
    metadata = _metadata()
    return DatasetContext(
        source_id="moldset_labeled_전처리_4",
        filename="moldset_preprocessed.csv",
        available=True,
        row_count_total=5,
        column_count=len(metadata.columns),
        columns=list(metadata.columns),
        dtypes=dict(metadata.dtypes),
        numeric_columns=list(metadata.numeric_columns),
    )


class _UnusedDatasetContextService:
    def build_context(self, _: str) -> DatasetContext:
        raise AssertionError("dataset context should be provided by the caller")


class _PlannerLLMShouldNotRun:
    def invoke_structured(self, **_: Any) -> object:
        raise AssertionError("clear quality/product questions must not call planner LLM")


def _planner_service() -> Any:
    service: Any = object.__new__(PlannerService)
    service.dataset_context_service = _UnusedDatasetContextService()
    service.analysis_processor = AnalysisProcessor()
    service.default_model = "test-model"
    service.llm = _PlannerLLMShouldNotRun()
    return service


def test_quality_report_planning_is_deterministic_without_llm() -> None:
    result = _planner_service().plan(
        user_input="이 데이터의 전체 품질 현황을 요약하는 리포트를 작성해줘. 양품/불량 비율, 불량 사유, 제품별 생산량을 포함해줘.",
        request_context=None,
        source_id="moldset_labeled_전처리_4",
        dataset_context=_dataset_context(),
        guideline_context=None,
        model_id=None,
    )

    assert result.route == "analysis"
    assert result.need_report is True
    assert result.analysis_plan is not None
    assert result.analysis_plan.analysis_type == "quality_status_summary"
    assert "PART_NO_86131AA000" in result.analysis_plan.required_columns
    assert "Reason_가스" in result.analysis_plan.required_columns


def test_part_no_count_planning_is_deterministic_without_llm() -> None:
    result = _planner_service().plan(
        user_input="PART_NO별 생산량을 계산해줘.",
        request_context=None,
        source_id="moldset_labeled_전처리_4",
        dataset_context=_dataset_context(),
        guideline_context=None,
        model_id=None,
    )

    assert result.route == "analysis"
    assert result.need_report is False
    assert result.analysis_plan is not None
    assert result.analysis_plan.analysis_type == "product_production_count"
    assert result.analysis_plan.group_by == ["PART_NO"]
    assert result.analysis_plan.required_columns == [
        "PART_NO_86131AA000",
        "PART_NO_86141AA000",
        "PART_NO_86141T1000",
    ]


def test_report_draft_falls_back_to_deterministic_markdown_on_timeout(
    monkeypatch: Any,
) -> None:
    def timeout_draft_report(**_: Any) -> str:
        raise TimeoutError("simulated report LLM timeout")

    monkeypatch.setattr(report_service_module, "draft_report", timeout_draft_report)
    service: Any = object.__new__(ReportService)
    service.default_model = "test-model"
    analysis_result = {
        "summary": "총 5건을 기준으로 품질 현황을 집계했습니다.",
        "execution_status": "success",
        "used_columns": ["PassOrFail", "PART_NO_86131AA000"],
        "raw_metrics": {
            "total_count": 5,
            "product_production": {"86131AA000": 1},
            "defect_reasons": {"가스": 3},
        },
        "table": [
            {
                "section": "product_production",
                "label": "86131AA000",
                "count": 1,
                "rate": 0.2,
            }
        ],
    }
    dataset_context = {
        "source_id": "moldset_labeled_전처리_4",
        "filename": "moldset_preprocessed.csv",
        "row_count_total": 5,
        "column_count": 7,
    }

    draft = service.build_report_draft(
        question="이 데이터의 전체 품질 현황을 요약하는 리포트를 작성해줘.",
        analysis_result=analysis_result,
        visualization_result=None,
        guideline_context=None,
        dataset_context=dataset_context,
        revision_instruction="",
        model_id=None,
        visualizations=[],
        default_model="test-model",
    )

    assert draft["status"] == "generated"
    summary = str(draft["summary"])
    assert summary.startswith("# 품질 현황 리포트")
    assert "총 5건을 기준으로 품질 현황을 집계했습니다." in summary
    assert "product_production" in summary
