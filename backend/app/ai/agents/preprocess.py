"""
V1 전처리 서브그래프.

역할:
- 데이터셋 프로파일링
- 전처리 필요 여부 판단
- 전처리 계획 생성
- 전처리 실행
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Literal

import pandas as pd
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.ai.agents.state import AgentState, PreprocessGraphState
from backend.app.domain.data_source.repository import DataSourceRepository
from backend.app.domain.preprocess.schemas import PreprocessOperation
from backend.app.domain.preprocess.service import PreprocessService


class PreprocessDecision(BaseModel):
    """전처리 실행 여부 판단 스키마."""

    step: Literal["run_preprocess", "skip_preprocess"] = Field(...)


class PreprocessPlan(BaseModel):
    """전처리 실행 계획 스키마."""

    operations: list[PreprocessOperation] = Field(default_factory=list)


def _call_structured(
    *,
    schema: type[BaseModel],
    system_prompt: str,
    human_prompt: str,
    model_id: str | None,
    default_model: str,
):
    """구조화 출력 LLM 호출을 수행한다."""
    model_name = model_id or default_model
    llm = init_chat_model(model_name).with_structured_output(schema)
    return llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]
    )


def build_preprocess_plan(
    *,
    state: AgentState,
    default_model: str = "gpt-5-nano",
) -> Dict[str, Any]:
    """LLM으로 전처리 연산 목록을 생성한다."""
    profile_json = json.dumps(state.get("dataset_profile", {}), ensure_ascii=False)
    plan = _call_structured(
        schema=PreprocessPlan,
        system_prompt=(
            "전처리 플래너다. 아래 연산만 사용해 operations를 생성하라: "
            "drop_missing, impute, drop_columns, rename_columns, scale, derived_column."
        ),
        human_prompt=(
            f"user_input={state.get('user_input', '')}\n"
            f"dataset_id={state.get('dataset_id')}\n"
            f"dataset_profile={profile_json}"
        ),
        model_id=state.get("model_id"),
        default_model=default_model,
    )
    return {"preprocess_plan": plan.model_dump()}


def run_preprocess_executor(
    *,
    state: AgentState,
    preprocess_service: PreprocessService,
) -> Dict[str, Any]:
    """전처리 계획을 실제 데이터셋에 적용한다."""
    dataset_id = state.get("dataset_id")
    if dataset_id is None:
        return {
            "preprocess_result": {
                "status": "failed",
                "applied_ops_count": 0,
                "error": "dataset_id is required",
            }
        }

    operations_raw = (state.get("preprocess_plan") or {}).get("operations", [])
    operations = [PreprocessOperation(**op) for op in operations_raw]
    if not operations:
        return {"preprocess_result": {"status": "skipped", "applied_ops_count": 0}}

    try:
        preprocess_service.apply(dataset_id=int(dataset_id), operations=operations)
        updated_profile = dict(state.get("dataset_profile", {}))
        updated_profile["preprocess_applied"] = True
        return {
            "dataset_profile": updated_profile,
            "preprocess_result": {"status": "applied", "applied_ops_count": len(operations)},
        }
    except Exception as exc:
        return {
            "preprocess_result": {
                "status": "failed",
                "applied_ops_count": 0,
                "error": str(exc),
            }
        }


def build_preprocess_workflow(
    *,
    db: Session,
    default_model: str = "gpt-5-nano",
):
    """프로파일링부터 실행까지 포함한 전처리 서브그래프를 생성한다."""
    repo = DataSourceRepository(db)
    preprocess_service = PreprocessService(db)

    def log_branch(point: str, branch: str, detail: str = "") -> None:
        """분기 지점과 선택 결과를 콘솔에 출력한다."""
        suffix = f" | {detail}" if detail else ""
        print(f"[branch:preprocess] {point} -> {branch}{suffix}")

    def ingestion_and_profile_node(state: PreprocessGraphState) -> Dict[str, Any]:
        """선택된 데이터셋의 최소 프로파일을 생성한다."""
        if state.get("dataset_profile"):
            return {}

        dataset_id = state.get("dataset_id")
        if not dataset_id:
            return {"dataset_profile": {"available": False}}

        dataset = repo.get_by_id(int(dataset_id))
        if not dataset or not dataset.storage_path:
            return {"dataset_profile": {"available": False}}

        file_path = Path(dataset.storage_path)
        if not file_path.exists():
            return {"dataset_profile": {"available": False}}

        try:
            sample_df = pd.read_csv(file_path, nrows=2000)
        except Exception:
            return {"dataset_profile": {"available": False}}

        missing_counts = sample_df.isna().sum().to_dict()
        total_rows = len(sample_df.index)
        missing_ratio = {
            col: (float(cnt) / float(total_rows) if total_rows > 0 else 0.0)
            for col, cnt in missing_counts.items()
        }

        return {
            "dataset_profile": {
                "available": True,
                "sample_rows": total_rows,
                "columns": sample_df.columns.tolist(),
                "numeric_columns": sample_df.select_dtypes(include=["number"]).columns.tolist(),
                "missing_ratio_by_column": missing_ratio,
            }
        }

    def preprocess_decision_node(state: PreprocessGraphState) -> Dict[str, Any]:
        """데이터 프로파일을 기반으로 전처리 필요 여부를 판단한다."""
        profile_json = json.dumps(state.get("dataset_profile", {}), ensure_ascii=False)
        decision = _call_structured(
            schema=PreprocessDecision,
            system_prompt=(
                "데이터 프로파일을 보고 전처리가 필요하면 run_preprocess, "
                "아니면 skip_preprocess를 반환하라."
            ),
            human_prompt=(
                f"user_input={state.get('user_input', '')}\n"
                f"dataset_profile={profile_json}"
            ),
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        log_branch("preprocess_decision", decision.step)
        return {"preprocess_decision": decision.model_dump()}

    def route_by_decision(state: PreprocessGraphState) -> str:
        """preprocess_decision 값으로 run/skip 경로를 결정한다."""
        step = (state.get("preprocess_decision") or {}).get("step")
        branch = "run_preprocess" if step == "run_preprocess" else "skip_preprocess"
        log_branch("route_by_decision", branch)
        return branch

    def planner_node(state: PreprocessGraphState) -> Dict[str, Any]:
        """전처리 실행 계획을 생성한다."""
        return build_preprocess_plan(
            state=state,
            default_model=default_model,
        )

    def executor_node(state: PreprocessGraphState) -> Dict[str, Any]:
        """전처리 실행 계획을 실제 데이터셋에 적용한다."""
        return run_preprocess_executor(
            state=state,
            preprocess_service=preprocess_service,
        )

    def skip_node(_: PreprocessGraphState) -> Dict[str, Any]:
        """전처리를 건너뛴 경우 기본 결과를 기록한다."""
        log_branch("execution", "skip_preprocess")
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


def build_preprocess_subgraph(
    *,
    db: Session,
    default_model: str = "gpt-5-nano",
):
    """이전 이름 호환을 위한 별칭 함수."""
    return build_preprocess_workflow(
        db=db,
        default_model=default_model,
    )
