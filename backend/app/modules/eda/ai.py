from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from ...core.ai import LLMGateway, PromptRegistry

PROMPTS = PromptRegistry(
    {
        "summary.system": (
            "당신은 데이터 EDA 결과를 해석하는 분석가다. "
            "반드시 한국어로 작성하고, 반드시 JSON 객체만 반환하라. "
            '키는 "structure_summary", "quality_issues", "key_insights", '
            '"preprocess_recommendations"만 사용하라. '
            '"structure_summary"는 문자열 하나, 나머지 3개 키는 문자열 배열이어야 한다. '
            "각 배열은 1~3개 항목으로 간결하게 작성하라. "
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
) -> dict[str, Any]:
    llm = LLMGateway(default_model=default_model)
    result = llm.invoke(
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("summary.system")),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ],
    )
    content = result.content if isinstance(result.content, str) else str(result.content)
    return _parse_summary_content(content)


def _parse_summary_content(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return _parse_summary_sections(content)

    return {
        "structure_summary": str(parsed.get("structure_summary", "")).strip(),
        "quality_issues": _coerce_string_list(parsed.get("quality_issues")),
        "key_insights": _coerce_string_list(parsed.get("key_insights")),
        "preprocess_recommendations": _coerce_string_list(parsed.get("preprocess_recommendations")),
    }


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _parse_summary_sections(content: str) -> dict[str, Any]:
    sections: dict[str, list[str]] = {
        "structure_summary": [],
        "quality_issues": [],
        "key_insights": [],
        "preprocess_recommendations": [],
    }
    current_key = "structure_summary"
    heading_map = {
        "데이터 구조 요약": "structure_summary",
        "품질 이슈": "quality_issues",
        "주요 인사이트": "key_insights",
        "전처리 추천": "preprocess_recommendations",
    }

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = line.lstrip("#").strip()
        mapped_key = heading_map.get(normalized)
        if mapped_key is not None:
            current_key = mapped_key
            continue
        cleaned = line.lstrip("-*0123456789. ").strip()
        if cleaned:
            sections[current_key].append(cleaned)

    structure_summary = " ".join(sections["structure_summary"]).strip()
    if not structure_summary:
        structure_summary = content.strip()

    return {
        "structure_summary": structure_summary,
        "quality_issues": sections["quality_issues"],
        "key_insights": sections["key_insights"],
        "preprocess_recommendations": sections["preprocess_recommendations"],
    }
