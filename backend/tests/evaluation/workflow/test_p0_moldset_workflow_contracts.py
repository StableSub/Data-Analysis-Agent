from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from backend.app.orchestration.client import AgentClient
from backend.app.orchestration.evidence import build_evidence_contract
from moldset_p0_oracles import expected_label_distribution
from runtime_assertions import assert_answerability, assert_evidence_keys, assert_used_columns


class _Runtime:
    def __init__(self, workflow: Any) -> None:
        self.workflow = workflow

    async def __aenter__(self) -> "_Runtime":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


class _Workflow:
    def __init__(self, snapshots: list[dict[str, Any]]) -> None:
        self._snapshots = snapshots

    async def astream(self, input_payload: Any, config: dict[str, Any], stream_mode: str):
        for snapshot in self._snapshots:
            yield snapshot


async def _collect(client: AgentClient) -> list[dict[str, Any]]:
    return [
        event
        async for event in client.astream_with_trace(
            session_id="benchmark-session",
            run_id="benchmark-run",
            question="PassOrFail 라벨 분포를 알려줘.",
        )
    ]


def test_evidence_contract_carries_p0_label_distribution_metrics() -> None:
    metrics = expected_label_distribution()
    evidence, answer_quality = build_evidence_contract(
        state={
            "source_id": "moldset_labeled.csv",
            "final_status": "success",
            "analysis_result": {
                "execution_status": "success",
                "summary": "총 2607건 중 정상 2555건, 불량 52건입니다.",
                "raw_metrics": metrics,
                "used_columns": ["PassOrFail"],
                "quality_status": "partial",
            },
            "analysis_plan": {"used_columns": ["PassOrFail"]},
        },
        merged_context={"applied_steps": ["analysis"]},
    )

    assert evidence["source_id"] == "moldset_labeled.csv"
    assert evidence["analysis_metrics"] == metrics
    assert_used_columns(evidence["used_columns"], ["PassOrFail"])
    assert_evidence_keys(evidence, ["source_id", "used_columns", "analysis_metrics"])
    assert_answerability(answer_quality, "answerable")


def test_agent_client_done_event_includes_evidence_and_answer_quality() -> None:
    evidence = {"source_id": "moldset_labeled.csv", "used_columns": ["PassOrFail"], "analysis_metrics": expected_label_distribution()}
    answer_quality = {"status": "answerable", "answerable": True, "warnings": []}
    workflow = _Workflow([
        {
            "final_status": "success",
            "output": {"type": "answer", "content": "총 2607건 중 불량 52건입니다."},
            "evidence_package": evidence,
            "answer_quality": answer_quality,
            "analysis_result": {"execution_status": "success", "used_columns": ["PassOrFail"]},
        }
    ])
    client = AgentClient(workflow_runtime_factory=lambda: _Runtime(workflow))

    events = asyncio.run(_collect(client))
    done = events[-1]

    assert done["type"] == "done"
    assert done["evidence_package"] == evidence
    assert done["answer_quality"] == answer_quality
    assert done["analysis_result"]["execution_status"] == "success"


def test_agent_client_approval_event_preserves_preprocess_stage() -> None:
    workflow = _Workflow([
        {
            "__interrupt__": (
                SimpleNamespace(value={"stage": "preprocess", "kind": "approval", "operations": [{"op": "scale"}]}),
            ),
            "planning_result": {"route": "preprocess", "preprocess_required": True},
        }
    ])
    client = AgentClient(workflow_runtime_factory=lambda: _Runtime(workflow))

    events = asyncio.run(_collect(client))
    approval = events[-1]

    assert approval["type"] == "approval_required"
    assert approval["pending_approval"]["stage"] == "preprocess"
    assert approval["pending_approval"]["operations"] == [{"op": "scale"}]
