"""Preprocessing subgraph."""

from __future__ import annotations

import json
from typing import Any, Dict, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field, ValidationError

from backend.app.modules.preprocess.schemas import PreprocessOperation
from backend.app.modules.preprocess.service import PreprocessService
from backend.app.orchestration.state import PreprocessGraphState
from backend.app.orchestration.utils import call_structured_llm


class PreprocessPlan(BaseModel):
    operations: list[PreprocessOperation] = Field(default_factory=list)
    planner_comment: str = ""


class PreprocessDecision(BaseModel):
    step: Literal["run_preprocess", "skip_preprocess"] = Field(...)
    reason_summary: str = ""


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
        or (reason_summary.strip() if isinstance(reason_summary, str) and reason_summary.strip() else "")
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
    """
    역할: 데이터 프로파일과 사용자 요청을 기반으로 전처리 연산 계획을 구조화 출력으로 생성한다.
    입력: `state.user_input`, `state.source_id`, `state.dataset_profile`, 기본 모델명을 받는다.
    출력: `preprocess_plan` 키에 직렬화 가능한 전처리 계획 딕셔너리를 담아 반환한다.
    데코레이터: 없음.
    호출 맥락: 전처리 서브그래프에서 planner 노드가 실제 실행 직전에 호출하는 계획 생성 함수다.
    """
    profile_json = json.dumps(state.get("dataset_profile", {}), ensure_ascii=False)
    revision_request = _get_revision_instruction(state)
    revision_text = f"\nrevision_request={revision_request}" if revision_request else ""
    plan = call_structured_llm(
        schema=PreprocessPlan,
        system_prompt=(
            "너는 전처리 플래너다. "
            "PreprocessPlan 스키마 형식으로만 반환하고 "
            "지원 연산은 drop_missing, impute, drop_columns, rename_columns, scale, derived_column다. "
            "전처리가 불필요하면 operations는 빈 배열로 반환하라. "
            "operations는 op+파라미터로 구성하며 "
            "planner_comment에는 판단 근거를 1~2문장으로 남겨라."
        ),
        human_prompt=(
            f"user_input={state.get('user_input', '')}\n"
            f"source_id={state.get('source_id')}\n"
            f"dataset_profile={profile_json}"
            f"{revision_text}"
        ),
        model_id=state.get("model_id"),
        default_model=default_model,
    )
    return {"preprocess_plan": plan.model_dump()}


def run_preprocess_executor(
    *,
    state: PreprocessGraphState,
    preprocess_service: PreprocessService,
) -> Dict[str, Any]:
    """
    역할: LLM이 만든 전처리 계획을 검증한 뒤 서비스 계층에 적용해 결과 메타데이터를 기록한다.
    입력: 전처리 상태(`state`)와 실제 변환을 수행할 `preprocess_service`를 받는다.
    출력: `preprocess_result`(applied/skipped/failed)와 갱신된 `dataset_profile`을 반환한다.
    데코레이터: 없음.
    호출 맥락: 전처리 서브그래프 executor 노드의 본체로 planner 다음 단계에서 실행된다.
    """
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
    """
    역할: 데이터셋 프로파일링, 전처리 필요성 판단, 계획 생성, 실행/스킵 경로를 가진 서브그래프를 구성한다.
    입력: DB 세션(`db`)과 기본 모델명(`default_model`)을 받아 내부 노드 의존성을 초기화한다.
    출력: `preprocess_result`를 상태에 누적하는 컴파일된 전처리 워크플로우를 반환한다.
    데코레이터: 없음.
    호출 맥락: 메인 워크플로우의 `preprocess_flow` 노드로 연결되어 데이터 파이프라인 초반에 실행된다.
    """
    def ingestion_and_profile_node(state: PreprocessGraphState) -> Dict[str, Any]:
        """
        역할: 데이터 파일 샘플을 읽어 컬럼/결측/타입 정보를 담은 `dataset_profile`을 생성한다.
        입력: `state.source_id`와 기존 `state.dataset_profile` 여부를 확인한다.
        출력: 프로파일이 이미 있으면 빈 딕셔너리, 없으면 `dataset_profile` 업데이트를 반환한다.
        데코레이터: 없음.
        호출 맥락: 전처리 서브그래프의 첫 노드로 이후 의사결정과 계획 생성의 입력을 준비한다.
        """
        if state.get("dataset_profile"):
            return {}
        return {
            "dataset_profile": preprocess_service.build_dataset_profile(
                str(state.get("source_id") or "")
            )
        }

    def preprocess_decision_node(state: PreprocessGraphState) -> Dict[str, Any]:
        """
        역할: 사용자 명시 요청 또는 LLM 판단으로 전처리 실행 여부를 결정한다.
        입력: `state.handoff.ask_preprocess`, `state.dataset_profile`, `state.user_input`를 참조한다.
        출력: `preprocess_decision.step`을 `run_preprocess` 또는 `skip_preprocess`로 반환한다.
        데코레이터: 없음.
        호출 맥락: profile 수집 직후 분기 키를 만드는 의사결정 노드로 conditional edge의 기준이 된다.
        """
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

        profile_json = json.dumps(state.get("dataset_profile", {}), ensure_ascii=False)
        decision = call_structured_llm(
            schema=PreprocessDecision,
            system_prompt=(
                "데이터 프로파일을 보고 run_preprocess 또는 skip_preprocess를 반환하라. "
                "reason_summary에는 판단 근거를 1문장으로 남겨라."
            ),
            human_prompt=f"user_input={state.get('user_input', '')}\n{profile_json}",
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        return {"preprocess_decision": decision.model_dump()}

    def route_by_decision(state: PreprocessGraphState) -> str:
        """
        역할: 전처리 의사결정 결과를 그래프 분기 문자열로 변환한다.
        입력: `state.preprocess_decision.step` 값을 포함한 상태를 받는다.
        출력: 실행 경로면 `run_preprocess`, 그 외는 `skip_preprocess`를 반환한다.
        데코레이터: 없음.
        호출 맥락: `preprocess_decision` 이후 conditional edge 라우터에서 직접 사용된다.
        """
        step = (state.get("preprocess_decision") or {}).get("step")
        return "run_preprocess" if step == "run_preprocess" else "skip_preprocess"

    def planner_node(state: PreprocessGraphState) -> Dict[str, Any]:
        """
        역할: 현재 상태를 기반으로 전처리 계획 생성 함수(`build_preprocess_plan`)를 호출한다.
        입력: 전처리 상태(`state`)를 그대로 전달한다.
        출력: `preprocess_plan` 딕셔너리를 담은 상태 업데이트를 반환한다.
        데코레이터: 없음.
        호출 맥락: 의사결정 결과가 `run_preprocess`일 때만 실행되는 중간 노드다.
        """
        return build_preprocess_plan(
            state=state,
            default_model=default_model,
        )

    def approval_gate_node(state: PreprocessGraphState) -> Dict[str, Any]:
        """
        역할: 생성된 전처리 계획을 사용자 승인 대기로 중단하고, 승인/수정/취소 결정을 반영한다.
        입력: 현재 `preprocess_plan`, `dataset_profile`, `revision_request`를 포함한 상태를 받는다.
        출력: 승인 시 `approved_plan`, 수정 시 `revision_request`, 취소 시 `preprocess_result/output`을 반환한다.
        데코레이터: 없음.
        호출 맥락: planner 다음 단계에서 `interrupt()`를 통해 HITL 승인 게이트로 동작한다.
        """
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
        revision_request = _get_revision_instruction(state)
        if revision_request:
            return "revise"
        return "approve"

    def executor_node(state: PreprocessGraphState) -> Dict[str, Any]:
        """
        역할: 계획된 연산을 실제 데이터셋에 적용하고 전처리 결과 메타데이터를 확정한다.
        입력: 전처리 상태(`state`)와 클로저의 `preprocess_service`를 사용한다.
        출력: `run_preprocess_executor`의 실행 결과(`preprocess_result`, 선택적 `dataset_profile`)를 반환한다.
        데코레이터: 없음.
        호출 맥락: planner 노드 다음 단계로 연결되어 전처리 경로의 마지막 실행 노드다.
        """
        return run_preprocess_executor(
            state=state,
            preprocess_service=preprocess_service,
        )

    def skip_node(_: PreprocessGraphState) -> Dict[str, Any]:
        """
        역할: 전처리를 수행하지 않는 경로에서 표준 스킵 결과를 상태에 기록한다.
        입력: 전처리 상태를 받지만 내부에서 사용하지 않는다.
        출력: `status=skipped`, `applied_ops_count=0`를 포함한 `preprocess_result`를 반환한다.
        데코레이터: 없음.
        호출 맥락: 의사결정이 스킵으로 정해졌을 때 executor를 우회해 종료로 이어지는 노드다.
        """
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
