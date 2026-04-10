from sqlalchemy.orm import Session

from .models import Report


class ReportRepository:
    """리포트 영속화/조회만 담당한다."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, report: Report) -> Report:
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report
