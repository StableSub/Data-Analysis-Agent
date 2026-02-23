"""
V1 시각화 서브그래프.

역할:
- 선택된 데이터셋에서 실제 차트 데이터를 생성한다.
- 최종 output은 생성하지 않고 상태만 누적한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from backend.app.ai.agents.state import VisualizationGraphState
from backend.app.domain.data_source.repository import DataSourceRepository


def _resolve_target_source_id(state: VisualizationGraphState) -> str | None:
    preprocess_result = state.get("preprocess_result")
    if isinstance(preprocess_result, dict) and preprocess_result.get("status") == "applied":
        output_source_id = preprocess_result.get("output_source_id")
        if isinstance(output_source_id, str) and output_source_id.strip():
            return output_source_id.strip()

    rag_result = state.get("rag_result")
    if isinstance(rag_result, dict):
        rag_source_id = rag_result.get("source_id")
        if isinstance(rag_source_id, str) and rag_source_id.strip():
            return rag_source_id.strip()

    source_id = state.get("source_id")
    if isinstance(source_id, str) and source_id.strip():
        return source_id.strip()

    return None


def build_visualization_workflow(*, db: Session, default_model: str = "gpt-5-nano"):
    """시각화 계획/생성 서브그래프를 생성한다."""
    _ = default_model
    data_source_repository = DataSourceRepository(db)

    def visualization_planner_node(state: VisualizationGraphState) -> Dict[str, Any]:
        source_id = _resolve_target_source_id(state)
        plan = {
            "status": "planned",
            "source_id": source_id,
            "chart_type": "scatter",
            "max_points": 120,
        }
        return {"visualization_plan": plan}

    def visualization_generator_node(state: VisualizationGraphState) -> Dict[str, Any]:
        plan = state.get("visualization_plan")
        plan_dict = plan if isinstance(plan, dict) else {}
        source_id_value = plan_dict.get("source_id")
        source_id = source_id_value if isinstance(source_id_value, str) and source_id_value else ""
        max_points_raw = plan_dict.get("max_points")
        max_points = max_points_raw if isinstance(max_points_raw, int) and max_points_raw > 0 else 120

        if not source_id:
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": "",
                    "summary": "시각화 대상 데이터셋이 없어 차트를 생성하지 못했습니다.",
                }
            }

        dataset = data_source_repository.get_by_source_id(source_id)
        if dataset is None or not dataset.storage_path:
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": source_id,
                    "summary": "시각화 대상 데이터셋을 찾지 못했습니다.",
                }
            }

        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": source_id,
                    "summary": "데이터 파일이 없어 차트를 생성하지 못했습니다.",
                }
            }

        df = pd.read_csv(file_path, nrows=max_points)
        if df.empty:
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": source_id,
                    "summary": "데이터가 비어 있어 차트를 생성하지 못했습니다.",
                }
            }

        numeric_columns = df.select_dtypes(include="number").columns.tolist()
        if len(numeric_columns) < 2:
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": source_id,
                    "summary": "수치형 컬럼이 2개 미만이라 산점도를 생성하지 못했습니다.",
                }
            }

        x_key, y_key = numeric_columns[0], numeric_columns[1]
        chart_df = df[[x_key, y_key]].dropna().head(max_points)
        if chart_df.empty:
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": source_id,
                    "summary": "유효한 수치 데이터가 없어 차트를 생성하지 못했습니다.",
                }
            }

        points = [
            {"x": float(row[x_key]), "y": float(row[y_key])}
            for _, row in chart_df.iterrows()
        ]

        return {
            "visualization_result": {
                "status": "generated",
                "source_id": source_id,
                "summary": f"{x_key}와 {y_key} 기준으로 scatter 차트를 생성했습니다.",
                "chart": {
                    "chart_type": "scatter",
                    "x_key": x_key,
                    "y_key": y_key,
                    "points": points,
                },
            }
        }

    graph = StateGraph(VisualizationGraphState)
    graph.add_node("visualization_planner", visualization_planner_node)
    graph.add_node("visualization_generator", visualization_generator_node)
    graph.add_edge(START, "visualization_planner")
    graph.add_edge("visualization_planner", "visualization_generator")
    graph.add_edge("visualization_generator", END)

    return graph.compile()
