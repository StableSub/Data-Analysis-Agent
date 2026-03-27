from pathlib import Path
from typing import Any, Dict

import pandas as pd

from ..datasets.repository import DatasetRepository
from ..datasets.service import DatasetReader


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
    """워크플로우용 시각화 데이터 조회를 담당한다."""

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
