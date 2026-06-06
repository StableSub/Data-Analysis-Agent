from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, AsyncIterator, Dict

import pytest

from backend.app.orchestration.client import AgentClient
from backend.app.modules.chat.service import ChatService

RAW_STRUCTURED_ERROR = (
    "1 validation error for QuestionUnderstanding ambiguity_status "
    "Field required [type=missing, input_value={'analysis_goal': ['raw-private']}] "
    "https://errors.pydantic.dev/2.12/v/missing"
)
FORBIDDEN_PUBLIC_TOKENS = (
    "QuestionUnderstanding",
    "ambiguity_status",
    "Field required",
    "input_value",
    "pydantic.dev",
    "raw-private",
    "diagnostic_message",
    "schema_name",
)


# ── 공통 헬퍼 ────────────────────────────────────────────────────────────────

def _collect(coro_or_agen) -> list[Dict[str, Any]]:
    """async generator 를 동기적으로 소비해 list 로 반환한다."""

    async def _run():
        return [e async for e in coro_or_agen]

    return asyncio.run(_run())


def _make_fake_workflow(snapshots: list[Dict[str, Any]]):
    """astream 을 흉내 내는 최소 workflow 객체를 반환한다."""

    class FakeWorkflow:
        async def astream(self, input_payload, config, *, stream_mode):
            for snap in snapshots:
                yield snap

    return FakeWorkflow()


@asynccontextmanager
async def _fake_runtime(workflow):
    yield SimpleNamespace(workflow=workflow)


def _make_agent(snapshots: list[Dict[str, Any]]) -> AgentClient:
    workflow = _make_fake_workflow(snapshots)

    def factory():
        return _fake_runtime(workflow)

    return AgentClient(workflow_runtime_factory=factory)


def _make_service(agent: AgentClient, *, source_exists: bool = True) -> ChatService:
    """ChatService 를 최소 fake repository 로 생성한다."""

    class FakeMessage:
        _next_id = 1

        def __init__(self, role, content):
            self.id = FakeMessage._next_id
            FakeMessage._next_id += 1
            self.role = role
            self.content = content
            self.created_at = datetime.now(timezone.utc)

    class FakeSession:
        def __init__(self):
            self.id = 1
            self.messages: list[FakeMessage] = []

    class FakeChatRepository:
        def __init__(self):
            self._session = FakeSession()

        def get_session(self, session_id):
            return self._session if session_id == self._session.id else None

        def create_session(self, *, title: str):
            return self._session

        def append_message(self, session, role, content):
            session.messages.append(FakeMessage(role, content))

        def get_history(self, session_id):
            return self._session.messages

        def delete_session(self, session_id):
            return True

    class FakeDataset:
        source_id = "test-source"

    class FakeDatasetRepository:
        def get_by_source_id(self, source_id):
            return FakeDataset() if source_exists else None

    repository: Any = FakeChatRepository()
    dataset_repository: Any = FakeDatasetRepository()
    return ChatService(
        agent=agent,
        repository=repository,
        dataset_repository=dataset_repository,
    )


def _serialized(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _assert_sanitized_public_event(value: Any) -> None:
    text = _serialized(value)
    for token in FORBIDDEN_PUBLIC_TOKENS:
        assert token not in text


# ── 스냅샷 픽스처 ─────────────────────────────────────────────────────────────

def _success_snapshot(
    *,
    evidence_package: Dict[str, Any] | None = None,
    answer_quality: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """정상 완료 workflow 최종 snapshot."""
    return {
        "output": {"type": "data_qa", "content": "평균 매출은 42입니다."},
        "final_status": "success",
        "evidence_package": evidence_package or {
            "source_id": "test-source",
            "analysis_status": "success",
            "analysis_metrics": {"avg_sales": 42},
            "warnings": [],
        },
        "answer_quality": answer_quality or {
            "answerable": True,
            "status": "answerable",
            "warnings": [],
        },
    }


def _fail_snapshot(*, error_stage: str = "analysis", execution_status: str = "fail") -> Dict[str, Any]:
    """analysis 실패 workflow 최종 snapshot."""
    return {
        "output": {"type": "data_qa", "content": "분석에 실패했습니다."},
        "final_status": "fail",
        "analysis_result": {
            "execution_status": execution_status,
            "error_stage": error_stage,
            "error_message": "컬럼을 찾을 수 없습니다.",
        },
    }


def _workflow_error_snapshot() -> Dict[str, Any]:
    return {
        "output": {"type": "planning_failed", "content": RAW_STRUCTURED_ERROR},
        "final_status": "fail",
        "workflow_error": {
            "stage": "question_understanding",
            "error_code": "structured_output_validation",
            "source": "llm_structured_output",
            "output_type": "planning_failed",
            "retryable": True,
            "safe_message": "질문을 이해하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            "diagnostic_message": RAW_STRUCTURED_ERROR,
            "details": {
                "schema_name": "QuestionUnderstanding",
                "field_path": "ambiguity_status",
            },
        },
        "analysis_result": {
            "execution_status": "fail",
            "error_stage": "question_understanding",
            "error_message": RAW_STRUCTURED_ERROR,
        },
    }


def _quality_fail_snapshot(*, quality_status: str) -> Dict[str, Any]:
    """execution_status=success 이지만 quality 로 실패 판정되는 snapshot."""
    return {
        "output": {"type": "data_qa", "content": "결과가 비어 있습니다."},
        "final_status": "success",
        "analysis_result": {
            "execution_status": "success",
            "quality_status": quality_status,
            "quality_reason": "분석 결과 테이블이 비어 있습니다.",
            "warnings": [
                {"code": "empty_table", "message": "no rows", "severity": "warning"}
            ],
        },
    }


# ── Phase 1 테스트 ────────────────────────────────────────────────────────────
# 목표: 기존 SSE core field 보존 + optional metadata 추가 + error event 신설


class TestDoneEventCoreFieldsPreserved:
    """기존 done event 의 core field 가 깨지지 않아야 한다."""

    def test_done_has_answer(self):
        agent = _make_agent([_success_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        done = next(e for e in events if e.get("type") == "done")
        assert isinstance(done["answer"], str) and done["answer"]

    def test_done_has_thought_steps(self):
        agent = _make_agent([_success_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        done = next(e for e in events if e.get("type") == "done")
        assert isinstance(done["thought_steps"], list)

    def test_done_has_output_type(self):
        agent = _make_agent([_success_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        done = next(e for e in events if e.get("type") == "done")
        assert done["output_type"] == "data_qa"


class TestDoneEventOptionalMetadata:
    """done event 에 evidence_package / answer_quality 가 optional 로 추가되어야 한다."""

    def test_done_includes_evidence_package(self):
        agent = _make_agent([_success_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        done = next(e for e in events if e.get("type") == "done")
        assert "evidence_package" in done
        assert isinstance(done["evidence_package"], dict)

    def test_done_includes_answer_quality(self):
        agent = _make_agent([_success_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        done = next(e for e in events if e.get("type") == "done")
        assert "answer_quality" in done
        assert isinstance(done["answer_quality"], dict)

    def test_done_evidence_package_fields(self):
        ep = {
            "source_id": "test-source",
            "analysis_status": "success",
            "analysis_metrics": {"avg_sales": 42},
            "warnings": [],
        }
        agent = _make_agent([_success_snapshot(evidence_package=ep)])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        done = next(e for e in events if e.get("type") == "done")
        assert done["evidence_package"]["source_id"] == "test-source"
        assert done["evidence_package"]["analysis_metrics"] == {"avg_sales": 42}

    def test_done_answer_quality_fields(self):
        aq = {"answerable": True, "status": "answerable", "warnings": []}
        agent = _make_agent([_success_snapshot(answer_quality=aq)])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        done = next(e for e in events if e.get("type") == "done")
        assert done["answer_quality"]["answerable"] is True
        assert done["answer_quality"]["status"] == "answerable"

    def test_done_without_evidence_package_does_not_error(self):
        """evidence_package 가 state 에 없어도 done event 자체는 정상 발행된다."""
        snap = {
            "output": {"type": "general_question", "content": "일반 질문 답변입니다."},
            "final_status": "success",
            # evidence_package 없음
        }
        agent = _make_agent([snap])
        events = _collect(agent.astream_with_trace(session_id="1", question="안녕?"))
        done = next(e for e in events if e.get("type") == "done")
        assert done["type"] == "done"
        assert "evidence_package" not in done


class TestErrorEventNewlyAdded:
    """실패 시 done 대신 error event 가 발행되어야 한다."""

    def test_analysis_fail_emits_error_not_done(self):
        agent = _make_agent([_fail_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        types = [e.get("type") for e in events]
        assert "error" in types
        assert "done" not in types

    def test_error_event_has_stage(self):
        agent = _make_agent([_fail_snapshot(error_stage="analysis")])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        error = next(e for e in events if e.get("type") == "error")
        assert isinstance(error["stage"], str) and error["stage"]

    def test_error_event_passes_terminal_status_metadata(self):
        agent = _make_agent([_fail_snapshot(error_stage="analysis")])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        error = next(e for e in events if e.get("type") == "error")
        assert error["status"] == "failed"
        assert error["error_stage"] == "analysis"
        assert error["error_message"] == "컬럼을 찾을 수 없습니다."

    def test_error_event_has_error_code(self):
        agent = _make_agent([_fail_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        error = next(e for e in events if e.get("type") == "error")
        assert error["error_code"] == "analysis_execution_failed"

    def test_error_event_has_retryable_bool(self):
        agent = _make_agent([_fail_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        error = next(e for e in events if e.get("type") == "error")
        assert isinstance(error["retryable"], bool)

    def test_analysis_fail_is_retryable(self):
        agent = _make_agent([_fail_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        error = next(e for e in events if e.get("type") == "error")
        assert error["retryable"] is True

    def test_error_event_preserves_answer_and_thought_steps(self):
        """error event 도 기존 호환 필드(answer, thought_steps)를 포함해야 한다."""
        agent = _make_agent([_fail_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        error = next(e for e in events if e.get("type") == "error")
        assert "answer" in error
        assert "thought_steps" in error

    def test_quality_empty_emits_error(self):
        agent = _make_agent([_quality_fail_snapshot(quality_status="empty")])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        types = [e.get("type") for e in events]
        assert "error" in types
        assert "done" not in types

    def test_quality_invalid_emits_error(self):
        agent = _make_agent([_quality_fail_snapshot(quality_status="invalid")])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        types = [e.get("type") for e in events]
        assert "error" in types

    def test_quality_partial_emits_done_not_error(self):
        """partial 은 warning 이지 실패가 아니다 — done 으로 와야 한다."""
        snap = {
            "output": {"type": "data_qa", "content": "부분 결과입니다."},
            "final_status": "success",
            "analysis_result": {
                "execution_status": "success",
                "quality_status": "partial",
                "warnings": [{"code": "empty_table", "message": "no rows", "severity": "warning"}],
            },
            "answer_quality": {"answerable": True, "status": "limited", "warnings": []},
        }
        agent = _make_agent([snap])
        events = _collect(agent.astream_with_trace(session_id="1", question="매출 평균은?"))
        types = [e.get("type") for e in events]
        assert "done" in types
        assert "error" not in types

    def test_workflow_error_event_uses_public_projection_only(self):
        agent = _make_agent([_workflow_error_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="불량률은?"))
        error = next(e for e in events if e.get("type") == "error")

        assert error["stage"] == "question_understanding"
        assert error["error_stage"] == "question_understanding"
        assert error["error_code"] == "structured_output_validation"
        assert error["output_type"] == "planning_failed"
        assert error["retryable"] is True
        assert "public_error" in error
        assert "workflow_error" not in error
        _assert_sanitized_public_event(error)

    def test_legacy_error_event_sanitizes_raw_summary_fallback(self):
        agent = _make_agent(
            [
                {
                    "output": {"type": "planning_failed", "content": RAW_STRUCTURED_ERROR},
                    "final_status": "fail",
                    "analysis_error": {
                        "stage": "question_understanding",
                        "message": RAW_STRUCTURED_ERROR,
                    },
                }
            ]
        )
        events = _collect(agent.astream_with_trace(session_id="1", question="불량률은?"))
        error = next(e for e in events if e.get("type") == "error")

        assert error["stage"] == "question_understanding"
        _assert_sanitized_public_event(error)


class TestApprovalRequiredPreserved:
    """approval_required event 와 resume 흐름이 기존대로 동작해야 한다."""

    def _make_approval_snapshot(self) -> Dict[str, Any]:
        return {
            "__interrupt__": (
                SimpleNamespace(
                    value={
                        "stage": "preprocess",
                        "kind": "plan_review",
                        "title": "전처리 계획 검토",
                        "summary": "3개 컬럼 정규화 예정",
                        "source_id": "test-source",
                        "plan": {"ops": ["normalize"]},
                    }
                ),
            ),
        }

    def test_approval_required_event_emitted(self):
        agent = _make_agent([self._make_approval_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="전처리 해줘"))
        types = [e.get("type") for e in events]
        assert "approval_required" in types

    def test_approval_required_has_pending_approval(self):
        agent = _make_agent([self._make_approval_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="전처리 해줘"))
        ev = next(e for e in events if e.get("type") == "approval_required")
        assert isinstance(ev["pending_approval"], dict)
        assert ev["pending_approval"]["stage"] == "preprocess"

    def test_approval_required_has_thought_steps(self):
        agent = _make_agent([self._make_approval_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="전처리 해줘"))
        ev = next(e for e in events if e.get("type") == "approval_required")
        assert isinstance(ev["thought_steps"], list)

    def test_approval_stops_stream(self):
        """approval_required 이후 done/error 가 오면 안 된다."""
        agent = _make_agent([self._make_approval_snapshot()])
        events = _collect(agent.astream_with_trace(session_id="1", question="전처리 해줘"))
        types = [e.get("type") for e in events]
        assert "done" not in types
        assert "error" not in types


class TestServiceLayerRelay:
    """service._relay_agent_events 가 SSE event 를 올바르게 relay 해야 한다."""

    def test_service_done_includes_evidence_package(self):
        agent = _make_agent([_success_snapshot()])
        service = _make_service(agent)
        events = _collect(service.ask_stream(question="매출 평균은?", session_id=1))
        done = next(e for e in events if e.get("event") == "done")
        assert "evidence_package" in done["data"]

    def test_service_done_includes_answer_quality(self):
        agent = _make_agent([_success_snapshot()])
        service = _make_service(agent)
        events = _collect(service.ask_stream(question="매출 평균은?", session_id=1))
        done = next(e for e in events if e.get("event") == "done")
        assert "answer_quality" in done["data"]

    def test_service_error_relayed_on_analysis_fail(self):
        agent = _make_agent([_fail_snapshot()])
        service = _make_service(agent)
        events = _collect(service.ask_stream(question="매출 평균은?", session_id=1))
        event_names = [e.get("event") for e in events]
        assert "error" in event_names
        assert "done" not in event_names

    def test_service_error_has_error_code(self):
        agent = _make_agent([_fail_snapshot()])
        service = _make_service(agent)
        events = _collect(service.ask_stream(question="매출 평균은?", session_id=1))
        error = next(e for e in events if e.get("event") == "error")
        assert "error_code" in error["data"]

    def test_service_error_passes_terminal_status_metadata(self):
        agent = _make_agent([_fail_snapshot(error_stage="analysis")])
        service = _make_service(agent)
        events = _collect(service.ask_stream(question="매출 평균은?", session_id=1))
        error = next(e for e in events if e.get("event") == "error")
        assert error["data"]["status"] == "failed"
        assert error["data"]["error_stage"] == "analysis"
        assert error["data"]["error_message"] == "컬럼을 찾을 수 없습니다."

    def test_service_error_has_retryable(self):
        agent = _make_agent([_fail_snapshot()])
        service = _make_service(agent)
        events = _collect(service.ask_stream(question="매출 평균은?", session_id=1))
        error = next(e for e in events if e.get("event") == "error")
        assert isinstance(error["data"]["retryable"], bool)

    def test_service_emits_session_event_first(self):
        agent = _make_agent([_success_snapshot()])
        service = _make_service(agent)
        events = _collect(service.ask_stream(question="매출 평균은?", session_id=1))
        assert events[0]["event"] == "session"
        assert "session_id" in events[0]["data"]
        assert "run_id" in events[0]["data"]

    def test_service_error_relay_and_history_hide_workflow_diagnostics(self):
        agent = _make_agent([_workflow_error_snapshot()])
        service = _make_service(agent)
        events = _collect(service.ask_stream(question="불량률은?", session_id=1))
        error = next(e for e in events if e.get("event") == "error")

        assert error["data"]["error_code"] == "structured_output_validation"
        assert error["data"]["error_stage"] == "question_understanding"
        assert "public_error" in error["data"]
        _assert_sanitized_public_event(error["data"])
        _assert_sanitized_public_event(service.get_history(1))


class TestInvalidSourceId:
    """잘못된 source_id 는 HTTP 404 가 아닌 SSE error event 로 처리되어야 한다."""

    def test_invalid_source_id_emits_error_event(self):
        agent = _make_agent([])
        service = _make_service(agent, source_exists=False)
        events = _collect(
            service.ask_stream(question="매출 평균은?", source_id="nonexistent-id")
        )
        event_names = [e.get("event") for e in events]
        assert "error" in event_names

    def test_invalid_source_id_error_code(self):
        agent = _make_agent([])
        service = _make_service(agent, source_exists=False)
        events = _collect(
            service.ask_stream(question="매출 평균은?", source_id="nonexistent-id")
        )
        error = next(e for e in events if e.get("event") == "error")
        assert error["data"]["error_code"] == "invalid_source_id"

    def test_invalid_source_id_not_retryable(self):
        agent = _make_agent([])
        service = _make_service(agent, source_exists=False)
        events = _collect(
            service.ask_stream(question="매출 평균은?", source_id="nonexistent-id")
        )
        error = next(e for e in events if e.get("event") == "error")
        assert error["data"]["retryable"] is False

    def test_invalid_source_id_has_terminal_status_metadata(self):
        agent = _make_agent([])
        service = _make_service(agent, source_exists=False)
        events = _collect(
            service.ask_stream(question="매출 평균은?", source_id="nonexistent-id")
        )
        error = next(e for e in events if e.get("event") == "error")
        assert error["data"]["status"] == "failed"
        assert error["data"]["error_stage"] == "dataset_resolution"
        assert error["data"]["error_source"] == "chat_source_validation"
        assert error["data"]["error_message"] == "요청한 데이터셋을 찾을 수 없습니다."

    def test_invalid_source_id_does_not_emit_session_event_without_existing_session(self):
        agent = _make_agent([])
        service = _make_service(agent, source_exists=False)
        events = _collect(
            service.ask_stream(question="매출 평균은?", source_id="nonexistent-id")
        )
        assert [event.get("event") for event in events] == ["error"]

    def test_invalid_source_id_keeps_existing_session_event(self):
        agent = _make_agent([])
        service = _make_service(agent, source_exists=False)
        events = _collect(
            service.ask_stream(question="매출 평균은?", session_id=1, source_id="nonexistent-id")
        )

        assert [event.get("event") for event in events] == ["session", "error"]
        assert events[0]["data"]["session_id"] == 1
        assert events[1]["data"]["session_id"] == 1
