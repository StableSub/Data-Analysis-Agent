from pathlib import Path
from typing import IO, Optional, Tuple

from .models import Dataset
from .repository import DataSourceRepository
from ...data_eng.encoding_detector import EncodingDetector


class DataSourceService:
    """Business logic for dataset ingestion and management."""

    def __init__(
        self,
        repository: DataSourceRepository,
        storage_dir: Path,
        detector: Optional[EncodingDetector] = None,
    ) -> None:
        self.repository = repository
        self.storage_dir = storage_dir
        self.detector = detector or EncodingDetector()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _persist_file(self, file_stream: IO[bytes], filename: str) -> Tuple[Path, int]:
        target_path = self.storage_dir / filename
        size = 0
        with open(target_path, "wb") as target:
            while chunk := file_stream.read(8192):
                size += len(chunk)
                target.write(chunk)
        return target_path, size

    def upload_dataset(
        self,
        *,
        file_stream: IO[bytes],
        display_name: str,
        original_filename: str,
    ) -> Dataset:
        encoding, delimiter = self.detector.detect(file_stream, original_filename)
        file_stream.seek(0)
        storage_path, size = self._persist_file(file_stream, original_filename)

        dataset = Dataset(
            name=display_name,
            original_filename=original_filename,
            storage_path=str(storage_path),
            encoding=encoding,
            delimiter=delimiter,
            size_bytes=size,
        )
        return self.repository.create(dataset)

    def list_datasets(self):
        return self.repository.list()

    def delete_dataset(self, dataset_id: int) -> bool:
        dataset = self.repository.get(dataset_id)
        if not dataset:
            return False
        path = Path(dataset.storage_path)
        if path.exists():
            path.unlink()
        self.repository.delete(dataset)
        return True
