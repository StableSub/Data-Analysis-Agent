from typing import List, Optional

from sqlalchemy.orm import Session

from .models import Guideline


class GuidelineRepository:
    """지침서 영속화/조회/활성화/삭제를 담당하는 저장소 계층."""

    def __init__(self, db: Session):
        """SQLAlchemy 세션을 주입받아 저장소를 초기화한다."""
        self.db = db

    def create(self, guideline: Guideline) -> Guideline:
        """새 Guideline 레코드를 저장하고 DB 최신 상태를 반환한다."""
        self.db.add(guideline)
        self.db.commit()
        self.db.refresh(guideline)
        return guideline

    def list_all(self) -> List[Guideline]:
        """전체 지침서를 최신 생성 순(id 내림차순)으로 조회한다."""
        return self.db.query(Guideline).order_by(Guideline.id.desc()).all()

    def get_by_id(self, guideline_id: int) -> Optional[Guideline]:
        """내부 PK(id)로 지침서 1건을 조회한다."""
        return self.db.query(Guideline).filter(Guideline.id == guideline_id).first()

    def get_by_source_id(self, source_id: str) -> Optional[Guideline]:
        """외부 노출 식별자(source_id)로 지침서 1건을 조회한다."""
        return self.db.query(Guideline).filter(Guideline.source_id == source_id).first()

    def get_active(self) -> Optional[Guideline]:
        """현재 활성화된 지침서 1건을 조회한다."""
        return self.db.query(Guideline).filter(Guideline.is_active.is_(True)).first()

    def get_latest_version(self, filename: str) -> Optional[Guideline]:
        """같은 파일명 기준 최신 버전의 지침서를 조회한다."""
        return (
            self.db.query(Guideline)
            .filter(Guideline.filename == filename)
            .order_by(Guideline.version.desc(), Guideline.id.desc())
            .first()
        )

    def deactivate_all(self) -> None:
        """모든 활성 지침서를 비활성화한다."""
        self.db.query(Guideline).filter(Guideline.is_active.is_(True)).update(
            {Guideline.is_active: False},
            synchronize_session=False,
        )
        self.db.commit()

    def save(self, guideline: Guideline) -> Guideline:
        """수정된 Guideline 레코드를 커밋하고 최신 상태를 반환한다."""
        self.db.add(guideline)
        self.db.commit()
        self.db.refresh(guideline)
        return guideline

    def activate(self, guideline: Guideline) -> Guideline:
        """전달된 지침서만 활성화 상태로 전환한다."""
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
        """전달받은 Guideline 레코드를 DB에서 삭제한다."""
        self.db.delete(guideline)
        self.db.commit()
