from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ...core.ai import PromptRegistry, StructuredOutputRunner

PROMPTS = PromptRegistry(
    {
        "recommend.system": (
            "사용자 질문과 컬럼 목록을 보고 가장 적합한 차트를 선택하라. "
            "x_column, y_column은 반드시 주어진 컬럼 목록에서 선택하라. "
            "hist는 y_column이 빈 문자열이다."
        ),
    }
)


class ChartSelection(BaseModel):
    chart_type: Literal["scatter", "line", "bar", "hist", "box"] = Field(...)
    x_column: str = Field(...)
    y_column: str = Field(default="")
    reason: str = Field(default="")


def recommend_chart(
    *,
    query: str,
    numeric_columns: list[str],
    datetime_columns: list[str],
    categorical_columns: list[str],
    model_id: str | None,
    default_model: str,
) -> dict[str, Any] | None:
    runner = StructuredOutputRunner(default_model=default_model)
    columns_info = (
        f"numeric: {numeric_columns}\n"
        f"datetime: {datetime_columns}\n"
        f"categorical: {categorical_columns}"
    )
    result = runner.invoke(
        schema=ChartSelection,
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("recommend.system")),
            HumanMessage(content=f"query: {query}\n\n{columns_info}"),
        ],
    )
    dump = result.model_dump()
    all_columns = numeric_columns + datetime_columns + categorical_columns
    x_column = str(dump.get("x_column") or "")
    y_column = str(dump.get("y_column") or "")
    if x_column not in all_columns:
        return None
    if y_column and y_column not in all_columns:
        return None
    return {
        "status": "planned",
        "mode": "llm",
        "chart_type": str(dump.get("chart_type") or ""),
        "x_key": x_column,
        "y_key": y_column,
        "reason": str(dump.get("reason") or ""),
        "x_is_datetime": x_column in datetime_columns,
    }
