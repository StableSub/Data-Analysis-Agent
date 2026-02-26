"""Preprocessing subgraph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Literal

import pandas as pd
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from backend.app.ai.agents.state import PreprocessGraphState
from backend.app.ai.agents.utils import call_structured_llm
from backend.app.domain.data_source.repository import DataSourceRepository
from backend.app.domain.preprocess.schemas import PreprocessOperation
from backend.app.domain.preprocess.service import PreprocessService

class PreprocessPlan(BaseModel):
    operations: list[PreprocessOperation] = Field(default_factory=list)
    planner_comment: str = ""

class PreprocessDecision(BaseModel):
    step: Literal["run_preprocess", "skip_preprocess"] = Field(...)
    reason_summary: str = ""

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
    """
    역할: 데이터셋 프로파일링, 전처리 필요성 판단, 계획 생성, 실행/스킵 경로를 가진 서브그래프를 구성한다.
    입력: DB 세션(`db`)과 기본 모델명(`default_model`)을 받아 내부 노드 의존성을 초기화한다.
    출력: `preprocess_result`를 상태에 누적하는 컴파일된 전처리 워크플로우를 반환한다.
    데코레이터: 없음.
    호출 맥락: 메인 워크플로우의 `preprocess_flow` 노드로 연결되어 데이터 파이프라인 초반에 실행된다.
    """
    repo = DataSourceRepository(db)
    preprocess_service = PreprocessService(db)

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
        numeric_cols = sample_df.select_dtypes(include="number").columns.tolist()
        datetime_cols = [
            col
            for col in sample_df.columns
            if (
                pd.to_datetime(sample_df[col], errors="coerce").notna().mean() >= 0.7
                and col not in numeric_cols
            )
        ]
        categorical_cols = [
            col
            for col in sample_df.columns
            if col not in numeric_cols and col not in datetime_cols
        ]
        sample_rows = sample_df.head(3)
        return {
            "dataset_profile": {
                "available": True,
                "row_count": len(sample_df),
                "columns": sample_df.columns.tolist(),
                "dtypes": sample_df.dtypes.astype(str).to_dict(),
                "missing_rates": sample_df.isna().mean().round(3).to_dict(),
                "sample_values": sample_rows.where(
                    sample_rows.notnull(),
                    None,
                ).to_dict(orient="list"),
                "numeric_columns": [str(c) for c in numeric_cols],
                "datetime_columns": [str(c) for c in datetime_cols],
                "categorical_columns": [str(c) for c in categorical_cols],
            }
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
