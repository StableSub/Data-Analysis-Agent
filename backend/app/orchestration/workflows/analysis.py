"""
V1 analysis 서브그래프.

역할:
- 자연어 질문을 분석 계획으로 구조화한다.
- 계획 기반으로 코드를 생성/실행한다.
- 실행 결과를 검증하고 성공 시 저장한다.
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from backend.app.modules.analysis.schemas import AnalysisExecutionResult
from backend.app.modules.analysis.service import AnalysisService
from backend.app.orchestration.state import AnalysisGraphState
from backend.app.orchestration.utils import resolve_target_source_id


def build_analysis_workflow(
    *,
    analysis_service: AnalysisService,
    default_model: str = "gpt-5-nano",
):
    def analysis_planning_node(state: AnalysisGraphState) -> Dict[str, Any]:
        question = str(state.get("user_input", "")).strip()
        source_id = resolve_target_source_id(state)
        if not question:
            analysis_error = analysis_service.processor.build_error(
                "question_understanding",
                "user_input is empty",
            )
            return {
                "analysis_error": analysis_error,
                "analysis_result": AnalysisExecutionResult(
                    execution_status="fail",
                    error_stage=analysis_error.stage,
                    error_message=analysis_error.message,
                ),
                "final_status": "fail",
            }

        try:
            dataset_meta = analysis_service.build_dataset_metadata(source_id or "")
            question_understanding = analysis_service.run_service.build_question_understanding(
                question=question,
                dataset_meta=dataset_meta,
                model_id=state.get("model_id"),
            )
            if question_understanding.ambiguity_status != "clear":
                return {
                    "dataset_meta": dataset_meta,
                    "question_understanding": question_understanding,
                    "final_status": "needs_clarification",
                    "clarification_question": question_understanding.clarification_message,
                }

            column_grounding = analysis_service.processor.ground_columns(
                question_understanding=question_understanding,
                dataset_meta=dataset_meta,
            )
            analysis_plan_draft = analysis_service.run_service.build_analysis_plan_draft(
                question=question,
                question_understanding=question_understanding,
                column_grounding=column_grounding,
                dataset_meta=dataset_meta,
                model_id=state.get("model_id"),
            )
            if analysis_plan_draft.ambiguity_status != "clear":
                clarification_message = (
                    analysis_plan_draft.clarification_message
                    or question_understanding.clarification_message
                )
                return {
                    "dataset_meta": dataset_meta,
                    "question_understanding": question_understanding,
                    "column_grounding": column_grounding,
                    "analysis_plan_draft": analysis_plan_draft,
                    "final_status": "needs_clarification",
                    "clarification_question": clarification_message,
                }

            analysis_plan = analysis_service.processor.validate_and_finalize_plan(
                plan_draft=analysis_plan_draft,
                dataset_meta=dataset_meta,
                column_grounding=column_grounding,
            )
            return {
                "dataset_meta": dataset_meta,
                "question_understanding": question_understanding,
                "column_grounding": column_grounding,
                "analysis_plan_draft": analysis_plan_draft,
                "analysis_plan": analysis_plan,
                "final_status": "planning",
            }
        except Exception as exc:
            analysis_error = analysis_service.processor.build_error(
                "plan_validation",
                str(exc),
                detail={"source_id": source_id or ""},
            )
            return {
                "analysis_error": analysis_error,
                "analysis_result": AnalysisExecutionResult(
                    execution_status="fail",
                    error_stage=analysis_error.stage,
                    error_message=analysis_error.message,
                ),
                "final_status": "fail",
            }

    def route_after_planning(state: AnalysisGraphState) -> str:
        status = state.get("final_status")
        if status == "needs_clarification":
            return "clarification"
        if status == "fail":
            return "fail"
        return "execute"

    def analysis_execution_node(state: AnalysisGraphState) -> Dict[str, Any]:
        source_id = resolve_target_source_id(state)
        dataset = analysis_service._get_dataset(source_id or "")
        if dataset is None:
            analysis_error = analysis_service.processor.build_error(
                "sandbox_execution",
                f"dataset not found: {source_id or ''}",
            )
            return {
                "analysis_error": analysis_error,
                "analysis_result": AnalysisExecutionResult(
                    execution_status="fail",
                    error_stage=analysis_error.stage,
                    error_message=analysis_error.message,
                ),
                "final_status": "executing",
            }

        execution_bundle = analysis_service._run_code_generation_loop(
            question=str(state.get("user_input", "")),
            dataset=dataset,
            analysis_plan=state["analysis_plan"],
            model_id=state.get("model_id"),
        )
        return {
            "generated_code": execution_bundle.get("generated_code"),
            "validated_code": execution_bundle.get("validated_code"),
            "sandbox_result": execution_bundle.get("sandbox_result"),
            "analysis_result": execution_bundle.get("analysis_result"),
            "analysis_error": execution_bundle.get("analysis_error"),
            "retry_count": execution_bundle.get("retry_count", 0),
            "final_status": "executing",
        }

    def analysis_validation_node(state: AnalysisGraphState) -> Dict[str, Any]:
        result = state.get("analysis_result")
        if not isinstance(result, AnalysisExecutionResult):
            analysis_error = analysis_service.processor.build_error(
                "result_validation",
                "analysis_result is missing",
            )
            return {
                "analysis_error": analysis_error,
                "analysis_result": AnalysisExecutionResult(
                    execution_status="fail",
                    error_stage=analysis_error.stage,
                    error_message=analysis_error.message,
                ),
                "final_status": "fail",
            }

        if result.execution_status == "success":
            return {
                "final_status": "success",
            }

        if state.get("analysis_error") is None:
            analysis_error = analysis_service.processor.build_error(
                result.error_stage or "result_validation",
                result.error_message or "analysis execution failed",
            )
            return {
                "analysis_error": analysis_error,
                "final_status": "fail",
            }
        return {
            "final_status": "fail",
        }

    def route_after_validation(state: AnalysisGraphState) -> str:
        if state.get("final_status") == "success":
            return "persist"
        return "end"

    def analysis_persist_result_node(state: AnalysisGraphState) -> Dict[str, Any]:
        result_id = analysis_service._persist_result(
            question=str(state.get("user_input", "")),
            source_id=resolve_target_source_id(state) or "",
            session_id=state.get("session_id"),
            analysis_plan=state.get("analysis_plan"),
            generated_code=state.get("generated_code"),
            execution_result=state["analysis_result"],
        )
        return {
            "analysis_result_id": result_id,
        }

    graph = StateGraph(AnalysisGraphState)
    graph.add_node("analysis_planning", analysis_planning_node)
    graph.add_node("analysis_execution", analysis_execution_node)
    graph.add_node("analysis_validation", analysis_validation_node)
    graph.add_node("analysis_persist_result", analysis_persist_result_node)

    graph.add_edge(START, "analysis_planning")
    graph.add_conditional_edges(
        "analysis_planning",
        route_after_planning,
        {
            "execute": "analysis_execution",
            "clarification": END,
            "fail": END,
        },
    )
    graph.add_edge("analysis_execution", "analysis_validation")
    graph.add_conditional_edges(
        "analysis_validation",
        route_after_validation,
        {
            "persist": "analysis_persist_result",
            "end": END,
        },
    )
    graph.add_edge("analysis_persist_result", END)
    return graph.compile()
