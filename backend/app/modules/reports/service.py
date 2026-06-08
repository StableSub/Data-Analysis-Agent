from __future__ import annotations

from typing import Any, Dict, List, Mapping

from .ai import draft_report
from .models import Report
from .repository import ReportRepository


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _build_table_metrics(table: list[Dict[str, Any]]) -> Dict[str, Any]:
    columns = list(table[0].keys()) if table else []
    return {
        "row_count": len(table),
        "columns": columns,
        "preview_rows": table[:5],
    }


def _format_metric_lines(metrics: Mapping[str, Any]) -> list[str]:
    if not metrics:
        return ["- 확인 가능한 주요 지표가 없습니다."]
    return [
        f"- {key}: {_format_report_value(value)}"
        for key, value in metrics.items()
    ]


def _format_table_preview(rows: list[Any]) -> list[str]:
    table_rows = [row for row in rows if isinstance(row, dict)]
    if not table_rows:
        return ["- 표 미리보기가 없습니다."]

    columns = list(table_rows[0].keys())
    if not columns:
        return ["- 표 미리보기가 없습니다."]

    header = "| " + " | ".join(str(column) for column in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| "
        + " | ".join(_format_table_cell(row.get(column)) for column in columns)
        + " |"
        for row in table_rows[:5]
    ]
    return [header, separator, *body]


def _format_report_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4g}"
    if isinstance(value, (str, int, bool)) or value is None:
        return str(value)
    if isinstance(value, list):
        return f"{len(value)}개 항목"
    if isinstance(value, dict):
        return f"{len(value)}개 하위 항목"
    return str(value)


def _format_table_cell(value: Any) -> str:
    return _format_report_value(value).replace("|", "\\|")


class ReportService:
    """리포트 초안 생성과 최종 저장 흐름을 담당한다."""

    def __init__(
        self,
        repository: ReportRepository,
        *,
        default_model: str = "gpt-5-nano",
    ) -> None:
        self.repository = repository
        self.default_model = default_model

    def save_report(self, *, session_id: int, summary_text: str) -> Report:
        return self.repository.create(
            Report(
                session_id=session_id,
                summary_text=summary_text,
            )
        )

    def build_metrics_from_results(
        self,
        *,
        analysis_result: Mapping[str, Any] | None,
        dataset_context: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        analysis_payload = dict(analysis_result or {})
        dataset_payload = dict(dataset_context or {})
        raw_metrics = _as_dict(analysis_payload.get("raw_metrics"))
        table = [
            row
            for row in _as_list(analysis_payload.get("table"))
            if isinstance(row, dict)
        ]
        quality_summary = _as_dict(dataset_payload.get("quality_summary"))

        if raw_metrics:
            primary_source = "analysis_result.raw_metrics"
            primary_metrics = raw_metrics
        elif table:
            primary_source = "analysis_result.table"
            primary_metrics = _build_table_metrics(table)
        else:
            primary_source = "dataset_context.quality_summary"
            primary_metrics = quality_summary

        return {
            "primary_source": primary_source,
            "primary_metrics": primary_metrics,
            "raw_metrics": raw_metrics,
            "table_metrics": _build_table_metrics(table),
            "quality_summary": quality_summary,
            "used_columns": [str(column) for column in _as_list(analysis_payload.get("used_columns"))],
            "analysis_summary": str(analysis_payload.get("summary") or ""),
            "analysis_execution_status": str(
                analysis_payload.get("execution_status") or "unknown"
            ),
            "dataset_overview": {
                "source_id": str(dataset_payload.get("source_id") or ""),
                "filename": str(dataset_payload.get("filename") or ""),
                "row_count_total": int(dataset_payload.get("row_count_total", 0) or 0),
                "column_count": int(dataset_payload.get("column_count", 0) or 0),
                "columns": [str(column) for column in _as_list(dataset_payload.get("columns"))],
            },
        }

    def build_report_payload(
        self,
        *,
        analysis_result: Mapping[str, Any] | None,
        visualization_result: Mapping[str, Any] | None,
        guideline_context: Mapping[str, Any] | None,
        dataset_context: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        metrics = self.build_metrics_from_results(
            analysis_result=analysis_result,
            dataset_context=dataset_context,
        )
        analysis_payload = dict(analysis_result or {})
        visualization_payload = dict(visualization_result or {})
        guideline_payload = dict(guideline_context or {})
        dataset_payload = dict(dataset_context or {})

        return {
            "analysis_result": {
                "summary": str(analysis_payload.get("summary") or ""),
                "execution_status": str(analysis_payload.get("execution_status") or ""),
                "used_columns": metrics["used_columns"],
                "raw_metrics": metrics["raw_metrics"],
                "table": _as_list(analysis_payload.get("table"))[:10],
            },
            "visualization_result": {
                "status": str(visualization_payload.get("status") or ""),
                "summary": str(visualization_payload.get("summary") or ""),
                "chart_type": str(
                    visualization_payload.get("chart_type")
                    or _as_dict(visualization_payload.get("chart_data")).get("chart_type")
                    or _as_dict(visualization_payload.get("chart")).get("chart_type")
                    or ""
                ),
                "caption": str(
                    _as_dict(visualization_payload.get("chart_data")).get("caption")
                    or _as_dict(visualization_payload.get("chart")).get("caption")
                    or ""
                ),
            },
            "guideline_context": {
                "status": str(guideline_payload.get("status") or ""),
                "has_evidence": bool(guideline_payload.get("has_evidence", False)),
                "retrieved_count": int(guideline_payload.get("retrieved_count", 0) or 0),
                "evidence_summary": str(guideline_payload.get("evidence_summary") or ""),
                "filename": str(guideline_payload.get("filename") or ""),
            },
            "dataset_context": {
                "source_id": str(dataset_payload.get("source_id") or ""),
                "filename": str(dataset_payload.get("filename") or ""),
                "row_count_total": int(dataset_payload.get("row_count_total", 0) or 0),
                "column_count": int(dataset_payload.get("column_count", 0) or 0),
                "quality_summary": metrics["quality_summary"],
            },
            "metrics": metrics,
        }

    def build_report_draft(
        self,
        *,
        question: str,
        analysis_result: Mapping[str, Any] | None,
        visualization_result: Mapping[str, Any] | None,
        guideline_context: Mapping[str, Any] | None,
        dataset_context: Mapping[str, Any] | None,
        revision_instruction: str,
        model_id: str | None,
        visualizations: List[Dict[str, object]] | None = None,
        default_model: str | None = None,
    ) -> Dict[str, object]:
        report_payload = self.build_report_payload(
            analysis_result=analysis_result,
            visualization_result=visualization_result,
            guideline_context=guideline_context,
            dataset_context=dataset_context,
        )
        try:
            report_text = draft_report(
                question=question,
                report_payload=report_payload,
                revision_instruction=revision_instruction,
                model_id=model_id,
                default_model=default_model or self.default_model,
            )
        except Exception:
            report_text = _build_deterministic_report_text(
                question=question,
                report_payload=report_payload,
            )
        return {
            "status": "generated",
            "summary": report_text,
            "metrics": report_payload["metrics"],
            "visualizations": list(visualizations or []),
        }


def _build_deterministic_report_text(
    *,
    question: str,
    report_payload: Mapping[str, Any],
) -> str:
    analysis_payload = _as_dict(report_payload.get("analysis_result"))
    dataset_payload = _as_dict(report_payload.get("dataset_context"))
    metrics_payload = _as_dict(report_payload.get("metrics"))
    raw_metrics = _as_dict(metrics_payload.get("raw_metrics"))
    primary_metrics = _as_dict(metrics_payload.get("primary_metrics"))
    table_metrics = _as_dict(metrics_payload.get("table_metrics"))

    filename = str(dataset_payload.get("filename") or "선택 데이터셋")
    row_count = dataset_payload.get("row_count_total")
    column_count = dataset_payload.get("column_count")
    analysis_summary = str(analysis_payload.get("summary") or "").strip()
    purpose = str(question or "").strip() or "선택 데이터셋의 품질 현황을 요약합니다."

    metric_source = raw_metrics or primary_metrics
    metric_lines = _format_metric_lines(metric_source)
    table_lines = _format_table_preview(_as_list(table_metrics.get("preview_rows")))

    return "\n".join(
        [
            "# 품질 현황 리포트",
            "",
            "## 분석 목적",
            purpose,
            "",
            "## 데이터 개요",
            f"- 파일: {filename}",
            f"- 행 수: {row_count if row_count not in (None, '') else '확인 불가'}",
            f"- 컬럼 수: {column_count if column_count not in (None, '') else '확인 불가'}",
            "",
            "## 핵심 요약",
            f"- {analysis_summary or '계산된 분석 결과를 기준으로 품질 현황을 요약했습니다.'}",
            "",
            "## 주요 지표",
            *metric_lines,
            "",
            "## 분석 결과",
            *table_lines,
            "",
            "## 한계 및 주의사항",
            "- 이 리포트는 현재 계산된 분석 결과와 데이터셋 메타정보에 근거한 자동 요약입니다.",
            "",
            "## 권고사항",
            "- 제품, 불량 사유, 설비 등 기준 축을 지정하면 원인 후보를 더 좁힐 수 있습니다.",
        ]
    )
