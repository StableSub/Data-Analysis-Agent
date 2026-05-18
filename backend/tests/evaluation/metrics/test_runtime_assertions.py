from __future__ import annotations

import pytest

from runtime_assertions import (
    assert_answer_contains_terms,
    assert_answer_excludes_terms,
    assert_answerability,
    assert_evidence_keys,
    assert_float_close,
    assert_no_forbidden_metric_keys,
    assert_table_close,
    assert_used_columns,
)


def test_assertion_helpers_accept_expected_runtime_payloads() -> None:
    assert_float_close(1.000001, 1.0, tolerance=0.00001)
    assert_used_columns(["PassOrFail", "PART_NAME"], ["PassOrFail"])
    assert_evidence_keys({"source_id": "s", "used_columns": []}, ["source_id"])
    assert_answer_contains_terms("총 2607건 중 불량 52건", ["2607", "52"])
    assert_answer_excludes_terms("총 2607건", ["정확도", "F1"])
    assert_answerability({"status": "answerable"}, "answerable")
    assert_no_forbidden_metric_keys({"total_count": 2607}, ["defect_rate_pct"])
    assert_table_close(
        [{"key": "A", "count": 2, "rate": 1.5}],
        [{"key": "A", "count": 2, "rate": 1.5}],
        key_column="key",
        metric_columns=["count", "rate"],
    )


def test_assertion_helpers_fail_with_context_payloads() -> None:
    with pytest.raises(AssertionError):
        assert_used_columns(["PassOrFail"], ["Reason"])
    with pytest.raises(AssertionError):
        assert_answer_excludes_terms("모델 정확도", ["정확도"])
    with pytest.raises(AssertionError):
        assert_no_forbidden_metric_keys({"defect_rate_pct": 1.0}, ["defect_rate_pct"])
