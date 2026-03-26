from typing import List, Optional

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

    def get(self, report_id: str) -> Optional[Report]:
        return self.db.query(Report).filter(Report.id == report_id).first()

    def list_by_session(self, session_id: int) -> List[Report]:
        return (
            self.db.query(Report)
            .filter(Report.session_id == session_id)
            .order_by(Report.id.asc())
            .all()
        )
