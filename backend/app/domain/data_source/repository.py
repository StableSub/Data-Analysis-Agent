from typing import List, Optional
from sqlalchemy.orm import Session
from .models import Dataset

class DataSourceRepository:
    """
    Dataset 테이블에 대해 DB에 직접 접근
    DB 읽기 및 쓰기만 담당
    """
    def __init__(self, db: Session):
        self.db = db

    def create(self, dataset: Dataset) -> Dataset:
        """
        Dataset ORM 객체를 DB에 저장(create)
        refresh: commit 후 DB에서 최신 값을 다시 로드
        """
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def list_all(self) -> List[Dataset]:
        """
        모든 Dataset 목록 조회
        업로드 시각(uploaded_at) 순으로 최신순 정렬
        """
        return self.db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()
    

    def list_by_workspace(self, workspace_id: str) -> List[Dataset]:
        """
        특정 workspace_id에 해당하는 Dataset 목록 조회
        """
        return (
            self.db.query(Dataset)
            .filter(Dataset.workspace_id == workspace_id)
            .order_by(Dataset.uploaded_at.desc())
            .all()
        )
    
    def get_by_id(self, dataset_id: int) -> Optional[Dataset]:
        """
        내부 ID 기준으로 Dataset 조회
        """
        return self.db.query(Dataset).filter(Dataset.id == dataset_id).first()

    def get_by_source_id(self, source_id: str) -> Optional[Dataset]:
        """
        외부 공개용 source_id 기준 조회
        """
        return (
            self.db.query(Dataset)
            .filter(Dataset.source_id == source_id)
            .first()
        )

    def delete(self, dataset: Dataset) -> None:
        """
        주어진 Dataset ORM 객체 삭제
        이미 get() 등을 통해 가져온 ORM 객체를 받아 삭제하는 방식
        """
        self.db.delete(dataset)
        self.db.commit()

