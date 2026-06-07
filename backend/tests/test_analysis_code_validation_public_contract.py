from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.sandbox import AnalysisSandbox
from backend.app.modules.analysis.schemas import (
    AnalysisError,
    AnalysisPlan,
    ExpectedOutputSpec,
    MetadataSnapshot,
    MetricSpec,
    VisualizationHint,
)
from backend.app.modules.analysis.service import AnalysisService
from backend.app.modules.chat.service import ChatService
from backend.app.modules.datasets.models import Dataset
from backend.app.orchestration.client import AgentClient
from backend.app.orchestration.error_contract import (
    build_workflow_error,
    public_message_for_stage,
    to_public_error,
)

FORBIDDEN_CODE_VALIDATION_MESSAGE = (
    "분석 코드를 검증하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
)
ANALYSIS_REPAIR_FAILED_MESSAGE = (
    "분석 코드를 자동으로 수정했지만 실행 가능한 형태로 만들지 못했습니다. "
    "질문 범위나 기준 컬럼을 좁혀 다시 실행해 주세요."
)


def _serialized(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _assert_no_public_code_validation(value: Any) -> None:
    text = _serialized(value)
    assert FORBIDDEN_CODE_VALIDATION_MESSAGE not in text
    assert '"error_stage": "code_validation"' not in text
    assert '"stage": "code_validation"' not in text


def _minimal_group_by_count_plan() -> AnalysisPlan:
    return AnalysisPlan(
        analysis_type="group_by_count",
        objective="불량 사유별 건수를 계산합니다.",
        required_columns=["PassOrFail", "Reason"],
        used_columns=["PassOrFail", "Reason"],
        group_by=["Reason"],
        metrics=[
            MetricSpec(
                name="count",
                aggregation="count",
                column=None,
                alias="count",
            )
        ],
        expected_output=ExpectedOutputSpec(
            require_summary=True,
            require_table=True,
            require_raw_metrics=False,
            expected_table_columns=["Reason", "count"],
            allow_empty_table=True,
            minimum_rows=0,
            require_group_axis=True,
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
        empty_result_policy="success_with_empty_summary",
        metadata_snapshot=MetadataSnapshot(
            columns=["PassOrFail", "Reason"],
            row_count=2,
        ),
        codegen_strategy="llm_codegen",
    )


def _unsupported_group_by_plan() -> AnalysisPlan:
    return _minimal_group_by_count_plan().model_copy(
        update={
            "metrics": [
                MetricSpec(name="count", aggregation="count", column=None, alias="count"),
                MetricSpec(
                    name="reason_sum",
                    aggregation="sum",
                    column="Reason",
                    alias="reason_sum",
                ),
            ]
        }
    )


def _write_dataset(path: Path) -> None:
    path.write_text("PassOrFail,Reason\n1,가스\n1,미성형\n", encoding="utf-8")


class _InvalidCodeRunService:
    def generate_analysis_code(self, **_: Any) -> str:
        return "result = df.groupby('Reason').size()"

    def repair_analysis_code(self, **kwargs: Any) -> str:
        error = kwargs["analysis_error"]
        assert isinstance(error, AnalysisError)
        return "result = df.groupby('Reason').size()"


def _build_code_validation_failure_bundle(
    tmp_path: Path,
    *,
    analysis_plan: AnalysisPlan | None = None,
) -> dict[str, Any]:
    dataset_path = tmp_path / "data.csv"
    _write_dataset(dataset_path)
    service: Any = object.__new__(AnalysisService)
    service.run_service = _InvalidCodeRunService()
    service.processor = AnalysisProcessor()
    service.sandbox = AnalysisSandbox(timeout_seconds=5)
    service.max_retries = 0
    dataset = Dataset(
        source_id="source-1",
        filename="data.csv",
        storage_path=str(dataset_path),
    )
    return service._run_code_generation_loop(
        question="불량 사유별 건수를 분석해줘.",
        dataset=dataset,
        analysis_plan=analysis_plan or _minimal_group_by_count_plan(),
        model_id=None,
    )


def _collect(coro_or_agen: Any) -> list[dict[str, Any]]:
    async def _run() -> list[dict[str, Any]]:
        return [event async for event in coro_or_agen]

    return asyncio.run(_run())


def _make_agent(snapshots: list[dict[str, Any]]) -> AgentClient:
    class FakeWorkflow:
        async def astream(self, input_payload: Any, config: Any, *, stream_mode: str):
            for snapshot in snapshots:
                yield snapshot

    @asynccontextmanager
    async def fake_runtime():
        yield SimpleNamespace(workflow=FakeWorkflow())

    return AgentClient(workflow_runtime_factory=fake_runtime)


def test_existing_sandbox_execution_public_message_contract_is_preserved() -> None:
    assert (
        public_message_for_stage("sandbox_execution")
        == "분석 코드를 실행하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    )


def test_retry_exhausted_code_validation_maps_to_public_analysis_repair_failed(
    tmp_path: Path,
) -> None:
    bundle = _build_code_validation_failure_bundle(
        tmp_path,
        analysis_plan=_unsupported_group_by_plan(),
    )
    analysis_error = bundle["analysis_error"]
    assert analysis_error is not None

    workflow_error = build_workflow_error(
        stage=analysis_error.stage,
        error_code="analysis_execution_failed",
        source="analysis_validation",
        output_type="analysis_failed",
        retryable=True,
        diagnostic_message=analysis_error.detail["diagnostic_message"],
        details=analysis_error.detail,
    )
    public_error = to_public_error(workflow_error)

    assert public_error["stage"] == "analysis_repair_failed"
    assert public_error["error_stage"] == "analysis_repair_failed"
    assert public_error["error_code"] == "analysis_repair_failed"
    assert public_error["message"] == ANALYSIS_REPAIR_FAILED_MESSAGE
    _assert_no_public_code_validation(public_error)


def test_error_contract_maps_code_validation_to_analysis_repair_failed() -> None:
    assert public_message_for_stage("code_validation") == ANALYSIS_REPAIR_FAILED_MESSAGE
    assert public_message_for_stage("code_validation") != FORBIDDEN_CODE_VALIDATION_MESSAGE

    public_error = to_public_error(
        {
            "stage": "code_validation",
            "error_code": "analysis_execution_failed",
            "source": "analysis_validation",
            "output_type": "analysis_failed",
            "retryable": True,
            "safe_message": FORBIDDEN_CODE_VALIDATION_MESSAGE,
            "diagnostic_message": "ValueError: generated code is missing output keys: summary",
            "details": {"internal_stage": "code_validation"},
        }
    )

    assert public_error["stage"] == "analysis_repair_failed"
    assert public_error["error_stage"] == "analysis_repair_failed"
    assert public_error["error_code"] == "analysis_repair_failed"
    assert public_error["message"] == ANALYSIS_REPAIR_FAILED_MESSAGE
    _assert_no_public_code_validation(public_error)


def test_public_sse_projection_never_emits_code_validation_stage() -> None:
    agent = _make_agent(
        [
            {
                "output": {
                    "type": "analysis_failed",
                    "content": FORBIDDEN_CODE_VALIDATION_MESSAGE,
                },
                "final_status": "fail",
                "analysis_result": {
                    "execution_status": "fail",
                    "error_stage": "code_validation",
                    "error_message": FORBIDDEN_CODE_VALIDATION_MESSAGE,
                    "quality_status": "invalid",
                },
            }
        ]
    )

    events = _collect(agent.astream_with_trace(session_id="1", question="불량 건수"))
    error = next(event for event in events if event.get("type") == "error")

    assert error["stage"] == "analysis_repair_failed"
    assert error["error_stage"] == "analysis_repair_failed"
    assert error["error_code"] == "analysis_repair_failed"
    assert error["error_message"] == ANALYSIS_REPAIR_FAILED_MESSAGE
    _assert_no_public_code_validation(error)


def test_chat_done_error_fields_prefer_public_error_over_internal_analysis_stage() -> None:
    error_fields = ChatService._extract_done_error_fields(
        report_result=None,
        preprocess_result=None,
        analysis_result={
            "execution_status": "fail",
            "error_stage": "code_validation",
            "error_message": FORBIDDEN_CODE_VALIDATION_MESSAGE,
        },
        visualization_result=None,
        output_payload={
            "type": "analysis_failed",
            "content": ANALYSIS_REPAIR_FAILED_MESSAGE,
            "public_error": {
                "stage": "analysis_repair_failed",
                "error_stage": "analysis_repair_failed",
                "message": ANALYSIS_REPAIR_FAILED_MESSAGE,
                "error_message": ANALYSIS_REPAIR_FAILED_MESSAGE,
            },
        },
    )

    assert error_fields["error_stage"] == "analysis_repair_failed"
    assert error_fields["error_message"] == ANALYSIS_REPAIR_FAILED_MESSAGE
    _assert_no_public_code_validation(error_fields)


def test_internal_diagnostic_keeps_original_code_validation_cause(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "data.csv"
    _write_dataset(dataset_path)
    service: Any = object.__new__(AnalysisService)
    service.run_service = _InvalidCodeRunService()
    service.processor = AnalysisProcessor()
    service.sandbox = AnalysisSandbox(timeout_seconds=5)
    service.max_retries = 0
    dataset = Dataset(
        source_id="source-1",
        filename="data.csv",
        storage_path=str(dataset_path),
    )
    bundle = service._run_code_generation_loop(
        question="불량 사유별 복합 지표를 분석해줘.",
        dataset=dataset,
        analysis_plan=_unsupported_group_by_plan(),
        model_id=None,
    )
    analysis_error = bundle["analysis_error"]

    assert analysis_error.stage == "code_validation"
    assert analysis_error.detail["internal_stage"] == "code_validation"
    assert "generated code" in analysis_error.detail["diagnostic_message"]


def test_invalid_llm_code_falls_back_to_deterministic_group_by_count(
    tmp_path: Path,
) -> None:
    bundle = _build_code_validation_failure_bundle(tmp_path)
    result = bundle["analysis_result"]

    assert bundle["final_status"] == "success"
    assert bundle["deterministic_fallback_used"] is True
    assert result.execution_status == "success"
    assert result.table == [
        {"Reason": "가스", "count": 1},
        {"Reason": "미성형", "count": 1},
    ]
    _assert_no_public_code_validation(result.model_dump())


def test_unsupported_plan_does_not_fake_success_and_uses_analysis_repair_failed_public_stage(
    tmp_path: Path,
) -> None:
    plan = _unsupported_group_by_plan()
    dataset_path = tmp_path / "data.csv"
    _write_dataset(dataset_path)
    service: Any = object.__new__(AnalysisService)
    service.run_service = _InvalidCodeRunService()
    service.processor = AnalysisProcessor()
    service.sandbox = AnalysisSandbox(timeout_seconds=5)
    service.max_retries = 0
    dataset = Dataset(
        source_id="source-1",
        filename="data.csv",
        storage_path=str(dataset_path),
    )

    bundle = service._run_code_generation_loop(
        question="불량 사유별 복합 지표를 분석해줘.",
        dataset=dataset,
        analysis_plan=plan,
        model_id=None,
    )
    analysis_error = bundle["analysis_error"]
    workflow_error = build_workflow_error(
        stage=analysis_error.stage,
        error_code="analysis_execution_failed",
        source="analysis_validation",
        output_type="analysis_failed",
        retryable=True,
        diagnostic_message=analysis_error.detail["diagnostic_message"],
        details=analysis_error.detail,
    )
    public_error = to_public_error(workflow_error)

    assert bundle["final_status"] == "fail"
    assert bundle.get("deterministic_fallback_used") is not True
    assert analysis_error.stage == "code_validation"
    assert analysis_error.detail["internal_stage"] == "code_validation"
    assert public_error["stage"] == "analysis_repair_failed"
    _assert_no_public_code_validation(public_error)
