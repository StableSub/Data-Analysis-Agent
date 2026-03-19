from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ...core.ai import LLMGateway, PromptRegistry, StructuredOutputRunner

PROMPTS = PromptRegistry(
    {
        "insight.system": (
            "질문과 검색 컨텍스트를 읽고 핵심 인사이트를 간단히 합성하라. "
            "insight_summary와 evidence_summary를 함께 반환하라."
        ),
        "answer.system": "주어진 검색 컨텍스트만 근거로 사용자 질문에 간결하게 답하라.",
    }
)


class InsightSynthesisPayload(BaseModel):
    insight_summary: str = Field(...)
    evidence_summary: str = Field(default="")


def synthesize_insight(
    *,
    query: str,
    context: str,
    model_id: str | None,
    default_model: str,
) -> InsightSynthesisPayload:
    runner = StructuredOutputRunner(default_model=default_model)
    return runner.invoke(
        schema=InsightSynthesisPayload,
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("insight.system")),
            HumanMessage(content=f"question:\n{query}\n\ncontext:\n{context}"),
        ],
    )


def answer_with_context(
    *,
    query: str,
    context: str,
    model_id: str | None,
    default_model: str,
) -> str:
    llm = LLMGateway(default_model=default_model)
    result = llm.invoke(
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("answer.system")),
            HumanMessage(content=f"question:\n{query}\n\ncontext:\n{context}"),
        ],
    )
    return result.content if isinstance(result.content, str) else str(result.content)
