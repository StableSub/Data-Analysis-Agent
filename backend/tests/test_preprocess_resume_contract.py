from backend.app.modules.planner.schemas import PlanningResult
from backend.app.modules.planner.service import build_handoff_from_planning_result
from backend.app.orchestration.builder import route_after_preprocess_result
from backend.app.orchestration.evidence import build_evidence_contract


def test_preprocess_only_handoff_does_not_request_analysis_after_approval() -> None:
    planning_result = PlanningResult(
        route="analysis",
        preprocess_required=True,
        ask_analysis=False,
    )

    handoff = build_handoff_from_planning_result(planning_result)

    assert handoff["ask_preprocess"] is True
    assert handoff["ask_analysis"] is False
    assert route_after_preprocess_result({"preprocess_result": {"status": "applied"}, "handoff": handoff}) == "merge_context"


def test_preprocess_result_is_answerable_evidence() -> None:
    evidence_package, answer_quality = build_evidence_contract(
        state={
            "source_id": "original-source",
            "preprocess_result": {
                "status": "applied",
                "summary": "전처리 연산 2개를 적용했습니다.",
                "output_source_id": "clean-source",
                "output_filename": "clean.csv",
            },
            "handoff": {
                "ask_preprocess": True,
                "ask_analysis": False,
            },
        },
        merged_context={"applied_steps": ["preprocess"]},
    )

    assert answer_quality.get("answerable") is True
    assert answer_quality.get("status") == "answerable"
    assert "abstain_reason" not in answer_quality
    assert evidence_package.get("source_id") == "clean-source"
    assert evidence_package.get("filename") == "clean.csv"
    assert evidence_package.get("preprocess_status") == "applied"
