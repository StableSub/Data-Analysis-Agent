import os
import uuid
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from ..datasets.models import Dataset
from ..datasets.reader import DatasetReader
from ..datasets.repository import DataSourceRepository
from .processor import PreprocessProcessor
from .schemas import PreprocessApplyResponse, PreprocessOperation


class PreprocessService:
    """전처리 실행 흐름만 담당한다."""

    def __init__(
        self,
        *,
        repository: DataSourceRepository,
        reader: DatasetReader,
        processor: PreprocessProcessor,
    ) -> None:
        self.repository = repository
        self.reader = reader
        self.processor = processor

    def build_dataset_profile(self, source_id: str) -> Dict[str, Any]:
        if not source_id:
            return {"available": False}

        dataset = self.repository.get_by_source_id(source_id)
        if not dataset or not dataset.storage_path:
            return {"available": False}

        file_path = Path(dataset.storage_path)
        if not file_path.exists():
            return {"available": False}

        sample_df = self.reader.read_csv(dataset.storage_path, nrows=2000)
        numeric_cols = sample_df.select_dtypes(include="number").columns.tolist()
        datetime_cols = [
            col
            for col in sample_df.columns
            if (
                pd.to_datetime(sample_df[col], errors="coerce").notna().mean() >= 0.7
                and col not in numeric_cols
            )
        ]
        categorical_cols = [
            col
            for col in sample_df.columns
            if col not in numeric_cols and col not in datetime_cols
        ]
        sample_rows = sample_df.head(3)
        return {
            "available": True,
            "row_count": len(sample_df),
            "columns": sample_df.columns.tolist(),
            "dtypes": sample_df.dtypes.astype(str).to_dict(),
            "missing_rates": sample_df.isna().mean().round(3).to_dict(),
            "sample_values": sample_rows.where(
                sample_rows.notnull(),
                None,
            ).to_dict(orient="list"),
            "numeric_columns": [str(c) for c in numeric_cols],
            "datetime_columns": [str(c) for c in datetime_cols],
            "categorical_columns": [str(c) for c in categorical_cols],
        }

    def apply(
        self,
        source_id: str,
        operations: list[PreprocessOperation],
    ) -> PreprocessApplyResponse:
        input_dataset = self.repository.get_by_source_id(source_id)
        if not input_dataset:
            raise FileNotFoundError(f"Dataset not found: {source_id}")
        if not input_dataset.storage_path:
            raise FileNotFoundError("Dataset file path not found")

        df = self.reader.read_csv(input_dataset.storage_path)
        processed = self.processor.apply_operations(df, operations)
        output_path, output_filename = self._build_output_path(input_dataset.storage_path)
        processed.to_csv(output_path, index=False)
        output_size = os.path.getsize(output_path)

        output_dataset = self.repository.create(
            Dataset(
                filename=output_filename,
                storage_path=str(output_path),
                filesize=output_size,
            )
        )
        return PreprocessApplyResponse(
            input_source_id=source_id,
            output_source_id=output_dataset.source_id,
            output_filename=output_filename,
        )

    @staticmethod
    def _build_output_path(source_path: str) -> tuple[Path, str]:
        source = Path(source_path)
        output_filename = f"{source.stem}_preprocessed_{uuid.uuid4().hex[:8]}.csv"
        return source.with_name(output_filename), output_filename
