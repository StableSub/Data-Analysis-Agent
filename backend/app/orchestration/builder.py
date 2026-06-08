from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Mapping

from langgraph.graph import END, START, StateGraph

from ..core.trace_logging import set_trace_stage
from ..modules.chat_fast_path import (
    decide_common_analytics_fast_path,
    try_fast_dataset_answer,
)
from ..modules.datasets.service import DatasetReadError
from ..modules.planner.service import build_handoff_from_planning_result
from .ai import answer_data_question, answer_general_question
from .error_contract import build_failure_output, build_workflow_error_from_exception
from .evidence import build_evidence_contract
from .guideline_routing import route_after_guideline
from .intake_router import build_intake_router_workflow
from .state import MainWorkflowState
from .state_view import build_merged_context
from .workflows.analysis import build_analysis_workflow
from .workflows.guideline import build_guideline_workflow
from .workflows.preprocess import build_preprocess_workflow
from .workflows.rag import build_rag_workflow
from .workflows.report import build_report_workflow
from .workflows.visualization import build_visualization_workflow

if TYPE_CHECKING:
    from ..modules.chat_fast_path.executor import CommonAnalyticsExecutionResult


def _analysis_result_from_common_analytics(
    result: CommonAnalyticsExecutionResult,
) -> dict[str, Any]:
    return {
        "execution_status": "success",
        "summary": result.summary,
        "used_columns": result.columns,
        "quality_status": "complete",
        "raw_metrics": result.raw_metrics,
        "table": result.table,
    }


def route_after_preprocess_result(state: MainWorkflowState | dict[str, Any]) -> str:
    preprocess_result = state.get("preprocess_result") or {}
    output = state.get("output") or {}
    if (
        preprocess_result.get("status") == "cancelled"
        or output.get("type") == "cancelled"
    ):
        return "cancelled"
    if (
        preprocess_result.get("status") == "failed"
        or output.get("type") == "preprocess_failed"
    ):
        return "failed"
    if _preprocess_has_downstream_work(state):
        return "analysis"
    return "merge_context"


def _preprocess_has_downstream_work(state: MainWorkflowState | dict[str, Any]) -> bool:
    handoff = state.get("handoff") or {}
    if not isinstance(handoff, dict):
        return False
    return any(
        bool(handoff.get(key, False))
        for key in ("ask_analysis", "ask_visualization", "ask_report")
    )


def _is_preprocess_only_result(state: MainWorkflowState | dict[str, Any]) -> bool:
    preprocess_result = state.get("preprocess_result")
    if not isinstance(preprocess_result, dict):
        return False
    if preprocess_result.get("status") not in {"applied", "skipped"}:
        return False
    return not _preprocess_has_downstream_work(state)


def _build_preprocess_answer(preprocess_result: Mapping[str, Any]) -> str:
    status = str(preprocess_result.get("status") or "").strip()
    summary = str(preprocess_result.get("summary") or "").strip()
    output_source_id = str(preprocess_result.get("output_source_id") or "").strip()
    output_filename = str(preprocess_result.get("output_filename") or "").strip()
    applied_ops_count = preprocess_result.get("applied_ops_count")

    if status == "skipped":
        return summary or "전처리가 필요하지 않아 원본 데이터로 진행할 수 있습니다."

    lines = [summary or "전처리를 적용했습니다."]
    if isinstance(applied_ops_count, int):
        lines.append(f"적용된 전처리 연산: {applied_ops_count}개")
    if output_filename:
        lines.append(f"생성된 데이터 파일: {output_filename}")
    if output_source_id:
        lines.append(f"새 데이터 소스 ID: {output_source_id}")
    return "\n".join(lines)


def build_main_workflow(
    *,
    planner_service,
    analysis_service,
    preprocess_service,
    eda_service,
    rag_service,
    guideline_service,
    guideline_rag_service,
    visualization_service,
    report_service,
    default_model: str = "gpt-5-nano",
    checkpointer: Any | None = None,
):
    intake_graph = build_intake_router_workflow(
        planner_service=planner_service,
    )
    preprocess_graph = build_preprocess_workflow(
        preprocess_service=preprocess_service,
        eda_service=eda_service,
        default_model=default_model,
    )
    analysis_graph = build_analysis_workflow(
        analysis_service=analysis_service,
        default_model=default_model,
    )
    rag_graph = build_rag_workflow(
        rag_service=rag_service,
        default_model=default_model,
    )
    guideline_graph = build_guideline_workflow(
        guideline_service=guideline_service,
        guideline_rag_service=guideline_rag_service,
        default_model=default_model,
    )
    visualization_graph = build_visualization_workflow(
        visualization_service=visualization_service,
        default_model=default_model,
    )
    report_graph = build_report_workflow(
        report_service=report_service,
        default_model=default_model,
    )

    def route_after_intake(state: MainWorkflowState) -> str:
        branch = str((state.get("handoff") or {}).get("next_step", "general_question"))
        return branch

    def route_after_chat_fast_path(state: MainWorkflowState) -> str:
        fast_path_result = state.get("fast_path_result") or {}
        if fast_path_result.get("status") == "handled":
            return "handled"
        return "skipped"

    def route_after_planner(state: MainWorkflowState) -> str:
        if state.get("final_status") == "fail":
            return "fail"

        planning_result = state.get("planning_result") or {}
        if bool(planning_result.get("needs_clarification", False)):
            return "clarification"

        route = str(planning_result.get("route", "fallback_rag"))
        if route == "general_question":
            return "general_question"
        if route == "fallback_rag":
            return "rag"
        if bool(planning_result.get("preprocess_required", False)):
            return "preprocess"
        return "analysis"

    def route_after_rag(state: MainWorkflowState) -> str:
        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_visualization", False)):
            return "visualization"
        return "merge_context"

    def route_after_preprocess(state: MainWorkflowState) -> str:
        return route_after_preprocess_result(state)

    def route_after_analysis(state: MainWorkflowState) -> str:
        final_status = state.get("final_status")
        if final_status == "needs_clarification":
            return "clarification"
        if final_status == "fail":
            return "fail"

        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_visualization", False)):
            return "visualization"
        return "merge_context"

    def route_after_merge_context(state: MainWorkflowState) -> str:
        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_report", False)):
            return "report"
        return "data_qa"

    def route_after_visualization(state: MainWorkflowState) -> str:
        visualization_result = state.get("visualization_result") or {}
        output = state.get("output") or {}
        if (
            visualization_result.get("status") == "cancelled"
            or output.get("type") == "cancelled"
        ):
            return "cancelled"
        return "merge_context"

    def status_terminal(state: MainWorkflowState) -> Dict[str, Any]:
        set_trace_stage("workflow_terminal")
        merged_context = build_merged_context(dict(state))
        evidence_package, answer_quality = build_evidence_contract(
            state=state,
            merged_context=merged_context,
        )
        output = state.get("output")
        output_payload = output if isinstance(output, dict) else {}
        content = str(output_payload.get("content") or "").strip()
        output_type = str(output_payload.get("type") or "status").strip() or "status"
        return {
            "merged_context": merged_context,
            "evidence_package": evidence_package,
            "answer_quality": answer_quality,
            "output": {
                **output_payload,
                "type": output_type,
                "content": content or "워크플로가 완료되지 않았습니다.",
                "evidence_package": evidence_package,
                "answer_quality": answer_quality,
            },
        }

    def general_question_terminal(state: MainWorkflowState) -> Dict[str, Any]:
        set_trace_stage("general_question")
        answer = answer_general_question(
            user_input=str(state.get("user_input", "")),
            request_context=str(state.get("request_context", "")),
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        return {
            "output": {
                "type": "general_question",
                "content": answer,
            }
        }

    def clarification_terminal(state: MainWorkflowState) -> Dict[str, Any]:
        set_trace_stage("clarification")
        clarification_question = str(state.get("clarification_question", "")).strip()
        output: Dict[str, Any] = {
            "type": "clarification",
            "content": clarification_question,
        }
        query_feedback = state.get("query_feedback")
        if isinstance(query_feedback, dict):
            output["query_feedback"] = query_feedback
        return {
            "output": output,
        }

    def merge_context_node(state: MainWorkflowState) -> Dict[str, Any]:
        set_trace_stage("merge_context")
        merged_context = build_merged_context(dict(state))
        evidence_package, answer_quality = build_evidence_contract(
            state=state,
            merged_context=merged_context,
        )
        return {
            "merged_context": merged_context,
            "evidence_package": evidence_package,
            "answer_quality": answer_quality,
        }

    def dataset_context_node(state: MainWorkflowState) -> Dict[str, Any]:
        set_trace_stage("dataset_context")
        source_id = str(state.get("source_id") or "").strip()
        dataset_context = planner_service.dataset_context_service.build_context(source_id)
        return {"dataset_context": dataset_context.model_dump()}

    def common_analytics_output(result: CommonAnalyticsExecutionResult) -> Dict[str, Any]:
        metric_labels = {
            "mean": "평균",
            "sum": "합계",
            "min": "최소값",
            "max": "최대값",
            "median": "중앙값",
            "ratio": "비율",
            "value_counts": "빈도",
            "top": "최빈값",
            "correlation": "상관계수",
            "outlier": "이상치",
        }
        metric_label = metric_labels.get(result.metric, result.metric)
        lines = [result.summary]
        if result.table:
            lines.append("")
            for row in result.table[:5]:
                if "group" in row:
                    lines.append(f"- {row['group']}: {row.get(result.metric)}")
                elif "ratio" in row:
                    lines.append(
                        f"- {row['value']}: {row['count']}건 ({row['ratio']:.2%})"
                    )
                else:
                    lines.append(f"- {row}")
        elif result.value is not None:
            columns = ", ".join(result.columns)
            lines[0] = f"{columns}의 {metric_label}은 {result.value}입니다."

        return {
            "type": "fast_common_analytics",
            "content": "\n".join(lines),
            "common_analytics_result": {
                "operation": result.operation,
                "metric": result.metric,
                "columns": result.columns,
                "summary": result.summary,
                "value": result.value,
                "table": result.table,
                "raw_metrics": result.raw_metrics,
            },
        }

    def common_analytics_with_evidence(
        state: MainWorkflowState,
        result: CommonAnalyticsExecutionResult,
    ) -> Dict[str, Any]:
        analysis_result = _analysis_result_from_common_analytics(result)
        evidence_state = dict(state)
        evidence_state["analysis_result"] = analysis_result
        evidence_state["final_status"] = "success"
        merged_context = build_merged_context(evidence_state)
        evidence_package, answer_quality = build_evidence_contract(
            state=evidence_state,
            merged_context=merged_context,
        )
        output = common_analytics_output(result)
        return {
            "output": {
                **output,
                "evidence_package": evidence_package,
                "answer_quality": answer_quality,
            },
            "analysis_result": analysis_result,
            "merged_context": merged_context,
            "evidence_package": evidence_package,
            "answer_quality": answer_quality,
        }

    def chat_fast_path_node(state: MainWorkflowState) -> Dict[str, Any]:
        set_trace_stage("chat_fast_path")
        dataset_context = state.get("dataset_context")
        if not isinstance(dataset_context, dict):
            return {
                "fast_path_result": {
                    "status": "skipped",
                    "reason": "dataset_context_unavailable",
                    "blockers": ["dataset_context_unavailable"],
                }
            }

        fast_dataset_answer = try_fast_dataset_answer(
            question=str(state.get("user_input", "")),
            dataset_context=dataset_context,
        )
        if fast_dataset_answer is not None:
            return {
                "output": fast_dataset_answer.output,
                "fast_path_result": fast_dataset_answer.fast_path_result,
            }

        decision = decide_common_analytics_fast_path(
            question=str(state.get("user_input", "")),
            dataset_context=dataset_context,
        )
        if not decision.eligible:
            result = decision.to_fast_path_result()
            return {
                "fast_path_result": {
                    **result,
                    "reason": "common_analytics_ineligible",
                }
            }

        source_id = str(state.get("source_id") or "").strip()
        dataset_repository = getattr(analysis_service, "dataset_repository", None)
        reader = getattr(eda_service, "reader", None)
        dataset = (
            dataset_repository.get_by_source_id(source_id)
            if dataset_repository is not None and source_id
            else None
        )
        storage_path = getattr(dataset, "storage_path", "") if dataset is not None else ""
        if not storage_path or reader is None:
            return {
                "fast_path_result": {
                    **decision.to_fast_path_result(),
                    "status": "skipped",
                    "reason": "common_analytics_dataset_unavailable",
                    "blockers": ["common_analytics_dataset_unavailable"],
                }
            }

        from ..modules.chat_fast_path.executor import execute_common_analytics

        try:
            common_result = execute_common_analytics(
                decision=decision,
                storage_path=storage_path,
                dataset_context=dataset_context,
                reader=reader,
            )
        except (DatasetReadError, FileNotFoundError, KeyError, ValueError):
            return {
                "fast_path_result": {
                    **decision.to_fast_path_result(),
                    "status": "skipped",
                    "reason": "common_analytics_execution_failed",
                    "blockers": ["common_analytics_execution_failed"],
                }
            }

        result_payload = common_analytics_with_evidence(state, common_result)
        result_payload["fast_path_result"] = decision.to_fast_path_result()
        return result_payload

    def planner_node(state: MainWorkflowState) -> Dict[str, Any]:
        set_trace_stage("planner")
        try:
            planning_result = planner_service.plan(
                user_input=str(state.get("user_input", "")),
                request_context=str(state.get("request_context", "")),
                source_id=str(state.get("source_id", "")),
                dataset_context=state.get("dataset_context"),
                guideline_context=state.get("guideline_context"),
                model_id=state.get("model_id"),
            )
        except Exception as exc:
            workflow_error = build_workflow_error_from_exception(
                stage="plan_validation",
                error_code="planning_failed",
                source="main_planner",
                output_type="planning_failed",
                retryable=True,
                exc=exc,
            )
            return {
                "workflow_error": workflow_error,
                "final_status": "fail",
                "output": build_failure_output(workflow_error),
            }

        query_feedback = (
            planning_result.query_feedback.model_dump(exclude_none=True)
            if planning_result.query_feedback is not None
            else None
        )
        result: Dict[str, Any] = {
            "planning_result": planning_result.model_dump(),
            "handoff": build_handoff_from_planning_result(planning_result),
            "clarification_question": planning_result.clarification_question,
        }
        if query_feedback is not None:
            result["query_feedback"] = query_feedback
        return result

    def data_qa_terminal(state: MainWorkflowState) -> Dict[str, Any]:
        set_trace_stage("data_qa")
        raw_evidence_package = state.get("evidence_package")
        evidence_package: dict[str, Any] = (
            dict(raw_evidence_package) if isinstance(raw_evidence_package, dict) else {}
        )
        raw_answer_quality = state.get("answer_quality")
        answer_quality: dict[str, Any] = (
            dict(raw_answer_quality) if isinstance(raw_answer_quality, dict) else {}
        )

        if answer_quality.get("answerable") is False:
            answer_text = str(
                answer_quality.get("abstain_reason")
                or "최종 답변을 만들 수 있는 분석 결과나 검색 근거가 충분하지 않습니다."
            ).strip()
            return {
                "data_qa_result": {"content": answer_text},
                "output": {
                    "type": "data_qa",
                    "content": answer_text,
                    "evidence_package": evidence_package,
                    "answer_quality": answer_quality,
                },
            }

        preprocess_result = state.get("preprocess_result")
        if _is_preprocess_only_result(state) and isinstance(preprocess_result, dict):
            answer_text = _build_preprocess_answer(preprocess_result)
            return {
                "data_qa_result": {"content": answer_text},
                "output": {
                    "type": "data_qa",
                    "content": answer_text,
                    "evidence_package": evidence_package,
                    "answer_quality": answer_quality,
                },
            }

        handoff = state.get("handoff") or {}
        visualization_result = state.get("visualization_result")
        analysis_result = state.get("analysis_result")
        if bool(handoff.get("ask_visualization", False)) and isinstance(visualization_result, dict):
            if visualization_result.get("status") == "generated":
                artifact = visualization_result.get("artifact")
                has_image_artifact = (
                    isinstance(artifact, dict)
                    and isinstance(artifact.get("image_base64"), str)
                    and bool(artifact.get("image_base64"))
                )
                summary = str(visualization_result.get("summary") or "").strip()
                if not summary and isinstance(analysis_result, dict):
                    summary = str(analysis_result.get("summary") or "").strip()

                prefix = "차트를 생성했습니다." if has_image_artifact else "차트 데이터를 생성했습니다."
                answer_text = prefix if not summary else f"{prefix}\n\n{summary}"
                return {
                    "data_qa_result": {"content": answer_text},
                    "output": {
                        "type": "data_qa",
                        "content": answer_text,
                        "evidence_package": evidence_package,
                        "answer_quality": answer_quality,
                    },
                }

        merged_context = state.get("merged_context")
        answer = answer_data_question(
            user_input=str(state.get("user_input", "")),
            merged_context=merged_context if isinstance(merged_context, dict) else {},
            evidence_package=evidence_package,
            answer_quality=answer_quality,
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        answer_text = str(answer or "").strip()
        return {
            "data_qa_result": {"content": answer_text},
            "output": {
                "type": "data_qa",
                "content": answer_text,
                "evidence_package": evidence_package,
                "answer_quality": answer_quality,
            },
        }

    def analysis_fail_terminal(state: MainWorkflowState) -> Dict[str, Any]:
        set_trace_stage("analysis_failed")
        merged_context = build_merged_context(dict(state))
        evidence_package, answer_quality = build_evidence_contract(
            state=state,
            merged_context=merged_context,
        )
        abstain_reason = str(
            answer_quality.get("abstain_reason")
            or "최종 답변을 만들 수 있는 분석 결과가 충분하지 않습니다."
        ).strip()
        return {
            "merged_context": merged_context,
            "evidence_package": evidence_package,
            "answer_quality": answer_quality,
            "output": {
                "type": "fail",
                "content": abstain_reason,
                "evidence_package": evidence_package,
                "answer_quality": answer_quality,
            },
        }

    graph = StateGraph(MainWorkflowState)
    graph.add_node("intake_flow", intake_graph)
    graph.add_node("general_question_terminal", general_question_terminal)
    graph.add_node("clarification_terminal", clarification_terminal)
    graph.add_node("dataset_context", dataset_context_node)
    graph.add_node("chat_fast_path", chat_fast_path_node)
    graph.add_node("planner", planner_node)
    graph.add_node("preprocess_flow", preprocess_graph)
    graph.add_node("analysis_flow", analysis_graph)
    graph.add_node("rag_flow", rag_graph)
    graph.add_node("guideline_flow", guideline_graph)
    graph.add_node("visualization_flow", visualization_graph)
    graph.add_node("merge_context", merge_context_node)
    graph.add_node("data_qa_terminal", data_qa_terminal)
    graph.add_node("analysis_fail_terminal", analysis_fail_terminal)
    graph.add_node("status_terminal", status_terminal)
    graph.add_node("report_flow", report_graph)

    graph.add_edge(START, "intake_flow")
    graph.add_conditional_edges(
        "intake_flow",
        route_after_intake,
        {
            "general_question": "general_question_terminal",
            "dataset_selected": "dataset_context",
            "guideline_selected": "guideline_flow",
        },
    )
    graph.add_edge("dataset_context", "chat_fast_path")
    graph.add_conditional_edges(
        "chat_fast_path",
        route_after_chat_fast_path,
        {
            "handled": END,
            "skipped": "guideline_flow",
        },
    )
    graph.add_conditional_edges(
        "guideline_flow",
        route_after_guideline,
        {
            "merge_context": "merge_context",
            "planner": "planner",
        },
    )
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "general_question": "general_question_terminal",
            "preprocess": "preprocess_flow",
            "analysis": "analysis_flow",
            "rag": "rag_flow",
            "clarification": "clarification_terminal",
            "fail": END,
        },
    )
    graph.add_conditional_edges(
        "preprocess_flow",
        route_after_preprocess,
        {
            "analysis": "analysis_flow",
            "merge_context": "merge_context",
            "cancelled": "status_terminal",
            "failed": "status_terminal",
        },
    )
    graph.add_conditional_edges(
        "analysis_flow",
        route_after_analysis,
        {
            "visualization": "visualization_flow",
            "merge_context": "merge_context",
            "clarification": "clarification_terminal",
            "fail": "analysis_fail_terminal",
        },
    )
    graph.add_conditional_edges(
        "rag_flow",
        route_after_rag,
        {
            "visualization": "visualization_flow",
            "merge_context": "merge_context",
        },
    )
    graph.add_conditional_edges(
        "visualization_flow",
        route_after_visualization,
        {
            "merge_context": "merge_context",
            "cancelled": "status_terminal",
        },
    )
    graph.add_conditional_edges(
        "merge_context",
        route_after_merge_context,
        {
            "report": "report_flow",
            "data_qa": "data_qa_terminal",
        },
    )
    graph.add_edge("report_flow", END)
    graph.add_edge("data_qa_terminal", END)
    graph.add_edge("analysis_fail_terminal", END)
    graph.add_edge("status_terminal", END)
    graph.add_edge("general_question_terminal", END)
    graph.add_edge("clarification_terminal", END)

    return graph.compile(checkpointer=checkpointer)
