from pathlib import Path
from typing import Any, Dict

import pandas as pd

from ..analysis.schemas import AnalysisExecutionResult, AnalysisPlan
from ..datasets.repository import DataSourceRepository
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
    """수동 시각화와 analysis 결과 기반 시각화용 데이터를 처리한다."""

    def __init__(
        self,
        *,
        repository: DataSourceRepository,
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

    def load_sample_frame(self, source_id: str, *, nrows: int) -> pd.DataFrame | None:
        file_path = self.resolve_source_path(source_id)
        if file_path is None:
            return None
        return self.reader.read_csv(str(file_path), nrows=nrows)

    def build_preview_rows(
        self,
        *,
        source_id: str,
        x_key: str,
        y_key: str,
        limit: int = 5,
    ) -> list[Dict[str, Any]]:
        df = self.load_sample_frame(source_id, nrows=limit)
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
        except ValueError as exc:
            return {"error": "INVALID_COLUMN", "message": str(exc)}
        except Exception as exc:
            return {"error": "INTERNAL_ERROR", "message": f"데이터 처리 중 오류: {exc}"}

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
        analysis_plan: AnalysisPlan,
        analysis_result: AnalysisExecutionResult,
    ) -> Dict[str, Any]:
        output = self.processor.build_from_analysis_result(
            analysis_plan=analysis_plan,
            analysis_result=analysis_result,
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
            return f"analysis 결과를 바탕으로 {chart_type} 시각화를 생성했습니다."
        if status == "fallback":
            row_count = len(fallback_table or [])
            return f"차트 대신 결과 표를 반환합니다. rows={row_count}"
        return "analysis 결과에서 시각화 가능한 차트를 만들지 못했습니다."
