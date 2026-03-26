import uuid
from pathlib import Path
from typing import IO, Any, Dict, List, Optional

import pandas as pd
from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from ..rag.dependencies import get_rag_service

from .models import Dataset
from .repository import DataSourceRepository


class DatasetUploadError(RuntimeError):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code


class DatasetStorage:
    """데이터셋 파일 저장/삭제만 담당한다."""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def persist_file(self, file_stream: IO[bytes], filename: str) -> tuple[Path, int]:
        if hasattr(file_stream, "seek"):
            file_stream.seek(0)

        target_path = self.storage_dir / f"{uuid.uuid4().hex}_{filename}"
        size = 0
        with open(target_path, "wb") as target:
            while True:
                chunk = file_stream.read(8192)
                if not chunk:
                    break
                size += len(chunk)
                target.write(chunk)
        return target_path, size

    def delete_file(self, storage_path: str) -> None:
        Path(storage_path).unlink()


class DatasetReader:
    """CSV 읽기 책임만 담당한다."""

    def read_csv(
        self,
        storage_path: str,
        *,
        nrows: Optional[int] = None,
        usecols: Optional[List[str]] = None,
        encoding: str = "utf-8",
    ) -> pd.DataFrame:
        file_path = Path(storage_path)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("파일이 존재하지 않습니다.")

        return pd.read_csv(
            file_path,
            encoding=encoding,
            sep=",",
            nrows=nrows,
            usecols=usecols,
        )


def _datasets_storage_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "storage" / "datasets"


def build_data_source_repository(db: Session) -> DataSourceRepository:
    return DataSourceRepository(db)


def get_data_source_repository(db: Session = Depends(get_db)) -> DataSourceRepository:
    return build_data_source_repository(db)


def build_dataset_storage() -> DatasetStorage:
    return DatasetStorage(_datasets_storage_dir())


def get_dataset_storage() -> DatasetStorage:
    return build_dataset_storage()


def build_dataset_reader() -> DatasetReader:
    return DatasetReader()


def get_dataset_reader() -> DatasetReader:
    return build_dataset_reader()


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


def build_data_source_service(
    *,
    repository: DataSourceRepository,
    storage: DatasetStorage,
    reader: DatasetReader,
    rag_service,
) -> DataSourceService:
    return DataSourceService(
        repository=repository,
        storage=storage,
        reader=reader,
        rag_service=rag_service,
    )


def get_data_source_service(
    repository: DataSourceRepository = Depends(get_data_source_repository),
    storage: DatasetStorage = Depends(get_dataset_storage),
    reader: DatasetReader = Depends(get_dataset_reader),
    rag_service=Depends(get_rag_service),
) -> DataSourceService:
    return build_data_source_service(
        repository=repository,
        storage=storage,
        reader=reader,
        rag_service=rag_service,
    )
