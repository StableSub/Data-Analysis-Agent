import json
from pathlib import Path
from typing import Any, Dict, List

from ..datasets.reader import DatasetReader
from ..datasets.repository import DataSourceRepository
from .ai import generate_summary_from_payload
from .metrics import build_dataset_metrics, build_report_payload
from .models import Report
from .repository import ReportRepository


class ReportService:
    """리포트 persistence와 direct 생성 흐름을 담당한다."""

    def __init__(
        self,
        repository: ReportRepository,
        *,
        dataset_repository: DataSourceRepository | None = None,
        reader: DatasetReader | None = None,
        agent: Any | None = None,
        default_model: str = "gpt-5-nano",
    ) -> None:
        self.repository = repository
        self.dataset_repository = dataset_repository
        self.reader = reader
        self.agent = agent
        self.default_model = default_model

    async def create_report(self, *, session_id: int, summary_text: str) -> Report:
        return self.repository.create(
            Report(
                session_id=session_id,
                summary_text=summary_text,
            )
        )

    def get_report(self, report_id: str) -> Report:
        report = self.repository.get(report_id)
        if not report:
            raise LookupError("REPORT_NOT_FOUND")
        return report

    def list_reports(self, session_id: int) -> List[Report]:
        return self.repository.list_by_session(session_id)

    def build_metrics_for_source(self, source_id: str) -> Dict[str, Any]:
        empty_metrics: Dict[str, Any] = {
            "source_id": source_id,
            "row_count": 0,
            "column_count": 0,
            "missing": {
                "missing_cells": 0,
                "total_cells": 0,
                "missing_rate": 0.0,
                "top_missing_columns": [],
            },
            "numeric_stats": [],
            "top_correlations": [],
        }
        if not source_id or self.dataset_repository is None or self.reader is None:
            return empty_metrics

        dataset = self.dataset_repository.get_by_source_id(source_id)
        if dataset is None or not dataset.storage_path:
            return empty_metrics

        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return empty_metrics

        df = self.reader.read_csv(dataset.storage_path, nrows=5000)
        if df.empty:
            return empty_metrics
        return build_dataset_metrics(df=df, source_id=source_id)

    async def generate_summary(
        self,
        *,
        analysis_results: List[Dict[str, Any]],
        visualizations: List[Dict[str, Any]],
        insights: List[Any],
    ) -> str:
        if not analysis_results and not visualizations and not insights:
            raise LookupError("NO_RESULTS")
        if self.agent is None:
            raise RuntimeError("GENERATION_ERROR")

        payload = build_report_payload(
            analysis_results=analysis_results,
            visualizations=visualizations,
            insights=insights,
        )

        if self.agent is not None:
            question = "다음 분석 결과를 간결하게 요약해 리포트를 작성해줘."
            context = json.dumps(payload, ensure_ascii=False)
            try:
                answer_parts: list[str] = []
                final_answer: str | None = None
                async for event in self.agent.astream_with_trace(question=question, context=context):
                    event_type = event.get("type")
                    if event_type == "chunk":
                        delta = event.get("delta")
                        if isinstance(delta, str) and delta:
                            answer_parts.append(delta)
                    elif event_type == "done":
                        done_answer = event.get("answer")
                        if isinstance(done_answer, str):
                            final_answer = done_answer
                return final_answer if final_answer is not None else "".join(answer_parts)
            except Exception as exc:
                raise RuntimeError("GENERATION_ERROR") from exc

        try:
            return generate_summary_from_payload(
                payload=payload,
                model_id=None,
                default_model=self.default_model,
            )
        except Exception as exc:
            raise RuntimeError("GENERATION_ERROR") from exc

    async def create_report_from_request(
        self,
        *,
        session_id: int,
        analysis_results: List[Dict[str, Any]],
        visualizations: List[Dict[str, Any]],
        insights: List[Any],
    ) -> Report:
        summary_text = await self.generate_summary(
            analysis_results=analysis_results,
            visualizations=visualizations,
            insights=insights,
        )
        return await self.create_report(
            session_id=session_id,
            summary_text=summary_text,
        )
