from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator, Mapping
from types import SimpleNamespace
from typing import Any, cast

from backend.app.orchestration import ai, builder
from backend.app.orchestration.evidence import (
    build_evidence_contract,
    is_dataset_metadata_question,
)
from backend.app.orchestration.workflows import analysis
from backend.app.modules.chat.service import ChatService


def _warning_codes(payload: Mapping[str, object]) -> set[str]:
    warnings = payload.get("warnings", [])
    if not isinstance(warnings, list):
        return set()
    return {
        str(warning.get("code"))
        for warning in warnings
        if isinstance(warning, Mapping)
    }


async def _fake_agent_stream(*events: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    for event in events:
        yield event


async def _collect_events(stream: AsyncIterator[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event async for event in stream]


class _FakeChatRepository:
    def __init__(self) -> None:
        self.messages: list[tuple[object, str, str]] = []

    def append_message(self, session: object, role: str, content: str) -> None:
        self.messages.append((session, role, content))


def _make_chat_service(repo: _FakeChatRepository | None = None) -> ChatService:
    return ChatService(
        agent=cast(Any, object()),
        repository=cast(Any, repo or _FakeChatRepository()),
        dataset_repository=cast(Any, object()),
    )


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

    assert evidence_package.get("source_id") == "clean-source"
    assert evidence_package.get("filename") == "clean.csv"
    assert evidence_package.get("used_columns") == ["sales", "segment"]
    assert evidence_package.get("analysis_status") == "success"
    assert evidence_package.get("analysis_metrics") == {"avg_sales": 42}
    assert evidence_package.get("analysis_table") == [{"segment": "A", "sales": 42}]
    assert evidence_package.get("applied_steps") == ["preprocess", "analysis"]
    assert _warning_codes(evidence_package) == {"rag_no_evidence", "no_active_guideline"}
    assert answer_quality == {
        "answerable": True,
        "status": "answerable",
        "warnings": evidence_package.get("warnings"),
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

    assert evidence_package.get("analysis_status") == "missing"
    assert _warning_codes(evidence_package) == {"analysis_missing", "rag_no_evidence"}
    assert answer_quality.get("answerable") is False
    assert answer_quality.get("status") == "unanswerable"
    assert "충분하지 않습니다" in str(answer_quality.get("abstain_reason", ""))


def test_evidence_contract_treats_metadata_question_as_answerable_from_dataset_context() -> None:
    evidence_package, answer_quality = build_evidence_contract(
        state={
            "source_id": "source-1",
            "user_input": "이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘.",
            "handoff": {"next_step": "fallback_rag", "ask_analysis": False},
            "dataset_context": {
                "available": True,
                "filename": "moldset_labeled.csv",
                "row_count_total": 2607,
                "column_count": 57,
                "columns": ["TimeStamp", "Injection_Time", "PassOrFail"],
            },
        },
        merged_context={"dataset_context": {"columns": ["TimeStamp", "Injection_Time", "PassOrFail"]}},
    )

    assert evidence_package.get("source_id") == "source-1"
    assert evidence_package.get("filename") == "moldset_labeled.csv"
    assert answer_quality.get("answerable") is True
    assert answer_quality.get("status") == "answerable"


def test_evidence_contract_does_not_make_non_metadata_fallback_question_answerable() -> None:
    _, answer_quality = build_evidence_contract(
        state={
            "source_id": "source-1",
            "user_input": "이 데이터에서 개선해야 할 점을 알려줘.",
            "handoff": {"next_step": "fallback_rag", "ask_analysis": False},
            "dataset_context": {
                "available": True,
                "filename": "moldset_labeled.csv",
                "row_count_total": 2607,
                "column_count": 57,
                "columns": ["TimeStamp", "Injection_Time", "PassOrFail"],
            },
        },
        merged_context={"dataset_context": {"columns": ["TimeStamp", "Injection_Time", "PassOrFail"]}},
    )

    assert answer_quality.get("answerable") is False
    assert answer_quality.get("status") == "unanswerable"


def test_dataset_metadata_question_detection_excludes_column_action_requests() -> None:
    assert is_dataset_metadata_question("이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘.")
    assert is_dataset_metadata_question("how many rows are in this dataset?")
    assert is_dataset_metadata_question("show me all columns and data types")
    assert is_dataset_metadata_question("show me the dataset schema")
    assert not is_dataset_metadata_question("which columns should I remove before training?")
    assert not is_dataset_metadata_question("show me rows where PassOrFail equals 1")
    assert not is_dataset_metadata_question("show me all columns as a chart")
    assert not is_dataset_metadata_question("전체 컬럼을 보고서로 작성해줘")
    assert not is_dataset_metadata_question(
        "analyze whether schema drift explains the defect rate"
    )


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

    assert evidence_package.get("analysis_status") == "fail"
    assert evidence_package.get("rag_retrieved_count") == 2
    assert {"analysis_failed", "analysis_missing"}.issubset(_warning_codes(evidence_package))
    assert answer_quality.get("answerable") is True
    assert answer_quality.get("status") == "limited"


def test_evidence_contract_merges_analysis_quality_warnings() -> None:
    evidence_package, answer_quality = build_evidence_contract(
        state={
            "source_id": "source-1",
            "handoff": {"ask_analysis": True},
            "analysis_result": {
                "execution_status": "success",
                "summary": "매출 합계는 10입니다.",
                "raw_metrics": {"total_sales": 10},
                "table": [],
                "used_columns": ["sales"],
                "quality_status": "partial",
                "quality_reason": "analysis returned no table rows but raw metrics are available",
                "warnings": [
                    {
                        "code": "empty_table",
                        "message": "analysis returned no table rows but raw metrics are available",
                        "severity": "warning",
                    }
                ],
            },
        },
        merged_context={"applied_steps": ["analysis"]},
    )

    assert evidence_package.get("analysis_status") == "success"
    assert evidence_package.get("analysis_quality_status") == "partial"
    assert evidence_package.get("analysis_quality_reason") == (
        "analysis returned no table rows but raw metrics are available"
    )
    assert evidence_package.get("analysis_metrics") == {"total_sales": 10}
    assert _warning_codes(evidence_package) == {"empty_table"}
    assert answer_quality.get("answerable") is True
    assert answer_quality.get("status") == "limited"


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
        merged_context={
            "analysis_result": {"summary": "42"},
            "dataset_context": {
                "columns": ["TimeStamp", "Injection_Time", "PassOrFail"],
                "dtypes": {
                    "TimeStamp": "datetime64[ns]",
                    "Injection_Time": "float64",
                    "PassOrFail": "int64",
                },
            },
        },
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
    assert "TimeStamp" in human_message.content
    assert "Injection_Time" in human_message.content
    system_message = messages[0]
    assert "사용자 질문의 모든 명시적 요청" in system_message.content
    assert "그 외 N개" in system_message.content


def test_builder_wires_evidence_contract_into_merge_data_qa_and_analysis_fail_paths() -> None:
    source = inspect.getsource(builder.build_main_workflow)

    assert "build_evidence_contract" in source
    assert '"evidence_package": evidence_package' in source
    assert '"answer_quality": answer_quality' in source
    assert "answer_quality.get(\"answerable\") is False" in source
    assert "analysis_fail_terminal" in source
    assert '"fail": "analysis_fail_terminal"' in source
    assert "status_terminal" in source
    assert '"cancelled": "status_terminal"' in source
    assert '"failed": "status_terminal"' in source


def test_chat_done_metadata_marks_fail_cancel_and_limited_status() -> None:
    preprocess_error = ChatService._extract_done_error_fields(
        report_result=None,
        preprocess_result={"status": "failed", "error": "bad preprocess"},
        analysis_result=None,
        visualization_result=None,
        output_payload={"type": "preprocess_failed", "content": "preprocess failed"},
    )

    assert preprocess_error["error_stage"] == "preprocess"
    assert preprocess_error["error_message"] == "bad preprocess"
    assert ChatService._derive_terminal_status(
        output_type="preprocess_failed",
        error_fields=preprocess_error,
        answer_quality=None,
    ) == "failed"
    assert ChatService._derive_terminal_status(
        output_type="cancelled",
        error_fields={"error_stage": None, "error_message": None, "error_type": None},
        answer_quality=None,
    ) == "cancelled"
    assert ChatService._derive_terminal_status(
        output_type="data_qa",
        error_fields={"error_stage": None, "error_message": None, "error_type": None},
        answer_quality={"status": "limited"},
    ) == "limited"


def test_chat_relay_done_exposes_status_error_and_evidence_metadata() -> None:
    repo = _FakeChatRepository()
    service = _make_chat_service(repo)

    events = asyncio.run(
        _collect_events(
            service._relay_agent_events(
                session_id=7,
                run_id="run-1",
                trace_id="trace-1",
                session=cast(Any, object()),
                agent_stream=_fake_agent_stream(
                    {
                        "type": "done",
                        "answer": "전처리 단계에서 오류가 발생했습니다.",
                        "thought_steps": [{"phase": "preprocess", "message": "failed"}],
                        "output_type": "preprocess_failed",
                        "preprocess_result": {
                            "status": "failed",
                            "error": "bad preprocess",
                        },
                        "output": {
                            "type": "preprocess_failed",
                            "content": "전처리 단계에서 오류가 발생했습니다.",
                            "evidence_package": {
                                "warnings": [
                                    {
                                        "stage": "preprocess",
                                        "code": "preprocess_not_applied",
                                        "message": "bad preprocess",
                                    }
                                ]
                            },
                            "answer_quality": {
                                "answerable": False,
                                "status": "unanswerable",
                            },
                        },
                    }
                ),
            )
        )
    )

    assert repo.messages[-1][1:] == ("assistant", "전처리 단계에서 오류가 발생했습니다.")
    assert events == [
        {
            "event": "done",
            "data": {
                "answer": "전처리 단계에서 오류가 발생했습니다.",
                "session_id": 7,
                "run_id": "run-1",
                "trace_id": "trace-1",
                "thought_steps": [{"phase": "preprocess", "message": "failed"}],
                "preprocess_result": {
                    "status": "failed",
                    "error": "bad preprocess",
                },
                "output_type": "preprocess_failed",
                "output": {
                    "type": "preprocess_failed",
                    "content": "전처리 단계에서 오류가 발생했습니다.",
                    "evidence_package": {
                        "warnings": [
                            {
                                "stage": "preprocess",
                                "code": "preprocess_not_applied",
                                "message": "bad preprocess",
                            }
                        ]
                    },
                    "answer_quality": {
                        "answerable": False,
                        "status": "unanswerable",
                    },
                },
                "evidence_package": {
                    "warnings": [
                        {
                            "stage": "preprocess",
                            "code": "preprocess_not_applied",
                            "message": "bad preprocess",
                        }
                    ]
                },
                "answer_quality": {
                    "answerable": False,
                    "status": "unanswerable",
                },
                "status": "failed",
                "error_stage": "preprocess",
                "error_message": "bad preprocess",
                "retryable": True,
            },
        }
    ]


def test_chat_relay_error_event_preserves_error_metadata_and_evidence() -> None:
    repo = _FakeChatRepository()
    service = _make_chat_service(repo)

    events = asyncio.run(
        _collect_events(
            service._relay_agent_events(
                session_id=9,
                run_id="run-2",
                trace_id="trace-2",
                session=cast(Any, object()),
                agent_stream=_fake_agent_stream(
                    {
                        "type": "error",
                        "answer": "분석 실행이 실패했습니다.",
                        "stage": "analysis",
                        "error_code": "analysis_failed",
                        "retryable": True,
                        "output_type": "analysis_failed",
                        "thought_steps": [{"phase": "analysis", "message": "failed"}],
                        "evidence_package": {
                            "analysis_status": "fail",
                            "warnings": [
                                {
                                    "stage": "analysis",
                                    "code": "analysis_failed",
                                    "message": "분석 실행이 실패했습니다.",
                                }
                            ],
                        },
                        "answer_quality": {
                            "answerable": False,
                            "status": "unanswerable",
                        },
                    }
                ),
            )
        )
    )

    assert repo.messages[-1][1:] == ("assistant", "분석 실행이 실패했습니다.")
    assert events == [
        {
            "event": "error",
            "data": {
                "session_id": 9,
                "run_id": "run-2",
                "trace_id": "trace-2",
                "thought_steps": [{"phase": "analysis", "message": "failed"}],
                "answer": "분석 실행이 실패했습니다.",
                "message": "분석 실행이 실패했습니다.",
                "status": "failed",
                "stage": "analysis",
                "error_stage": "analysis",
                "error_message": "분석 실행이 실패했습니다.",
                "error_code": "analysis_failed",
                "retryable": True,
                "output_type": "analysis_failed",
                "evidence_package": {
                    "analysis_status": "fail",
                    "warnings": [
                        {
                            "stage": "analysis",
                            "code": "analysis_failed",
                            "message": "분석 실행이 실패했습니다.",
                        }
                    ],
                },
                "answer_quality": {
                    "answerable": False,
                    "status": "unanswerable",
                },
            },
        }
    ]


def test_analysis_workflow_marks_internal_failures_invalid_quality() -> None:
    source = inspect.getsource(analysis.build_analysis_workflow)

    assert 'quality_status="invalid"' in source
    assert 'quality_reason=analysis_error.message' in source
