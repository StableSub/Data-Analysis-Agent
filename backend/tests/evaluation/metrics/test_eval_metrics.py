from __future__ import annotations

from runtime_assertions import (
    answerability_accuracy,
    column_grounding_f1,
    evidence_coverage_rate,
    forbidden_term_violation_rate,
    protected_column_violation_rate,
    route_accuracy,
    scaled_detection_accuracy,
)


def test_route_and_answerability_accuracy_metrics() -> None:
    cases = [
        {"expected_route": "analysis", "actual_route": "analysis", "expected_answer_status": "answerable", "actual_answer_status": "answerable"},
        {"expected_route": "preprocess", "actual_route": "analysis", "expected_answer_status": "approval_required", "actual_answer_status": "answerable"},
    ]

    assert route_accuracy(cases) == 0.5
    assert answerability_accuracy(cases) == 0.5


def test_grounding_evidence_and_violation_metrics() -> None:
    assert column_grounding_f1(["PassOrFail", "Reason"], ["PassOrFail", "PART_NAME"]) == 0.5
    assert evidence_coverage_rate({"source_id": "s", "used_columns": []}, ["source_id", "used_columns", "analysis_metrics"]) == 2 / 3
    assert protected_column_violation_rate(["PassOrFail"], ["Injection_Time", "PassOrFail"]) == 1.0
    assert protected_column_violation_rate(["PassOrFail"], ["Injection_Time"]) == 0.0


def test_forbidden_term_and_scaled_detection_metrics() -> None:
    assert forbidden_term_violation_rate([
        {"answer": "정확도는 계산할 수 없습니다.", "forbidden_answer_terms": ["정확도"]},
        {"answer": "불량률은 1.9%입니다.", "forbidden_answer_terms": ["정확도"]},
    ]) == 0.5
    assert scaled_detection_accuracy([
        {"expected_scaled_like": True, "actual_scaled_like": True},
        {"expected_scaled_like": True, "actual_scaled_like": False},
    ]) == 0.5
