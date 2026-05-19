from __future__ import annotations

import asyncio
from typing import Any

import pytest

from conftest import live_model_id, live_timeout_seconds, require_benchmark_dataset, selected_cases
from eval_cases import load_case_file
from runtime_assertions import assert_answerability, assert_no_forbidden_metric_keys, assert_used_columns

pytestmark = pytest.mark.live_benchmark


async def _collect_events(agent: Any, *, case: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    dataset = require_benchmark_dataset(case["dataset"]).as_agent_dataset()
    async for event in agent.astream_with_trace(
        session_id="live-benchmark",
        run_id=f"live-{case['case_id']}",
        question=case["question"],
        dataset=dataset,
        model_id=live_model_id(),
    ):
        events.append(event)
    return events


def _run_live_case(agent: Any, case: dict[str, Any]) -> dict[str, Any]:
    return {
        "case": case,
        "events": asyncio.run(
            asyncio.wait_for(
                _collect_events(agent, case=case),
                timeout=live_timeout_seconds(),
            )
        ),
    }


def test_agent_client_live_p1_selected_cases(live_agent_client: Any) -> None:
    cases = selected_cases(load_case_file("p1_dataset_quality_cases.jsonl"))
    if not cases:
        pytest.skip("no P1 cases selected by BENCHMARK_LIVE_CASE_IDS")

    for case in cases:
        result = _run_live_case(live_agent_client, case)
        events = result["events"]
        done_events = [event for event in events if event.get("type") == "done"]
        error_events = [event for event in events if event.get("type") == "error"]

        if case["case_id"] == "p1_unlabeled_defect_rate_abstain":
            _assert_unlabeled_abstain(case, done_events, error_events)
        elif case["case_id"] in {"p1_cn7_scaled_detection", "p1_rg3_scaled_detection"}:
            _assert_scaled_detection(case, done_events, error_events)
        elif case["case_id"] == "p1_labeled_data_yn_label_distribution":
            _assert_labeled_data_distribution(case, done_events, error_events)
        else:
            pytest.fail(f"unsupported P1 live case: {case['case_id']}")


def _assert_unlabeled_abstain(
    case: dict[str, Any],
    done_events: list[dict[str, Any]],
    error_events: list[dict[str, Any]],
) -> None:
    forbidden = case.get("forbidden_metric_keys", [])
    if error_events:
        error = error_events[-1]
        assert error.get("error_code") in {
            "planning_failed",
            "analysis_validation_failed",
            "analysis_execution_failed",
            "answer_unanswerable",
        }, {"case_id": case["case_id"], "error": error}
        assert_no_forbidden_metric_keys(error.get("evidence_package", {}).get("analysis_metrics", {}), forbidden, context=case["case_id"])
        return

    assert done_events, {"case_id": case["case_id"]}
    done = done_events[-1]
    evidence = done.get("evidence_package", {})
    assert_answerability(done.get("answer_quality", {}), "unanswerable", context=case["case_id"])
    assert_no_forbidden_metric_keys(evidence.get("analysis_metrics", {}), forbidden, context=case["case_id"])


def _assert_scaled_detection(
    case: dict[str, Any],
    done_events: list[dict[str, Any]],
    error_events: list[dict[str, Any]],
) -> None:
    assert not error_events, {"case_id": case["case_id"], "error_events": error_events}
    assert done_events, {"case_id": case["case_id"]}
    done = done_events[-1]
    evidence = done.get("evidence_package", {})
    assert_used_columns(evidence.get("used_columns", []), case.get("expected_used_columns", []), context=case["case_id"])
    assert_answerability(done.get("answer_quality", {}), {"answerable", "limited"}, context=case["case_id"])
    metrics = evidence.get("analysis_metrics", {})
    if "scaled_like" in metrics:
        assert metrics["scaled_like"] is True
    else:
        assert "스케일" in done.get("answer", "") or "scaled" in done.get("answer", "").lower()


def _assert_labeled_data_distribution(
    case: dict[str, Any],
    done_events: list[dict[str, Any]],
    error_events: list[dict[str, Any]],
) -> None:
    assert not error_events, {"case_id": case["case_id"], "error_events": error_events}
    assert done_events, {"case_id": case["case_id"]}
    done = done_events[-1]
    evidence = done.get("evidence_package", {})
    metrics = evidence.get("analysis_metrics", {})
    expected = case.get("expected_metrics", {})
    assert_used_columns(evidence.get("used_columns", []), ["PassOrFail"], context=case["case_id"])
    assert int(metrics["total_count"]) == expected["total_count"]
    assert int(metrics["y_count"]) == expected["y_count"]
    assert int(metrics["n_count"]) == expected["n_count"]
