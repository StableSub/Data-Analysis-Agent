import uuid
from pathlib import Path
from typing import IO, Any, Dict, List, Optional, Tuple

from .models import Guideline
from .repository import GuidelineRepository


class GuidelineService:
    """지침서 파일 저장/조회/활성화/삭제를 담당한다."""

    def __init__(self, repository: GuidelineRepository, storage_dir: Path) -> None:
        """저장소와 파일 저장 경로를 초기화하고, 저장 디렉터리를 보장한다."""
        self.repository = repository
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _persist_file(self, file_stream: IO[bytes], filename: str) -> Tuple[Path, int]:
        """업로드 파일 스트림을 디스크에 저장하고 (경로, 파일 크기)를 반환한다."""
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

    def upload_guideline(
        self,
        *,
        file_stream: IO[bytes],
        original_filename: str,
        display_name: Optional[str] = None,
    ) -> Guideline:
        """파일을 저장한 뒤 Guideline 메타데이터를 생성해 DB에 저장한다."""
        storage_path, size = self._persist_file(file_stream, original_filename)
        latest = self.repository.get_latest_version(display_name or original_filename)
        next_version = (latest.version + 1) if latest else 1

        guideline = Guideline(
            filename=display_name or original_filename,
            storage_path=str(storage_path),
            filesize=size,
            version=next_version,
            is_active=False,
        )
        return self.repository.create(guideline)

    def list_guidelines(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Guideline]:
        """지침서 목록을 조회하고 skip/limit으로 단순 페이지네이션한다."""
        guidelines = self.repository.list_all()
        end = skip + limit if limit is not None else None
        return guidelines[skip:end]

    def get_guideline_detail(self, guideline_id: int) -> Optional[Dict[str, Guideline]]:
        """guideline_id로 단건 상세를 조회해 API 응답 형태(dict)로 반환한다."""
        guideline = self.repository.get_by_id(guideline_id)
        if not guideline:
            return None
        return {"guideline": guideline}

    def get_active_guideline(self) -> Optional[Guideline]:
        """현재 활성화된 지침서를 반환한다."""
        return self.repository.get_active()

    def activate_guideline(self, source_id: str) -> Dict[str, Any]:
        """source_id 기준으로 지침서를 활성화하고 기존 active는 해제한다."""
        guideline = self.repository.get_by_source_id(source_id)
        if not guideline:
            return {
                "success": False,
                "message": "지침서를 찾을 수 없습니다.",
            }

        activated = self.repository.activate(guideline)
        return {
            "success": True,
            "guideline": activated,
            "message": "지침서가 활성화되었습니다.",
        }

    def delete_guideline(self, source_id: str) -> Dict[str, Any]:
        """source_id 기준으로 실제 파일과 DB 메타데이터를 함께 삭제한다."""
        guideline = self.repository.get_by_source_id(source_id)
        if not guideline:
            return {
                "success": False,
                "deleted_file": None,
                "message": "지침서를 찾을 수 없습니다.",
            }

        deleted_info = {
            "source_id": guideline.source_id,
            "guideline_id": guideline.guideline_id,
            "filename": guideline.filename,
            "storage_path": guideline.storage_path,
            "is_active": guideline.is_active,
        }

        file_path = Path(guideline.storage_path)
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            raise

        self.repository.delete(guideline)
        return {
            "success": True,
            "deleted_file": deleted_info,
            "message": "지침서가 성공적으로 삭제되었습니다.",
        }
