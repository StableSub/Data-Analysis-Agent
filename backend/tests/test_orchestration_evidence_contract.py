from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Any, cast

from backend.app.orchestration import ai, builder
from backend.app.orchestration.evidence import build_evidence_contract


def _warning_codes(payload: dict) -> set[str]:
    return {str(warning.get("code")) for warning in payload.get("warnings", [])}


def test_evidence_contract_prefers_structured_analysis_and_keeps_mild_no_evidence_answerable() -> None:
    evidence_package, answer_quality = build_evidence_contract(
        state={
            "source_id": "raw-source",
            "handoff": {"ask_analysis": True},
            "preprocess_result": {
                "status": "applied",
                "output_source_id": "clean-source",
                "output_filename": "clean.csv",
            },
            "analysis_plan": {"used_columns": ["fallback_only"]},
            "analysis_result": {
                "execution_status": "success",
                "summary": "평균 매출은 42입니다.",
                "raw_metrics": {"avg_sales": 42},
                "table": [{"segment": "A", "sales": 42}],
                "used_columns": ["sales", "sales", " segment "],
            },
            "rag_result": {"source_id": "rag-source", "retrieved_count": "0"},
            "guideline_result": {
                "status": "no_active_guideline",
                "retrieved_count": 0,
                "evidence_summary": "활성 가이드라인이 없습니다.",
            },
        },
        merged_context={"applied_steps": ["preprocess", "analysis", "analysis"]},
    )

    assert evidence_package["source_id"] == "clean-source"
    assert evidence_package["filename"] == "clean.csv"
    assert evidence_package["used_columns"] == ["sales", "segment"]
    assert evidence_package["analysis_status"] == "success"
    assert evidence_package["analysis_metrics"] == {"avg_sales": 42}
    assert evidence_package["analysis_table"] == [{"segment": "A", "sales": 42}]
    assert evidence_package["applied_steps"] == ["preprocess", "analysis"]
    assert _warning_codes(evidence_package) == {"rag_no_evidence", "no_active_guideline"}
    assert answer_quality == {
        "answerable": True,
        "status": "answerable",
        "warnings": evidence_package["warnings"],
    }


def test_evidence_contract_marks_requested_missing_analysis_unanswerable() -> None:
    evidence_package, answer_quality = build_evidence_contract(
        state={
            "source_id": "source-1",
            "handoff": {"ask_analysis": True},
            "rag_result": {"retrieved_count": 0, "evidence_summary": "검색 결과가 없습니다."},
        },
        merged_context={},
    )

    assert evidence_package["analysis_status"] == "missing"
    assert _warning_codes(evidence_package) == {"analysis_missing", "rag_no_evidence"}
    assert answer_quality["answerable"] is False
    assert answer_quality["status"] == "unanswerable"
    assert "충분하지 않습니다" in answer_quality["abstain_reason"]


def test_evidence_contract_keeps_retrieval_answerable_but_limited_when_analysis_failed() -> None:
    evidence_package, answer_quality = build_evidence_contract(
        state={
            "source_id": "source-1",
            "handoff": {"ask_analysis": True},
            "analysis_result": {
                "execution_status": "fail",
                "error_message": "컬럼을 찾을 수 없습니다.",
            },
            "rag_result": {
                "retrieved_count": 2,
                "evidence_summary": "관련 문서 근거 2건을 찾았습니다.",
            },
        },
        merged_context={},
    )

    assert evidence_package["analysis_status"] == "fail"
    assert evidence_package["rag_retrieved_count"] == 2
    assert {"analysis_failed", "analysis_missing"}.issubset(_warning_codes(evidence_package))
    assert answer_quality["answerable"] is True
    assert answer_quality["status"] == "limited"


def test_answer_data_question_serializes_evidence_contract(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeGateway:
        def __init__(self, *, default_model: str) -> None:
            captured["default_model"] = default_model

        def invoke(self, *, model_id: str | None, messages: list[object]) -> SimpleNamespace:
            captured["model_id"] = model_id
            captured["messages"] = messages
            return SimpleNamespace(content="answer")

    monkeypatch.setattr(ai, "LLMGateway", FakeGateway)

    answer = ai.answer_data_question(
        user_input="매출 평균은?",
        merged_context={"analysis_result": {"summary": "42"}},
        evidence_package={"analysis_metrics": {"avg_sales": 42}},
        answer_quality={"answerable": True, "status": "answerable"},
        model_id="test-model",
        default_model="default-model",
    )

    assert answer == "answer"
    assert captured["default_model"] == "default-model"
    assert captured["model_id"] == "test-model"
    messages = cast(list[Any], captured["messages"])
    human_message = messages[1]
    assert "evidence_package" in human_message.content
    assert "answer_quality" in human_message.content
    assert "avg_sales" in human_message.content
    assert "merged_context" in human_message.content


def test_builder_wires_evidence_contract_into_merge_data_qa_and_analysis_fail_paths() -> None:
    source = inspect.getsource(builder.build_main_workflow)

    assert "build_evidence_contract" in source
    assert '"evidence_package": evidence_package' in source
    assert '"answer_quality": answer_quality' in source
    assert "answer_quality.get(\"answerable\") is False" in source
    assert "analysis_fail_terminal" in source
    assert '"fail": "analysis_fail_terminal"' in source
