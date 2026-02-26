from __future__ import annotations

from typing import Any, Dict

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel


def resolve_target_source_id(state: Dict[str, Any]) -> str | None:
    """
    역할: 전처리/검색 상태를 우선순위로 해석해 현재 파이프라인의 대상 source ID를 확정한다.
    입력: `preprocess_result`, `rag_result`, `source_id` 키를 포함할 수 있는 상태 딕셔너리를 받는다.
    출력: 유효한 source ID 문자열을 반환하거나 찾지 못하면 `None`을 반환한다.
    데코레이터: 없음.
    호출 맥락: RAG, Visualization, Report 서브그래프에서 공통으로 대상 데이터셋을 식별할 때 사용된다.
    """
    preprocess_result = state.get("preprocess_result")
    if isinstance(preprocess_result, dict) and preprocess_result.get("status") == "applied":
        output_source_id = preprocess_result.get("output_source_id")
        if isinstance(output_source_id, str) and output_source_id.strip():
            return output_source_id.strip()

    rag_result = state.get("rag_result")
    if isinstance(rag_result, dict):
        rag_source_id = rag_result.get("source_id")
        if isinstance(rag_source_id, str) and rag_source_id.strip():
            return rag_source_id.strip()

    source_id = state.get("source_id")
    if isinstance(source_id, str) and source_id.strip():
        return source_id.strip()
    return None


def call_structured_llm(
    *,
    schema: type[BaseModel],
    system_prompt: str,
    human_prompt: str,
    model_id: str | None,
    default_model: str,
) -> BaseModel:
    """
    역할: 구조화 출력 스키마가 필요한 LLM 호출을 공통 방식으로 실행한다.
    입력: 출력 스키마, 시스템/사용자 프롬프트, 모델 식별자(`model_id`, `default_model`)를 받는다.
    출력: 지정한 `schema` 타입의 Pydantic 결과 객체를 반환한다.
    데코레이터: 없음.
    호출 맥락: Intake, Preprocess, Visualization에서 일관된 temperature=0 분류/선택 호출에 사용된다.
    """
    model_name = model_id or default_model
    llm = init_chat_model(model_name, temperature=0).with_structured_output(
        schema,
        method="function_calling",
    )
    return llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]
    )
