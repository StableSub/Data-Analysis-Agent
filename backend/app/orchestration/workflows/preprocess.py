"""Preprocessing subgraph."""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import ValidationError

from backend.app.modules.preprocess.ai import (
    PreprocessPlan,
    build_preprocess_plan as build_preprocess_plan_with_ai,
    decide_preprocess,
)
from backend.app.modules.preprocess.schemas import PreprocessOperation
from backend.app.modules.preprocess.service import PreprocessService
from backend.app.orchestration.state import PreprocessGraphState


def _get_revision_instruction(state: PreprocessGraphState) -> str:
    revision_request = state.get("revision_request")
    if isinstance(revision_request, dict):
        if revision_request.get("stage") == "preprocess":
            instruction = revision_request.get("instruction")
            if isinstance(instruction, str):
                return instruction.strip()
        return ""
    return str(revision_request or "").strip()


def _collect_affected_columns(operations: list[PreprocessOperation]) -> list[str]:
    columns: list[str] = []
    for operation in operations:
        if operation.op in {"drop_missing", "impute", "drop_columns", "scale"}:
            columns.extend(operation.columns)
        elif operation.op == "rename_columns":
            columns.extend(operation.rename_from)
            columns.extend(operation.rename_to)
        elif operation.op == "derived_column":
            columns.append(operation.name)
    return list(dict.fromkeys(str(column) for column in columns if str(column).strip()))


def _build_preprocess_review_payload(
    *,
    state: PreprocessGraphState,
    plan: PreprocessPlan,
) -> Dict[str, Any]:
    profile = state.get("dataset_profile") or {}
    missing_rates = profile.get("missing_rates")
    top_missing_columns: list[Dict[str, Any]] = []
    if isinstance(missing_rates, dict):
        sorted_items = sorted(
            (
                (str(column), float(rate))
                for column, rate in missing_rates.items()
                if isinstance(rate, (int, float)) and float(rate) > 0
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        top_missing_columns = [
            {"column": column, "missing_rate": rate}
            for column, rate in sorted_items[:5]
        ]

    operations = [operation.model_dump() for operation in plan.operations]
    planner_comment = plan.planner_comment.strip()
    decision = state.get("preprocess_decision") or {}
    reason_summary = decision.get("reason_summary")
    summary = (
        planner_comment
        or (
            reason_summary.strip()
            if isinstance(reason_summary, str) and reason_summary.strip()
            else ""
        )
        or "전처리 계획을 검토한 뒤 승인 여부를 결정해 주세요."
    )

    row_count = profile.get("row_count")
    row_count_value = int(row_count) if isinstance(row_count, int) else None

    return {
        "stage": "preprocess",
        "kind": "plan_review",
        "title": "Preprocess plan review",
        "summary": summary,
        "source_id": str(state.get("source_id") or ""),
        "plan": {
            "operations": operations,
            "planner_comment": planner_comment,
            "top_missing_columns": top_missing_columns,
            "affected_columns": _collect_affected_columns(plan.operations),
            "row_count": row_count_value,
        },
    }


def build_preprocess_plan(
    *,
    state: PreprocessGraphState,
    default_model: str = "gpt-5-nano",
):
    plan = build_preprocess_plan_with_ai(
        user_input=str(state.get("user_input", "")),
        source_id=str(state.get("source_id") or ""),
        dataset_profile=state.get("dataset_profile", {}),
        revision_request=_get_revision_instruction(state),
        model_id=state.get("model_id"),
        default_model=default_model,
    )
    return {"preprocess_plan": plan.model_dump()}


def run_preprocess_executor(
    *,
    state: PreprocessGraphState,
    preprocess_service: PreprocessService,
) -> Dict[str, Any]:
    source_id = state.get("source_id")
    if not source_id:
        return {
            "preprocess_result": {
                "status": "failed",
                "applied_ops_count": 0,
                "error": "source_id is required",
            }
        }

    plan_raw = state.get("preprocess_plan") or {}
    approved_plan = state.get("approved_plan")
    try:
        plan = PreprocessPlan.model_validate(approved_plan or plan_raw)
        operations = plan.operations
        plan_comment = plan.planner_comment
    except ValidationError as exc:
        return {
            "preprocess_result": {
                "status": "failed",
                "applied_ops_count": 0,
                "error": f"invalid operation format: {exc}",
            }
        }
    if not operations:
        return {
            "preprocess_result": {
                "status": "skipped",
                "applied_ops_count": 0,
            }
        }

    apply_response = preprocess_service.apply(source_id=str(source_id), operations=operations)
    if plan_comment:
        print(f"[preprocess] planner_comment={plan_comment}")
    updated_profile = dict(state.get("dataset_profile", {}))
    updated_profile["preprocess_applied"] = True
    return {
        "dataset_profile": updated_profile,
        "preprocess_result": {
            "status": "applied",
            "applied_ops_count": len(operations),
            "input_source_id": apply_response.input_source_id,
            "output_source_id": apply_response.output_source_id,
            "output_filename": apply_response.output_filename,
        },
        "revision_request": {},
        "approved_plan": {},
        "pending_approval": {},
    }


def build_preprocess_workflow(
    *,
    preprocess_service: PreprocessService,
    default_model: str = "gpt-5-nano",
):
    def ingestion_and_profile_node(state: PreprocessGraphState) -> Dict[str, Any]:
        if state.get("dataset_profile"):
            return {}
        return {
            "dataset_profile": preprocess_service.build_dataset_profile(
                str(state.get("source_id") or "")
            )
        }

    def preprocess_decision_node(state: PreprocessGraphState) -> Dict[str, Any]:
        handoff = state.get("handoff")
        if isinstance(handoff, dict) and "ask_preprocess" in handoff:
            ask_preprocess = bool(handoff.get("ask_preprocess", False))
            decision_step = "run_preprocess" if ask_preprocess else "skip_preprocess"
            reason = (
                "사용자 요청에 따라 전처리를 수행합니다."
                if ask_preprocess
                else "사용자 요청에 따라 전처리를 생략합니다."
            )
            return {
                "preprocess_decision": {
                    "step": decision_step,
                    "reason_summary": reason,
                }
            }

        decision = decide_preprocess(
            user_input=str(state.get("user_input", "")),
            dataset_profile=state.get("dataset_profile", {}),
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        return {"preprocess_decision": decision.model_dump()}

    def route_by_decision(state: PreprocessGraphState) -> str:
        step = (state.get("preprocess_decision") or {}).get("step")
        return "run_preprocess" if step == "run_preprocess" else "skip_preprocess"

    def planner_node(state: PreprocessGraphState) -> Dict[str, Any]:
        return build_preprocess_plan(
            state=state,
            default_model=default_model,
        )

    def approval_gate_node(state: PreprocessGraphState) -> Dict[str, Any]:
        plan = PreprocessPlan.model_validate(state.get("preprocess_plan") or {})
        payload = _build_preprocess_review_payload(state=state, plan=plan)
        decision_raw = interrupt(payload)

        decision = ""
        instruction = ""
        if isinstance(decision_raw, dict):
            decision_value = decision_raw.get("decision")
            instruction_value = decision_raw.get("instruction")
            if isinstance(decision_value, str):
                decision = decision_value
            if isinstance(instruction_value, str):
                instruction = instruction_value.strip()
        elif isinstance(decision_raw, str):
            decision = decision_raw

        if decision == "approve":
            return {
                "approved_plan": plan.model_dump(),
                "pending_approval": {},
                "revision_request": {},
            }

        if decision == "revise":
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
        if _get_revision_instruction(state):
            return "revise"
        return "approve"

    def executor_node(state: PreprocessGraphState) -> Dict[str, Any]:
        return run_preprocess_executor(
            state=state,
            preprocess_service=preprocess_service,
        )

    def skip_node(_: PreprocessGraphState) -> Dict[str, Any]:
        return {"preprocess_result": {"status": "skipped", "applied_ops_count": 0}}

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
