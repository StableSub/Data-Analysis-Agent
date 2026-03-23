"""
V1 RAG 서브그래프.

역할:
- 선택 데이터셋의 인덱스 존재 여부를 확인하고 필요 시 생성한다.
- 검색 컨텍스트를 수집한 뒤 insight를 합성한다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph

from backend.app.modules.rag.ai import synthesize_insight
from backend.app.modules.rag.service import RagService, RetrievedChunk
from backend.app.orchestration.state import RagGraphState
from backend.app.orchestration.utils import resolve_target_source_id


def build_rag_workflow(*, rag_service: RagService, default_model: str = "gpt-5-nano"):
    def ensure_rag_index_node(state: RagGraphState) -> Dict[str, Any]:
        target_source_id = resolve_target_source_id(state)
        return {"rag_index_status": rag_service.ensure_index_for_source(target_source_id or "")}

    def retrieve_context_node(state: RagGraphState) -> Dict[str, Any]:
        query = str(state.get("user_input", "")).strip()
        target_source_id = resolve_target_source_id(state)
        index_status = state.get("rag_index_status")
        status_value = ""
        if isinstance(index_status, dict):
            status_raw = index_status.get("status")
            status_value = status_raw if isinstance(status_raw, str) else ""

        retrieved: List[RetrievedChunk] = []
        if query and target_source_id and status_value in {"existing", "created"}:
            retrieved = rag_service.query_for_source(
                query=query,
                top_k=3,
                source_id=target_source_id,
            )

        context = rag_service.build_context(retrieved) if retrieved else ""
        retrieved_chunks = [
            {
                "source_id": item.source_id,
                "chunk_id": item.chunk_id,
                "score": item.score,
                "content": item.content,
            }
            for item in retrieved
        ]

        return {
            "rag_result": {
                "query": query,
                "source_id": target_source_id,
                "retrieved_chunks": retrieved_chunks,
                "context": context,
                "retrieved_count": len(retrieved_chunks),
            },
            "rag_data_exists": bool(retrieved_chunks),
        }

    def insight_synthesis_node(state: RagGraphState) -> Dict[str, Any]:
        rag_result = state.get("rag_result")
        rag_result_dict = rag_result if isinstance(rag_result, dict) else {}
        retrieved_count_raw = rag_result_dict.get("retrieved_count")
        retrieved_count = retrieved_count_raw if isinstance(retrieved_count_raw, int) else 0

        if not bool(state.get("rag_data_exists", False)):
            no_evidence_summary = "질문과 직접 연결되는 근거를 찾지 못했습니다."
            return {
                "insight": {
                    "summary": no_evidence_summary,
                    "retrieved_count": 0,
                },
                "rag_result": {
                    **rag_result_dict,
                    "evidence_summary": no_evidence_summary,
                },
            }

        query_raw = rag_result_dict.get("query")
        context_raw = rag_result_dict.get("context")
        query = query_raw if isinstance(query_raw, str) else ""
        context = context_raw if isinstance(context_raw, str) else ""

        llm_result = synthesize_insight(
            query=query,
            context=context,
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        insight_summary = llm_result.insight_summary
        evidence_summary = llm_result.evidence_summary.strip() or insight_summary

        source_id_raw = rag_result_dict.get("source_id")
        source_id = source_id_raw if isinstance(source_id_raw, str) else ""
        return {
            "insight": {
                "summary": insight_summary,
                "retrieved_count": retrieved_count,
                "source_id": source_id,
            },
            "rag_result": {
                **rag_result_dict,
                "evidence_summary": evidence_summary,
            },
        }

    graph = StateGraph(RagGraphState)
    graph.add_node("ensure_rag_index", ensure_rag_index_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("insight_synthesis", insight_synthesis_node)
    graph.add_edge(START, "ensure_rag_index")
    graph.add_edge("ensure_rag_index", "retrieve_context")
    graph.add_edge("retrieve_context", "insight_synthesis")
    graph.add_edge("insight_synthesis", END)

    return graph.compile()


async def generate_rag_answer(
    *,
    service: RagService,
    query: str,
    top_k: int = 3,
    source_filter: Optional[List[str]] = None,
) -> tuple[str, List[RetrievedChunk]] | None:
    return await service.answer_query(
        query=query,
        top_k=top_k,
        source_filter=source_filter,
    )
