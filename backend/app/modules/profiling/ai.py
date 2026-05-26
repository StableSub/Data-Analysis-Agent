from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ...core.ai import LLMGateway, PromptRegistry


PROMPTS = PromptRegistry(
    {
        "column_aliases.system": (
            "You build a deterministic column alias dictionary for data analysis. "
            "For each provided dataset column, return short aliases that a Korean or English user may naturally use. "
            "Include Korean aliases when the column is English. "
            "Do not invent business facts or values. "
            "Return aliases only for the provided columns. "
            "Avoid aliases that could ambiguously match many unrelated columns. "
            "Use concise nouns or noun phrases, not full questions. "
            "When representative sample values clearly indicate a categorical column, "
            "include natural Korean and English value expressions that users may use to refer to that column. "
            "For example, if a Gender-like column has Male/Female values, include aliases such as 성별, 남성, 여성."
        ),
    }
)


class ColumnAliasItem(BaseModel):
    column: str = Field(...)
    aliases: list[str] = Field(default_factory=list)


class ColumnAliasPayload(BaseModel):
    columns: list[ColumnAliasItem] = Field(default_factory=list)


def generate_column_aliases(
    *,
    payload: dict[str, Any],
    model_id: str | None,
    default_model: str,
) -> dict[str, list[str]]:
    llm = LLMGateway(default_model=default_model)
    result = llm.invoke_structured(
        schema=ColumnAliasPayload,
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("column_aliases.system")),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ],
    )
    return _normalize_alias_payload(result, allowed_columns=payload.get("columns"))


def _normalize_alias_payload(
    payload: ColumnAliasPayload,
    *,
    allowed_columns: object,
) -> dict[str, list[str]]:
    allowed = {str(column).strip() for column in allowed_columns if str(column).strip()} if isinstance(allowed_columns, list) else set()
    aliases_by_column: dict[str, list[str]] = {}
    for item in payload.columns:
        column = item.column.strip()
        if column not in allowed:
            continue
        aliases = []
        seen = set()
        for alias in item.aliases:
            text = str(alias).strip()
            normalized = text.lower()
            if text and normalized not in seen and text != column:
                seen.add(normalized)
                aliases.append(text)
        if aliases:
            aliases_by_column[column] = aliases[:12]
    return aliases_by_column
