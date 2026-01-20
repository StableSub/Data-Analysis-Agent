from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Iterable, Optional, TypedDict

from langgraph.graph import END, StateGraph

from ..llm.client import LLMClient
from .manager_agent import ManagerPlan, ManagerPlanStep


@dataclass
class VisualizationCodeResponse:
    objective: str
    code: str
    notes: str = ""


class VisualizationState(TypedDict):
    question: str
    data_context: str
    plan: list[dict]
    raw_response: str
    response: VisualizationCodeResponse


class VisualizationAgent:
    """
    시각화를 위한 파이썬 코드를 생성하는 에이전트.
    LangGraph를 이용해 생성->파싱 흐름을 구성한다.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.graph = self._build_graph().compile()

    def generate_code(
        self, question: str, data_context: Optional[str] = None
    ) -> VisualizationCodeResponse:
        state = self.graph.invoke(
            {
                "question": question,
                "data_context": data_context or "",
                "plan": [],
            }
        )
        return state["response"]

    def generate_code_from_plan(
        self,
        question: str,
        plan: ManagerPlan,
        data_context: Optional[str] = None,
    ) -> VisualizationCodeResponse:
        state = self.graph.invoke(
            {
                "question": question,
                "data_context": data_context or "",
                "plan": self._plan_to_payload(plan.steps),
            }
        )
        return state["response"]

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(VisualizationState)
        graph.add_node("draft", self._draft_node)
        graph.add_node("parse", self._parse_node)
        graph.set_entry_point("draft")
        graph.add_edge("draft", "parse")
        graph.add_edge("parse", END)
        return graph

    def _draft_node(self, state: VisualizationState) -> dict:
        context = self._build_context(
            data_context=state.get("data_context", ""),
            plan=state.get("plan", []),
        )
        response = self.llm_client.ask(question=state["question"], context=context)
        return {"raw_response": response}

    @staticmethod
    def _build_context(data_context: str, plan: Iterable[dict]) -> str:
        plan_text = json.dumps(list(plan), ensure_ascii=False, indent=2)
        return (
            "역할: Visualization Agent\n"
            "- 사용자 질문에 대한 시각화용 파이썬 코드를 생성한다.\n"
            "- 출력은 반드시 JSON 형식으로만 제공한다.\n"
            "- 코드는 pandas + matplotlib 또는 seaborn을 사용한다.\n"
            "- 기본 데이터프레임 이름은 df로 가정한다.\n"
            "- 외부 네트워크 호출이나 파일 입출력은 포함하지 않는다.\n"
            "\n"
            "Manager Plan:\n"
            f"{plan_text}\n"
            "\n"
            "데이터 컨텍스트:\n"
            f"{data_context or '없음'}\n"
            "\n"
            "출력 JSON 스키마:\n"
            "{\n"
            '  "objective": "시각화 목표 요약",\n'
            '  "code": "파이썬 코드 (여러 줄 가능)",\n'
            '  "notes": "가정/주의사항 (없으면 빈 문자열)"\n'
            "}\n"
        )

    @staticmethod
    def _parse_response(response: str, fallback_question: str) -> VisualizationCodeResponse:
        cleaned = VisualizationAgent._strip_code_fences(response)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            return VisualizationCodeResponse(
                objective=fallback_question.strip() or "Visualize the data",
                code=(
                    "import matplotlib.pyplot as plt\n\n"
                    "# TODO: add visualization steps based on the question\n"
                    "df.hist(figsize=(10, 6))\n"
                    "plt.tight_layout()\n"
                    "plt.show()\n"
                ),
                notes="LLM 응답 파싱 실패로 기본 코드를 생성했습니다.",
            )

        return VisualizationCodeResponse(
            objective=str(payload.get("objective", fallback_question)).strip(),
            code=str(payload.get("code", "")).strip(),
            notes=str(payload.get("notes", "")).strip(),
        )

    def _parse_node(self, state: VisualizationState) -> dict:
        raw_response = state.get("raw_response", "")
        parsed = self._parse_response(raw_response, fallback_question=state["question"])
        return {"response": parsed}

    @staticmethod
    def _plan_to_payload(steps: Iterable[ManagerPlanStep]) -> list[dict]:
        return [asdict(step) for step in steps]

    @staticmethod
    def _strip_code_fences(response: str) -> str:
        text = response.strip()
        if text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
        return text
