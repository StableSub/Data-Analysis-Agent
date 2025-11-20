from pathlib import Path
from typing import IO, Optional, Tuple
import uuid

from .models import Dataset
from .repository import DataSourceRepository


class DataSourceService:
    def __init__(self, repository: DataSourceRepository, storage_dir: Path) -> None:
        self.repository = repository
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True) # 업로드 디렉토리가 없으면 생성

    def _persist_file(self, file_stream: IO[bytes], filename: str) -> Tuple[Path, int]:
        """
        업로드된 파일 스트림을 storage_dir 아래에 저장하고, 최종 파일 크기를 반환
        """
        # 스트림 위치를 항상 처음으로 돌려놓기
        if hasattr(file_stream, "seek"):
            file_stream.seek(0)

        # 파일 이름 중복 방지
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        target_path = self.storage_dir / unique_name
        
        size = 0
        with open(target_path, "wb") as target:
            while chunk := file_stream.read(8192):  # 8192 bytes씩 읽기
                size += len(chunk)
                target.write(chunk)
    
        return target_path, size

    def upload_dataset(
        self,
        *,
        file_stream: IO[bytes],
        original_filename: str,
        display_name: Optional[str] = None,
        encoding: Optional[str] = None,
        delimiter: Optional[str] = None,
    ) -> Dataset:
        """
        업로드된 파일을 저장하고, Dataset 객체를 생성하여 DB에 저장
        """
        # 파일 저장 + 파일 크기 계산
        storage_path, size = self._persist_file(file_stream, original_filename)

        # Dataset ORM 객체 생성
        dataset = Dataset(
            filename=display_name or original_filename,
            storage_path=str(storage_path),
            encoding=encoding,
            delimiter=delimiter,
            filesize=size,
            extra_metadata=None,
        )
        return self.repository.create(dataset)