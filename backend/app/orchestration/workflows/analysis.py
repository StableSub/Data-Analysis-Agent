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

from backend.app.core.trace_logging import set_trace_stage
from backend.app.modules.analysis.schemas import AnalysisExecutionResult
from backend.app.modules.planner.schemas import PlanningResult
from backend.app.modules.analysis.service import AnalysisService
from backend.app.orchestration.state import AnalysisGraphState
from backend.app.orchestration.utils import resolve_target_source_id


# analysis 서브그래프를 조립한다.
# planning -> execution -> validation -> persist 흐름을 구성한다.
def build_analysis_workflow(
    *,
    analysis_service: AnalysisService,
    default_model: str = "gpt-5-nano",
):
    def _as_dict(value: Any) -> Dict[str, Any] | None:
        if isinstance(value, dict):
            return value
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump()
            if isinstance(dumped, dict):
                return dumped
        return None

    def _build_failure_output(message: str) -> Dict[str, Any]:
        return {
            "type": "analysis_failed",
            "content": message,
        }

    def _current_dataset_context(
        state: AnalysisGraphState,
        *,
        source_id: str,
    ) -> Dict[str, Any]:
        dataset_context = _as_dict(state.get("dataset_context"))
        if dataset_context is not None and dataset_context.get("source_id") == source_id:
            return dataset_context
        return analysis_service.dataset_context_service.build_context(source_id).model_dump()

    def _should_replan(
        state: AnalysisGraphState,
        *,
        target_source_id: str,
    ) -> bool:
        planning_result = _as_dict(state.get("planning_result"))
        if planning_result is None:
            return True
        if bool(planning_result.get("needs_clarification", False)):
            return False
        analysis_plan = _as_dict(planning_result.get("analysis_plan"))
        if analysis_plan is None:
            return True
        dataset_context = _as_dict(state.get("dataset_context"))
        if dataset_context is None:
            return True
        return str(dataset_context.get("source_id") or "") != target_source_id

    # 질문 해석, 컬럼 grounding, plan 초안 생성, 최종 plan 확정까지 수행한다.
    # 모호한 질문이면 needs_clarification 상태로 종료한다.
    def analysis_planning_node(state: AnalysisGraphState) -> Dict[str, Any]:
        set_trace_stage("analysis_planning")
        question = str(state.get("user_input", "")).strip()
        source_id = resolve_target_source_id(state)
        if not question:
            analysis_error = analysis_service.processor.build_error(
                "question_understanding",
                "user_input is empty",
            )
            error_message = analysis_error.message
            return {
                "analysis_error": analysis_error.model_dump(),
                "analysis_result": AnalysisExecutionResult(
                    execution_status="fail",
                    error_stage=analysis_error.stage,
                    error_message=analysis_error.message,
                ).model_dump(),
                "final_status": "fail",
                "output": _build_failure_output(error_message),
            }

        try:
            if source_id is None:
                raise ValueError("source_id is required for analysis")

            dataset_context = _current_dataset_context(state, source_id=source_id)
            if _should_replan(state, target_source_id=source_id):
                planning_result = analysis_service.planner_service.plan(
                    user_input=question,
                    request_context=str(state.get("request_context", "")),
                    source_id=source_id,
                    dataset_context=dataset_context,
                    guideline_context=state.get("guideline_context"),
                    model_id=state.get("model_id"),
                )
            else:
                planning_result_dict = _as_dict(state.get("planning_result")) or {}
                planning_result = PlanningResult.model_validate(planning_result_dict)
            if planning_result.needs_clarification:
                return {
                    "planning_result": planning_result.model_dump(),
                    "dataset_context": dataset_context,
                    "final_status": "needs_clarification",
                    "clarification_question": planning_result.clarification_question,
                }
            if planning_result.route != "analysis" or planning_result.analysis_plan is None:
                raise ValueError("planner did not route this request to analysis")
            analysis_plan = planning_result.analysis_plan
            return {
                "planning_result": planning_result.model_dump(),
                "dataset_context": dataset_context,
                "dataset_meta": analysis_plan.metadata_snapshot.model_dump(),
                "analysis_plan": analysis_plan.model_dump(),
                "final_status": "planning",
            }
        except Exception as exc:
            analysis_error = analysis_service.processor.build_error(
                "plan_validation",
                str(exc),
                detail={"source_id": source_id or ""},
            )
            error_message = analysis_error.message
            return {
                "analysis_error": analysis_error.model_dump(),
                "analysis_result": AnalysisExecutionResult(
                    execution_status="fail",
                    error_stage=analysis_error.stage,
                    error_message=analysis_error.message,
                ).model_dump(),
                "final_status": "fail",
                "output": _build_failure_output(error_message),
            }

    # planning 결과에 따라 execution, clarification 종료, fail 종료를 분기한다.
    def route_after_planning(state: AnalysisGraphState) -> str:
        status = state.get("final_status")
        if status == "needs_clarification":
            return "clarification"
        if status == "fail":
            return "fail"
        return "execute"

    def analysis_clarification_node(state: AnalysisGraphState) -> Dict[str, Any]:
        set_trace_stage("analysis_clarification")
        clarification_question = str(state.get("clarification_question", "")).strip()
        return {
            "final_status": "needs_clarification",
            "clarification_question": clarification_question,
        }

    # 최종 plan을 기반으로 코드 생성, code repair, sandbox 실행까지 수행한다.
    def analysis_execution_node(state: AnalysisGraphState) -> Dict[str, Any]:
        set_trace_stage("analysis_execution")
        source_id = resolve_target_source_id(state)
        dataset = analysis_service._get_dataset(source_id or "")
        if dataset is None:
            analysis_error = analysis_service.processor.build_error(
                "sandbox_execution",
                f"dataset not found: {source_id or ''}",
            )
            result = {
                "analysis_error": analysis_error.model_dump(),
                "analysis_result": AnalysisExecutionResult(
                    execution_status="fail",
                    error_stage=analysis_error.stage,
                    error_message=analysis_error.message,
                ).model_dump(),
                "final_status": "executing",
            }
            return result

        execution_bundle = analysis_service._run_code_generation_loop(
            question=str(state.get("user_input", "")),
            dataset=dataset,
            analysis_plan=state["analysis_plan"],
            model_id=state.get("model_id"),
        )
        result = {
            "generated_code": execution_bundle.get("generated_code"),
            "validated_code": execution_bundle.get("validated_code"),
            "sandbox_result": _as_dict(execution_bundle.get("sandbox_result")),
            "analysis_result": _as_dict(execution_bundle.get("analysis_result")),
            "analysis_error": _as_dict(execution_bundle.get("analysis_error")),
            "retry_count": execution_bundle.get("retry_count", 0),
            "final_status": "executing",
        }
        return result

    # execution 결과를 기준으로 success/fail 최종 상태를 확정한다.
    def analysis_validation_node(state: AnalysisGraphState) -> Dict[str, Any]:
        set_trace_stage("analysis_validation")
        result = state.get("analysis_result")
        if not isinstance(result, dict):
            analysis_error = analysis_service.processor.build_error(
                "result_validation",
                "analysis_result is missing",
            )
            error_message = analysis_error.message
            output = {
                "analysis_error": analysis_error.model_dump(),
                "analysis_result": AnalysisExecutionResult(
                    execution_status="fail",
                    error_stage=analysis_error.stage,
                    error_message=analysis_error.message,
                ).model_dump(),
                "final_status": "fail",
                "output": _build_failure_output(error_message),
            }
            return output

        execution_result = AnalysisExecutionResult.model_validate(result)

        if execution_result.execution_status == "success":
            return {
                "final_status": "success",
            }

        if state.get("analysis_error") is None:
            analysis_error = analysis_service.processor.build_error(
                execution_result.error_stage or "result_validation",
                execution_result.error_message or "analysis execution failed",
            )
            error_message = analysis_error.message
            return {
                "analysis_error": analysis_error.model_dump(),
                "final_status": "fail",
                "output": _build_failure_output(error_message),
            }
        existing_error = state.get("analysis_error") or {}
        error_message = str(existing_error.get("message") or execution_result.error_message or "analysis execution failed")
        return {
            "final_status": "fail",
            "output": _build_failure_output(error_message),
        }

    # validation 결과가 success면 persist로 아니면 바로 종료한다.
    def route_after_validation(state: AnalysisGraphState) -> str:
        if state.get("final_status") == "success":
            return "persist"
        return "end"

    # 최종 성공 결과를 results 저장소에 기록한다.
    def analysis_persist_result_node(state: AnalysisGraphState) -> Dict[str, Any]:
        set_trace_stage("analysis_persist")
        try:
            result_id = analysis_service._persist_result(
                question=str(state.get("user_input", "")),
                source_id=resolve_target_source_id(state) or "",
                session_id=state.get("session_id"),
                analysis_plan=state.get("analysis_plan"),
                generated_code=state.get("generated_code"),
                execution_result=AnalysisExecutionResult.model_validate(state["analysis_result"]),
            )
            return {
                "analysis_result_id": result_id,
            }
        except Exception as exc:
            analysis_error = analysis_service.processor.build_error(
                "persist_result",
                str(exc),
            )
            return {
                "analysis_error": analysis_error.model_dump(),
                "final_status": "fail",
                "output": _build_failure_output(analysis_error.message),
            }

    graph = StateGraph(AnalysisGraphState)
    graph.add_node("analysis_planning", analysis_planning_node)
    graph.add_node("analysis_clarification", analysis_clarification_node)
    graph.add_node("analysis_execution", analysis_execution_node)
    graph.add_node("analysis_validation", analysis_validation_node)
    graph.add_node("analysis_persist_result", analysis_persist_result_node)

    graph.add_edge(START, "analysis_planning")
    graph.add_conditional_edges(
        "analysis_planning",
        route_after_planning,
        {
            "execute": "analysis_execution",
            "clarification": "analysis_clarification",
            "fail": END,
        },
    )
    graph.add_edge("analysis_clarification", END)
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
