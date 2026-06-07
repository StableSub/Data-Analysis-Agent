from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.sandbox import AnalysisSandbox
from backend.app.modules.analysis.schemas import (
    AnalysisPlan,
    ExpectedOutputSpec,
    MetadataSnapshot,
    MetricSpec,
    QuestionUnderstanding,
    TimeContext,
    VisualizationHint,
)
from backend.app.modules.analysis.service import AnalysisService
from backend.app.modules.datasets.models import Dataset
from backend.app.modules.planner.service import PlannerService
from backend.app.modules.profiling.schemas import DatasetContext
from backend.app.orchestration.error_contract import (
    build_workflow_error,
    to_public_error,
)


def _write_pressure_dataset(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "Max_Injection_Pressure,EQUIP_CD,TimeStamp,PassOrFail",
                "101.0,A,2026-06-01T00:00:00,0",
                "102.0,A,2026-06-01T01:00:00,0",
                "103.0,A,2026-06-01T02:00:00,0",
                "104.0,A,2026-06-01T03:00:00,0",
                "450.0,B,2026-06-01T04:00:00,1",
                "98.0,B,2026-06-01T05:00:00,0",
                "99.0,B,2026-06-01T06:00:00,0",
                "97.0,B,2026-06-01T07:00:00,0",
            ]
        ),
        encoding="utf-8",
    )


def _write_nonnumeric_pressure_dataset(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "Max_Injection_Pressure,EQUIP_CD,TimeStamp,PassOrFail",
                "high,A,2026-06-01T00:00:00,0",
                "low,A,2026-06-01T01:00:00,0",
                "unknown,B,2026-06-01T02:00:00,1",
            ]
        ),
        encoding="utf-8",
    )


def _pressure_metadata() -> MetadataSnapshot:
    return MetadataSnapshot(
        columns=[
            "Max_Injection_Pressure",
            "EQUIP_CD",
            "TimeStamp",
            "PassOrFail",
            "PART_NO_86131AA000",
        ],
        dtypes={
            "Max_Injection_Pressure": "float64",
            "EQUIP_CD": "object",
            "TimeStamp": "datetime64[ns]",
            "PassOrFail": "int64",
            "PART_NO_86131AA000": "int64",
        },
        numeric_columns=["Max_Injection_Pressure", "PassOrFail", "PART_NO_86131AA000"],
        datetime_columns=["TimeStamp"],
        categorical_columns=["EQUIP_CD", "PART_NO_86131AA000"],
        row_count=8,
    )


def _nonnumeric_pressure_plan() -> AnalysisPlan:
    metadata = _pressure_metadata().model_copy(
        update={
            "dtypes": {
                "Max_Injection_Pressure": "object",
                "EQUIP_CD": "object",
                "TimeStamp": "datetime64[ns]",
                "PassOrFail": "int64",
                "PART_NO_86131AA000": "int64",
            },
            "numeric_columns": ["PassOrFail", "PART_NO_86131AA000"],
            "categorical_columns": [
                "Max_Injection_Pressure",
                "EQUIP_CD",
                "PART_NO_86131AA000",
            ],
        }
    )
    return _pressure_plan().model_copy(update={"metadata_snapshot": metadata})


def _pressure_dataset_context() -> DatasetContext:
    return DatasetContext(
        source_id="moldset_labeled_전처리_4",
        filename="pressure.csv",
        available=True,
        row_count_total=8,
        row_count_sample=8,
        column_count=5,
        columns=[
            "Max_Injection_Pressure",
            "EQUIP_CD",
            "TimeStamp",
            "PassOrFail",
            "PART_NO_86131AA000",
        ],
        dtypes={
            "Max_Injection_Pressure": "float64",
            "EQUIP_CD": "object",
            "TimeStamp": "datetime64[ns]",
            "PassOrFail": "int64",
            "PART_NO_86131AA000": "int64",
        },
        numeric_columns=["Max_Injection_Pressure", "PassOrFail", "PART_NO_86131AA000"],
        datetime_columns=["TimeStamp"],
        categorical_columns=["EQUIP_CD", "PART_NO_86131AA000"],
        group_key_columns=["EQUIP_CD", "PART_NO_86131AA000"],
    )


def _pressure_plan() -> AnalysisPlan:
    return AnalysisPlan(
        analysis_type="outlier_detection_and_root_cause_inference",
        objective="'Max_Injection_Pressure'에서 이상치가 있는지 확인하고 원인을 추정합니다.",
        required_columns=[
            "Max_Injection_Pressure",
            "EQUIP_CD",
            "TimeStamp",
            "PassOrFail",
        ],
        used_columns=[
            "Max_Injection_Pressure",
            "EQUIP_CD",
            "TimeStamp",
            "PassOrFail",
        ],
        group_by=["EQUIP_CD"],
        metrics=[
            MetricSpec(
                name="max_injection_pressure_avg",
                aggregation="avg",
                column="Max_Injection_Pressure",
                alias="Max_Injection_Pressure_avg",
            ),
            MetricSpec(
                name="max_injection_pressure_min",
                aggregation="min",
                column="Max_Injection_Pressure",
                alias="Max_Injection_Pressure_min",
            ),
            MetricSpec(
                name="max_injection_pressure_max",
                aggregation="max",
                column="Max_Injection_Pressure",
                alias="Max_Injection_Pressure_max",
            ),
            MetricSpec(
                name="defect_rate",
                aggregation="rate",
                column="PassOrFail",
                positive_value=1,
                alias="defect_rate",
            ),
        ],
        time_context=TimeContext(
            time_column="TimeStamp",
            range_type="none",
            grain=None,
        ),
        expected_output=ExpectedOutputSpec(
            require_summary=True,
            require_table=True,
            require_raw_metrics=True,
            expected_table_columns=[
                "EQUIP_CD",
                "Max_Injection_Pressure_avg",
                "Max_Injection_Pressure_min",
                "Max_Injection_Pressure_max",
                "defect_rate",
            ],
            allow_empty_table=True,
            minimum_rows=0,
            require_group_axis=True,
            require_outlier_info=True,
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
        empty_result_policy="success_with_empty_summary",
        metadata_snapshot=_pressure_metadata(),
        codegen_strategy="llm_codegen",
    )


def test_exact_quoted_column_is_grounded_from_raw_question() -> None:
    understanding = QuestionUnderstanding(
        analysis_goal=["이상치 탐지"],
        metric_keywords=["Max Injection Pressure"],
        group_keywords=[],
        ambiguity_status="clear",
    )

    result = AnalysisProcessor().ground_columns(
        question_understanding=understanding,
        dataset_meta=_pressure_metadata(),
        raw_question="'Max_Injection_Pressure'에서 이상치가 있는지 확인하고 원인을 추정해줘.",
    )

    assert result.resolved_columns["Max_Injection_Pressure"] == "Max_Injection_Pressure"
    assert result.confidence == 1.0


def test_explicit_outlier_question_uses_deterministic_planner_without_llm() -> None:
    class NoDatasetContextService:
        def build_context(self, source_id: str) -> DatasetContext:
            raise AssertionError(f"unexpected dataset context lookup: {source_id}")

    class NoLlmGateway:
        def invoke_structured(self, **_: Any) -> Any:
            raise AssertionError("explicit outlier planning must not call the LLM")

    planner = PlannerService(
        dataset_context_service=cast(Any, NoDatasetContextService()),
        analysis_processor=AnalysisProcessor(),
    )
    planner.llm = cast(Any, NoLlmGateway())

    result = planner.plan(
        user_input="'Max_Injection_Pressure'에서 이상치가 있는지 확인하고 원인을 추정해줘.",
        request_context="",
        source_id="moldset_labeled_전처리_4",
        dataset_context=_pressure_dataset_context(),
        guideline_context={},
        model_id="gpt-5-nano",
    )

    assert result.route == "analysis"
    assert result.analysis_plan is not None
    assert result.analysis_plan.analysis_type == "outlier_detection_and_root_cause_inference"
    assert result.analysis_plan.used_columns == [
        "Max_Injection_Pressure",
        "EQUIP_CD",
        "PassOrFail",
        "TimeStamp",
    ]
    assert result.analysis_plan.expected_output.require_outlier_info is True
    assert result.analysis_plan.expected_output.require_time_axis is False


def test_sandbox_execution_failure_recovers_with_outlier_fallback(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "pressure.csv"
    _write_pressure_dataset(dataset_path)

    class RuntimeFailingRunService:
        def generate_analysis_code(self, **_: Any) -> str:
            return (
                "summary = ''\n"
                "table = []\n"
                "raw_metrics = {}\n"
                "used_columns = ['Max_Injection_Pressure', 'EQUIP_CD', 'TimeStamp', 'PassOrFail']\n"
                "raise RuntimeError('forced runtime failure before JSON output')\n"
                "print(json.dumps({'summary': summary, 'table': table, 'raw_metrics': raw_metrics, 'used_columns': used_columns}, ensure_ascii=False))"
            )

        def repair_analysis_code(self, **_: Any) -> str:
            raise AssertionError("max_retries=0 should not request LLM repair")

    service: Any = object.__new__(AnalysisService)
    service.run_service = RuntimeFailingRunService()
    service.processor = AnalysisProcessor()
    service.sandbox = AnalysisSandbox(timeout_seconds=5)
    service.max_retries = 0
    dataset = Dataset(
        source_id="moldset_labeled_전처리_4",
        filename="pressure.csv",
        storage_path=str(dataset_path),
    )

    bundle = service._run_code_generation_loop(
        question="'Max_Injection_Pressure'에서 이상치가 있는지 확인하고 원인을 추정해줘.",
        dataset=dataset,
        analysis_plan=_pressure_plan(),
        model_id=None,
    )

    assert bundle["final_status"] == "success"
    assert bundle["deterministic_fallback_used"] is True
    result = bundle["analysis_result"]
    assert result.execution_status == "success"
    assert result.raw_metrics["outliers"]["target_column"] == "Max_Injection_Pressure"
    assert result.raw_metrics["outliers"]["outlier_count"] >= 1
    assert "Max_Injection_Pressure" in result.summary
    assert "PART_NO_86131AA000" not in result.used_columns


def test_nonnumeric_outlier_target_returns_actionable_validation_failure(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "pressure_nonnumeric.csv"
    _write_nonnumeric_pressure_dataset(dataset_path)

    class NoRunService:
        def generate_analysis_code(self, **_: Any) -> str:
            raise AssertionError("deterministic outlier code should run before LLM codegen")

        def repair_analysis_code(self, **_: Any) -> str:
            raise AssertionError("deterministic validation failure should not need repair")

    service: Any = object.__new__(AnalysisService)
    service.run_service = NoRunService()
    service.processor = AnalysisProcessor()
    service.sandbox = AnalysisSandbox(timeout_seconds=5)
    service.max_retries = 0
    dataset = Dataset(
        source_id="qa-nonnumeric-pressure",
        filename="pressure_nonnumeric.csv",
        storage_path=str(dataset_path),
    )

    bundle = service._run_code_generation_loop(
        question="'Max_Injection_Pressure'에서 이상치가 있는지 확인하고 원인을 추정해줘.",
        dataset=dataset,
        analysis_plan=_nonnumeric_pressure_plan(),
        model_id=None,
    )

    assert bundle["final_status"] == "fail"
    result = bundle["analysis_result"]
    assert result.error_stage == "result_validation"
    error = bundle["analysis_error"]
    assert error.detail["failed_column"] == "Max_Injection_Pressure"
    assert "숫자 값" in error.detail["reason_summary"]
    assert "숫자 형식" in error.detail["suggested_action"]


def test_unrecoverable_outlier_failure_returns_actionable_public_error() -> None:
    workflow_error = build_workflow_error(
        stage="sandbox_execution",
        error_code="analysis_execution_failed",
        source="analysis_validation",
        output_type="analysis_failed",
        retryable=True,
        diagnostic_message=(
            "Traceback (most recent call last): File "
            "\"/tmp/generated_analysis.py\", line 1, in <module>"
        ),
        details={
            "internal_stage": "sandbox_execution",
            "failed_column": "Max_Injection_Pressure",
            "operation": "numeric outlier detection",
            "reason_summary": "대상 컬럼에 숫자로 변환 가능한 값이 없습니다.",
            "suggested_action": "Max_Injection_Pressure 컬럼의 숫자 형식과 결측값을 확인해 주세요.",
        },
    )

    public_error = to_public_error(workflow_error)

    assert public_error["stage"] == "sandbox_execution"
    assert public_error["failed_column"] == "Max_Injection_Pressure"
    assert public_error["operation"] == "numeric outlier detection"
    assert "Max_Injection_Pressure" in public_error["message"]
    assert "숫자" in public_error["message"]
    assert "확인" in public_error["message"]
    assert "Traceback" not in public_error["message"]
    assert "/tmp/generated_analysis.py" not in public_error["message"]
