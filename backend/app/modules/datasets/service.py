import uuid
from pathlib import Path
from typing import IO, Any, Iterator, List, Optional

import pandas as pd

from .models import Dataset
from .repository import DatasetRepository

ALLOWED_DATASET_EXTENSIONS = {".csv"}
DATASET_READ_ERROR_DETAIL = "데이터셋을 읽을 수 없습니다. UTF-8 CSV인지 확인해 주세요."
UTF8_CSV_UPLOAD_ERROR_DETAIL = "UTF-8 CSV만 업로드할 수 있습니다."


class DatasetReadError(Exception):
    """Raised when a stored dataset cannot be read as a UTF-8 CSV."""


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

    @staticmethod
    def _resolve_file(storage_path: str) -> Path:
        file_path = Path(storage_path)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("파일이 존재하지 않습니다.")
        return file_path

    def read_csv(
        self,
        storage_path: str,
        *,
        nrows: Optional[int] = None,
        usecols: Optional[List[str]] = None,
        encoding: str = "utf-8",
    ) -> pd.DataFrame:
        file_path = self._resolve_file(storage_path)
        try:
            return pd.read_csv(
                file_path,
                encoding=encoding,
                sep=",",
                nrows=nrows,
                usecols=usecols,
            )
        except (UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
            raise DatasetReadError(DATASET_READ_ERROR_DETAIL) from exc

    def read_csv_chunks(
        self,
        storage_path: str,
        *,
        chunksize: int,
        usecols: Optional[List[str]] = None,
        encoding: str = "utf-8",
    ) -> Iterator[pd.DataFrame]:
        file_path = self._resolve_file(storage_path)
        try:
            reader = pd.read_csv(
                file_path,
                encoding=encoding,
                sep=",",
                chunksize=chunksize,
                usecols=usecols,
            )
        except (UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
            raise DatasetReadError(DATASET_READ_ERROR_DETAIL) from exc

        def iterator() -> Iterator[pd.DataFrame]:
            try:
                for chunk in reader:
                    yield chunk
            except (UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
                raise DatasetReadError(DATASET_READ_ERROR_DETAIL) from exc

        return iterator()

class DatasetService:
    """데이터셋 흐름만 담당한다."""

    def __init__(
        self,
        *,
        repository: DatasetRepository,
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
        if Path(original_filename).suffix.lower() not in ALLOWED_DATASET_EXTENSIONS:
            raise ValueError("CSV 파일만 업로드할 수 있습니다.")

        storage_path, size = self.storage.persist_file(file_stream, original_filename)
        try:
            self.reader.read_csv(str(storage_path), nrows=5)
        except DatasetReadError as exc:
            try:
                self.storage.delete_file(str(storage_path))
            except FileNotFoundError:
                pass
            raise ValueError(UTF8_CSV_UPLOAD_ERROR_DETAIL) from exc

        dataset = Dataset(
            filename=display_name or original_filename,
            storage_path=str(storage_path),
            filesize=size,
        )
        return self.repository.create(dataset)

    def list_datasets(self, skip: int = 0, limit: int = 20) -> tuple[List[Dataset], int]:
        items = self.repository.list_page(skip=skip, limit=limit)
        total = self.repository.count_all()
        return items, total

    def get_dataset_detail(self, source_id: str) -> Optional[Dataset]:
        return self.repository.get_by_source_id(source_id)

    def delete_dataset(self, source_id: str) -> bool:
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset:
            return False

        try:
            self.storage.delete_file(dataset.storage_path)
        except FileNotFoundError:
            pass

        self.repository.delete(dataset)
        return True

    def get_dataset_sample(self, source_id: str, n_rows: int = 5) -> Optional[dict[str, Any]]:
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset:
            return None

        df = self.reader.read_csv(dataset.storage_path, nrows=n_rows)

        return {
            "source_id": source_id,
            "columns": df.columns.tolist(),
            "rows": df.where(pd.notnull(df), None).to_dict(orient="records"),
        }
