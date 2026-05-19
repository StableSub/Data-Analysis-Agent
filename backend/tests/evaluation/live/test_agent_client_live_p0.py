from __future__ import annotations

import asyncio
from typing import Any

import pytest

from conftest import (
    live_model_id,
    live_timeout_seconds,
    require_benchmark_dataset,
    selected_cases,
)
from eval_cases import load_case_file
from moldset_p0_oracles import (
    expected_defect_rate_by_part,
    expected_defect_reason_counts,
    expected_label_distribution,
)
from runtime_assertions import (
    assert_answer_contains_terms,
    assert_answer_excludes_terms,
    assert_answerability,
    assert_float_close,
    assert_table_close,
    assert_used_columns,
)

pytestmark = pytest.mark.live_benchmark


async def _collect_events(agent: Any, *, case: dict[str, Any], source_id: str) -> list[dict[str, Any]]:
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
    registration = require_benchmark_dataset(case["dataset"])
    events = asyncio.run(
        asyncio.wait_for(
            _collect_events(agent, case=case, source_id=registration.source_id),
            timeout=live_timeout_seconds(),
        )
    )
    error_events = [event for event in events if event.get("type") == "error"]
    assert not error_events, {"case_id": case["case_id"], "error_events": error_events}
    done_events = [event for event in events if event.get("type") == "done"]
    assert done_events, {"case_id": case["case_id"], "events": events}
    return done_events[-1]


def _evidence(done: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    evidence = done.get("evidence_package")
    assert isinstance(evidence, dict), {"case_id": case["case_id"], "done": done}
    return evidence


def _analysis_metrics(done: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    evidence = _evidence(done, case)
    metrics = evidence.get("analysis_metrics")
    assert isinstance(metrics, dict), {"case_id": case["case_id"], "evidence": evidence}
    return metrics


def _analysis_table(done: dict[str, Any], case: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = _evidence(done, case)
    table = evidence.get("analysis_table")
    assert isinstance(table, list), {"case_id": case["case_id"], "evidence": evidence}
    return table


def test_agent_client_live_p0_selected_cases(live_agent_client: Any) -> None:
    cases = selected_cases(load_case_file("p0_moldset_analysis_cases.jsonl"))
    if not cases:
        pytest.skip("no P0 analysis cases selected by BENCHMARK_LIVE_CASE_IDS")

    for case in cases:
        done = _run_live_case(live_agent_client, case)
        assert done.get("output_type") == "data_qa"
        assert_answer_excludes_terms(done.get("answer", ""), case.get("forbidden_answer_terms", []), context=case["case_id"])

        if case["case_id"] == "p0_moldset_label_distribution":
            _assert_label_distribution(done, case)
        elif case["case_id"] == "p0_moldset_defect_rate_by_part":
            _assert_defect_rate_by_part(done, case)
        elif case["case_id"] == "p0_moldset_defect_reason_counts":
            _assert_defect_reason_counts(done, case)
        else:
            pytest.fail(f"unsupported P0 live case: {case['case_id']}")


def _assert_label_distribution(done: dict[str, Any], case: dict[str, Any]) -> None:
    expected = expected_label_distribution()
    evidence = _evidence(done, case)
    metrics = _label_distribution_metrics(done, case)

    assert evidence["source_id"] == require_benchmark_dataset(case["dataset"]).source_id
    assert_used_columns(evidence.get("used_columns", []), ["PassOrFail"], context=case["case_id"])
    assert_answerability(done.get("answer_quality", {}), {"answerable", "limited"}, context=case["case_id"])
    assert int(metrics["total_count"]) == expected["total_count"]
    assert int(metrics["normal_count"]) == expected["normal_count"]
    assert int(metrics["defect_count"]) == expected["defect_count"]
    assert_float_close(metrics["defect_rate_pct"], expected["defect_rate_pct"], tolerance=1e-6, context=case["case_id"])
    assert_answer_contains_terms(done.get("answer", ""), case.get("expected_answer_contains", []), context=case["case_id"])


def _label_distribution_metrics(done: dict[str, Any], case: dict[str, Any]) -> dict[str, float | int]:
    metrics = _analysis_metrics(done, case)
    required = {"total_count", "normal_count", "defect_count", "defect_rate_pct"}
    if required.issubset(metrics):
        return {
            "total_count": int(metrics["total_count"]),
            "normal_count": int(metrics["normal_count"]),
            "defect_count": int(metrics["defect_count"]),
            "defect_rate_pct": float(metrics["defect_rate_pct"]),
        }

    table = _analysis_table(done, case)
    count_by_label: dict[str, int] = {}
    for row in table:
        if "PassOrFail" not in row:
            continue
        label = _normalize_pass_or_fail_label(row["PassOrFail"])
        count_key = next(
            (key for key in ("PassOrFail_count", "count", "total_count") if key in row),
            None,
        )
        assert count_key is not None, {"case_id": case["case_id"], "row": row}
        count_by_label[label] = int(row[count_key])

    normal_count = count_by_label.get("0")
    defect_count = count_by_label.get("1")
    assert normal_count is not None and defect_count is not None, {
        "case_id": case["case_id"],
        "metrics": metrics,
        "table": table,
    }
    total_count = int(metrics.get("total_count") or normal_count + defect_count)
    return {
        "total_count": total_count,
        "normal_count": normal_count,
        "defect_count": defect_count,
        "defect_rate_pct": defect_count / total_count * 100,
    }


def _normalize_pass_or_fail_label(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _assert_defect_rate_by_part(done: dict[str, Any], case: dict[str, Any]) -> None:
    evidence = _evidence(done, case)
    assert_used_columns(evidence.get("used_columns", []), ["PART_NAME", "PassOrFail"], context=case["case_id"])
    assert_answerability(done.get("answer_quality", {}), {"answerable", "limited"}, context=case["case_id"])
    assert_table_close(
        _analysis_table(done, case),
        expected_defect_rate_by_part(),
        key_column="PART_NAME",
        metric_columns=["total_count", "defect_count", "defect_rate_pct"],
        tolerance=1e-6,
        context=case["case_id"],
    )


def _assert_defect_reason_counts(done: dict[str, Any], case: dict[str, Any]) -> None:
    evidence = _evidence(done, case)
    assert_used_columns(evidence.get("used_columns", []), ["Reason", "PassOrFail"], context=case["case_id"])
    assert_answerability(done.get("answer_quality", {}), {"answerable", "limited"}, context=case["case_id"])
    assert_table_close(
        _analysis_table(done, case),
        expected_defect_reason_counts(),
        key_column="Reason",
        metric_columns=["defect_count"],
        tolerance=1e-6,
        context=case["case_id"],
    )
