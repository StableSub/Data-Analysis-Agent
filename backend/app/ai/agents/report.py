"""
V1 리포트 서브그래프.

역할:
- 선택 데이터셋의 정량 지표와 인사이트/시각화를 반영한 리포트를 생성한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from backend.app.ai.agents.state import ReportGraphState
from backend.app.domain.data_source.repository import DataSourceRepository


def _resolve_target_source_id(state: ReportGraphState) -> str | None:
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


def _safe_float(value: Any, ndigits: int = 4) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), ndigits)


def _build_metrics(*, df: pd.DataFrame, source_id: str) -> Dict[str, Any]:
    row_count = int(df.shape[0])
    column_count = int(df.shape[1])
    total_cells = row_count * column_count
    missing_cells = int(df.isna().sum().sum())
    missing_rate = (missing_cells / total_cells) if total_cells > 0 else 0.0

    missing_by_column = df.isna().mean().sort_values(ascending=False)
    top_missing_columns = [
        {
            "column": str(column),
            "missing_rate": round(float(rate), 4),
        }
        for column, rate in missing_by_column.head(5).items()
        if float(rate) > 0
    ]

    numeric_df = df.select_dtypes(include="number")
    numeric_stats: list[Dict[str, Any]] = []
    for column in numeric_df.columns[:8]:
        series = numeric_df[column].dropna()
        if series.empty:
            continue
        numeric_stats.append(
            {
                "column": str(column),
                "min": _safe_float(series.min()),
                "max": _safe_float(series.max()),
                "mean": _safe_float(series.mean()),
                "median": _safe_float(series.median()),
                "std": _safe_float(series.std()),
            }
        )

    correlation_pairs: list[Dict[str, Any]] = []
    if numeric_df.shape[1] >= 2:
        corr_matrix = numeric_df.corr(numeric_only=True)
        cols = list(corr_matrix.columns)
        for i, col1 in enumerate(cols):
            for col2 in cols[i + 1:]:
                value = corr_matrix.loc[col1, col2]
                if pd.isna(value):
                    continue
                corr_value = float(value)
                correlation_pairs.append(
                    {
                        "column_1": str(col1),
                        "column_2": str(col2),
                        "correlation": round(corr_value, 4),
                        "abs_corr": abs(corr_value),
                    }
                )
    correlation_pairs.sort(key=lambda item: item["abs_corr"], reverse=True)
    top_correlations = [
        {
            "column_1": item["column_1"],
            "column_2": item["column_2"],
            "correlation": item["correlation"],
        }
        for item in correlation_pairs[:5]
    ]

    return {
        "source_id": source_id,
        "row_count": row_count,
        "column_count": column_count,
        "missing": {
            "missing_cells": missing_cells,
            "total_cells": total_cells,
            "missing_rate": round(missing_rate, 4),
            "top_missing_columns": top_missing_columns,
        },
        "numeric_stats": numeric_stats,
        "top_correlations": top_correlations,
    }


def build_report_workflow(*, db: Session, default_model: str = "gpt-5-nano"):
    """리포트 합성 서브그래프를 생성한다."""
    data_source_repository = DataSourceRepository(db)

    def report_composer_node(state: ReportGraphState) -> Dict[str, Any]:
        target_source_id = _resolve_target_source_id(state)

        metrics: Dict[str, Any] = {
            "source_id": target_source_id,
            "row_count": 0,
            "column_count": 0,
            "missing": {
                "missing_cells": 0,
                "total_cells": 0,
                "missing_rate": 0.0,
                "top_missing_columns": [],
            },
            "numeric_stats": [],
            "top_correlations": [],
        }
        if target_source_id:
            dataset = data_source_repository.get_by_source_id(target_source_id)
            if dataset is not None and dataset.storage_path:
                file_path = Path(dataset.storage_path)
                if file_path.exists() and file_path.is_file():
                    df = pd.read_csv(file_path, nrows=5000)
                    if not df.empty:
                        metrics = _build_metrics(df=df, source_id=target_source_id)

        report_visualizations: list[Dict[str, Any]] = []

        insight = state.get("insight")
        insight_summary = ""
        if isinstance(insight, dict) and isinstance(insight.get("summary"), str):
            insight_summary = str(insight.get("summary")).strip()

        visualization_result = state.get("visualization_result")
        visualization_summary = ""
        if isinstance(visualization_result, dict):
            viz_summary = visualization_result.get("summary")
            if isinstance(viz_summary, str) and viz_summary.strip():
                visualization_summary = viz_summary.strip()
            if visualization_result.get("status") == "generated":
                chart = visualization_result.get("chart")
                artifact = visualization_result.get("artifact")
                if isinstance(chart, dict):
                    visualization_item: Dict[str, Any] = {"chart": chart}
                    if isinstance(artifact, dict):
                        visualization_item["artifact"] = artifact
                    report_visualizations.append(visualization_item)

        user_input = state.get("user_input", "")
        question = str(user_input).split("\n\ncontext:\n", 1)[0]
        model_name = state.get("model_id") or default_model
        llm = init_chat_model(model_name)
        result = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "당신은 데이터 분석 리포트 작성자다. "
                        "반드시 아래 3개 섹션 제목으로만 한국어 리포트를 작성하라.\n"
                        "요약\n핵심 인사이트\n권고사항\n"
                        "각 섹션은 2~5문장으로 작성하고, 가능한 한 수치를 인용하라. "
                        "단계 로그 설명은 금지한다."
                    )
                ),
                HumanMessage(
                    content=(
                        f"사용자 질문:\n{question}\n\n"
                        f"정량 지표(metrics):\n{json.dumps(metrics, ensure_ascii=False)}\n\n"
                        f"RAG 인사이트 요약:\n{insight_summary}\n\n"
                        f"시각화 요약:\n{visualization_summary}\n"
                    )
                ),
            ]
        )
        report_text = result.content if isinstance(result.content, str) else str(result.content)

        return {
            "report_result": {
                "summary": report_text,
                "metrics": metrics,
                "visualizations": report_visualizations,
            },
            "output": {
                "type": "report_answer",
                "content": report_text,
            },
        }

    graph = StateGraph(ReportGraphState)
    graph.add_node("report_composer", report_composer_node)
    graph.add_edge(START, "report_composer")
    graph.add_edge("report_composer", END)

    return graph.compile()
