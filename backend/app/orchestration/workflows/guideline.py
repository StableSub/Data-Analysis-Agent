"""
Guideline 서브그래프.

역할:
- 활성화된 지침서 인덱스 존재 여부를 확인하고 필요 시 생성한다.
- 질문과 관련된 지침서 컨텍스트를 검색한다.
- 검색 결과를 근거 요약 형태로 정리한다.
"""

from __future__ import annotations

from typing import Any, Dict

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from ..state import GuidelineGraphState
from ...modules.guidelines.service import GuidelineService
from ...modules.rag.service import GuidelineRagService


class GuidelineSynthesisPayload(BaseModel):
    evidence_summary: str = Field(...)


def build_guideline_workflow(
    *,
    guideline_service: GuidelineService,
    guideline_rag_service: GuidelineRagService,
    default_model: str = "gpt-5-nano",
):
    """
    역할: 활성 지침서 확인, 검색, 근거 요약 3단계로 구성된 guideline 서브그래프를 생성한다.
    입력: guideline 조회용 service, guideline RAG service, 요약용 기본 모델명을 받는다.
    출력: `guideline_result`, `guideline_index_status`를 누적하는 컴파일된 그래프를 반환한다.
    """
    def build_guideline_context(
        *,
        active_source_id: str,
        guideline_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "guideline_source_id": active_source_id or str(guideline_result.get("source_id") or ""),
            "guideline_id": str(guideline_result.get("guideline_id") or ""),
            "filename": str(guideline_result.get("filename") or ""),
            "status": str(guideline_result.get("status") or ""),
            "retrieved_chunks": list(guideline_result.get("retrieved_chunks") or []),
            "retrieved_count": int(guideline_result.get("retrieved_count", 0) or 0),
            "has_evidence": bool(guideline_result.get("has_evidence", False)),
            "evidence_summary": str(guideline_result.get("evidence_summary") or ""),
        }

    def ensure_guideline_index_node(state: GuidelineGraphState) -> Dict[str, Any]:
        """
        역할: 활성 지침서의 인덱스 존재 여부를 확인하고 필요 시 새로 인덱싱한다.
        """
        active_guideline = guideline_service.get_active_guideline()
        if active_guideline is None:
            guideline_result = {
                "status": "no_active_guideline",
                "has_evidence": False,
                "retrieved_chunks": [],
                "retrieved_count": 0,
                "evidence_summary": "활성화된 지침서가 없어 지침 근거를 확인하지 못했습니다.",
            }
            return {
                "active_guideline_source_id": "",
                "guideline_index_status": {"status": "no_active_guideline"},
                "guideline_result": guideline_result,
                "guideline_context": build_guideline_context(
                    active_source_id="",
                    guideline_result=guideline_result,
                ),
                "guideline_data_exists": False,
            }

        source_id = active_guideline.source_id
        index_status = guideline_rag_service.ensure_index_for_guideline(active_guideline)

        return {
            "active_guideline_source_id": source_id,
            "guideline_index_status": {
                "status": index_status.get("status", "missing"),
                "source_id": source_id,
                "guideline_id": active_guideline.guideline_id,
                "filename": active_guideline.filename,
            },
        }

    def retrieve_guideline_context_node(state: GuidelineGraphState) -> Dict[str, Any]:
        """
        역할: 사용자 질문으로 활성 지침서 검색을 수행해 컨텍스트와 청크 메타데이터를 구성한다.
        """
        query = str(state.get("user_input", "")).strip()
        index_status = state.get("guideline_index_status")
        active_source_id = state.get("active_guideline_source_id") or ""

        status_value = ""
        if isinstance(index_status, dict):
            status_raw = index_status.get("status")
            status_value = status_raw if isinstance(status_raw, str) else ""

        active_guideline = (
            guideline_service.get_guideline_by_source_id(active_source_id)
            if active_source_id
            else None
        )

        retrieved = []
        if query and active_source_id and status_value in {"existing", "created"}:
            retrieved = guideline_rag_service.query_for_source(
                query=query,
                source_id=active_source_id,
                top_k=3,
            )

        context = guideline_rag_service.build_context(retrieved) if retrieved else ""
        retrieved_chunks = [
            {
                "source_id": item.source_id,
                "chunk_id": item.chunk_id,
                "score": item.score,
                "content": item.content,
            }
            for item in retrieved
        ]

        guideline_result = {
            "query": query,
            "source_id": active_source_id,
            "guideline_id": active_guideline.guideline_id if active_guideline else "",
            "filename": active_guideline.filename if active_guideline else "",
            "retrieved_chunks": retrieved_chunks,
            "context": context,
            "retrieved_count": len(retrieved_chunks),
            "has_evidence": bool(retrieved_chunks),
            "status": (
                "no_active_guideline"
                if status_value == "no_active_guideline"
                else ("retrieved" if retrieved_chunks else "no_evidence")
            ),
        }
        return {
            "guideline_result": {
                **guideline_result,
            },
            "guideline_context": build_guideline_context(
                active_source_id=active_source_id,
                guideline_result=guideline_result,
            ),
            "guideline_data_exists": bool(retrieved_chunks),
        }

    def summarize_guideline_evidence_node(state: GuidelineGraphState) -> Dict[str, Any]:
        """
        역할: 검색된 지침 근거가 있을 때 간단한 근거 요약을 생성한다.
        """
        guideline_result = state.get("guideline_result")
        guideline_result_dict = guideline_result if isinstance(guideline_result, dict) else {}

        if not bool(state.get("guideline_data_exists", False)):
            existing_summary = str(guideline_result_dict.get("evidence_summary") or "").strip()
            if existing_summary:
                no_evidence_summary = existing_summary
            elif guideline_result_dict.get("status") == "no_active_guideline":
                no_evidence_summary = "활성화된 지침서가 없어 지침 근거를 확인하지 못했습니다."
            else:
                no_evidence_summary = "관련 지침 근거를 찾지 못했습니다."
            updated_guideline_result = {
                **guideline_result_dict,
                "has_evidence": False,
                "evidence_summary": no_evidence_summary,
                "status": guideline_result_dict.get("status", "no_evidence"),
            }
            return {
                "guideline_result": updated_guideline_result,
                "guideline_context": build_guideline_context(
                    active_source_id=str(state.get("active_guideline_source_id") or ""),
                    guideline_result=updated_guideline_result,
                ),
            }

        query = str(guideline_result_dict.get("query", ""))
        context = str(guideline_result_dict.get("context", ""))
        model_name = state.get("model_id") or default_model
        llm = init_chat_model(model_name).with_structured_output(
            GuidelineSynthesisPayload,
            method="function_calling",
        )
        llm_result = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "질문과 지침서 검색 컨텍스트를 읽고, 답변에 바로 활용할 수 있는 지침 근거 요약을 짧게 작성하라."
                    )
                ),
                HumanMessage(
                    content=(
                        f"question:\n{query}\n\n"
                        f"guideline_context:\n{context}"
                    )
                ),
            ]
        )
        updated_guideline_result = {
            **guideline_result_dict,
            "has_evidence": True,
            "evidence_summary": llm_result.evidence_summary,
            "status": "retrieved",
        }
        return {
            "guideline_result": updated_guideline_result,
            "guideline_context": build_guideline_context(
                active_source_id=str(state.get("active_guideline_source_id") or ""),
                guideline_result=updated_guideline_result,
            ),
        }

    graph = StateGraph(GuidelineGraphState)
    graph.add_node("ensure_guideline_index", ensure_guideline_index_node)
    graph.add_node("retrieve_guideline_context", retrieve_guideline_context_node)
    graph.add_node("summarize_guideline_evidence", summarize_guideline_evidence_node)
    graph.add_edge(START, "ensure_guideline_index")
    graph.add_edge("ensure_guideline_index", "retrieve_guideline_context")
    graph.add_edge("retrieve_guideline_context", "summarize_guideline_evidence")
    graph.add_edge("summarize_guideline_evidence", END)

    return graph.compile()
