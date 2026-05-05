from __future__ import annotations

from typing import Any, Mapping

from .state import (
    AnswerQualityPayload,
    EvidencePackagePayload,
    EvidenceWarningPayload,
)

_DEFAULT_ABSTAIN_REASON = (
    "최종 답변을 만들 수 있는 분석 결과나 검색 근거가 "
    "충분하지 않습니다."
)
_MILD_NO_EVIDENCE_CODES = {
    "rag_no_evidence",
    "no_evidence",
    "no_active_guideline",
}


def build_evidence_contract(
    *,
    state: Mapping[str, Any],
    merged_context: Mapping[str, Any],
) -> tuple[EvidencePackagePayload, AnswerQualityPayload]:
    """Build deterministic final-answer evidence metadata.

    This helper is intentionally side-effect free: it does not call an LLM, DB,
    or service layer. Missing upstream Backend 2/4 evidence is represented by
    empty fields, zero counts, and warnings rather than by fallback queries.
    """

    preprocess_result = _as_dict(state.get("preprocess_result"))
    rag_result = _as_dict(state.get("rag_result"))
    guideline_result = _as_dict(state.get("guideline_result"))
    visualization_result = _as_dict(state.get("visualization_result"))
    analysis_result = _as_dict(state.get("analysis_result"))
    analysis_plan = _as_dict(state.get("analysis_plan"))
    handoff = _as_dict(state.get("handoff")) or {}

    warnings: list[EvidenceWarningPayload] = []
    evidence_package: EvidencePackagePayload = {
        "analysis_status": _analysis_status(
            analysis_result,
            state.get("final_status"),
        ),
        "rag_retrieved_count": _as_int(
            rag_result.get("retrieved_count") if rag_result else None
        ),
        "guideline_retrieved_count": _as_int(
            guideline_result.get("retrieved_count")
            if guideline_result
            else None
        ),
        "applied_steps": _as_str_list(merged_context.get("applied_steps")),
    }

    source_id = _resolve_source_id(
        state=state,
        preprocess_result=preprocess_result,
        rag_result=rag_result,
    )
    if source_id:
        evidence_package["source_id"] = source_id

    if preprocess_result is not None:
        filename = _as_non_empty_str(preprocess_result.get("output_filename"))
        if filename:
            evidence_package["filename"] = filename
        preprocess_status = _as_non_empty_str(preprocess_result.get("status"))
        if preprocess_status:
            evidence_package["preprocess_status"] = preprocess_status
        if preprocess_status in {"failed", "cancelled"}:
            _append_warning(
                warnings,
                stage="preprocess",
                code="preprocess_not_applied",
                message=_as_non_empty_str(preprocess_result.get("error"))
                or _as_non_empty_str(preprocess_result.get("summary"))
                or preprocess_status,
            )

    used_columns = _first_non_empty_str_list(
        analysis_result.get("used_columns") if analysis_result else None,
        analysis_plan.get("used_columns") if analysis_plan else None,
    )
    if used_columns:
        evidence_package["used_columns"] = used_columns

    if analysis_result is not None:
        analysis_summary = _as_non_empty_str(analysis_result.get("summary"))
        if analysis_summary:
            evidence_package["analysis_summary"] = analysis_summary
        analysis_metrics = _as_dict(analysis_result.get("raw_metrics"))
        if analysis_metrics is not None:
            evidence_package["analysis_metrics"] = analysis_metrics
        analysis_table = _as_dict_list(analysis_result.get("table"))
        if analysis_table is not None:
            evidence_package["analysis_table"] = analysis_table
        if analysis_result.get("execution_status") == "fail":
            _append_warning(
                warnings,
                stage="analysis",
                code="analysis_failed",
                message=_as_non_empty_str(analysis_result.get("error_message"))
                or _as_non_empty_str(analysis_result.get("summary"))
                or "분석 실행이 실패했습니다.",
            )

    if bool(handoff.get("ask_analysis", False)) and not _analysis_has_evidence(
        analysis_result
    ):
        _append_warning(
            warnings,
            stage="analysis",
            code="analysis_missing",
            message="분석 결과가 최종 근거에 없습니다.",
        )

    if rag_result is not None:
        rag_summary = _as_non_empty_str(rag_result.get("evidence_summary"))
        if rag_summary:
            evidence_package["rag_evidence_summary"] = rag_summary
        if evidence_package["rag_retrieved_count"] == 0:
            _append_warning(
                warnings,
                stage="rag",
                code="rag_no_evidence",
                message=rag_summary or "검색 근거가 없습니다.",
            )

    if guideline_result is not None:
        guideline_status = _as_non_empty_str(guideline_result.get("status"))
        if guideline_status:
            evidence_package["guideline_status"] = guideline_status
        guideline_summary = _as_non_empty_str(
            guideline_result.get("evidence_summary")
        )
        if guideline_summary:
            evidence_package["guideline_evidence_summary"] = guideline_summary
        if guideline_status in {"no_evidence", "no_active_guideline"}:
            _append_warning(
                warnings,
                stage="guideline",
                code=guideline_status,
                message=guideline_summary or "활용 가능한 가이드라인 근거가 없습니다.",
            )

    evidence_package["warnings"] = warnings

    answerable = (
        _analysis_has_evidence(analysis_result)
        or _has_retrieval_evidence(evidence_package)
        or _visualization_has_evidence(visualization_result)
    )
    answer_quality: AnswerQualityPayload = {
        "answerable": answerable,
        "warnings": warnings,
    }
    if answerable:
        answer_quality["status"] = (
            "answerable" if _only_mild_warnings(warnings) else "limited"
        )
    else:
        answer_quality["status"] = "unanswerable"
        answer_quality["abstain_reason"] = _DEFAULT_ABSTAIN_REASON

    return evidence_package, answer_quality


def _as_dict(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, float):
        return max(int(value), 0)
    if isinstance(value, str):
        try:
            return max(int(value.strip()), 0)
        except ValueError:
            return 0
    return 0


def _append_warning(
    warnings: list[EvidenceWarningPayload],
    *,
    stage: str,
    code: str,
    message: str,
) -> None:
    warnings.append({"stage": stage, "code": code, "message": message})


def _resolve_source_id(
    *,
    state: Mapping[str, Any],
    preprocess_result: Mapping[str, Any] | None,
    rag_result: Mapping[str, Any] | None,
) -> str:
    if preprocess_result is not None:
        output_source_id = _as_non_empty_str(
            preprocess_result.get("output_source_id")
        )
        if output_source_id:
            return output_source_id
    if rag_result is not None:
        rag_source_id = _as_non_empty_str(rag_result.get("source_id"))
        if rag_source_id:
            return rag_source_id
    return _as_non_empty_str(state.get("source_id")) or ""


def _analysis_has_evidence(analysis_result: Mapping[str, Any] | None) -> bool:
    if (
        analysis_result is None
        or analysis_result.get("execution_status") != "success"
    ):
        return False
    return bool(
        _as_non_empty_str(analysis_result.get("summary"))
        or _as_dict(analysis_result.get("raw_metrics"))
        or _as_dict_list(analysis_result.get("table"))
    )


def _analysis_status(
    analysis_result: Mapping[str, Any] | None,
    final_status: Any,
) -> str:
    if analysis_result is not None:
        execution_status = _as_non_empty_str(
            analysis_result.get("execution_status")
        )
        if execution_status:
            return execution_status
    return _as_non_empty_str(final_status) or "missing"


def _has_retrieval_evidence(evidence_package: Mapping[str, Any]) -> bool:
    return _as_int(evidence_package.get("rag_retrieved_count")) > 0 or _as_int(
        evidence_package.get("guideline_retrieved_count")
    ) > 0


def _visualization_has_evidence(
    visualization_result: Mapping[str, Any] | None,
) -> bool:
    return (
        visualization_result is not None
        and visualization_result.get("status") == "generated"
    )


def _only_mild_warnings(warnings: list[EvidenceWarningPayload]) -> bool:
    return all(
        str(warning.get("code") or "") in _MILD_NO_EVIDENCE_CODES
        for warning in warnings
    )


def _first_non_empty_str_list(*values: Any) -> list[str]:
    for value in values:
        items = _as_str_list(value)
        if items:
            return items
    return []


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    deduped: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            deduped.append(text)
    return deduped


def _as_dict_list(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    rows = [item for item in value if isinstance(item, dict)]
    return rows if rows else []


def _as_non_empty_str(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()
