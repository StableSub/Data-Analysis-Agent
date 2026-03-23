"""
V1 시각화 서브그래프.

역할:
- 선택된 데이터셋에서 시각화 계획을 생성한다.
- 계획된 파이썬 코드를 샌드박스 실행해 PNG를 생성한다.
- 최종 output은 생성하지 않고 상태만 누적한다.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field, ValidationError

from backend.app.modules.visualization.ai import recommend_chart
from backend.app.modules.visualization.service import VisualizationService
from backend.app.orchestration.state import VisualizationGraphState
from backend.app.orchestration.utils import resolve_target_source_id

MAX_SAMPLE_ROWS = 2000
MAX_POINTS = 120

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
    chart_type: str = Field(default="")
    x_key: str = Field(default="")
    y_key: str = Field(default="")
    reason: str = Field(default="")
    python_code: str = Field(default="")
    output_filename: str = Field(default="")
    x_is_datetime: bool = Field(default=False)


def _get_visualization_revision_instruction(state: VisualizationGraphState) -> str:
    revision_request = state.get("revision_request")
    if isinstance(revision_request, dict):
        if revision_request.get("stage") == "visualization":
            instruction = revision_request.get("instruction")
            if isinstance(instruction, str):
                return instruction.strip()
        return ""
    return str(revision_request or "").strip()


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
) -> Dict[str, Any]:
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
            return {
                "status": "unavailable",
                "mode": mode,
                "chart_type": "scatter",
                "x_key": "",
                "y_key": "",
                "reason": "산점도 요청이 있었지만 수치형 컬럼이 2개 미만입니다.",
                "x_is_datetime": False,
            }
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
            return {
                "status": "unavailable",
                "mode": mode,
                "chart_type": "line",
                "x_key": "",
                "y_key": "",
                "reason": "라인 차트 요청이 있었지만 사용할 컬럼 조합이 없습니다.",
                "x_is_datetime": False,
            }
    elif requested_chart_type == "bar":
        if categorical_columns and numeric_columns:
            chart_type = "bar"
            x_key, y_key = categorical_columns[0], numeric_columns[0]
            reason = "사용자가 막대 차트를 요청해 categorical+numeric 조합을 선택했습니다."
        else:
            return {
                "status": "unavailable",
                "mode": mode,
                "chart_type": "bar",
                "x_key": "",
                "y_key": "",
                "reason": "막대 차트 요청이 있었지만 categorical+numeric 조합이 없습니다.",
                "x_is_datetime": False,
            }
    elif requested_chart_type == "hist":
        if numeric_columns:
            chart_type = "hist"
            x_key, y_key = numeric_columns[0], ""
            reason = "사용자가 히스토그램을 요청해 수치형 컬럼 1개를 선택했습니다."
        else:
            return {
                "status": "unavailable",
                "mode": mode,
                "chart_type": "hist",
                "x_key": "",
                "y_key": "",
                "reason": "히스토그램 요청이 있었지만 수치형 컬럼이 없습니다.",
                "x_is_datetime": False,
            }
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
            return {
                "status": "unavailable",
                "mode": mode,
                "chart_type": "box",
                "x_key": "",
                "y_key": "",
                "reason": "박스플롯 요청이 있었지만 수치형 컬럼이 없습니다.",
                "x_is_datetime": False,
            }
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
            return {
                "status": "unavailable",
                "mode": mode,
                "chart_type": "",
                "x_key": "",
                "y_key": "",
                "reason": "시각화에 사용할 컬럼 조합을 찾지 못했습니다.",
                "x_is_datetime": False,
            }

    return {
        "status": "planned",
        "mode": mode,
        "chart_type": chart_type,
        "x_key": x_key,
        "y_key": y_key,
        "reason": reason,
        "x_is_datetime": x_is_datetime,
    }


def _select_chart_with_llm(
    *,
    query: str,
    numeric_columns: list[str],
    datetime_columns: list[str],
    categorical_columns: list[str],
    model_id: str | None,
    default_model: str,
) -> Dict[str, Any] | None:
    return recommend_chart(
        query=query,
        numeric_columns=numeric_columns,
        datetime_columns=datetime_columns,
        categorical_columns=categorical_columns,
        model_id=model_id,
        default_model=default_model,
    )


def _build_visualization_review_payload(
    *,
    state: VisualizationGraphState,
    plan: VisualizationPlan,
    preview_rows: list[Dict[str, Any]],
) -> Dict[str, Any]:
    summary = plan.reason.strip() or "시각화 계획을 검토한 뒤 승인 여부를 결정해 주세요."
    return {
        "stage": "visualization",
        "kind": "plan_review",
        "title": "Visualization plan review",
        "summary": summary,
        "source_id": str(plan.source_id or state.get("source_id") or ""),
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


def build_visualization_workflow(
    *,
    visualization_service: VisualizationService,
    default_model: str = "gpt-5-nano",
):
    def visualization_planner_node(state: VisualizationGraphState) -> Dict[str, Any]:
        source_id = resolve_target_source_id(state)
        query = str(state.get("user_input", "")).strip()
        revision_request = _get_visualization_revision_instruction(state)
        planner_query = f"{query}\n수정 요청: {revision_request}" if revision_request else query
        requested_chart_type = _detect_requested_chart_type(planner_query)
        mode = "specified" if requested_chart_type else "auto"

        empty_plan = {
            "status": "unavailable",
            "source_id": source_id or "",
            "mode": mode,
            "chart_type": requested_chart_type or "",
            "x_key": "",
            "y_key": "",
            "reason": "",
            "python_code": "",
            "output_filename": "",
        }

        if not source_id:
            return {
                "visualization_plan": {
                    **empty_plan,
                    "reason": "시각화 대상 source_id가 없어 계획을 생성하지 못했습니다.",
                }
            }

        df = visualization_service.load_sample_frame(source_id, nrows=MAX_SAMPLE_ROWS)
        if df is None:
            return {
                "visualization_plan": {
                    **empty_plan,
                    "reason": "시각화 대상 데이터셋을 찾지 못했습니다.",
                }
            }

        if df.empty:
            return {
                "visualization_plan": {
                    **empty_plan,
                    "reason": "데이터가 비어 있어 시각화 계획을 생성하지 못했습니다.",
                }
            }

        profile = state.get("dataset_profile")
        profile_dict = profile if isinstance(profile, dict) else {}
        has_profile_columns = (
            bool(profile_dict.get("available"))
            and isinstance(profile_dict.get("numeric_columns"), list)
            and isinstance(profile_dict.get("datetime_columns"), list)
            and isinstance(profile_dict.get("categorical_columns"), list)
        )
        if has_profile_columns:
            numeric_columns = [str(col) for col in profile_dict.get("numeric_columns", [])]
            datetime_columns = [str(col) for col in profile_dict.get("datetime_columns", [])]
            categorical_columns = [str(col) for col in profile_dict.get("categorical_columns", [])]
        else:
            numeric_columns = [
                str(col) for col in df.select_dtypes(include="number").columns.tolist()
            ]
            datetime_columns = _infer_datetime_columns(df)
            datetime_set = set(datetime_columns)
            numeric_set = set(numeric_columns)
            categorical_columns = [
                str(col)
                for col in df.columns
                if str(col) not in datetime_set and str(col) not in numeric_set
            ]

        selection = _select_chart_with_llm(
            query=planner_query,
            numeric_columns=numeric_columns,
            datetime_columns=datetime_columns,
            categorical_columns=categorical_columns,
            model_id=state.get("model_id"),
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
            return {
                "visualization_plan": {
                    **empty_plan,
                    "reason": selection["reason"],
                }
            }

        chart_type = str(selection["chart_type"])
        x_key = str(selection["x_key"])
        y_key = str(selection["y_key"])
        x_is_datetime = bool(selection["x_is_datetime"])
        output_filename = f"viz_{chart_type}.png"
        python_code = visualization_service.build_execution_code(
            source_id=source_id,
            chart_type=chart_type,
            x_key=x_key,
            y_key=y_key,
            output_filename=output_filename,
            max_points=MAX_POINTS,
            x_is_datetime=x_is_datetime,
        )
        if not python_code:
            return {
                "visualization_plan": {
                    **empty_plan,
                    "reason": "시각화 실행 코드를 생성하지 못했습니다.",
                }
            }
        return {
            "visualization_plan": {
                "status": "planned",
                "source_id": source_id,
                "mode": str(selection["mode"]),
                "chart_type": chart_type,
                "x_key": x_key,
                "y_key": y_key,
                "reason": str(selection["reason"]),
                "python_code": python_code,
                "output_filename": output_filename,
                "x_is_datetime": x_is_datetime,
            }
        }

    def route_after_planner(state: VisualizationGraphState) -> str:
        plan_dict = state.get("visualization_plan") or {}
        if plan_dict.get("status") == "planned":
            return "approval"
        return "execute"

    def approval_gate_node(state: VisualizationGraphState) -> Dict[str, Any]:
        plan = VisualizationPlan.model_validate(state.get("visualization_plan") or {})
        source_id = str(plan.source_id or state.get("source_id") or "")
        preview_rows = visualization_service.build_preview_rows(
            source_id=source_id,
            x_key=plan.x_key,
            y_key=plan.y_key,
            limit=5,
        )
        payload = _build_visualization_review_payload(
            state=state,
            plan=plan,
            preview_rows=preview_rows,
        )
        decision_raw = interrupt(payload)

        decision = ""
        instruction = ""
        if isinstance(decision_raw, dict):
            decision_value = decision_raw.get("decision")
            instruction_value = decision_raw.get("instruction")
            if isinstance(decision_value, str):
                decision = decision_value
            if isinstance(instruction_value, str):
                instruction = instruction_value.strip()
        elif isinstance(decision_raw, str):
            decision = decision_raw

        if decision == "approve":
            return {
                "approved_plan": plan.model_dump(),
                "pending_approval": {},
                "revision_request": {},
            }

        if decision == "revise":
            return {
                "approved_plan": {},
                "pending_approval": payload,
                "revision_request": {
                    "stage": "visualization",
                    "instruction": instruction,
                },
            }

        return {
            "approved_plan": {},
            "pending_approval": {},
            "revision_request": {},
            "visualization_result": {
                "status": "cancelled",
                "source_id": source_id,
                "summary": "시각화 계획 검토 단계에서 실행을 취소했습니다.",
            },
            "output": {
                "type": "cancelled",
                "content": "시각화 계획 검토 단계에서 실행을 취소했습니다.",
            },
        }

    def route_after_approval(state: VisualizationGraphState) -> str:
        result = state.get("visualization_result") or {}
        if result.get("status") == "cancelled":
            return "cancel"
        if _get_visualization_revision_instruction(state):
            return "revise"
        return "approve"

    def visualization_executor_node(state: VisualizationGraphState) -> Dict[str, Any]:
        plan_raw = state.get("approved_plan") or state.get("visualization_plan") or {}
        try:
            plan = VisualizationPlan.model_validate(plan_raw)
        except ValidationError as exc:
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": "",
                    "summary": f"시각화 계획 형식이 올바르지 않습니다: {exc}",
                },
                "revision_request": {},
                "approved_plan": {},
                "pending_approval": {},
            }

        if plan.status != "planned":
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": str(plan.source_id or ""),
                    "summary": plan.reason or "시각화 계획이 없어 실행을 생략했습니다.",
                },
                "revision_request": {},
                "approved_plan": {},
                "pending_approval": {},
            }

        if not plan.python_code or not plan.output_filename or not plan.chart_type:
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": str(plan.source_id or ""),
                    "summary": "시각화 실행 코드가 없어 차트를 생성하지 못했습니다.",
                },
                "revision_request": {},
                "approved_plan": {},
                "pending_approval": {},
            }

        result = visualization_service.execute_generated_chart(
            source_id=str(plan.source_id or ""),
            chart_type=plan.chart_type,
            x_key=plan.x_key,
            y_key=plan.y_key,
            python_code=plan.python_code,
            output_filename=plan.output_filename,
            x_is_datetime=plan.x_is_datetime,
            max_sample_rows=MAX_SAMPLE_ROWS,
        )

        return {
            "visualization_result": result,
            "revision_request": {},
            "approved_plan": {},
            "pending_approval": {},
        }

    def cancel_node(_: VisualizationGraphState) -> Dict[str, Any]:
        return {}

    graph = StateGraph(VisualizationGraphState)
    graph.add_node("visualization_planner", visualization_planner_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("visualization_executor", visualization_executor_node)
    graph.add_node("cancel", cancel_node)
    graph.add_edge(START, "visualization_planner")
    graph.add_conditional_edges(
        "visualization_planner",
        route_after_planner,
        {
            "approval": "approval_gate",
            "execute": "visualization_executor",
        },
    )
    graph.add_conditional_edges(
        "approval_gate",
        route_after_approval,
        {
            "approve": "visualization_executor",
            "revise": "visualization_planner",
            "cancel": "cancel",
        },
    )
    graph.add_edge("visualization_executor", END)
    graph.add_edge("cancel", END)

    return graph.compile()
