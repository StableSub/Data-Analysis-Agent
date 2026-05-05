from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..core.ai import LLMGateway, PromptRegistry

PROMPTS = PromptRegistry(
    {
        "intent.system": (
            "데이터셋이 이미 선택된 상황이다. "
            "질문을 보고 ask_analysis, ask_preprocess, ask_visualization, ask_report, ask_guideline을 true/false로 판단하라. "
            "평균 계산, 합계, 그룹화, 최근 N개월 필터링, 추세 분석, 비교, 상관 분석, 시각화는 전처리가 아니라 분석이다. "
            "timestamp/date 컬럼에서 월, 주, 일 단위로 집계하거나 버킷팅하는 것도 전처리가 아니라 분석이다. "
            "월별 추세를 위해 year_month 같은 파생 값을 내부적으로 사용하는 것은 분석 단계에서 처리할 수 있으므로, 그 이유만으로 ask_preprocess를 true로 두지 마라. "
            "ask_preprocess는 결측치 처리, 형변환, 이상한 문자열 정리, 정규화, 스케일링, 인코딩, 컬럼명 변경, 파생 컬럼 생성처럼 "
            "데이터를 먼저 정제하거나 변환해야 할 때만 true로 두어라. "
            "질문이 전처리와 분석을 모두 요구하면 ask_preprocess와 ask_analysis를 둘 다 true로 둘 수 있다. "
            "명시적 데이터 정제 요청이 없고 원본 데이터로 바로 집계/분석이 가능하면 ask_preprocess는 false로 두어라. "
            "관계 분석 질문(X와 Y의 관계, scatter)은 기본적으로 원시 관측치 기반 분석이며, 평균이나 그룹 집계를 명시적으로 요구하지 않았다면 ask_preprocess를 true로 두지 마라."
        ),
        "general.system": "사용자 질문에 간결하고 정확하게 답하라.",
        "data_qa.system": (
            "주어진 evidence_package, answer_quality, merged_context만 근거로 사용자 데이터 질문에 답하라. "
            "answer_quality.answerable이 false이면 abstain_reason을 중심으로 답하고, 근거 밖의 숫자/컬럼/결론을 만들지 마라. "
            "evidence_package.analysis_metrics, analysis_table, used_columns를 우선 근거로 사용하라. "
            "이미 제공된 analysis_result, rag_result, guideline_result, visualization_result 안에서만 답하라. "
            "실제 결과와 해석을 먼저 직접적으로 제시하라. 방법 설명이나 일반론은 필요할 때만 최소한으로 덧붙여라."
        ),
    }
)


class IntentDecision(BaseModel):
    ask_analysis: bool = Field(False)
    ask_preprocess: bool = Field(False)
    ask_visualization: bool = Field(False)
    ask_report: bool = Field(False)
    ask_guideline: bool = Field(False)


def analyze_intent(
    *,
    user_input: str,
    model_id: str | None,
    default_model: str,
) -> IntentDecision:
    llm = LLMGateway(default_model=default_model)
    return llm.invoke_structured(
        schema=IntentDecision,
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("intent.system")),
            HumanMessage(content=user_input),
        ],
    )


def answer_general_question(
    *,
    user_input: str,
    request_context: str | None = None,
    model_id: str | None,
    default_model: str,
) -> str:
    llm = LLMGateway(default_model=default_model)
    content = user_input
    if isinstance(request_context, str) and request_context.strip():
        content = f"question:\n{user_input}\n\nrequest_context:\n{request_context.strip()}"
    result = llm.invoke(
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("general.system")),
            HumanMessage(content=content),
        ],
    )
    return result.content if isinstance(result.content, str) else str(result.content)


def answer_data_question(
    *,
    user_input: str,
    merged_context: dict,
    evidence_package: dict,
    answer_quality: dict,
    model_id: str | None,
    default_model: str,
) -> str:
    llm = LLMGateway(default_model=default_model)
    result = llm.invoke(
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("data_qa.system")),
            HumanMessage(
                content=(
                    f"question:\n{user_input}\n\n"
                    f"evidence_package:\n{json.dumps(evidence_package, ensure_ascii=False)}\n\n"
                    f"answer_quality:\n{json.dumps(answer_quality, ensure_ascii=False)}\n\n"
                    f"merged_context:\n{json.dumps(merged_context, ensure_ascii=False)}"
                )
            ),
        ],
    )
    return result.content if isinstance(result.content, str) else str(result.content)
