from typing import Any

from sqlalchemy.orm import Session

from .models import AnalysisResult


class ResultsRepository:
    """저장된 분석 결과 조회만 담당한다."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_analysis_result_data(self, result_id: str) -> Any | None:
        result = self.db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()
        if result is None:
            return None
        return result.data_json
