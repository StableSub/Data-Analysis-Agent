"""
Guideline 서브그래프.

역할:
- 현재 chat 요청에서 선택된 지침서 인덱스 존재 여부를 확인하고 필요 시 생성한다.
- 질문과 관련된 지침서 컨텍스트를 검색한다.
- 검색 결과를 근거 요약 형태로 정리한다.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from ...core.ai import LLMGateway
from ...core.trace_logging import set_trace_stage
from ..guideline_status import (
    GUIDELINE_MISSING,
    NO_GUIDELINE_EVIDENCE,
    NO_ACTIVE_GUIDELINE,
    NO_SELECTED_GUIDELINE,
)
from ..state import GuidelineGraphState
from ...modules.guidelines.service import GuidelineService
from ...modules.rag.errors import RagEmbeddingError, RagError
from ...modules.rag.service import GuidelineRagService

_GUIDELINE_FALLBACK_MAX_CHARS = 12_000
_GUIDELINE_FALLBACK_WINDOW_CHARS = 1_800
_GUIDELINE_FALLBACK_KEYWORDS = (
    "PassOrFail",
    "불량",
    "양품",
    "defect",
    "failure",
    "pass",
    "fail",
    "3시그마",
    "threshold",
)


class GuidelineSynthesisPayload(BaseModel):
    evidence_summary: str = Field(...)


def _build_semantic_glossary(
    *,
    guideline_result: Mapping[str, Any],
    dataset_context: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    columns = _coerce_dataset_columns(dataset_context)
    text = _semantic_source_text(guideline_result)
    if not text.strip() or not columns:
        return {}

    glossary: Dict[str, Any] = {}
    product_columns = _product_columns_from_guideline(text=text, columns=columns)
    if product_columns:
        glossary["product"] = {
            "columns": product_columns,
            "source": "guideline",
        }

    defect_indicator = _defect_indicator_from_guideline(text=text, columns=columns)
    if defect_indicator:
        glossary["defect_indicator"] = defect_indicator
        defect_column = str(defect_indicator["column"])
        defect_value = int(defect_indicator["defect_value"])
        glossary["defect_rate"] = {
            "metric": "defect_rate",
            "column": defect_column,
            "positive_value": defect_value,
            "formula": f"count({defect_column} == {defect_value}) / count(*)",
            "source": "guideline",
        }

    return glossary


def _coerce_dataset_columns(dataset_context: Mapping[str, Any] | None) -> list[str]:
    if dataset_context is None:
        return []
    raw_columns = dataset_context.get("columns")
    if not isinstance(raw_columns, list):
        return []
    columns: list[str] = []
    for raw_column in raw_columns:
        column = str(raw_column).strip()
        if column and column not in columns:
            columns.append(column)
    return columns


def _semantic_source_text(guideline_result: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for key in ("evidence_summary", "context"):
        value = str(guideline_result.get(key) or "").strip()
        if value:
            parts.append(value)
    raw_chunks = guideline_result.get("retrieved_chunks")
    if isinstance(raw_chunks, list):
        for raw_chunk in raw_chunks:
            if not isinstance(raw_chunk, Mapping):
                continue
            content = str(raw_chunk.get("content") or "").strip()
            if content:
                parts.append(content)
    return "\n".join(parts)


def _select_guideline_fallback_excerpt(*, text: str, query: str) -> str:
    normalized_text = text.strip()
    if len(normalized_text) <= _GUIDELINE_FALLBACK_MAX_CHARS:
        return normalized_text

    terms = {
        term.lower()
        for term in _GUIDELINE_FALLBACK_KEYWORDS
        if term.strip()
    }
    for token in query.replace(".", " ").replace(",", " ").split():
        normalized_token = token.strip().lower()
        if len(normalized_token) >= 2:
            terms.add(normalized_token)

    lower_text = normalized_text.lower()
    spans: list[tuple[int, int]] = []
    for term in terms:
        index = lower_text.find(term)
        if index < 0:
            continue
        start = max(0, index - _GUIDELINE_FALLBACK_WINDOW_CHARS)
        end = min(
            len(normalized_text),
            index + len(term) + _GUIDELINE_FALLBACK_WINDOW_CHARS,
        )
        spans.append((start, end))

    if not spans:
        return normalized_text[:_GUIDELINE_FALLBACK_MAX_CHARS].rstrip()

    spans.sort()
    merged_spans: list[tuple[int, int]] = []
    for start, end in spans:
        if not merged_spans or start > merged_spans[-1][1]:
            merged_spans.append((start, end))
            continue
        previous_start, previous_end = merged_spans[-1]
        merged_spans[-1] = (previous_start, max(previous_end, end))

    excerpts: list[str] = []
    total_length = 0
    for start, end in merged_spans:
        if total_length >= _GUIDELINE_FALLBACK_MAX_CHARS:
            break
        excerpt = normalized_text[start:end].strip()
        if not excerpt:
            continue
        remaining = _GUIDELINE_FALLBACK_MAX_CHARS - total_length
        clipped = excerpt[:remaining].rstrip()
        excerpts.append(clipped)
        total_length += len(clipped)

    return "\n...\n".join(excerpts).strip()


def _product_columns_from_guideline(*, text: str, columns: list[str]) -> list[str]:
    normalized_text = text.lower()
    candidates = [
        ("PART_NAME", ("part_name", "제품명", "제품 이름", "product name")),
        ("PART_NO", ("part_no", "제품 식별", "제품 번호", "product id", "part no")),
    ]
    product_columns: list[str] = []
    for column, terms in candidates:
        if column not in columns:
            continue
        if any(term in normalized_text for term in terms) or "제품" in text:
            product_columns.append(column)
    return product_columns


def _defect_indicator_from_guideline(*, text: str, columns: list[str]) -> Dict[str, Any]:
    if "PassOrFail" not in columns or "PassOrFail" not in text:
        return {}
    normalized_text = text.lower()
    if "불량" not in text and "defect" not in normalized_text:
        return {}
    if "1" not in text:
        return {}
    indicator: Dict[str, Any] = {
        "column": "PassOrFail",
        "defect_value": 1,
    }
    if "0" in text and ("정상" in text or "pass" in normalized_text):
        indicator["pass_value"] = 0
    return indicator


def build_guideline_workflow(
    *,
    guideline_service: GuidelineService,
    guideline_rag_service: GuidelineRagService,
    default_model: str = "gpt-5-nano",
):
    """
    역할: 선택 지침서 확인, 검색, 근거 요약 3단계로 구성된 guideline 서브그래프를 생성한다.
    입력: guideline 조회용 service, guideline RAG service, 요약용 기본 모델명을 받는다.
    출력: `guideline_result`, `guideline_index_status`를 누적하는 컴파일된 그래프를 반환한다.
    """
    def build_guideline_context(
        *,
        active_source_id: str,
        guideline_result: Dict[str, Any],
        dataset_context: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "guideline_source_id": active_source_id or str(guideline_result.get("source_id") or ""),
            "guideline_id": str(guideline_result.get("guideline_id") or ""),
            "filename": str(guideline_result.get("filename") or ""),
            "status": str(guideline_result.get("status") or ""),
            "retrieved_chunks": list(guideline_result.get("retrieved_chunks") or []),
            "retrieved_count": int(guideline_result.get("retrieved_count", 0) or 0),
            "has_evidence": bool(guideline_result.get("has_evidence", False)),
            "evidence_summary": str(guideline_result.get("evidence_summary") or ""),
        }
        semantic_glossary = _build_semantic_glossary(
            guideline_result=guideline_result,
            dataset_context=dataset_context,
        )
        if semantic_glossary:
            context["semantic_glossary"] = semantic_glossary
        return context

    def build_guideline_unavailable_payload(
        *,
        exc: RagError,
        query: str,
        active_source_id: str,
        active_guideline: Any,
        selection_source: str,
        dataset_context: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        if isinstance(exc, RagEmbeddingError):
            evidence_summary = (
                "지침 검색 임베딩을 준비하지 못해 이번 답변에서는 지침 근거를 사용하지 않았습니다."
            )
            error_code = "guideline_embedding_error"
        else:
            evidence_summary = (
                "지침 검색을 완료하지 못해 이번 답변에서는 지침 근거를 사용하지 않았습니다."
            )
            error_code = "guideline_rag_error"

        fallback_context = load_guideline_fallback_context(
            active_guideline=active_guideline,
            query=query,
        )
        if fallback_context:
            retrieved_chunks = [
                {
                    "source_id": active_source_id,
                    "chunk_id": 0,
                    "score": 0.0,
                    "content": fallback_context,
                    "retrieval_mode": "raw_text_fallback",
                }
            ]
            guideline_result = {
                "query": query,
                "source_id": active_source_id,
                "guideline_id": active_guideline.guideline_id if active_guideline else "",
                "filename": active_guideline.filename if active_guideline else "",
                "retrieved_chunks": retrieved_chunks,
                "context": fallback_context,
                "retrieved_count": len(retrieved_chunks),
                "has_evidence": True,
                "selection_source": selection_source,
                "status": "retrieved",
                "error_code": error_code,
                "retrieval_mode": "raw_text_fallback",
                "evidence_summary": (
                    "지침 검색 인덱스 대신 원문 지침 일부를 직접 참조했습니다."
                ),
            }
            return {
                "guideline_result": guideline_result,
                "guideline_context": build_guideline_context(
                    active_source_id=active_source_id,
                    guideline_result=guideline_result,
                    dataset_context=dataset_context,
                ),
                "guideline_data_exists": True,
            }

        guideline_result = {
            "query": query,
            "source_id": active_source_id,
            "guideline_id": active_guideline.guideline_id if active_guideline else "",
            "filename": active_guideline.filename if active_guideline else "",
            "retrieved_chunks": [],
            "context": "",
            "retrieved_count": 0,
            "has_evidence": False,
            "selection_source": selection_source,
            "status": NO_GUIDELINE_EVIDENCE,
            "error_code": error_code,
            "evidence_summary": evidence_summary,
        }
        return {
            "guideline_result": guideline_result,
            "guideline_context": build_guideline_context(
                active_source_id=active_source_id,
                guideline_result=guideline_result,
                dataset_context=dataset_context,
            ),
            "guideline_data_exists": False,
        }

    def load_guideline_fallback_context(
        *,
        active_guideline: Any,
        query: str,
    ) -> str:
        if active_guideline is None:
            return ""
        loader = getattr(guideline_rag_service, "load_guideline_text", None)
        if not callable(loader):
            return ""
        try:
            raw_text = str(loader(active_guideline) or "")
        except (OSError, UnicodeDecodeError, ImportError, RuntimeError, ValueError):
            return ""
        return _select_guideline_fallback_excerpt(text=raw_text, query=query)

    def ensure_guideline_index_node(state: GuidelineGraphState) -> Dict[str, Any]:
        set_trace_stage("guideline_index")
        """
        역할: 선택된 지침서의 인덱스 존재 여부를 확인하고 필요 시 새로 인덱싱한다.
        """
        has_selection_key = "active_guideline_source_id" in state
        selected_source_id = str(state.get("active_guideline_source_id") or "").strip()
        active_guideline = None
        selection_source = "selected" if selected_source_id else "active"
        if selected_source_id:
            active_guideline = guideline_service.get_guideline_by_source_id(
                selected_source_id
            )
            if active_guideline is None:
                guideline_result = {
                    "status": GUIDELINE_MISSING,
                    "source_id": selected_source_id,
                    "has_evidence": False,
                    "retrieved_chunks": [],
                    "retrieved_count": 0,
                    "evidence_summary": "선택한 지침서를 찾을 수 없어 지침 근거를 확인하지 못했습니다.",
                    "selection_source": "selected",
                }
                return {
                    "active_guideline_source_id": selected_source_id,
                    "guideline_index_status": {
                        "status": GUIDELINE_MISSING,
                        "source_id": selected_source_id,
                        "selection_source": "selected",
                    },
                    "guideline_result": guideline_result,
                    "guideline_context": build_guideline_context(
                        active_source_id=selected_source_id,
                        guideline_result=guideline_result,
                        dataset_context=state.get("dataset_context"),
                    ),
                    "guideline_data_exists": False,
                }
        else:
            active_guideline = guideline_service.get_active_guideline()

        if active_guideline is None:
            absence_status = (
                NO_SELECTED_GUIDELINE if has_selection_key else NO_ACTIVE_GUIDELINE
            )
            evidence_summary = (
                "선택된 지침서가 없어 지침 근거를 확인하지 못했습니다."
                if has_selection_key
                else "활성화된 지침서가 없어 지침 근거를 확인하지 못했습니다."
            )
            guideline_result = {
                "status": absence_status,
                "has_evidence": False,
                "retrieved_chunks": [],
                "retrieved_count": 0,
                "evidence_summary": evidence_summary,
                "selection_source": selection_source,
            }
            return {
                "active_guideline_source_id": "",
                "guideline_index_status": {
                    "status": absence_status,
                    "selection_source": selection_source,
                },
                "guideline_result": guideline_result,
                "guideline_context": build_guideline_context(
                    active_source_id="",
                    guideline_result=guideline_result,
                    dataset_context=state.get("dataset_context"),
                ),
                "guideline_data_exists": False,
            }

        source_id = str(active_guideline.source_id)
        try:
            index_status = guideline_rag_service.ensure_index_for_guideline(active_guideline)
        except RagError as exc:
            unavailable_payload = build_guideline_unavailable_payload(
                exc=exc,
                query=str(state.get("user_input", "")).strip(),
                active_source_id=source_id,
                active_guideline=active_guideline,
                selection_source=selection_source,
                dataset_context=state.get("dataset_context"),
            )
            return {
                "active_guideline_source_id": source_id,
                "guideline_index_status": {
                    "status": NO_GUIDELINE_EVIDENCE,
                    "source_id": source_id,
                    "guideline_id": active_guideline.guideline_id,
                    "filename": active_guideline.filename,
                    "selection_source": selection_source,
                    "error_code": unavailable_payload["guideline_result"]["error_code"],
                },
                **unavailable_payload,
            }

        return {
            "active_guideline_source_id": source_id,
            "guideline_index_status": {
                "status": index_status.get("status", "missing"),
                "source_id": source_id,
                "guideline_id": active_guideline.guideline_id,
                "filename": active_guideline.filename,
                "selection_source": selection_source,
            },
        }

    def retrieve_guideline_context_node(state: GuidelineGraphState) -> Dict[str, Any]:
        set_trace_stage("guideline_retrieve")
        """
        역할: 사용자 질문으로 선택 지침서 검색을 수행해 컨텍스트와 청크 메타데이터를 구성한다.
        """
        query = str(state.get("user_input", "")).strip()
        index_status = state.get("guideline_index_status")
        active_source_id = str(state.get("active_guideline_source_id") or "")

        status_value = ""
        if isinstance(index_status, dict):
            status_raw = index_status.get("status")
            status_value = status_raw if isinstance(status_raw, str) else ""

        active_guideline = (
            guideline_service.get_guideline_by_source_id(active_source_id)
            if active_source_id
            else None
        )
        if status_value == NO_GUIDELINE_EVIDENCE:
            existing_result = state.get("guideline_result")
            existing_error = (
                existing_result
                if isinstance(existing_result, dict)
                else {"error_code": "guideline_rag_error"}
            )
            exc = (
                RagEmbeddingError()
                if existing_error.get("error_code") == "guideline_embedding_error"
                else RagError("GUIDELINE_RAG_ERROR", code="GUIDELINE_RAG_ERROR")
            )
            unavailable_selection_source = (
                str(index_status.get("selection_source") or "")
                if isinstance(index_status, dict)
                else ""
            )
            return build_guideline_unavailable_payload(
                exc=exc,
                query=query,
                active_source_id=active_source_id,
                active_guideline=active_guideline,
                selection_source=unavailable_selection_source,
                dataset_context=state.get("dataset_context"),
            )

        retrieved = []
        if query and active_source_id and status_value in {"existing", "created"}:
            try:
                retrieved = guideline_rag_service.query_for_source(
                    query=query,
                    source_id=active_source_id,
                    top_k=3,
                )
            except RagError as exc:
                unavailable_selection_source = (
                    str(index_status.get("selection_source") or "")
                    if isinstance(index_status, dict)
                    else ""
                )
                return build_guideline_unavailable_payload(
                    exc=exc,
                    query=query,
                    active_source_id=active_source_id,
                    active_guideline=active_guideline,
                    selection_source=unavailable_selection_source,
                    dataset_context=state.get("dataset_context"),
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
            "selection_source": (
                index_status.get("selection_source")
                if isinstance(index_status, dict)
                else ""
            ),
            "status": (
                status_value
                if status_value in {
                    NO_ACTIVE_GUIDELINE,
                    NO_SELECTED_GUIDELINE,
                    GUIDELINE_MISSING,
                }
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
                dataset_context=state.get("dataset_context"),
            ),
            "guideline_data_exists": bool(retrieved_chunks),
        }

    def summarize_guideline_evidence_node(state: GuidelineGraphState) -> Dict[str, Any]:
        set_trace_stage("guideline_synthesis")
        """
        역할: 검색된 지침 근거가 있을 때 간단한 근거 요약을 생성한다.
        """
        guideline_result = state.get("guideline_result")
        guideline_result_dict = guideline_result if isinstance(guideline_result, dict) else {}

        if not bool(state.get("guideline_data_exists", False)):
            existing_summary = str(guideline_result_dict.get("evidence_summary") or "").strip()
            if existing_summary:
                no_evidence_summary = existing_summary
            elif guideline_result_dict.get("status") == NO_ACTIVE_GUIDELINE:
                no_evidence_summary = "활성화된 지침서가 없어 지침 근거를 확인하지 못했습니다."
            elif guideline_result_dict.get("status") == NO_SELECTED_GUIDELINE:
                no_evidence_summary = "선택된 지침서가 없어 지침 근거를 확인하지 못했습니다."
            elif guideline_result_dict.get("status") == GUIDELINE_MISSING:
                no_evidence_summary = "선택한 지침서를 찾을 수 없어 지침 근거를 확인하지 못했습니다."
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
                    dataset_context=state.get("dataset_context"),
                ),
            }

        query = str(guideline_result_dict.get("query", ""))
        context = str(guideline_result_dict.get("context", ""))
        model_name = state.get("model_id") or default_model
        llm = LLMGateway(default_model=default_model)
        llm_result = llm.invoke_structured(
            schema=GuidelineSynthesisPayload,
            model_id=model_name,
            messages=[
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
            ],
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
                dataset_context=state.get("dataset_context"),
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
