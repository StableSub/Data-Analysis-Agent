from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..analysis.schemas import AnalysisPlan


PlanningRoute = Literal["general_question", "analysis", "fallback_rag"]


class PlannerDecision(BaseModel):
    is_general_question: bool = False
    ask_analysis: bool = False
    preprocess_required: bool = False
    need_visualization: bool = False
    need_report: bool = False
    guideline_context_used: bool = False


class PlanningResult(BaseModel):
    route: PlanningRoute
    needs_clarification: bool = False
    clarification_question: str = ""
    preprocess_required: bool = False
    analysis_plan: AnalysisPlan | None = None
    need_visualization: bool = False
    need_report: bool = False
    guideline_context_used: bool = False
