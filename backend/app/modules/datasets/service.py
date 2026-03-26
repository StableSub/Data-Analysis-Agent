import uuid
from pathlib import Path
from typing import IO, Any, Dict, List, Optional

import pandas as pd

from .models import Dataset
from .repository import DataSourceRepository


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

class DataSourceService:
    """데이터셋 흐름만 담당한다."""

    def __init__(
        self,
        *,
        repository: DataSourceRepository,
        storage: DatasetStorage,
        reader: DatasetReader,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.reader = reader

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
