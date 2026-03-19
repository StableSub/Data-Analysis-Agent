from __future__ import annotations

import json
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..core.ai import LLMGateway, PromptRegistry, StructuredOutputRunner

PROMPTS = PromptRegistry(
    {
        "intent.system": (
            "데이터셋이 이미 선택된 상황이다. "
            "step은 data_pipeline으로 반환하라. "
            "질문을 보고 ask_preprocess, ask_visualization, ask_report를 true/false로 판단하라."
        ),
        "general.system": "사용자 질문에 간결하고 정확하게 답하라.",
        "data_qa.system": "주어진 merged_context를 근거로 사용자 데이터 질문에 간결하게 답하라.",
    }
)


class IntentDecision(BaseModel):
    step: Literal["general_question", "data_pipeline"] = Field(...)
    ask_preprocess: bool = Field(False)
    ask_visualization: bool = Field(False)
    ask_report: bool = Field(False)


def analyze_intent(
    *,
    user_input: str,
    model_id: str | None,
    default_model: str,
) -> IntentDecision:
    runner = StructuredOutputRunner(default_model=default_model)
    return runner.invoke(
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
    model_id: str | None,
    default_model: str,
) -> str:
    llm = LLMGateway(default_model=default_model)
    result = llm.invoke(
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("general.system")),
            HumanMessage(content=user_input),
        ],
    )
    return result.content if isinstance(result.content, str) else str(result.content)


def answer_data_question(
    *,
    user_input: str,
    merged_context: dict,
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
                    f"merged_context:\n{json.dumps(merged_context, ensure_ascii=False)}"
                )
            ),
        ],
    )
    return result.content if isinstance(result.content, str) else str(result.content)
