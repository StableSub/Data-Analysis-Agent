"""
V1 RAG 서브그래프.

역할:
- 선택 데이터셋의 인덱스 존재 여부를 확인하고 필요 시 생성한다.
- 검색 컨텍스트를 수집한 뒤 insight를 합성한다.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.ai.agents.state import RagGraphState
from backend.app.ai.agents.utils import resolve_target_source_id
from backend.app.domain.data_source.repository import DataSourceRepository
from backend.app.rag.core.embedding import E5Embedder
from backend.app.rag.repository import RagRepository
from backend.app.rag.service import RagService


@lru_cache(maxsize=1)
def _cached_embedder() -> E5Embedder:
    """
    역할: RAG 임베딩에 사용하는 `E5Embedder` 인스턴스를 단일 객체로 재사용한다.
    입력: 인자를 받지 않고 내부에서 기본 임베더를 생성한다.
    출력: 재사용 가능한 `E5Embedder` 객체를 반환한다.
    데코레이터: @lru_cache(maxsize=1). 임베더 싱글톤 재사용으로 초기화 비용과 중복 객체 생성을 줄인다.
    호출 맥락: RAG 워크플로우 빌드 시 `RagService` 생성자에 주입되는 공용 팩토리다.
    """
    return E5Embedder()


class InsightSynthesisPayload(BaseModel):
    insight_summary: str = Field(...)
    evidence_summary: str = Field(...)


def build_rag_workflow(*, db: Session, default_model: str = "gpt-5-nano"):
    """
    역할: 인덱스 보장, 검색, 인사이트 합성 3단계로 구성된 RAG 서브그래프를 생성한다.
    입력: DB 세션(`db`)과 인사이트 합성 기본 모델명(`default_model`)을 받는다.
    출력: `rag_result`, `rag_index_status`, `insight`를 누적하는 컴파일된 그래프를 반환한다.
    데코레이터: 없음.
    호출 맥락: 메인 워크플로우에서 전처리 이후 `rag_flow` 노드로 연결되어 실행된다.
    """
    dataset_repository = DataSourceRepository(db)
    rag_repository = RagRepository(db)
    rag_service = RagService(
        repository=rag_repository,
        storage_dir=Path("storage") / "vectors",
        embedder=_cached_embedder(),
    )

    def ensure_rag_index_node(state: RagGraphState) -> Dict[str, Any]:
        """
        역할: 대상 source의 RAG 인덱스 존재 여부를 확인하고 필요 시 새로 인덱싱한다.
        입력: `state.preprocess_result`, `state.rag_result`, `state.source_id`를 통해 대상 source를 해석한다.
        출력: 인덱스 상태(`existing/created/missing/no_source/dataset_missing`)를 `rag_index_status`로 반환한다.
        데코레이터: 없음.
        호출 맥락: RAG 서브그래프 첫 노드로, 이후 검색 노드가 실행 가능한 전제조건을 마련한다.
        """
        target_source_id = resolve_target_source_id(state)
        if not target_source_id:
            return {"rag_index_status": {"status": "no_source"}}

        dataset = dataset_repository.get_by_source_id(target_source_id)
        if dataset is None:
            return {
                "rag_index_status": {
                    "status": "dataset_missing",
                    "source_id": target_source_id,
                }
            }

        source_meta = rag_repository.get_source(target_source_id)
        index_path = rag_service._index_path(target_source_id)
        if source_meta is not None and index_path.exists():
            return {
                "rag_index_status": {
                    "status": "existing",
                    "source_id": target_source_id,
                }
            }

        rag_service.index_dataset(dataset)
        updated_meta = rag_repository.get_source(target_source_id)
        updated_index_path = rag_service._index_path(target_source_id)
        status = "created" if updated_meta is not None and updated_index_path.exists() else "missing"
        return {
            "rag_index_status": {
                "status": status,
                "source_id": target_source_id,
            }
        }

    def retrieve_context_node(state: RagGraphState) -> Dict[str, Any]:
        """
        역할: 사용자 질문으로 벡터 검색을 수행해 컨텍스트 문자열과 청크 메타데이터를 구성한다.
        입력: `state.user_input`, `state.rag_index_status`, 대상 source ID를 포함한 상태를 받는다.
        출력: `rag_result`(query/context/retrieved_chunks 등)와 `rag_data_exists` 플래그를 반환한다.
        데코레이터: 없음.
        호출 맥락: 인덱스 확인 노드 다음 단계에서 실행되어 인사이트 합성의 근거 데이터를 준비한다.
        """
        query = str(state.get("user_input", "")).strip()
        target_source_id = resolve_target_source_id(state)
        index_status = state.get("rag_index_status")
        status_value = ""
        if isinstance(index_status, dict):
            status_raw = index_status.get("status")
            status_value = status_raw if isinstance(status_raw, str) else ""

        retrieved = []
        if query and target_source_id and status_value in {"existing", "created"}:
            source_meta = rag_repository.get_source(target_source_id)
            index_path = rag_service._index_path(target_source_id)
            if source_meta is not None and index_path.exists():
                retrieved = rag_service.query(
                    query=query,
                    top_k=3,
                    source_filter=[target_source_id],
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
        """
        역할: 검색 근거가 있을 때 LLM으로 인사이트 요약과 근거 요약을 생성하고 상태에 병합한다.
        입력: `state.rag_result`, `state.rag_data_exists`, `state.model_id`를 참조한다.
        출력: `insight.summary`와 `rag_result.evidence_summary`를 포함한 상태 업데이트를 반환한다.
        데코레이터: 없음.
        호출 맥락: RAG 서브그래프의 마지막 노드로, 이후 시각화/리포트 단계의 핵심 입력을 제공한다.
        """
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

        model_id = state.get("model_id")
        model_name = model_id if isinstance(model_id, str) and model_id.strip() else default_model
        llm = init_chat_model(model_name).with_structured_output(
            InsightSynthesisPayload,
            method="function_calling",
        )
        llm_result = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "질문과 검색 컨텍스트를 읽고 핵심 인사이트를 간단히 합성하라. "
                        "insight_summary와 evidence_summary를 함께 반환하라."
                    )
                ),
                HumanMessage(
                    content=(
                        f"question:\n{query}\n\n"
                        f"context:\n{context}"
                    )
                ),
            ]
        )
        insight_summary = llm_result.insight_summary
        evidence_summary = llm_result.evidence_summary

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
