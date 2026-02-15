"""
V1 리포트 서브그래프.

역할:
- 현재는 분기 확인용 출력만 반환한다.
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from backend.app.ai.agents.state import ReportGraphState


def build_report_workflow(default_model: str = "gpt-5-nano"):
    """리포트 분기 확인용 서브그래프를 생성한다."""
    _ = default_model

    def report_branch_node(_: ReportGraphState) -> Dict[str, Any]:
        """리포트 분기가 선택되었음을 출력한다."""
        return {
            "output": {
                "type": "report_branch",
                "content": "Report branch selected",
            }
        }

    graph = StateGraph(ReportGraphState)
    graph.add_node("report_branch", report_branch_node)
    graph.add_edge(START, "report_branch")
    graph.add_edge("report_branch", END)

    return graph.compile()
