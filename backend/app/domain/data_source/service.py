from pathlib import Path
from typing import IO, Optional, Tuple, List
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
        workspace_id: Optional[str] = None,
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
            workspace_id=workspace_id,
        )
        return self.repository.create(dataset)
    
    def list_datasets(
        self,
        workspace_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dataset]:
        """
        워크스페이스 단위 데이터 소스 목록 조회
        - workspace_id 가 주어지면 해당 워크스페이스 기준으로 필터링
        - 없으면 전체 데이터셋 기준
        - skip / limit 로 간단한 페이지네이션 처리
        """
        if workspace_id:
            datasets = self.repository.list_by_workspace(workspace_id)
        else:
            datasets = self.repository.list_all()

        # 간단한 슬라이싱 기반 페이지네이션
        end = skip + limit if limit is not None else None
        return datasets[skip:end]
    

    def get_dataset_detail(self, dataset_id: int) -> Optional[dict]:
        """
        단일 데이터 소스 상세 정보 반환.
        """
        dataset = self.repository.get_by_id(dataset_id)
        if not dataset:
            return None

        return {
            "dataset": dataset,
        }
        
        