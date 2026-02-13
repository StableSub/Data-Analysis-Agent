from typing import List, Optional

from sqlalchemy.orm import Session

from .models import Dataset


class DataSourceRepository:
    """데이터셋 영속화/조회/삭제를 담당하는 저장소 계층."""

    def __init__(self, db: Session):
        """SQLAlchemy 세션을 주입받아 저장소를 초기화한다."""
        self.db = db

    def create(self, dataset: Dataset) -> Dataset:
        """새 Dataset 레코드를 저장하고 DB 최신 상태를 반환한다."""
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def list_all(self) -> List[Dataset]:
        """전체 데이터셋을 최신 생성 순(id 내림차순)으로 조회한다."""
        return self.db.query(Dataset).order_by(Dataset.id.desc()).all()

    def get_by_id(self, dataset_id: int) -> Optional[Dataset]:
        """내부 PK(id)로 데이터셋 1건을 조회한다."""
        return self.db.query(Dataset).filter(Dataset.id == dataset_id).first()

    def get_by_source_id(self, source_id: str) -> Optional[Dataset]:
        """외부 노출 식별자(source_id)로 데이터셋 1건을 조회한다."""
        return self.db.query(Dataset).filter(Dataset.source_id == source_id).first()

    def delete(self, dataset: Dataset) -> None:
        """전달받은 Dataset 레코드를 DB에서 삭제한다."""
        self.db.delete(dataset)
        self.db.commit()
