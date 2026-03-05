import json
from typing import Any, Dict, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ...ai.agents.client import AgentClient
from .models import Report


class ReportService:
    """리포트 생성/조회/목록의 최소 기능만 제공한다."""

    def __init__(self, db: Session) -> None:
        self.db = db

    async def create_report(
        self,
        *,
        session_id: int,
        analysis_results: List[Dict[str, Any]],
        visualizations: List[Dict[str, Any]],
        insights: List[Any],
        agent: AgentClient,
    ) -> Report:
        """입력 데이터를 바탕으로 LLM 요약 리포트를 생성한다."""
        if not analysis_results and not visualizations and not insights:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NO_RESULTS")

        payload = {
            "analysis_results": analysis_results,
            "visualizations": visualizations,
            "insights": insights,
        }
        question = "다음 분석 결과를 간결하게 요약해 리포트를 작성해줘."
        context = json.dumps(payload, ensure_ascii=False)

        try:
            summary_text = await self._collect_answer_from_agent_stream(
                agent,
                question=question,
                context=context,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GENERATION_ERROR",
            ) from exc

        report = Report(
            session_id=session_id,
            summary_text=summary_text,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    @staticmethod
    async def _collect_answer_from_agent_stream(
        agent: AgentClient,
        *,
        question: str,
        context: str,
    ) -> str:
        answer_parts: list[str] = []
        final_answer: str | None = None
        async for event in agent.astream_with_trace(question=question, context=context):
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

    def get_report(self, report_id: str) -> Report:
        """리포트 단건을 조회한다."""
        report = self.db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="REPORT_NOT_FOUND")
        return report

    def list_reports(self, session_id: int) -> List[Report]:
        """세션별 리포트 목록을 조회한다."""
        return (
            self.db.query(Report)
            .filter(Report.session_id == session_id)
            .order_by(Report.id.asc())
            .all()
        )
