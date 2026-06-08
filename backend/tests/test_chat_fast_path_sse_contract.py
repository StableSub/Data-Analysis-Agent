from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast

from backend.app.modules.chat.service import ChatService
from backend.app.modules.chat.repository import ChatRepository
from backend.app.modules.datasets.repository import DatasetRepository
from backend.app.orchestration.client import AgentClient

Event = dict[str, object]
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


def _collect(events: AsyncIterator[Event]) -> list[Event]:
    async def _run() -> list[Event]:
        return [event async for event in events]

    return asyncio.run(_run())


def _as_event_dict(value: object) -> Event:
    assert isinstance(value, dict)
    return cast(Event, value)


def _serialized(value: object) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _assert_sanitized_public_event(value: object) -> None:
    text = _serialized(value)
    for token in FORBIDDEN_PUBLIC_TOKENS:
        assert token not in text


class _FakeWorkflow:
    _snapshots: list[Event]

    def __init__(self, snapshots: list[Event]) -> None:
        self._snapshots = snapshots

    async def astream(
        self,
        input_payload: object,
        config: object,
        *,
        stream_mode: str,
    ) -> AsyncIterator[Event]:
        _ = input_payload, config, stream_mode
        for snapshot in self._snapshots:
            yield snapshot


def _make_agent_client(snapshots: list[Event]) -> AgentClient:
    @asynccontextmanager
    async def _runtime() -> AsyncGenerator[SimpleNamespace, None]:
        yield SimpleNamespace(workflow=_FakeWorkflow(snapshots))

    return AgentClient(workflow_runtime_factory=_runtime)


class _FakeMessage:
    _next_id: int = 1
    id: int
    role: str
    content: str
    created_at: datetime

    def __init__(self, role: str, content: str) -> None:
        self.id = _FakeMessage._next_id
        _FakeMessage._next_id += 1
        self.role = role
        self.content = content
        self.created_at = datetime.now(timezone.utc)


class _FakeSession:
    id: int
    messages: list[_FakeMessage]

    def __init__(self) -> None:
        self.id = 1
        self.messages = []


class _FakeChatRepository:
    session: _FakeSession

    def __init__(self) -> None:
        self.session = _FakeSession()

    def get_session(self, session_id: int) -> _FakeSession | None:
        return self.session if session_id == self.session.id else None

    def create_session(self, *, title: str) -> _FakeSession:
        _ = title
        return self.session

    def append_message(self, session: _FakeSession, role: str, content: str) -> None:
        session.messages.append(_FakeMessage(role, content))

    def get_history(self, session_id: int) -> list[_FakeMessage]:
        return self.session.messages if session_id == self.session.id else []

    def delete_session(self, session_id: int) -> bool:
        return session_id == self.session.id


class _FakeDatasetRepository:
    _source_exists: bool

    def __init__(self, *, source_exists: bool = True) -> None:
        self._source_exists = source_exists

    def get_by_source_id(self, source_id: str) -> SimpleNamespace | None:
        if not self._source_exists:
            return None
        return SimpleNamespace(source_id=source_id)


class _FakeAgent:
    _events: list[Event]

    def __init__(self, events: list[Event]) -> None:
        self._events = events

    async def astream_with_trace(self, **kwargs: object) -> AsyncIterator[Event]:
        _ = kwargs
        for event in self._events:
            yield event


def _make_service(
    agent: object,
    *,
    source_exists: bool = True,
) -> ChatService:
    return ChatService(
        agent=cast(AgentClient, agent),
        repository=cast(ChatRepository, cast(object, _FakeChatRepository())),
        dataset_repository=cast(
            DatasetRepository,
            cast(object, _FakeDatasetRepository(source_exists=source_exists)),
        ),
    )


def test_agent_client_maps_fast_dataset_answer_done_event_to_data_qa() -> None:
    content = (
        "데이터 크기: moldset_labeled.csv 데이터셋은 총 2,607행, 57열입니다.\n"
        "주요 컬럼:\n- TimeStamp: 날짜/시간형 컬럼\n컬럼 구성: 숫자형 3개입니다."
    )
    agent = _make_agent_client(
        [
            {
                "output": {"type": "fast_dataset_answer", "content": content},
                "final_status": "success",
            }
        ]
    )

    events = _collect(
        agent.astream_with_trace(
            session_id="1",
            run_id="run-fast-dataset",
            question="이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘.",
        )
    )

    done = next(event for event in events if event.get("type") == "done")
    assert done["answer"] == content
    assert done["output_type"] == "data_qa"
    assert done["output"] == {"type": "fast_dataset_answer", "content": content}


def test_agent_client_done_preserves_optional_evidence_and_quality_metadata() -> None:
    evidence_package: Event = {
        "source_id": "dataset-source",
        "analysis_status": "success",
        "warnings": [],
    }
    answer_quality: Event = {
        "answerable": True,
        "status": "answerable",
        "warnings": [],
    }
    agent = _make_agent_client(
        [
            {
                "output": {"type": "fast_dataset_answer", "content": "요약입니다."},
                "final_status": "success",
                "evidence_package": evidence_package,
                "answer_quality": answer_quality,
            }
        ]
    )

    events = _collect(
        agent.astream_with_trace(
            session_id="1",
            run_id="run-metadata",
            question="이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘.",
        )
    )

    done = next(event for event in events if event.get("type") == "done")
    assert done["evidence_package"] == evidence_package
    assert done["answer_quality"] == answer_quality
    assert done["output_type"] == "data_qa"


def test_agent_client_workflow_error_sanitizes_internal_structured_output_details() -> None:
    agent = _make_agent_client(
        [
            {
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
        ]
    )

    events = _collect(
        agent.astream_with_trace(
            session_id="1",
            run_id="run-sanitized-error",
            question="요약해줘.",
        )
    )

    error = next(event for event in events if event.get("type") == "error")
    assert error["stage"] == "question_understanding"
    assert error["error_code"] == "structured_output_validation"
    assert error["retryable"] is True
    _assert_sanitized_public_event(error)


def test_chat_service_relays_fast_dataset_answer_done_contract() -> None:
    content = (
        "데이터 크기: moldset_labeled.csv 데이터셋은 총 2,607행, 57열입니다.\n"
        "주요 컬럼:\n- TimeStamp: 날짜/시간형 컬럼\n컬럼 구성: 숫자형 3개입니다."
    )
    service = _make_service(
        _FakeAgent(
            [
                {"type": "chunk", "delta": content[:20]},
                {"type": "chunk", "delta": content[20:]},
                {
                    "type": "done",
                    "answer": content,
                    "output_type": "data_qa",
                    "output": {"type": "fast_dataset_answer", "content": content},
                    "thought_steps": [],
                },
            ]
        )
    )

    events = _collect(
        service.ask_stream(
            question="이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘.",
            source_id="dataset-source",
            trace_id="contract-test",
        )
    )

    assert events[0]["event"] == "session"
    done = events[-1]
    assert done["event"] == "done"
    done_data = _as_event_dict(done["data"])
    assert done_data["answer"] == content
    assert done_data["output_type"] == "data_qa"
    assert done_data["output"] == {"type": "fast_dataset_answer", "content": content}
    assert done_data["status"] == "success"


def test_chat_service_invalid_source_id_keeps_public_error_contract() -> None:
    service = _make_service(_FakeAgent([]), source_exists=False)

    events = _collect(
        service.ask_stream(
            question="이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘.",
            source_id="missing-source",
            trace_id="invalid-source-contract",
        )
    )

    error = events[-1]
    assert error["event"] == "error"
    error_data = _as_event_dict(error["data"])
    assert error_data["status"] == "failed"
    assert error_data["stage"] == "dataset_resolution"
    assert error_data["error_code"] == "invalid_source_id"
    assert error_data["retryable"] is False


def test_chat_service_relays_approval_required_contract() -> None:
    pending_approval: Event = {
        "stage": "visualization",
        "kind": "plan_review",
        "title": "시각화 승인",
        "summary": "차트 생성을 승인해 주세요.",
        "source_id": "dataset-source",
        "plan": cast(Event, {}),
    }
    thought_steps: list[Event] = [
        {
            "phase": "visualization",
            "message": "승인을 기다립니다.",
            "status": "pending",
        }
    ]
    service = _make_service(
        _FakeAgent(
            [
                {
                    "type": "approval_required",
                    "pending_approval": pending_approval,
                    "thought_steps": thought_steps,
                }
            ]
        )
    )

    events = _collect(
        service.ask_stream(
            question="차트로 보여줘.",
            source_id="dataset-source",
            trace_id="approval-contract",
        )
    )

    approval = events[-1]
    assert approval["event"] == "approval_required"
    approval_data = _as_event_dict(approval["data"])
    assert approval_data["pending_approval"] == pending_approval
    assert approval_data["thought_steps"] == thought_steps
    assert approval_data["trace_id"] == "approval-contract"
