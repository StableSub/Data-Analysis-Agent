"""Preprocessing subgraph."""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.app.core.trace_logging import set_trace_stage
from backend.app.modules.planner.service import (
    build_preprocess_decision_from_planning_result,
)
from backend.app.modules.planner.schemas import PlanningResult
from backend.app.modules.preprocess.executor import execute_preprocess_plan
from backend.app.modules.preprocess.planner import (
    PreprocessPlan,
    build_preprocess_plan,
    build_preprocess_review_payload,
    get_revision_instruction,
)
from backend.app.modules.eda.service import EDAService
from backend.app.modules.preprocess.service import PreprocessService
from backend.app.modules.profiling.schemas import DatasetProfile
from backend.app.orchestration.state import PreprocessGraphState


def build_preprocess_workflow(
    *,
    preprocess_service: PreprocessService,
    eda_service: EDAService,
    default_model: str = "gpt-5-nano",
):
    def ingestion_and_profile_node(state: PreprocessGraphState) -> Dict[str, Any]:
        set_trace_stage("preprocess_profile")
        if state.get("dataset_profile"):
            return {}
        return {
            "dataset_profile": preprocess_service.build_dataset_profile(
                str(state.get("source_id") or "")
            )
        }

    def preprocess_decision_node(state: PreprocessGraphState) -> Dict[str, Any]:
        set_trace_stage("preprocess_decision")
        planning_result = state.get("planning_result")
        if isinstance(planning_result, dict):
            decision = build_preprocess_decision_from_planning_result(
                PlanningResult.model_validate(planning_result)
            )
            return {"preprocess_decision": decision}
        decision = {
            "step": "skip_preprocess",
            "reason_summary": "planner 결과가 없어 전처리를 생략합니다.",
        }
        return {"preprocess_decision": decision}

    def route_by_decision(state: PreprocessGraphState) -> str:
        step = (state.get("preprocess_decision") or {}).get("step")
        return "run_preprocess" if step == "run_preprocess" else "skip_preprocess"

    def planner_node(state: PreprocessGraphState) -> Dict[str, Any]:
        set_trace_stage("preprocess_plan")
        dataset_profile = dict(state.get("dataset_profile") or {})
        if "preprocess_recommendations" not in dataset_profile:
            profile_model = DatasetProfile.model_validate(dataset_profile)
            recommendations = eda_service.get_preprocess_recommendations(
                str(state.get("source_id") or ""),
                profile=profile_model,
                include_outlier_analysis=False,
            )
            dataset_profile["preprocess_recommendations"] = (
                recommendations.model_dump().get("recommendations", [])
                if recommendations is not None
                else []
            )

        plan = build_preprocess_plan(
            user_input=str(state.get("user_input", "")),
            source_id=str(state.get("source_id") or ""),
            dataset_profile=dataset_profile,
            revision_request=state.get("revision_request"),
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        return {
            "dataset_profile": dataset_profile,
            "preprocess_plan": plan.model_dump(),
        }

    def approval_gate_node(state: PreprocessGraphState) -> Dict[str, Any]:
        set_trace_stage("preprocess_approval")
        plan = PreprocessPlan.model_validate(state.get("preprocess_plan") or {})
        decision = state.get("preprocess_decision") or {}
        reason_summary = decision.get("reason_summary")
        payload = build_preprocess_review_payload(
            source_id=str(state.get("source_id") or ""),
            dataset_profile=state.get("dataset_profile", {}),
            plan=plan,
            reason_summary=str(reason_summary) if isinstance(reason_summary, str) else "",
        )
        decision_raw = interrupt(payload)

        decision_value = ""
        instruction = ""
        if isinstance(decision_raw, dict):
            raw_decision = decision_raw.get("decision")
            raw_instruction = decision_raw.get("instruction")
            if isinstance(raw_decision, str):
                decision_value = raw_decision
            if isinstance(raw_instruction, str):
                instruction = raw_instruction.strip()
        elif isinstance(decision_raw, str):
            decision_value = decision_raw

        if decision_value == "approve":
            return {
                "approved_plan": plan.model_dump(),
                "pending_approval": {},
                "revision_request": {},
            }

        if decision_value == "revise":
            return {
                "approved_plan": {},
                "pending_approval": payload,
                "revision_request": {
                    "stage": "preprocess",
                    "instruction": instruction,
                },
            }

        return {
            "approved_plan": {},
            "pending_approval": {},
            "revision_request": {},
            "preprocess_result": {
                "status": "cancelled",
                "summary": "전처리 계획 검토 단계에서 실행을 취소했습니다.",
                "applied_ops_count": 0,
            },
            "output": {
                "type": "cancelled",
                "content": "전처리 계획 검토 단계에서 실행을 취소했습니다.",
            },
        }

    def route_after_approval(state: PreprocessGraphState) -> str:
        result = state.get("preprocess_result") or {}
        if result.get("status") == "cancelled":
            return "cancel"
        if get_revision_instruction(state.get("revision_request")):
            return "revise"
        return "approve"

    def executor_node(state: PreprocessGraphState) -> Dict[str, Any]:
        set_trace_stage("preprocess_execute")
        return execute_preprocess_plan(
            source_id=str(state.get("source_id") or "") or None,
            preprocess_plan=state.get("preprocess_plan"),
            approved_plan=state.get("approved_plan"),
            dataset_profile=state.get("dataset_profile"),
            preprocess_service=preprocess_service,
        )

    def skip_node(_: PreprocessGraphState) -> Dict[str, Any]:
        set_trace_stage("preprocess_skip")
        return {
            "preprocess_result": {
                "status": "skipped",
                "summary": "전처리 없이 다음 단계로 진행했습니다.",
                "applied_ops_count": 0,
            }
        }

    def cancel_node(_: PreprocessGraphState) -> Dict[str, Any]:
        return {}

    graph = StateGraph(PreprocessGraphState)
    graph.add_node("ingestion_and_profile", ingestion_and_profile_node)
    graph.add_node("preprocess_decision", preprocess_decision_node)
    graph.add_node("planner", planner_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("executor", executor_node)
    graph.add_node("skip", skip_node)
    graph.add_node("cancel", cancel_node)
    graph.add_edge(START, "ingestion_and_profile")
    graph.add_edge("ingestion_and_profile", "preprocess_decision")
    graph.add_conditional_edges(
        "preprocess_decision",
        route_by_decision,
        {
            "run_preprocess": "planner",
            "skip_preprocess": "skip",
        },
    )
    graph.add_edge("planner", "approval_gate")
    graph.add_conditional_edges(
        "approval_gate",
        route_after_approval,
        {
            "approve": "executor",
            "revise": "planner",
            "cancel": "cancel",
        },
    )
    graph.add_edge("executor", END)
    graph.add_edge("skip", END)
    graph.add_edge("cancel", END)
    return graph.compile()
