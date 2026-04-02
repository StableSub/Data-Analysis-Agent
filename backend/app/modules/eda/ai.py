from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from ...core.ai import LLMGateway, PromptRegistry

PROMPTS = PromptRegistry(
    {
        "summary.system": (
            "당신은 데이터 EDA 결과를 해석하는 분석가다. "
            "반드시 한국어로 작성하고, 아래 4개 섹션 제목만 사용하라.\n"
            "데이터 구조 요약\n품질 이슈\n주요 인사이트\n전처리 추천\n"
            "각 섹션은 1~3문장으로 간결하게 작성하라. "
            "원본 데이터 행을 추측하지 말고 제공된 통계/요약만 근거로 사용하라. "
            "가능하면 수치를 직접 인용하라."
        ),
    }
)


def generate_eda_ai_summary(
    *,
    payload: dict[str, Any],
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
