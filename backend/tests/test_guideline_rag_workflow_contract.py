from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from backend.app.modules.planner.schemas import PlanningResult
from backend.app.modules.rag.service import RetrievedChunk
from backend.app.orchestration import builder
from backend.app.orchestration.builder import build_main_workflow
from backend.app.orchestration.evidence import build_evidence_contract
from backend.app.orchestration.workflows import guideline as guideline_workflow
from backend.app.orchestration.workflows.guideline import build_guideline_workflow


class _FakeGuidelineService:
    def __init__(
        self,
        guidelines: dict[str, SimpleNamespace] | None = None,
        *,
        active: SimpleNamespace | None = None,
    ) -> None:
        self._guidelines = guidelines or {}
        self._active = active

    def get_active_guideline(self) -> SimpleNamespace | None:
        return self._active

    def get_guideline_by_source_id(self, source_id: str) -> SimpleNamespace | None:
        return self._guidelines.get(source_id)


class _FakeGuidelineRagService:
    def __init__(self, *, retrieved: list[RetrievedChunk] | None = None) -> None:
        self._retrieved = retrieved or []
        self.queries: list[str] = []

    def ensure_index_for_guideline(self, guideline: SimpleNamespace) -> dict[str, str]:
        return {"status": "existing", "source_id": str(guideline.source_id)}

    def query_for_source(
        self,
        *,
        query: str,
        source_id: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        self.queries.append(source_id)
        return self._retrieved[:top_k]

    def build_context(self, retrieved: list[RetrievedChunk]) -> str:
        return "\n\n".join(item.content for item in retrieved)


class _PlannerMustNotRun:
    def plan(self, **_: Any) -> PlanningResult:
        raise AssertionError("guideline-only runs must not fall through to dataset planner")


class _GeneralPlanner:
    def plan(self, **_: Any) -> PlanningResult:
        return PlanningResult(route="general_question")


class _NoopRagService:
    def ensure_index_for_source(self, source_id: str) -> dict[str, str]:
        return {"status": "no_source", "source_id": source_id}

    def query_for_source(self, *, query: str, top_k: int, source_id: str) -> list[Any]:
        return []

    def build_context(self, retrieved: list[Any]) -> str:
        return ""


class _FakeGuidelineGateway:
    def __init__(self, *, default_model: str) -> None:
        self.default_model = default_model

    def invoke_structured(
        self,
        *,
        schema: type[Any],
        model_id: str | None,
        messages: list[Any],
    ) -> Any:
        return schema(evidence_summary="안전 한계 기준은 80도 이하입니다.")


def _guideline(source_id: str = "guideline-source") -> SimpleNamespace:
    return SimpleNamespace(
        source_id=source_id,
        guideline_id="guide_contract",
        filename="safety.pdf",
    )


def test_guideline_selected_without_dataset_reaches_guideline_evidence(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}
    source_id = "guideline-source"
    retrieved = [
        RetrievedChunk(
            source_id=source_id,
            chunk_id=0,
            score=0.91,
            content="안전 한계 기준은 80도 이하입니다.",
        )
    ]

    def answer_from_evidence(
        *,
        user_input: str,
        merged_context: dict[str, Any],
        evidence_package: dict[str, Any],
        answer_quality: dict[str, Any],
        model_id: str | None,
        default_model: str,
    ) -> str:
        captured["merged_context"] = merged_context
        captured["evidence_package"] = evidence_package
        captured["answer_quality"] = answer_quality
        return "가이드라인 근거: 안전 한계 기준은 80도 이하입니다."

    monkeypatch.setattr(guideline_workflow, "LLMGateway", _FakeGuidelineGateway)
    monkeypatch.setattr(builder, "answer_data_question", answer_from_evidence)
    monkeypatch.setattr(builder, "answer_general_question", lambda **_: "일반 답변")

    workflow = build_main_workflow(
        planner_service=_PlannerMustNotRun(),
        analysis_service=object(),
        preprocess_service=object(),
        eda_service=object(),
        rag_service=_NoopRagService(),
        guideline_service=_FakeGuidelineService({source_id: _guideline(source_id)}),
        guideline_rag_service=_FakeGuidelineRagService(retrieved=retrieved),
        visualization_service=object(),
        report_service=object(),
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": "안전 한계 기준을 알려줘",
            "active_guideline_source_id": source_id,
            "model_id": "test-model",
        }
    )

    assert result["output"]["type"] == "data_qa"
    assert result["output"]["content"].startswith("가이드라인 근거:")
    assert result["guideline_result"]["status"] == "retrieved"
    assert result["evidence_package"]["guideline_retrieved_count"] == 1
    assert result["answer_quality"]["answerable"] is True
    assert "guideline" in captured["merged_context"]["applied_steps"]


def test_guideline_selected_source_takes_priority_over_active_guideline(monkeypatch) -> None:
    selected_id = "selected-guideline"
    active_id = "active-guideline"
    selected = _guideline(selected_id)
    active = _guideline(active_id)
    monkeypatch.setattr(guideline_workflow, "LLMGateway", _FakeGuidelineGateway)
    guideline_service: Any = _FakeGuidelineService(
        {selected_id: selected, active_id: active},
        active=active,
    )
    guideline_rag_service = _FakeGuidelineRagService(
        retrieved=[
            RetrievedChunk(
                source_id=selected_id,
                chunk_id=0,
                score=0.91,
                content="PART_NAME은 제품명이고 PassOrFail=1은 불량입니다.",
            )
        ]
    )
    workflow = build_guideline_workflow(
        guideline_service=guideline_service,
        guideline_rag_service=cast(Any, guideline_rag_service),
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": "제품별 불량률 기준은?",
            "active_guideline_source_id": selected_id,
        }
    )

    assert result["active_guideline_source_id"] == selected_id
    assert guideline_rag_service.queries == [selected_id]
    assert result["guideline_result"]["status"] in {"retrieved", "no_evidence"}


def test_guideline_blank_selection_falls_back_to_active_guideline(
    monkeypatch,
) -> None:
    source_id = "guideline-source"
    active_guideline = _guideline(source_id)
    monkeypatch.setattr(guideline_workflow, "LLMGateway", _FakeGuidelineGateway)
    guideline_service: Any = _FakeGuidelineService(
        {source_id: active_guideline},
        active=active_guideline,
    )
    guideline_rag_service = _FakeGuidelineRagService(
        retrieved=[
            RetrievedChunk(
                source_id=source_id,
                chunk_id=0,
                score=0.91,
                content="PART_NAME은 제품명이고 PassOrFail=1은 불량입니다.",
            )
        ]
    )
    workflow = build_guideline_workflow(
        guideline_service=guideline_service,
        guideline_rag_service=cast(Any, guideline_rag_service),
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": "안전 기준은?",
            "active_guideline_source_id": "",
        }
    )

    assert result["active_guideline_source_id"] == source_id
    assert guideline_rag_service.queries == [source_id]
    assert result["guideline_result"]["status"] == "retrieved"
    assert result["guideline_result"]["retrieved_count"] == 1


def test_guideline_missing_selection_key_uses_active_guideline(monkeypatch) -> None:
    source_id = "guideline-source"
    active_guideline = _guideline(source_id)
    monkeypatch.setattr(guideline_workflow, "LLMGateway", _FakeGuidelineGateway)
    guideline_service: Any = _FakeGuidelineService(
        {source_id: active_guideline},
        active=active_guideline,
    )
    guideline_rag_service = _FakeGuidelineRagService(
        retrieved=[
            RetrievedChunk(
                source_id=source_id,
                chunk_id=0,
                score=0.91,
                content="PART_NAME은 제품명이고 PassOrFail=1은 불량입니다.",
            )
        ]
    )
    workflow = build_guideline_workflow(
        guideline_service=guideline_service,
        guideline_rag_service=cast(Any, guideline_rag_service),
        default_model="test-model",
    )

    result = workflow.invoke({"user_input": "안전 기준은?"})

    assert result["active_guideline_source_id"] == source_id
    assert guideline_rag_service.queries == [source_id]
    assert result["guideline_result"]["status"] == "retrieved"
    assert result["guideline_result"]["retrieved_count"] == 1


def test_guideline_missing_selection_key_without_active_is_no_active_guideline() -> None:
    guideline_service: Any = _FakeGuidelineService()
    guideline_rag_service: Any = _FakeGuidelineRagService()
    workflow = build_guideline_workflow(
        guideline_service=guideline_service,
        guideline_rag_service=cast(Any, guideline_rag_service),
        default_model="test-model",
    )

    result = workflow.invoke({"user_input": "안전 기준은?"})

    assert result["guideline_index_status"]["status"] == "no_active_guideline"
    assert result["guideline_result"]["status"] == "no_active_guideline"
    assert result["guideline_result"]["retrieved_count"] == 0


def test_guideline_context_includes_semantic_glossary_from_guideline_and_dataset(
    monkeypatch,
) -> None:
    source_id = "guideline-source"
    active_guideline = _guideline(source_id)

    monkeypatch.setattr(guideline_workflow, "LLMGateway", _FakeGuidelineGateway)

    workflow = build_guideline_workflow(
        guideline_service=cast(Any, _FakeGuidelineService(
            {source_id: active_guideline},
            active=active_guideline,
        )),
        guideline_rag_service=cast(Any, _FakeGuidelineRagService(
            retrieved=[
                RetrievedChunk(
                    source_id=source_id,
                    chunk_id=0,
                    score=0.91,
                    content=(
                        "PART_NAME은 제품명입니다. "
                        "PassOrFail 컬럼에서 1은 불량, 0은 정상입니다. "
                        "불량률은 불량 건수 / 전체 건수입니다."
                    ),
                )
            ]
        )),
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": "제품별 불량률을 분석해줘",
            "dataset_context": {
                "columns": ["PART_NO", "PART_NAME", "PassOrFail", "TimeStamp"],
                "numeric_columns": ["PassOrFail"],
                "categorical_columns": ["PART_NO", "PART_NAME"],
            },
        }
    )

    semantic_glossary = result["guideline_context"]["semantic_glossary"]
    assert semantic_glossary["product"]["columns"] == ["PART_NAME", "PART_NO"]
    assert semantic_glossary["defect_indicator"] == {
        "column": "PassOrFail",
        "defect_value": 1,
        "pass_value": 0,
    }
    assert semantic_glossary["defect_rate"]["formula"] == (
        "count(PassOrFail == 1) / count(*)"
    )


def test_guideline_stale_selection_is_guideline_missing() -> None:
    guideline_service: Any = _FakeGuidelineService()
    guideline_rag_service: Any = _FakeGuidelineRagService()
    workflow = build_guideline_workflow(
        guideline_service=guideline_service,
        guideline_rag_service=guideline_rag_service,
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": "안전 기준은?",
            "active_guideline_source_id": "deleted-guideline",
        }
    )

    assert result["active_guideline_source_id"] == "deleted-guideline"
    assert result["guideline_index_status"]["status"] == "guideline_missing"
    assert result["guideline_result"]["status"] == "guideline_missing"
    assert result["guideline_result"]["retrieved_count"] == 0


def test_no_guideline_no_dataset_stays_general_question(monkeypatch) -> None:
    monkeypatch.setattr(builder, "answer_general_question", lambda **_: "일반 답변")

    workflow = build_main_workflow(
        planner_service=_GeneralPlanner(),
        analysis_service=object(),
        preprocess_service=object(),
        eda_service=object(),
        rag_service=_NoopRagService(),
        guideline_service=_FakeGuidelineService(),
        guideline_rag_service=_FakeGuidelineRagService(),
        visualization_service=object(),
        report_service=object(),
        default_model="test-model",
    )

    result = workflow.invoke({"user_input": "안녕?", "model_id": "test-model"})

    assert result["output"] == {
        "type": "general_question",
        "content": "일반 답변",
    }
    assert "guideline_result" not in result


def test_selected_guideline_no_dataset_general_question_stays_general(
    monkeypatch,
) -> None:
    source_id = "guideline-source"

    monkeypatch.setattr(builder, "answer_general_question", lambda **_: "일반 답변")

    workflow = build_main_workflow(
        planner_service=_GeneralPlanner(),
        analysis_service=object(),
        preprocess_service=object(),
        eda_service=object(),
        rag_service=_NoopRagService(),
        guideline_service=_FakeGuidelineService({source_id: _guideline(source_id)}),
        guideline_rag_service=_FakeGuidelineRagService(),
        visualization_service=object(),
        report_service=object(),
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": "안녕?",
            "active_guideline_source_id": source_id,
            "model_id": "test-model",
        }
    )

    assert result["output"] == {
        "type": "general_question",
        "content": "일반 답변",
    }
    assert "guideline_result" not in result


def test_evidence_contract_warns_for_precise_guideline_absence_statuses() -> None:
    for status in ("no_selected_guideline", "guideline_missing"):
        evidence_package, answer_quality = build_evidence_contract(
            state={
                "analysis_result": {
                    "execution_status": "success",
                    "summary": "분석 근거는 충분합니다.",
                },
                "guideline_result": {
                    "status": status,
                    "retrieved_count": 0,
                    "evidence_summary": "선택한 가이드라인 근거가 없습니다.",
                },
            },
            merged_context={"applied_steps": ["analysis"]},
        )

        assert evidence_package.get("guideline_status") == status
        warnings = evidence_package.get("warnings", [])
        assert {str(warning.get("code")) for warning in warnings} == {status}
        assert answer_quality.get("answerable") is True
        assert answer_quality.get("status") == "answerable"
