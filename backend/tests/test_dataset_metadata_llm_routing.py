from __future__ import annotations

from collections.abc import Mapping
from types import SimpleNamespace
from typing import Never, Protocol, cast

import pytest

from backend.app.modules.profiling.schemas import DatasetContext
from backend.app.orchestration import builder


class _WorkflowWithInvoke(Protocol):
    def invoke(self, input_payload: Mapping[str, object]) -> Mapping[str, object]:
        ...


def _dataset_context() -> DatasetContext:
    return DatasetContext(
        source_id="dataset-source",
        filename="moldset_labeled.csv",
        available=True,
        row_count_total=2607,
        row_count_sample=3,
        column_count=9,
        columns=[
            "TimeStamp",
            "PART_NO",
            "PART_NAME",
            "EQUIP_NAME",
            "Mold_Temperature",
            "Injection_Pressure",
            "PassOrFail",
            "Reason",
            "Shift",
        ],
        dtypes={
            "TimeStamp": "datetime64[ns]",
            "PART_NO": "object",
            "PART_NAME": "object",
            "EQUIP_NAME": "object",
            "Mold_Temperature": "float64",
            "Injection_Pressure": "float64",
            "PassOrFail": "int64",
            "Reason": "object",
            "Shift": "object",
        },
        datetime_columns=["TimeStamp"],
        numeric_columns=["Mold_Temperature", "Injection_Pressure", "PassOrFail"],
        categorical_columns=["PART_NO", "PART_NAME", "EQUIP_NAME", "Reason", "Shift"],
        group_key_columns=["PART_NO", "PART_NAME", "EQUIP_NAME"],
    )


class _DatasetContextService:
    def build_context(
        self,
        source_id: str,
        *,
        include_ai_aliases: bool | None = None,
    ) -> DatasetContext:
        _ = include_ai_aliases
        return _dataset_context().model_copy(update={"source_id": source_id})


class _MetadataQaPlannerService:
    def __init__(self) -> None:
        self.dataset_context_service: _DatasetContextService = _DatasetContextService()

    def plan(self, **_: object) -> Never:
        raise AssertionError("metadata QA should not require planner validation")


class _NoopGuidelineService:
    def get_active_guideline(self) -> None:
        return None

    def get_guideline_by_source_id(self, source_id: str) -> None:
        _ = source_id
        return None


class _NoopGuidelineRagService:
    pass


class _NoopRagService:
    def ensure_index_for_source(self, source_id: str) -> dict[str, str]:
        raise AssertionError(f"metadata QA should not require RAG index: {source_id}")

    def query_for_source(
        self,
        *,
        query: str,
        top_k: int,
        source_id: str,
    ) -> list[object]:
        _ = (query, top_k, source_id)
        raise AssertionError("metadata QA should not query RAG")

    def build_context(self, retrieved: list[object]) -> str:
        _ = retrieved
        raise AssertionError("metadata QA should not build RAG context")


def test_column_summary_metadata_question_reaches_data_qa_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def answer_from_dataset_metadata(
        *,
        user_input: str,
        merged_context: dict[str, object],
        evidence_package: dict[str, object],
        answer_quality: dict[str, object],
        model_id: str | None,
        default_model: str,
    ) -> str:
        _ = (model_id, default_model)
        captured["user_input"] = user_input
        captured["merged_context"] = merged_context
        captured["evidence_package"] = evidence_package
        captured["answer_quality"] = answer_quality
        return "LLM metadata answer"

    monkeypatch.setattr(builder, "answer_data_question", answer_from_dataset_metadata)

    workflow = cast(
        _WorkflowWithInvoke,
        cast(
            object,
            builder.build_main_workflow(
                planner_service=_MetadataQaPlannerService(),
                analysis_service=SimpleNamespace(dataset_repository=None),
                preprocess_service=object(),
                eda_service=SimpleNamespace(reader=None),
                rag_service=_NoopRagService(),
                guideline_service=_NoopGuidelineService(),
                guideline_rag_service=_NoopGuidelineRagService(),
                visualization_service=object(),
                report_service=object(),
                default_model="test-model",
            ),
        ),
    )

    result = workflow.invoke(
        {
            "user_input": "이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘.",
            "source_id": "dataset-source",
            "model_id": "test-model",
        }
    )

    assert captured["user_input"] == "이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘."
    answer_quality = cast(Mapping[str, object], captured["answer_quality"])
    merged_context = cast(Mapping[str, object], captured["merged_context"])
    dataset_context = cast(Mapping[str, object], merged_context["dataset_context"])
    output = cast(Mapping[str, object], result["output"])
    fast_path_result = cast(Mapping[str, object], result["fast_path_result"])

    assert answer_quality["answerable"] is True
    assert dataset_context["columns"] == _dataset_context().columns
    assert output["type"] == "data_qa"
    assert output["content"] == "LLM metadata answer"
    assert fast_path_result["status"] == "skipped"


def test_analytic_schema_question_still_reaches_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_data_qa_is_called(**_: object) -> str:
        raise AssertionError("analytic schema question should not bypass planner")

    monkeypatch.setattr(builder, "answer_data_question", fail_if_data_qa_is_called)

    workflow = cast(
        _WorkflowWithInvoke,
        cast(
            object,
            builder.build_main_workflow(
                planner_service=_MetadataQaPlannerService(),
                analysis_service=SimpleNamespace(dataset_repository=None),
                preprocess_service=object(),
                eda_service=SimpleNamespace(reader=None),
                rag_service=_NoopRagService(),
                guideline_service=_NoopGuidelineService(),
                guideline_rag_service=_NoopGuidelineRagService(),
                visualization_service=object(),
                report_service=object(),
                default_model="test-model",
            ),
        ),
    )

    result = workflow.invoke(
        {
            "user_input": "analyze whether schema drift explains the defect rate",
            "source_id": "dataset-source",
            "model_id": "test-model",
        }
    )
    output = cast(Mapping[str, object], result["output"])

    assert result["final_status"] == "fail"
    assert output["type"] == "planning_failed"
