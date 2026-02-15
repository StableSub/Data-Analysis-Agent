"""
V1 시각화 서브그래프.

역할:
- 현재는 분기 확인용 출력만 반환한다.
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from backend.app.ai.agents.state import VisualizationGraphState


def build_visualization_workflow(default_model: str = "gpt-5-nano"):
    """시각화 분기 확인용 서브그래프를 생성한다."""
    _ = default_model

    def visualization_branch_node(_: VisualizationGraphState) -> Dict[str, Any]:
        """시각화 분기가 선택되었음을 출력한다."""
        return {
            "output": {
                "type": "visualization_branch",
                "content": "Visualization branch selected",
            }
        }

    graph = StateGraph(VisualizationGraphState)
    graph.add_node("visualization_branch", visualization_branch_node)
    graph.add_edge(START, "visualization_branch")
    graph.add_edge("visualization_branch", END)

    return graph.compile()
