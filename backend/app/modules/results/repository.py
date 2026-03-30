import uuid
from typing import Any

from sqlalchemy.orm import Session

from .models import AnalysisResult


class ResultsRepository:
    """저장된 분석 결과 조회만 담당한다."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_analysis_result(
        self,
        *,
        question: str | None = None,
        source_id: str | None = None,
        session_id: str | None = None,
        analysis_plan: Any | None = None,
        generated_code: str | None = None,
        execution_result: Any | None = None,
    ) -> AnalysisResult:
        plan_json = self._model_dump(analysis_plan)
        result_json = self._build_result_json(execution_result)
        table_json = self._extract_attr(execution_result, "table", default=[])
        used_columns = self._extract_attr(execution_result, "used_columns", default=[])
        execution_status = self._extract_attr(execution_result, "execution_status")
        error_stage = self._extract_attr(execution_result, "error_stage")
        error_message = self._extract_attr(execution_result, "error_message")

        result = AnalysisResult(
            id=str(uuid.uuid4()),
            data_json=table_json or result_json,
            analysis_plan_json=plan_json,
            generated_code=generated_code,
            used_columns=used_columns,
            result_json=result_json,
            table=table_json,
            chart_data=None,
            execution_status=execution_status,
            error_stage=error_stage,
            error_message=error_message,
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def get_analysis_result_data(self, result_id: str) -> Any | None:
        result = self.db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()
        if result is None:
            return None
        if result.table is not None:
            return result.table
        if result.data_json is not None:
            return result.data_json
        return result.result_json

    def get_analysis_result(self, result_id: str) -> AnalysisResult | None:
        return self.db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()

    def update_chart_data(self, result_id: str, chart_data: Any) -> AnalysisResult | None:
        result = self.get_analysis_result(result_id)
        if result is None:
            return None
        result.chart_data = chart_data
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def _extract_attr(self, value: Any, key: str, default: Any = None) -> Any:
        if value is None:
            return default
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)

    def _model_dump(self, value: Any) -> Any:
        if value is None:
            return None
        dump_method = getattr(value, "model_dump", None)
        if callable(dump_method):
            return dump_method()
        return value

    def _build_result_json(self, execution_result: Any) -> dict[str, Any] | None:
        if execution_result is None:
            return None
        summary = self._extract_attr(execution_result, "summary")
        raw_metrics = self._extract_attr(execution_result, "raw_metrics", default={})
        if summary is None and raw_metrics in (None, {}):
            return None
        return {
            "summary": summary,
            "raw_metrics": raw_metrics or {},
        }
