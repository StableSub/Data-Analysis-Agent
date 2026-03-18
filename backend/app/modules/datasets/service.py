from pathlib import Path
from typing import IO, Any, Dict, List, Optional

import pandas as pd

from .models import Dataset
from .reader import DatasetReader
from .repository import DataSourceRepository
from .storage import DatasetStorage
from .errors import DatasetUploadError


class DataSourceService:
    """데이터셋 흐름만 담당한다."""

    def __init__(
        self,
        *,
        repository: DataSourceRepository,
        storage: DatasetStorage,
        reader: DatasetReader,
        rag_service: Any | None = None,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.reader = reader
        self.rag_service = rag_service

    def upload_dataset(
        self,
        *,
        file_stream: IO[bytes],
        original_filename: str,
        display_name: Optional[str] = None,
    ) -> Dataset:
        storage_path, size = self.storage.persist_file(file_stream, original_filename)
        dataset = Dataset(
            filename=display_name or original_filename,
            storage_path=str(storage_path),
            filesize=size,
        )
        dataset = self.repository.create(dataset)
        if self.rag_service is not None:
            try:
                self.rag_service.index_dataset(dataset)
            except Exception as exc:
                if getattr(exc, "code", "") == "EMBEDDING_ERROR":
                    raise DatasetUploadError("EMBEDDING_ERROR") from exc
                raise
        return dataset

    def list_datasets(self, skip: int = 0, limit: int = 20) -> List[Dataset]:
        datasets = self.repository.list_all()
        end = skip + limit if limit is not None else None
        return datasets[skip:end]

    def get_dataset_detail(self, dataset_id: int) -> Optional[Dict[str, Dataset]]:
        dataset = self.repository.get_by_id(dataset_id)
        if not dataset:
            return None
        return {"dataset": dataset}

    def get_dataset_by_source_id(self, source_id: str) -> Optional[Dataset]:
        return self.repository.get_by_source_id(source_id)

    def delete_dataset(self, source_id: str) -> Dict[str, Any]:
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset:
            return {
                "success": False,
                "deleted_file": None,
                "message": "데이터셋을 찾을 수 없습니다.",
            }

        deleted_info = {
            "source_id": dataset.source_id,
            "filename": dataset.filename,
            "storage_path": dataset.storage_path,
        }

        try:
            self.storage.delete_file(dataset.storage_path)
        except FileNotFoundError:
            pass

        self.repository.delete(dataset)

        if self.rag_service is not None:
            try:
                self.rag_service.delete_source(source_id)
            except Exception:
                pass

        return {
            "success": True,
            "deleted_file": deleted_info,
            "message": "데이터셋이 성공적으로 삭제되었습니다.",
        }

    def get_dataset_sample(self, source_id: str, n_rows: int = 5) -> Optional[Dict[str, Any]]:
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset:
            return None

        try:
            df = self.reader.read_csv(dataset.storage_path, nrows=n_rows)
        except Exception:
            return None

        return {
            "source_id": source_id,
            "columns": df.columns.tolist(),
            "rows": df.where(pd.notnull(df), None).to_dict(orient="records"),
        }
