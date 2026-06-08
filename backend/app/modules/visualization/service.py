from pathlib import Path
from typing import Any, Dict

import pandas as pd

from ...orchestration.error_contract import public_message_for_stage
from ..analysis.schemas import AnalysisExecutionResult, AnalysisPlan
from ..datasets.repository import DatasetRepository
from ..datasets.service import DatasetReader
from .processor import VisualizationProcessor
from .schemas import ManualVizRequest


def _serialize_preview_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _build_preview_rows(
    *,
    df: pd.DataFrame,
    x_key: str,
    y_key: str,
    limit: int = 5,
) -> list[Dict[str, Any]]:
    preview_columns = [column for column in [x_key, y_key] if column]
    if not preview_columns:
        return []
    sample = df[preview_columns].head(limit).copy()
    return [
        {str(column): _serialize_preview_value(value) for column, value in row.items()}
        for row in sample.to_dict(orient="records")
    ]


class VisualizationService:
    """워크플로우와 API용 시각화 데이터 처리를 담당한다."""

    def __init__(
        self,
        *,
        repository: DatasetRepository,
        reader: DatasetReader,
        processor: VisualizationProcessor | None = None,
    ) -> None:
        self.repository = repository
        self.reader = reader
        self.processor = processor or VisualizationProcessor()

    def resolve_source_path(self, source_id: str) -> Path | None:
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset or not dataset.storage_path:
            return None
        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return None
        return file_path

    def load_sample_frame(self, source_id: str, *, nrows: int) -> tuple[pd.DataFrame | None, str]:
        file_path = self.resolve_source_path(source_id)
        if file_path is None:
            return None, "dataset_missing"
        if file_path.suffix.lower() != ".csv":
            return None, "unsupported_format"
        try:
            return self.reader.read_csv(str(file_path), nrows=nrows), "available"
        except Exception:
            return None, "read_error"

    def build_preview_rows(
        self,
        *,
        source_id: str,
        x_key: str,
        y_key: str,
        limit: int = 5,
    ) -> list[Dict[str, Any]]:
        df, _ = self.load_sample_frame(source_id, nrows=limit)
        if df is None or df.empty:
            return []
        return _build_preview_rows(df=df, x_key=x_key, y_key=y_key, limit=limit)

    def get_manual_viz_data(self, request: ManualVizRequest) -> Dict[str, Any]:
        dataset = self.repository.get_by_source_id(request.source_id)
        if not dataset:
            return {"error": "NOT_FOUND", "message": "데이터셋을 찾을 수 없습니다."}

        requested_cols = [request.columns.x, request.columns.y]
        if request.columns.color:
            requested_cols.append(request.columns.color)
        if request.columns.group:
            requested_cols.append(request.columns.group)
        requested_cols = list(dict.fromkeys(requested_cols))

        try:
            df = self.reader.read_csv(
                dataset.storage_path,
                nrows=request.limit,
                usecols=requested_cols,
            )
        except FileNotFoundError:
            return {"error": "FILE_NOT_FOUND", "message": "파일이 존재하지 않습니다."}
        except ValueError:
            return {"error": "INVALID_COLUMN", "message": "요청한 시각화 컬럼이 올바르지 않습니다."}
        except Exception:
            return {"error": "INTERNAL_ERROR", "message": public_message_for_stage("visualization")}

        if df.empty:
            return {"error": "NO_DATA", "message": "조회된 데이터가 없습니다."}

        return {
            "chart_type": request.chart_type,
            "data": df.where(pd.notnull(df), None).to_dict(orient="records"),
        }

    def build_from_analysis_result(
        self,
        *,
        source_id: str,
        analysis_plan: AnalysisPlan | Dict[str, Any],
        analysis_result: AnalysisExecutionResult | Dict[str, Any],
    ) -> Dict[str, Any]:
        resolved_plan = (
            analysis_plan
            if isinstance(analysis_plan, AnalysisPlan)
            else AnalysisPlan.model_validate(analysis_plan)
        )
        resolved_result = (
            analysis_result
            if isinstance(analysis_result, AnalysisExecutionResult)
            else AnalysisExecutionResult.model_validate(analysis_result)
        )
        output = self.processor.build_from_analysis_result(
            analysis_plan=resolved_plan,
            analysis_result=resolved_result,
        )

        chart_data = (
            output.chart_data.model_dump() if output.chart_data is not None else None
        )
        fallback_table = output.fallback_table
        chart_summary = self._build_chart_summary(
            status=output.status,
            chart_data=chart_data,
            fallback_table=fallback_table,
        )

        return {
            "status": output.status,
            "source_id": source_id,
            "summary": chart_summary,
            "chart": chart_data,
            "chart_data": chart_data,
            "charts": [chart_data] if chart_data is not None else [],
            "fallback_table": fallback_table,
        }

    def _build_chart_summary(
        self,
        *,
        status: str,
        chart_data: Dict[str, Any] | None,
        fallback_table: list[Dict[str, Any]] | None,
    ) -> str:
        if status == "generated" and chart_data:
            chart_type = chart_data.get("chart_type") or "chart"
            x_values = chart_data.get("x")
            series_raw = chart_data.get("series")
            series_names = [
                str(item.get("name") or "").strip()
                for item in series_raw
                if isinstance(item, dict) and str(item.get("name") or "").strip()
            ] if isinstance(series_raw, list) else []
            y_label = ", ".join(series_names) if series_names else "값"
            x_label = _infer_x_axis_label(series_names)
            point_count = len(x_values) if isinstance(x_values, list) else 0
            return (
                f"{chart_type} 시각화입니다. x축은 {x_label} 범주를, y값은 {y_label}을 "
                f"나타냅니다. {point_count}개 항목을 비교해 큰 차이가 나는 구간을 "
                "보면 분석 결과를 빠르게 읽을 수 있습니다."
            )
        if status == "fallback":
            row_count = len(fallback_table or [])
            return (
                f"차트 대신 결과 표를 반환합니다. 표의 {row_count}개 행을 기준으로 "
                "값이 큰 항목과 작은 항목을 비교해 보세요."
            )
        return "analysis 결과에서 시각화 가능한 차트를 만들지 못했습니다. 표 결과를 먼저 확인해 주세요."


def _infer_x_axis_label(series_names: list[str]) -> str:
    for name in series_names:
        if name.endswith("_count") and len(name) > len("_count"):
            return name[: -len("_count")]
    return "분석 기준"
