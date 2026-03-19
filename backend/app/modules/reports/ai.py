from __future__ import annotations

import json
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from ...core.ai import LLMGateway, PromptRegistry

PROMPTS = PromptRegistry(
    {
        "draft.system": (
            "당신은 데이터 분석 리포트 작성자다. "
            "반드시 아래 3개 섹션 제목으로만 한국어 리포트를 작성하라.\n"
            "요약\n핵심 인사이트\n권고사항\n"
            "각 섹션은 2~5문장으로 작성하고, 가능한 한 수치를 인용하라. "
            "단계 로그 설명은 금지한다."
        ),
        "summary.system": "다음 분석 결과를 간결하게 요약해 리포트를 작성해줘.",
    }
)


def draft_report(
    *,
    question: str,
    metrics: Dict[str, Any],
    insight_summary: str,
    visualization_summary: str,
    revision_instruction: str,
    model_id: str | None,
    default_model: str,
) -> str:
    llm = LLMGateway(default_model=default_model)
    result = llm.invoke(
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("draft.system")),
            HumanMessage(
                content=(
                    f"사용자 질문:\n{question}\n\n"
                    f"정량 지표(metrics):\n{json.dumps(metrics, ensure_ascii=False)}\n\n"
                    f"RAG 인사이트 요약:\n{insight_summary}\n\n"
                    f"시각화 요약:\n{visualization_summary}\n"
                    + (f"\n수정 요청:\n{revision_instruction}\n" if revision_instruction else "")
                )
            ),
        ],
    )
    return result.content if isinstance(result.content, str) else str(result.content)


def generate_summary_from_payload(
    *,
    payload: Dict[str, Any],
    model_id: str | None,
    default_model: str,
) -> str:
    llm = LLMGateway(default_model=default_model)
    result = llm.invoke(
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("summary.system")),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ],
    )
    return result.content if isinstance(result.content, str) else str(result.content)
