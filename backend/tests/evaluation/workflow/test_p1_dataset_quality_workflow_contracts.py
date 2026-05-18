from __future__ import annotations

from backend.app.orchestration.evidence import build_evidence_contract
from runtime_assertions import assert_answerability, assert_no_forbidden_metric_keys


def test_missing_analysis_evidence_for_unlabeled_defect_rate_is_unanswerable() -> None:
    evidence, answer_quality = build_evidence_contract(
        state={
            "source_id": "unlabeled_data.csv",
            "final_status": "success",
            "handoff": {"ask_analysis": True},
        },
        merged_context={"applied_steps": ["analysis"]},
    )

    assert evidence["analysis_status"] == "success"
    assert evidence["source_id"] == "unlabeled_data.csv"
    assert evidence["warnings"][0]["code"] == "analysis_missing"
    assert_no_forbidden_metric_keys(evidence.get("analysis_metrics", {}), ["defect_count", "defect_rate_pct"])
    assert_answerability(answer_quality, "unanswerable")


def test_scaled_detection_evidence_is_answerable_when_metrics_are_present() -> None:
    metrics = {"scaled_like": True, "mean_abs_max": 0.002, "std_range": [0.999, 1.001]}
    evidence, answer_quality = build_evidence_contract(
        state={
            "source_id": "moldset_labeled_cn7.csv",
            "final_status": "success",
            "analysis_result": {
                "execution_status": "success",
                "summary": "주요 공정 컬럼은 평균 0, 표준편차 1 수준으로 이미 스케일링되어 있습니다.",
                "raw_metrics": metrics,
                "used_columns": ["Injection_Time", "Filling_Time", "Plasticizing_Time", "Cycle_Time"],
                "quality_status": "complete",
            },
        },
        merged_context={"applied_steps": ["analysis"]},
    )

    assert evidence["analysis_metrics"] == metrics
    assert evidence["used_columns"] == ["Injection_Time", "Filling_Time", "Plasticizing_Time", "Cycle_Time"]
    assert_answerability(answer_quality, "answerable")
