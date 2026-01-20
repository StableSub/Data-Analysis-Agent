from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Optional

from .analysis_agent import AnalysisAgent, AnalysisCodeResponse
from .manager_agent import ManagerAgent, ManagerPlan
from .visualization_agent import VisualizationAgent, VisualizationCodeResponse
from ..llm.client import LLMClient


@dataclass
class PlanStepResult:
    step_id: int
    objective: str
    assigned_agent: str
    output: dict[str, Any]


@dataclass
class PlanExecutionResult:
    plan: ManagerPlan
    steps: list[PlanStepResult]


class PlanRouter:
    """
    ManagerAgent가 생성한 계획을 code_agent/ viz_agent로 라우팅해 실행한다.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        *,
        preset: str = "gemini_flash",
    ) -> None:
        llm = llm_client or LLMClient(preset=preset)
        self.manager = ManagerAgent(llm)
        self.analysis_agent = AnalysisAgent(llm)
        self.visualization_agent = VisualizationAgent(llm)

    def execute(
        self,
        question: str,
        *,
        dataset_id: Optional[str] = None,
        data_context: Optional[str] = None,
    ) -> PlanExecutionResult:
        plan = self.manager.create_plan(
            user_input=question,
            available_agents=["code_agent", "viz_agent"],
        )
        context = self._build_context(data_context, dataset_id)
        steps: list[PlanStepResult] = []
        for step in plan.steps:
            output = self._run_step(step.assigned_agent, question, plan, context)
            steps.append(
                PlanStepResult(
                    step_id=step.step_id,
                    objective=step.objective,
                    assigned_agent=step.assigned_agent,
                    output=output,
                )
            )
        return PlanExecutionResult(plan=plan, steps=steps)

    def _run_step(
        self,
        assigned_agent: str,
        question: str,
        plan: ManagerPlan,
        context: str,
    ) -> dict[str, Any]:
        if assigned_agent == "code_agent":
            response = self.analysis_agent.generate_code_from_plan(
                question=question,
                plan=plan,
                data_context=context,
            )
            return self._serialize_response(response)
        if assigned_agent == "viz_agent":
            response = self.visualization_agent.generate_code_from_plan(
                question=question,
                plan=plan,
                data_context=context,
            )
            return self._serialize_response(response)
        return {"error": f"Unsupported agent: {assigned_agent}"}

    @staticmethod
    def _build_context(data_context: Optional[str], dataset_id: Optional[str]) -> str:
        parts: list[str] = []
        if dataset_id:
            parts.append(f"dataset_id: {dataset_id}")
        if data_context:
            parts.append(data_context)
        return "\n".join(parts)

    @staticmethod
    def _serialize_response(
        response: AnalysisCodeResponse | VisualizationCodeResponse,
    ) -> dict[str, Any]:
        return asdict(response)
