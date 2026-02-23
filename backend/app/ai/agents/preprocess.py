"""Preprocessing subgraph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Literal

import pandas as pd
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from backend.app.ai.agents.state import PreprocessGraphState
from backend.app.domain.data_source.repository import DataSourceRepository
from backend.app.domain.preprocess.schemas import PreprocessOperation
from backend.app.domain.preprocess.service import PreprocessService

class PreprocessPlan(BaseModel):
    operations: list[PreprocessOperation] = Field(default_factory=list)
    planner_comment: str = ""

class PreprocessDecision(BaseModel):
    step: Literal["run_preprocess", "skip_preprocess"] = Field(...)
    reason_summary: str = ""

def _call_structured(
    *,
    schema: type[BaseModel],
    system_prompt: str,
    human_prompt: str,
    model_id: str | None,
    default_model: str,
) -> BaseModel:
    model_name = model_id or default_model
    llm = init_chat_model(model_name).with_structured_output(
        schema,
        method="function_calling",
    )
    result = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]
    )
    payload = result.model_dump() if hasattr(result, "model_dump") else result
    print(f"[preprocess] llm response={payload}")
    return result

def build_preprocess_plan(
    *,
    state: PreprocessGraphState,
    default_model: str = "gpt-5-nano",
):
    profile_json = json.dumps(state.get("dataset_profile", {}), ensure_ascii=False)
    plan = _call_structured(
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
    try:
        plan = PreprocessPlan.model_validate(plan_raw)
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
    }

def build_preprocess_workflow(
    *,
    db: Session,
    default_model: str = "gpt-5-nano",
):
    repo = DataSourceRepository(db)
    preprocess_service = PreprocessService(db)

    def ingestion_and_profile_node(state: PreprocessGraphState) -> Dict[str, Any]:
        if state.get("dataset_profile"):
            return {}

        source_id = state.get("source_id")
        if not source_id:
            return {"dataset_profile": {"available": False}}

        dataset = repo.get_by_source_id(str(source_id))
        if not dataset or not dataset.storage_path:
            return {"dataset_profile": {"available": False}}

        file_path = Path(dataset.storage_path)
        if not file_path.exists():
            return {"dataset_profile": {"available": False}}

        sample_df = pd.read_csv(file_path, nrows=2000)
        return {
            "dataset_profile": {
                "available": True,
                "columns": sample_df.columns.tolist(),
            }
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

        profile_json = json.dumps(state.get("dataset_profile", {}), ensure_ascii=False)
        decision = _call_structured(
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
        step = (state.get("preprocess_decision") or {}).get("step")
        return "run_preprocess" if step == "run_preprocess" else "skip_preprocess"

    def planner_node(state: PreprocessGraphState) -> Dict[str, Any]:
        return build_preprocess_plan(
            state=state,
            default_model=default_model,
        )

    def executor_node(state: PreprocessGraphState) -> Dict[str, Any]:
        return run_preprocess_executor(
            state=state,
            preprocess_service=preprocess_service,
        )

    def skip_node(_: PreprocessGraphState) -> Dict[str, Any]:
        return {"preprocess_result": {"status": "skipped", "applied_ops_count": 0}}

    graph = StateGraph(PreprocessGraphState)
    graph.add_node("ingestion_and_profile", ingestion_and_profile_node)
    graph.add_node("preprocess_decision", preprocess_decision_node)
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("skip", skip_node)
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
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", END)
    graph.add_edge("skip", END)
    return graph.compile()
