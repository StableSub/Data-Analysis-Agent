"""
V1 RAG 서브그래프.

역할:
- 현재는 분기 확인용 출력만 반환한다.
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from backend.app.ai.agents.state import RagGraphState


def build_rag_workflow(default_model: str = "gpt-5-nano"):
    """RAG 분기 확인용 서브그래프를 생성한다."""
    _ = default_model

    def rag_branch_node(_: RagGraphState) -> Dict[str, Any]:
        """RAG 분기가 선택되었음을 출력한다."""
        return {
            "output": {
                "type": "rag_branch",
                "content": "RAG branch selected",
            }
        }

    graph = StateGraph(RagGraphState)
    graph.add_node("rag_branch", rag_branch_node)
    graph.add_edge(START, "rag_branch")
    graph.add_edge("rag_branch", END)

    return graph.compile()
