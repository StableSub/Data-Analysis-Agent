from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


def assert_float_close(actual: float, expected: float, *, tolerance: float = 1e-6, context: str = "float") -> None:
    assert math.isclose(float(actual), float(expected), abs_tol=tolerance), {
        "context": context,
        "actual": actual,
        "expected": expected,
        "tolerance": tolerance,
    }


def assert_used_columns(actual: Iterable[str], expected: Iterable[str], *, context: str = "used_columns") -> None:
    actual_set = {str(column) for column in actual}
    expected_set = {str(column) for column in expected}
    assert expected_set.issubset(actual_set), {
        "context": context,
        "missing": sorted(expected_set - actual_set),
        "actual": sorted(actual_set),
    }


def assert_evidence_keys(payload: Mapping[str, Any], expected_keys: Iterable[str], *, context: str = "evidence") -> None:
    missing = [key for key in expected_keys if key not in payload]
    assert not missing, {"context": context, "missing": missing, "payload": dict(payload)}


def assert_answer_contains_terms(answer: str, terms: Iterable[str], *, context: str = "answer") -> None:
    missing = [term for term in terms if term not in answer]
    assert not missing, {"context": context, "missing": missing, "answer": answer}


def assert_answer_excludes_terms(answer: str, terms: Iterable[str], *, context: str = "answer") -> None:
    present = [term for term in terms if term in answer]
    assert not present, {"context": context, "present": present, "answer": answer}


def assert_answerability(answer_quality: Mapping[str, Any], expected_status: str | Iterable[str], *, context: str = "answer_quality") -> None:
    expected = {expected_status} if isinstance(expected_status, str) else set(expected_status)
    actual = str(answer_quality.get("status") or "")
    assert actual in expected, {"context": context, "actual": actual, "expected": sorted(expected)}


def assert_no_forbidden_metric_keys(payload: Mapping[str, Any], forbidden_keys: Iterable[str], *, context: str = "metrics") -> None:
    found = sorted(set(forbidden_keys) & set(payload.keys()))
    assert not found, {"context": context, "forbidden_keys": found, "payload": dict(payload)}


def assert_table_close(
    actual_table: Sequence[Mapping[str, Any]],
    expected_table: Sequence[Mapping[str, Any]],
    *,
    key_column: str,
    metric_columns: Iterable[str],
    tolerance: float = 1e-6,
    context: str = "table",
) -> None:
    actual_by_key = {str(row[key_column]): row for row in actual_table}
    expected_by_key = {str(row[key_column]): row for row in expected_table}
    assert set(actual_by_key) == set(expected_by_key), {
        "context": context,
        "actual_keys": sorted(actual_by_key),
        "expected_keys": sorted(expected_by_key),
    }
    for key, expected_row in expected_by_key.items():
        actual_row = actual_by_key[key]
        for metric in metric_columns:
            actual_value = actual_row.get(metric)
            expected_value = expected_row.get(metric)
            if isinstance(expected_value, float):
                assert_float_close(float(actual_value), expected_value, tolerance=tolerance, context=f"{context}.{key}.{metric}")
            else:
                assert actual_value == expected_value, {
                    "context": f"{context}.{key}.{metric}",
                    "actual": actual_value,
                    "expected": expected_value,
                }


def route_accuracy(cases: Sequence[Mapping[str, Any]]) -> float:
    return _rate(cases, lambda case: case.get("expected_route") == case.get("actual_route"))


def answerability_accuracy(cases: Sequence[Mapping[str, Any]]) -> float:
    return _rate(cases, lambda case: case.get("expected_answer_status") == case.get("actual_answer_status"))


def forbidden_term_violation_rate(cases: Sequence[Mapping[str, Any]]) -> float:
    def has_violation(case: Mapping[str, Any]) -> bool:
        answer = str(case.get("answer") or "")
        return any(str(term) in answer for term in case.get("forbidden_answer_terms", []))
    return _rate(cases, has_violation)


def column_grounding_f1(expected_columns: Iterable[str], actual_columns: Iterable[str]) -> float:
    expected = {str(column) for column in expected_columns}
    actual = {str(column) for column in actual_columns}
    if not expected and not actual:
        return 1.0
    if not expected or not actual:
        return 0.0
    overlap = len(expected & actual)
    precision = overlap / len(actual)
    recall = overlap / len(expected)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def evidence_coverage_rate(payload: Mapping[str, Any], expected_keys: Iterable[str]) -> float:
    keys = list(expected_keys)
    if not keys:
        return 1.0
    present = sum(1 for key in keys if key in payload)
    return present / len(keys)


def protected_column_violation_rate(protected_columns: Iterable[str], actual_columns: Iterable[str]) -> float:
    protected = {str(column) for column in protected_columns}
    actual = {str(column) for column in actual_columns}
    return 1.0 if protected & actual else 0.0


def scaled_detection_accuracy(cases: Sequence[Mapping[str, Any]]) -> float:
    return _rate(cases, lambda case: bool(case.get("expected_scaled_like")) == bool(case.get("actual_scaled_like")))


def _rate(cases: Sequence[Mapping[str, Any]], predicate) -> float:
    if not cases:
        return 1.0
    return sum(1 for case in cases if predicate(case)) / len(cases)
