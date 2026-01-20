from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable, List, TypedDict

from langgraph.graph import END, StateGraph

from ..llm.client import LLMClient


@dataclass
class ManagerPlanStep:
    step_id: int
    objective: str
    assigned_agent: str
    act: str
    expected_observation: str
    depends_on: List[int] = field(default_factory=list)


@dataclass
class ManagerPlan:
    intent: str
    steps: List[ManagerPlanStep]
    notes: str = ""


class ManagerState(TypedDict):
    user_input: str
    available_agents: List[str]
    raw_plan: str
    plan: ManagerPlan


class ManagerAgent:
    """
    사용자 요청을 분석하고 ReAct 스타일의 작업 계획을 수립/라우팅하는 관리자 에이전트.
    실제 실행/호출은 외부 시스템이 담당하고, 이 클래스는 계획/할당만 생성한다.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.graph = self._build_graph().compile()

    def create_plan(self, user_input: str, available_agents: Iterable[str]) -> ManagerPlan:
        """사용자 입력과 사용 가능한 하위 에이전트를 바탕으로 계획을 생성한다."""
        state = self.graph.invoke(
            {
                "user_input": user_input,
                "available_agents": list(available_agents),
            }
        )
        return state["plan"]

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(ManagerState)
        graph.add_node("plan", self._plan_node)
        graph.add_node("parse", self._parse_node)
        graph.set_entry_point("plan")
        graph.add_edge("plan", "parse")
        graph.add_edge("parse", END)
        return graph

    def _plan_node(self, state: ManagerState) -> dict:
        context = self._build_planner_context(state.get("available_agents", []))
        response = self.llm_client.ask(question=state["user_input"], context=context)
        return {"raw_plan": response}

    def _parse_node(self, state: ManagerState) -> dict:
        raw_plan = state.get("raw_plan", "")
        plan = self._parse_plan(raw_plan, fallback_input=state["user_input"])
        return {"plan": plan}

    @staticmethod
    def _build_planner_context(available_agents: Iterable[str]) -> str:
        allowed_agents = [a for a in available_agents if a in ("code_agent", "viz_agent")]
        if not allowed_agents:
            allowed_agents = ["code_agent", "viz_agent"]
        agents = ", ".join(allowed_agents)
        return (
            "역할: Manager Agent (Planner)\n"
            "목표: 사용자 요청을 분석해서 코드 생성 에이전트와 시각화 에이전트만 활용하는\n"
            "최소 실행 가능한 계획(JSON)을 만든다.\n"
            "\n"
            "중요 규칙:\n"
            "1) 출력은 반드시 JSON만. 설명/문장/코드블럭/주석 금지.\n"
            "2) 사용 가능한 에이전트는 아래 2개뿐이다. 다른 이름 쓰지 마.\n"
            "   - code_agent\n"
            "   - viz_agent\n"
            "3) steps는 최대 4개까지만 만든다.\n"
            "4) depends_on은 step_id를 참조한다. 의존성이 없으면 [].\n"
            '5) assigned_agent는 반드시 "code_agent" 또는 "viz_agent" 중 하나.\n'
            "6) act에는 에이전트가 실제로 할 일을 한 문장으로 구체적으로 쓴다.\n"
            "7) expected_observation에는 이 step이 끝나면 얻을 결과물을 간단히 쓴다.\n"
            "8) 데이터가 필요하면 context에 dataset_id가 있다고 가정하고,\n"
            "   act에 dataset_id를 사용하라고 명시한다.\n"
            "9) 시각화가 필요하면 viz_agent step 포함, 그 전에 code_agent 단계에서\n"
            "   전처리/집계 코드를 만들도록 한다.\n"
            "\n"
            "사용 가능한 하위 에이전트:\n"
            f"{agents}\n"
            "\n"
            "출력 JSON 스키마:\n"
            "{\n"
            '  "intent": "요청 의도 요약",\n'
            '  "notes": "가정/주의사항(없으면 빈 문자열)",\n'
            '  "steps": [\n'
            "    {\n"
            '      "step_id": 1,\n'
            '      "objective": "단계 목표",\n'
            '      "assigned_agent": "code_agent | viz_agent",\n'
            '      "act": "실행할 행동(한 문장, 구체적으로)",\n'
            '      "expected_observation": "기대 결과/관찰",\n'
            '      "depends_on": []\n'
            "    }\n"
            "  ]\n"
            "}\n"
        )

    @staticmethod
    def _parse_plan(response: str, fallback_input: str) -> ManagerPlan:
        cleaned = ManagerAgent._strip_code_fences(response)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            return ManagerPlan(
                intent=fallback_input.strip() or "요청 분석 필요",
                notes="LLM 응답 파싱 실패로 기본 계획을 생성했습니다.",
                steps=[
                    ManagerPlanStep(
                        step_id=1,
                        objective="요청 의도 확인",
                        assigned_agent="manager",
                        act="사용자 의도와 요구사항을 확인한다.",
                        expected_observation="명확한 목표와 제약 조건",
                        depends_on=[],
                    )
                ],
            )

        steps: List[ManagerPlanStep] = []
        for item in payload.get("steps", []):
            steps.append(
                ManagerPlanStep(
                    step_id=int(item.get("step_id", len(steps) + 1)),
                    objective=str(item.get("objective", "")).strip(),
                    assigned_agent=str(item.get("assigned_agent", "manager")).strip(),
                    act=str(item.get("act", "")).strip(),
                    expected_observation=str(item.get("expected_observation", "")).strip(),
                    depends_on=list(item.get("depends_on", [])),
                )
            )

        return ManagerPlan(
            intent=str(payload.get("intent", fallback_input)).strip(),
            notes=str(payload.get("notes", "")).strip(),
            steps=steps,
        )

    @staticmethod
    def _strip_code_fences(response: str) -> str:
        text = response.strip()
        if text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
        return text
