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

    def list(self) -> List[Dataset]:
        """
        모든 Dataset 목록 조회
        업로드 시각(uploaded_at) 순으로 최신순 정렬
        """
        return self.db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()

    def get(self, dataset_id: int) -> Optional[Dataset]:
        """
        특정 Dataset 한 건 조회(존재하지 않으면 None 반환)
        """
        return self.db.query(Dataset).filter(Dataset.id == dataset_id).first()

    def delete(self, dataset: Dataset) -> None:
        """
        주어진 Dataset ORM 객체 삭제
        이미 get() 등을 통해 가져온 ORM 객체를 받아 삭제하는 방식
        """
        self.db.delete(dataset)
        self.db.commit()
