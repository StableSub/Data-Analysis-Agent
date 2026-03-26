from typing import List, Optional

from sqlalchemy.orm import Session

from .models import Guideline


class GuidelineRepository:
    """지침서 영속화/조회/활성화/삭제를 담당하는 저장소 계층."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, guideline: Guideline) -> Guideline:
        self.db.add(guideline)
        self.db.commit()
        self.db.refresh(guideline)
        return guideline

    def list_all(self) -> List[Guideline]:
        return self.db.query(Guideline).order_by(Guideline.id.desc()).all()

    def get_by_source_id(self, source_id: str) -> Optional[Guideline]:
        return self.db.query(Guideline).filter(Guideline.source_id == source_id).first()

    def get_active(self) -> Optional[Guideline]:
        return self.db.query(Guideline).filter(Guideline.is_active.is_(True)).first()

    def get_latest_version(self, filename: str) -> Optional[Guideline]:
        return (
            self.db.query(Guideline)
            .filter(Guideline.filename == filename)
            .order_by(Guideline.version.desc(), Guideline.id.desc())
            .first()
        )

    def activate(self, guideline: Guideline) -> Guideline:
        self.db.query(Guideline).filter(Guideline.is_active.is_(True)).update(
            {Guideline.is_active: False},
            synchronize_session=False,
        )
        guideline.is_active = True
        self.db.add(guideline)
        self.db.commit()
        self.db.refresh(guideline)
        return guideline

    def delete(self, guideline: Guideline) -> None:
        self.db.delete(guideline)
        self.db.commit()
