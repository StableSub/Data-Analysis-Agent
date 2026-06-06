from __future__ import annotations

from backend.app.modules.planner.schemas import PlannerDecision
from backend.app.modules.planner.service import (
    _apply_planner_decision_guards,
    _should_force_skip_preprocess_for_analysis_request,
)


def test_aggregate_visualization_request_does_not_require_preprocess() -> None:
    question = "양품과 불량의 비율, 불량 사유별 건수, 제품별 생산량을 각각 적절한 그래프로 시각화해줘."

    assert _should_force_skip_preprocess_for_analysis_request(question) is True


def test_explicit_preprocess_request_keeps_preprocess_path() -> None:
    question = "수치형 컬럼을 표준화한 뒤 불량 여부와의 관계를 분석해줘."

    assert _should_force_skip_preprocess_for_analysis_request(question) is False


def test_guard_overrides_only_preprocess_required_for_plain_visualization() -> None:
    decision = PlannerDecision(
        is_general_question=False,
        ask_analysis=True,
        preprocess_required=True,
        need_visualization=True,
        need_report=False,
        guideline_context_used=False,
    )

    guarded = _apply_planner_decision_guards(
        decision,
        "양품과 불량의 비율, 불량 사유별 건수, 제품별 생산량을 각각 적절한 그래프로 시각화해줘.",
    )

    assert guarded.preprocess_required is False
    assert guarded.need_visualization is True
    assert guarded.ask_analysis is True


def test_guard_removes_guideline_induced_visualization_when_user_did_not_ask_for_chart() -> None:
    decision = PlannerDecision(
        is_general_question=False,
        ask_analysis=True,
        preprocess_required=False,
        need_visualization=True,
        need_report=False,
        guideline_context_used=True,
    )

    guarded = _apply_planner_decision_guards(
        decision,
        "날짜별 불량 건수를 분석해줘.",
    )

    assert guarded.need_visualization is False
    assert guarded.ask_analysis is True


def test_guard_preserves_explicit_preprocess_decision() -> None:
    decision = PlannerDecision(
        is_general_question=False,
        ask_analysis=True,
        preprocess_required=True,
        need_visualization=True,
        need_report=False,
        guideline_context_used=False,
    )

    guarded = _apply_planner_decision_guards(
        decision,
        "결측치를 처리하고 수치형 컬럼을 표준화한 뒤 불량 여부를 시각화해줘.",
    )

    assert guarded.preprocess_required is True
    assert guarded.need_visualization is True
