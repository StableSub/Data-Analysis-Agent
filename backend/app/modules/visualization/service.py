from pathlib import Path
from typing import Any, Dict

import pandas as pd

from ..datasets.repository import DatasetRepository
from ..datasets.service import DatasetReader
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
        {
            str(column): _serialize_preview_value(value)
            for column, value in row.items()
        }
        for row in sample.to_dict(orient="records")
    ]


class VisualizationService:
    """수동 시각화용 데이터 추출을 담당한다."""

    def __init__(
        self,
        *,
        repository: DatasetRepository,
        reader: DatasetReader,
    ) -> None:
        self.repository = repository
        self.reader = reader

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
