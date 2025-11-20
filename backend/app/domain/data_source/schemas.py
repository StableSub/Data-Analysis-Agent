from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class DatasetRead(BaseModel):
    """
    DB에 저장된 Dataset 한 건을 읽어올 때 사용하는 스키마.
    SELECT 결과를 반환할 때 사용.
    models.Dataset과 필드 이름/타입을 맞춤.
    """
    id: int
    filename: str
    storage_path: str
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    filesize: Optional[int] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    uploaded_at: datetime

    class Config: # SQLAlchemy 모델 객체를 그대로 응답으로 리턴할 수 있게 해주는 설정
        orm_mode = True


class DatasetUploadRequest(BaseModel):
    """
    파일 업로드 요청 시 함께 전달되는 옵션 정보 스키마(프론트 -> 벡엔드로 보내는 업로드 옵션 정보)
    실제 파일 내용은 FastAPI의 UploadFile로 받고,
    이 클래스는 업로드 옵션(메타 정보)만 JSON으로 받음.
    """
    encoding: Optional[str] = None
    delimiter: Optional[str] = None


class DatasetUploadResponse(BaseModel):
    """
    파일 업로드 성공 시, 프론트에 돌려주는 응답 스키마.
    - 업로드된 데이터셋의 기본 메타 정보
    """
    id: int
    filename: str
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    filesize: Optional[int] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    uploaded_at: datetime