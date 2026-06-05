from __future__ import annotations

from backend.app.orchestration import builder
from backend.app.orchestration.builder import build_main_workflow
from backend.app.orchestration.guideline_routing import route_after_guideline
from backend.app.orchestration.workflows import guideline as guideline_workflow
from backend.tests.guideline_first_fakes import (
    ActiveGuidelineService,
    FakeGuidelineRagService,
    GuidelineAwarePlannerLLM,
    GuidelineSummaryGateway,
    NoopRagService,
    PlannerMustNotRun,
    PlannerMustNotRunWithContext,
    dataset_context,
    guideline,
    guideline_chunk,
    guideline_context_payload,
    planner_service,
)


def test_guideline_check_prefers_active_guideline_context(monkeypatch) -> None:
    source_id = "guideline-source"
    active_guideline = guideline(source_id)

    monkeypatch.setattr(guideline_workflow, "LLMGateway", GuidelineSummaryGateway)
    monkeypatch.setattr(
        builder,
        "answer_data_question",
        lambda **_: "가이드라인 근거: 제품은 PART_NAME, 불량은 PassOrFail=1",
    )
    monkeypatch.setattr(builder, "answer_general_question", lambda **_: "일반 답변")

    workflow = build_main_workflow(
        planner_service=PlannerMustNotRun(),
        analysis_service=object(),
        preprocess_service=object(),
        eda_service=object(),
        rag_service=NoopRagService(),
        guideline_service=ActiveGuidelineService(
            active=active_guideline,
            guidelines={source_id: active_guideline},
        ),
        guideline_rag_service=FakeGuidelineRagService(
            retrieved=[guideline_chunk(source_id)]
        ),
        visualization_service=object(),
        report_service=object(),
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": "현재 가이드라인으로 올라온 파일 확인 좀",
            "active_guideline_source_id": source_id,
            "model_id": "test-model",
        }
    )

    assert result["output"]["type"] == "data_qa"
    assert result["output"]["content"].startswith("가이드라인 근거:")
    assert result["guideline_result"]["status"] == "retrieved"
    assert result["guideline_result"]["filename"] == "manufacturing-guideline.pdf"


def test_guideline_check_with_dataset_does_not_fall_through_to_planner(
    monkeypatch,
) -> None:
    source_id = "guideline-source"
    active_guideline = guideline(source_id)

    monkeypatch.setattr(guideline_workflow, "LLMGateway", GuidelineSummaryGateway)
    monkeypatch.setattr(
        builder,
        "answer_data_question",
        lambda **_: "가이드라인 근거: 제품은 PART_NAME, 불량은 PassOrFail=1",
    )
    monkeypatch.setattr(builder, "answer_general_question", lambda **_: "일반 답변")

    workflow = build_main_workflow(
        planner_service=PlannerMustNotRunWithContext(),
        analysis_service=object(),
        preprocess_service=object(),
        eda_service=object(),
        rag_service=NoopRagService(),
        guideline_service=ActiveGuidelineService(
            active=active_guideline,
            guidelines={source_id: active_guideline},
        ),
        guideline_rag_service=FakeGuidelineRagService(
            retrieved=[guideline_chunk(source_id)]
        ),
        visualization_service=object(),
        report_service=object(),
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": "현재 가이드라인으로 올라온 파일 확인 좀",
            "source_id": "dataset-source",
            "active_guideline_source_id": source_id,
            "model_id": "test-model",
        }
    )

    assert result["output"]["type"] == "data_qa"
    assert result["output"]["content"].startswith("가이드라인 근거:")
    assert result["guideline_result"]["status"] == "retrieved"


def test_guideline_check_without_active_guideline_does_not_use_general_answer(
    monkeypatch,
) -> None:
    def fail_if_data_qa_llm_called(**_: object) -> str:
        raise AssertionError("unsupported guideline checks must not call data QA LLM")

    monkeypatch.setattr(builder, "answer_general_question", lambda **_: "일반 답변")
    monkeypatch.setattr(builder, "answer_data_question", fail_if_data_qa_llm_called)

    workflow = build_main_workflow(
        planner_service=PlannerMustNotRun(),
        analysis_service=object(),
        preprocess_service=object(),
        eda_service=object(),
        rag_service=NoopRagService(),
        guideline_service=ActiveGuidelineService(active=None, guidelines={}),
        guideline_rag_service=FakeGuidelineRagService(),
        visualization_service=object(),
        report_service=object(),
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": "현재 가이드라인으로 올라온 파일 확인 좀",
            "active_guideline_source_id": "",
            "model_id": "test-model",
        }
    )

    assert result["output"]["type"] == "data_qa"
    assert result["output"]["content"] != "일반 답변"
    assert result["guideline_result"]["status"] == "no_selected_guideline"
    assert result["answer_quality"]["answerable"] is False
    assert result["answer_quality"]["status"] == "unanswerable"
    assert "충분하지 않습니다" in result["answer_quality"]["abstain_reason"]


def test_guideline_context_resolves_defect_rate_before_clarification() -> None:
    result = planner_service(GuidelineAwarePlannerLLM()).plan(
        user_input="제품별 불량률을 막대그래프로 시각화해줘.",
        request_context=None,
        source_id="dataset-source",
        dataset_context=dataset_context(),
        guideline_context=guideline_context_payload(),
        model_id="test-model",
    )

    assert result.needs_clarification is False
    assert result.analysis_plan is not None
    assert result.guideline_context_used is True
    assert result.analysis_plan.group_by == ["PART_NAME"]
    assert "PassOrFail=1" in result.analysis_plan.objective
    assert result.analysis_plan.filters == []
    assert result.analysis_plan.metrics[0].column == "PassOrFail"
    assert result.analysis_plan.metrics[0].positive_value == 1
    assert result.analysis_plan.metrics[0].aggregation == "rate"
    assert {"PART_NAME", "PassOrFail"} <= set(result.analysis_plan.used_columns)


def test_guideline_analysis_request_with_dataset_still_reaches_planner() -> None:
    analysis_questions = [
        "가이드라인 기준으로 제품별 불량률을 그래프로 보여줘",
        "가이드라인 기준으로 불량 건수 알려줘",
        "가이드라인 기준으로 제품 불량 건수를 알려줘",
    ]

    for question in analysis_questions:
        assert (
            route_after_guideline(
                {
                    "source_id": "dataset-source",
                    "user_input": question,
                }
            )
            == "planner"
        )


def test_without_guideline_still_clarifies() -> None:
    result = planner_service(GuidelineAwarePlannerLLM()).plan(
        user_input="제품별 불량률을 막대그래프로 시각화해줘.",
        request_context=None,
        source_id="dataset-source",
        dataset_context=dataset_context(),
        guideline_context=None,
        model_id="test-model",
    )

    assert result.needs_clarification is True
    assert result.clarification_question == "제품/불량률 매핑을 확인해야 합니다."
    assert result.guideline_context_used is False
