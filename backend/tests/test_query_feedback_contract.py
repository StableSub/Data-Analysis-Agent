from __future__ import annotations

import asyncio
from collections.abc import Sequence
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, Dict

from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from backend.app.core.ai import LLMGateway
from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.planner.service import PlannerService
from backend.app.modules.profiling.schemas import DatasetContext
from backend.app.modules.query_feedback import (
    QueryFeedback,
    QueryFeedbackAction,
    QueryFeedbackContext,
    QueryFeedbackGenerator,
)
from backend.app.orchestration.builder import build_main_workflow
from backend.app.orchestration.client import AgentClient
from backend.tests.guideline_first_fakes import (
    ActiveGuidelineService,
    FakeGuidelineRagService,
    NoopRagService,
)


MISSING_COLUMN_QUESTION = (
    "Mold_Temperature 컬럼과 Max_Injection_Pressure 컬럼의 상관관계를 분석해줘."
)


class _StaticMoldDatasetContextService:
    def build_context(
        self,
        source_id: str,
        *,
        include_ai_aliases: bool | None = None,
    ) -> DatasetContext:
        _ = include_ai_aliases
        return _mold_dataset_context().model_copy(update={"source_id": source_id})


class _UnexpectedPlannerLLM(LLMGateway):
    def invoke_structured(
        self,
        *,
        schema: type[BaseModel],
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ) -> BaseModel:
        _ = (schema, messages, model_id, temperature)
        raise AssertionError("missing explicit column should not invoke planner LLM")


class _FeedbackLLM(LLMGateway):
    def __init__(self) -> None:
        super().__init__(default_model="test-model")
        self.prompt_text = ""

    def invoke_structured(
        self,
        *,
        schema: type[BaseModel],
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ) -> BaseModel:
        _ = (model_id, temperature)
        self.prompt_text = "\n".join(
            str(getattr(message, "content", "")) for message in messages
        )
        if schema is QueryFeedback:
            return QueryFeedback(
                title="없는 컬럼을 실제 컬럼으로 바꾸세요",
                message=(
                    "질문에 쓴 Mold_Temperature는 현재 데이터에 없으므로 "
                    "Mold_Temperature_1 같은 실제 컬럼명을 사용해야 합니다."
                ),
                actions=[
                    QueryFeedbackAction(
                        label="실제 컬럼명으로 질문 고치기",
                        description=(
                            "Mold_Temperature 대신 Mold_Temperature_1과 "
                            "Max_Injection_Pressure의 상관관계를 요청해 주세요."
                        ),
                        prompt=(
                            "Mold_Temperature_1 컬럼과 Max_Injection_Pressure 컬럼의 "
                            "상관관계를 분석해줘."
                        ),
                    )
                ],
            )
        raise AssertionError(f"unexpected schema: {schema}")


class _FailingFeedbackLLM(LLMGateway):
    def invoke_structured(
        self,
        *,
        schema: type[BaseModel],
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ) -> BaseModel:
        _ = (schema, messages, model_id, temperature)
        raise TimeoutError("feedback LLM timed out")


def test_missing_explicit_column_uses_llm_query_feedback() -> None:
    feedback_llm = _FeedbackLLM()
    planner_service = _planner_service(feedback_llm)

    result = planner_service.plan(
        user_input=MISSING_COLUMN_QUESTION,
        request_context=None,
        source_id="moldset-source",
        dataset_context=_mold_dataset_context(),
        guideline_context=None,
        model_id="test-model",
    )

    assert result.needs_clarification is True
    assert result.query_feedback is not None
    assert result.query_feedback.title == "없는 컬럼을 실제 컬럼으로 바꾸세요"
    assert "Mold_Temperature_1" in result.query_feedback.actions[0].description
    assert MISSING_COLUMN_QUESTION in feedback_llm.prompt_text
    assert "Mold_Temperature" in feedback_llm.prompt_text
    assert "Mold_Temperature_1" in feedback_llm.prompt_text


def test_main_workflow_clarification_output_includes_query_feedback() -> None:
    workflow = build_main_workflow(
        planner_service=_planner_service(_FeedbackLLM()),
        analysis_service=object(),
        preprocess_service=object(),
        eda_service=object(),
        rag_service=NoopRagService(),
        guideline_service=ActiveGuidelineService(active=None, guidelines={}),
        guideline_rag_service=FakeGuidelineRagService(),
        visualization_service=object(),
        report_service=object(),
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": MISSING_COLUMN_QUESTION,
            "source_id": "moldset-source",
            "model_id": "test-model",
        }
    )

    feedback = result["output"]["query_feedback"]
    assert result["output"]["type"] == "clarification"
    assert feedback["title"] == "없는 컬럼을 실제 컬럼으로 바꾸세요"
    assert "Mold_Temperature_1" in feedback["actions"][0]["description"]
    assert "prompt" not in feedback["actions"][0]


def test_query_feedback_falls_back_when_llm_generation_fails() -> None:
    generator = QueryFeedbackGenerator(
        default_model="test-model",
        llm=_FailingFeedbackLLM(default_model="test-model"),
    )

    feedback = generator.generate(
        QueryFeedbackContext(
            user_input=MISSING_COLUMN_QUESTION,
            issue_type="missing_column",
            stage="plan_validation",
            message="현재 데이터에는 `Mold_Temperature` 컬럼이 없습니다.",
            missing_column="Mold_Temperature",
            related_columns=["Mold_Temperature_1"],
            available_columns=["Mold_Temperature_1", "Max_Injection_Pressure"],
        ),
        model_id="test-model",
    )

    serialized = str(feedback.model_dump())
    assert "Mold_Temperature" in serialized
    assert "Mold_Temperature_1" in serialized
    assert "feedback LLM timed out" not in serialized
    assert feedback.actions


def test_failed_workflow_event_adds_query_feedback_from_public_error() -> None:
    agent = _make_agent(
        [
            {
                "user_input": "'BadColumn'에서 이상치가 있는지 확인해줘.",
                "final_status": "fail",
                "workflow_error": {
                    "stage": "result_validation",
                    "error_code": "analysis_validation_failed",
                    "source": "analysis_validation",
                    "output_type": "analysis_failed",
                    "retryable": False,
                    "safe_message": "분석 결과를 검증하는 중 오류가 발생했습니다.",
                    "diagnostic_message": "column BadColumn does not exist",
                    "details": {
                        "failed_column": "BadColumn",
                        "operation": "outlier_detection",
                        "reason_summary": "BadColumn 컬럼이 데이터셋에 없습니다.",
                        "suggested_action": "실제 수치 컬럼명을 사용해 주세요.",
                    },
                },
            }
        ],
        feedback_llm=_FeedbackLLM(),
    )

    events = _collect(agent.astream_with_trace(session_id="1", question="bad query"))
    error = next(event for event in events if event.get("type") == "error")

    assert error["query_feedback"]["title"] == "없는 컬럼을 실제 컬럼으로 바꾸세요"
    assert error["output"]["query_feedback"] == error["query_feedback"]
    assert error["public_error"]["failed_column"] == "BadColumn"


def _planner_service(feedback_llm: LLMGateway) -> PlannerService:
    service = PlannerService(
        dataset_context_service=_StaticMoldDatasetContextService(),
        analysis_processor=AnalysisProcessor(),
        default_model="test-model",
    )
    service.llm = _UnexpectedPlannerLLM(default_model="test-model")
    service.query_feedback_generator = QueryFeedbackGenerator(
        default_model="test-model",
        llm=feedback_llm,
    )
    return service


def _mold_dataset_context() -> DatasetContext:
    temperature_columns = [f"Mold_Temperature_{number}" for number in range(1, 13)]
    columns = [
        "Max_Injection_Pressure",
        *temperature_columns,
        "PassOrFail",
    ]
    return DatasetContext(
        source_id="moldset-source",
        filename="moldset.csv",
        available=True,
        row_count_total=100,
        row_count_sample=3,
        column_count=len(columns),
        columns=columns,
        dtypes={column: "float64" for column in columns},
        numeric_columns=columns,
        categorical_columns=[],
        sample_rows=[],
    )


def _collect(coro_or_agen: Any) -> list[Dict[str, Any]]:
    async def _run() -> list[Dict[str, Any]]:
        return [event async for event in coro_or_agen]

    return asyncio.run(_run())


def _make_agent(
    snapshots: list[Dict[str, Any]],
    *,
    feedback_llm: LLMGateway,
) -> AgentClient:
    class FakeWorkflow:
        async def astream(self, input_payload: Any, config: Any, *, stream_mode: str):
            _ = (input_payload, config, stream_mode)
            for snapshot in snapshots:
                yield snapshot

    @asynccontextmanager
    async def fake_runtime():
        yield SimpleNamespace(workflow=FakeWorkflow())

    return AgentClient(
        workflow_runtime_factory=fake_runtime,
        default_model="test-model",
        query_feedback_generator=QueryFeedbackGenerator(
            default_model="test-model",
            llm=feedback_llm,
        ),
    )
