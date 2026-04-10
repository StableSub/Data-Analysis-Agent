from __future__ import annotations

from typing import Any, Literal, Mapping

from langchain_core.messages import HumanMessage, SystemMessage
import pandas as pd
from pydantic import BaseModel, Field

from ...core.ai import LLMGateway, PromptRegistry
from .service import VisualizationService

PROMPTS = PromptRegistry(
    {
        "recommend.system": (
            "사용자 질문과 컬럼 목록을 보고 가장 적합한 차트를 선택하라. "
            "x_column, y_column은 반드시 주어진 컬럼 목록에서 선택하라. "
            "hist는 y_column이 빈 문자열이다."
        ),
    }
)

CHART_KEYWORDS: dict[str, tuple[str, ...]] = {
    "scatter": ("scatter", "산점도", "점그래프"),
    "line": ("line", "라인", "선그래프", "시계열"),
    "bar": ("bar", "막대"),
    "hist": ("hist", "histogram", "히스토그램"),
    "box": ("box", "boxplot", "박스플롯"),
}


class VisualizationPlan(BaseModel):
    status: str = Field(default="unavailable")
    source_id: str = Field(default="")
    mode: str = Field(default="")
    chart_type: Literal["scatter", "line", "bar", "hist", "box", ""] = Field(default="")
    x_key: str = Field(default="")
    y_key: str = Field(default="")
    reason: str = Field(default="")
    x_is_datetime: bool = Field(default=False)


class ChartSelection(BaseModel):
    chart_type: Literal["scatter", "line", "bar", "hist", "box"] = Field(...)
    x_column: str = Field(...)
    y_column: str = Field(default="")
    reason: str = Field(default="")


def get_revision_instruction(revision_request: Mapping[str, Any] | str | None) -> str:
    if isinstance(revision_request, dict):
        if revision_request.get("stage") == "visualization":
            instruction = revision_request.get("instruction")
            if isinstance(instruction, str):
                return instruction.strip()
        return ""
    return str(revision_request or "").strip()


def build_visualization_review_payload(
    *,
    source_id: str,
    plan: VisualizationPlan,
    preview_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = plan.reason.strip() or "시각화 계획을 검토한 뒤 승인 여부를 결정해 주세요."
    return {
        "stage": "visualization",
        "kind": "plan_review",
        "title": "Visualization plan review",
        "summary": summary,
        "source_id": source_id,
        "plan": {
            "chart_type": plan.chart_type,
            "x_key": plan.x_key,
            "y_key": plan.y_key,
            "mode": plan.mode,
            "reason": plan.reason,
            "x_is_datetime": plan.x_is_datetime,
            "preview_rows": preview_rows,
        },
    }


def build_visualization_plan(
    *,
    source_id: str | None,
    user_input: str,
    revision_request: Mapping[str, Any] | str | None,
    dataset_profile: dict[str, Any] | None,
    model_id: str | None,
    default_model: str,
    visualization_service: VisualizationService,
    max_sample_rows: int,
) -> VisualizationPlan:
    query = user_input.strip()
    revision_text = get_revision_instruction(revision_request)
    planner_query = f"{query}\n수정 요청: {revision_text}" if revision_text else query
    requested_chart_type = _detect_requested_chart_type(planner_query)
    mode = "specified" if requested_chart_type else "auto"

    empty_plan = VisualizationPlan(
        status="unavailable",
        source_id=source_id or "",
        mode=mode,
        chart_type=requested_chart_type or "",
    )

    if not source_id:
        return empty_plan.model_copy(
            update={"reason": "시각화 대상 source_id가 없어 계획을 생성하지 못했습니다."}
        )

    df, load_status = visualization_service.load_sample_frame(source_id, nrows=max_sample_rows)
    if load_status == "dataset_missing":
        return empty_plan.model_copy(
            update={"reason": "시각화 대상 데이터셋을 찾지 못했습니다."}
        )
    if load_status == "unsupported_format":
        return empty_plan.model_copy(
            update={"reason": "CSV 형식 데이터셋만 시각화 계획을 생성할 수 있습니다."}
        )
    if load_status == "read_error":
        return empty_plan.model_copy(
            update={"reason": "데이터를 읽지 못해 시각화 계획을 생성하지 못했습니다."}
        )

    if df.empty:
        return empty_plan.model_copy(
            update={"reason": "데이터가 비어 있어 시각화 계획을 생성하지 못했습니다."}
        )

    numeric_columns, datetime_columns, categorical_columns = _resolve_columns(
        df=df,
        dataset_profile=dataset_profile or {},
    )
    selection = _recommend_chart(
        query=planner_query,
        numeric_columns=numeric_columns,
        datetime_columns=datetime_columns,
        categorical_columns=categorical_columns,
        model_id=model_id,
        default_model=default_model,
    )
    if selection is None:
        selection = _select_chart(
            requested_chart_type=requested_chart_type,
            numeric_columns=numeric_columns,
            datetime_columns=datetime_columns,
            categorical_columns=categorical_columns,
        )

    if selection["status"] != "planned":
        return empty_plan.model_copy(update={"reason": str(selection["reason"])})

    return VisualizationPlan(
        status="planned",
        source_id=source_id,
        mode=str(selection["mode"]),
        chart_type=str(selection["chart_type"]),
        x_key=str(selection["x_key"]),
        y_key=str(selection["y_key"]),
        reason=str(selection["reason"]),
        x_is_datetime=bool(selection["x_is_datetime"]),
    )


def _resolve_columns(
    *,
    df: pd.DataFrame,
    dataset_profile: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    if (
        bool(dataset_profile.get("available"))
        and isinstance(dataset_profile.get("numeric_columns"), list)
        and isinstance(dataset_profile.get("datetime_columns"), list)
        and isinstance(dataset_profile.get("categorical_columns"), list)
    ):
        return (
            [str(col) for col in dataset_profile.get("numeric_columns", [])],
            [str(col) for col in dataset_profile.get("datetime_columns", [])],
            [str(col) for col in dataset_profile.get("categorical_columns", [])],
        )

    numeric_columns = [str(col) for col in df.select_dtypes(include="number").columns.tolist()]
    datetime_columns = _infer_datetime_columns(df)
    datetime_set = set(datetime_columns)
    numeric_set = set(numeric_columns)
    categorical_columns = [
        str(col)
        for col in df.columns
        if str(col) not in datetime_set and str(col) not in numeric_set
    ]
    return numeric_columns, datetime_columns, categorical_columns


def _recommend_chart(
    *,
    query: str,
    numeric_columns: list[str],
    datetime_columns: list[str],
    categorical_columns: list[str],
    model_id: str | None,
    default_model: str,
) -> dict[str, Any] | None:
    llm = LLMGateway(default_model=default_model)
    columns_info = (
        f"numeric: {numeric_columns}\n"
        f"datetime: {datetime_columns}\n"
        f"categorical: {categorical_columns}"
    )
    result = llm.invoke_structured(
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


def _detect_requested_chart_type(query: str) -> str | None:
    lowered = query.lower()
    for chart_type, keywords in CHART_KEYWORDS.items():
        for keyword in keywords:
            if keyword.isascii():
                if keyword in lowered:
                    return chart_type
                continue
            if keyword in query:
                return chart_type
    return None


def _infer_datetime_columns(df: pd.DataFrame) -> list[str]:
    datetime_columns = [
        str(col)
        for col in df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns.tolist()
    ]
    for col in df.columns:
        col_name = str(col)
        if col_name in datetime_columns:
            continue
        lowered = col_name.lower()
        if "date" not in lowered and "time" not in lowered:
            continue
        parsed = pd.to_datetime(df[col], errors="coerce")
        parsed_ratio = float(parsed.notna().mean()) if len(parsed) > 0 else 0.0
        if parsed_ratio >= 0.7:
            datetime_columns.append(col_name)
    return datetime_columns


def _select_chart(
    *,
    requested_chart_type: str | None,
    numeric_columns: list[str],
    datetime_columns: list[str],
    categorical_columns: list[str],
) -> dict[str, Any]:
    mode = "specified" if requested_chart_type else "auto"
    chart_type = requested_chart_type or ""
    x_key = ""
    y_key = ""
    reason = ""
    x_is_datetime = False

    if requested_chart_type == "scatter":
        if len(numeric_columns) >= 2:
            chart_type = "scatter"
            x_key, y_key = numeric_columns[0], numeric_columns[1]
            reason = "사용자가 산점도를 요청해 수치형 2개 컬럼을 선택했습니다."
        else:
            return _unavailable_selection(mode=mode, chart_type="scatter", reason="산점도 요청이 있었지만 수치형 컬럼이 2개 미만입니다.")
    elif requested_chart_type == "line":
        if datetime_columns and numeric_columns:
            chart_type = "line"
            x_key, y_key = datetime_columns[0], numeric_columns[0]
            x_is_datetime = True
            reason = "사용자가 라인 차트를 요청해 datetime+numeric 조합을 선택했습니다."
        elif len(numeric_columns) >= 2:
            chart_type = "line"
            x_key, y_key = numeric_columns[0], numeric_columns[1]
            reason = "시간 컬럼이 없어 수치형 2개 컬럼으로 라인 차트를 구성했습니다."
        else:
            return _unavailable_selection(mode=mode, chart_type="line", reason="라인 차트 요청이 있었지만 사용할 컬럼 조합이 없습니다.")
    elif requested_chart_type == "bar":
        if categorical_columns and numeric_columns:
            chart_type = "bar"
            x_key, y_key = categorical_columns[0], numeric_columns[0]
            reason = "사용자가 막대 차트를 요청해 categorical+numeric 조합을 선택했습니다."
        else:
            return _unavailable_selection(mode=mode, chart_type="bar", reason="막대 차트 요청이 있었지만 categorical+numeric 조합이 없습니다.")
    elif requested_chart_type == "hist":
        if numeric_columns:
            chart_type = "hist"
            x_key, y_key = numeric_columns[0], ""
            reason = "사용자가 히스토그램을 요청해 수치형 컬럼 1개를 선택했습니다."
        else:
            return _unavailable_selection(mode=mode, chart_type="hist", reason="히스토그램 요청이 있었지만 수치형 컬럼이 없습니다.")
    elif requested_chart_type == "box":
        if categorical_columns and numeric_columns:
            chart_type = "box"
            x_key, y_key = categorical_columns[0], numeric_columns[0]
            reason = "사용자가 박스플롯을 요청해 categorical+numeric 조합을 선택했습니다."
        elif numeric_columns:
            chart_type = "box"
            x_key, y_key = "", numeric_columns[0]
            reason = "사용자가 박스플롯을 요청해 수치형 컬럼 1개를 선택했습니다."
        else:
            return _unavailable_selection(mode=mode, chart_type="box", reason="박스플롯 요청이 있었지만 수치형 컬럼이 없습니다.")
    else:
        if datetime_columns and numeric_columns:
            chart_type = "line"
            x_key, y_key = datetime_columns[0], numeric_columns[0]
            x_is_datetime = True
            reason = "datetime+numeric 조합을 감지해 line 차트를 자동 선택했습니다."
        elif len(numeric_columns) >= 2:
            chart_type = "scatter"
            x_key, y_key = numeric_columns[0], numeric_columns[1]
            reason = "수치형 컬럼 2개 이상이라 scatter 차트를 자동 선택했습니다."
        elif len(numeric_columns) == 1:
            chart_type = "hist"
            x_key, y_key = numeric_columns[0], ""
            reason = "수치형 컬럼이 1개라 histogram 차트를 자동 선택했습니다."
        elif categorical_columns and numeric_columns:
            chart_type = "bar"
            x_key, y_key = categorical_columns[0], numeric_columns[0]
            reason = "categorical+numeric 조합을 감지해 bar 차트를 자동 선택했습니다."
        else:
            return _unavailable_selection(mode=mode, chart_type="", reason="시각화에 사용할 컬럼 조합을 찾지 못했습니다.")

    return {
        "status": "planned",
        "mode": mode,
        "chart_type": chart_type,
        "x_key": x_key,
        "y_key": y_key,
        "reason": reason,
        "x_is_datetime": x_is_datetime,
    }


def _unavailable_selection(*, mode: str, chart_type: str, reason: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "mode": mode,
        "chart_type": chart_type,
        "x_key": "",
        "y_key": "",
        "reason": reason,
        "x_is_datetime": False,
    }
