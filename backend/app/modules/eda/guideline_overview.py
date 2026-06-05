from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .schemas import EDADatasetOverview
from ..guidelines.service import GuidelineService


def build_guideline_context(
    *,
    source_id: str,
    payload: Mapping[str, object],
    guideline_source_id: str | None,
    guideline_service: GuidelineService | None,
) -> dict[str, object] | None:
    if guideline_service is None:
        return None

    selected_guideline_source_id = (guideline_source_id or "").strip()
    guideline = (
        guideline_service.get_guideline_by_source_id(selected_guideline_source_id)
        if selected_guideline_source_id
        else guideline_service.get_active_guideline()
    )
    if guideline is None:
        return None

    storage_path = getattr(guideline, "storage_path", "")
    guideline_text = _load_guideline_text(Path(str(storage_path)))
    if not guideline_text.strip():
        return None

    columns = _coerce_string_list(_nested_get(payload, "summary", "columns"))
    dataset = _as_mapping(payload.get("dataset"))
    filename = str(dataset.get("filename") or source_id)
    terms = _build_guideline_match_terms(columns=columns, filename=filename)
    selected_lines, matched_terms = _select_guideline_lines(
        guideline_text,
        terms=terms,
    )

    context_text = "\n".join(selected_lines).strip()
    if not context_text:
        context_text = guideline_text[:4000].strip()

    return {
        "guideline_source_id": str(
            getattr(guideline, "source_id", selected_guideline_source_id)
        ),
        "guideline_filename": str(getattr(guideline, "filename", "")),
        "matched_terms": matched_terms[:12],
        "content": context_text[:8000],
    }


def build_dataset_overview(
    *,
    summary_content: Mapping[str, Any],
    guideline_context: Mapping[str, object] | None,
    payload: Mapping[str, object],
) -> EDADatasetOverview | None:
    if guideline_context is None:
        return None

    raw_overview = summary_content.get("dataset_overview")
    overview = raw_overview if isinstance(raw_overview, Mapping) else {}
    summary = str(overview.get("summary") or "").strip()
    key_points = _coerce_string_list(overview.get("key_points"))

    if not summary:
        summary = _fallback_dataset_overview_summary(
            payload=payload,
            guideline_context=guideline_context,
        )
    if not key_points:
        key_points = _fallback_dataset_overview_points(guideline_context)

    return EDADatasetOverview(
        guideline_source_id=str(guideline_context.get("guideline_source_id") or ""),
        guideline_filename=str(guideline_context.get("guideline_filename") or ""),
        summary=summary,
        key_points=key_points[:4],
        matched_terms=_coerce_string_list(guideline_context.get("matched_terms"))[:12],
    )


def _load_guideline_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts: list[str] = []
        total_len = 0
        for page in reader.pages:
            text = page.extract_text() or ""
            if not text.strip():
                continue
            remaining = 20_000 - total_len
            if remaining <= 0:
                break
            snippet = text[:remaining]
            parts.append(snippet)
            total_len += len(snippet)
            if total_len >= 20_000:
                break
        return "\n".join(parts)
    return path.read_text(encoding="utf-8", errors="ignore")[:20_000]


def _build_guideline_match_terms(*, columns: list[str], filename: str) -> list[str]:
    terms: list[str] = []
    for value in [filename, Path(filename).stem, *columns]:
        normalized = str(value).strip()
        if not normalized or normalized in terms:
            continue
        terms.append(normalized)
    return terms


def _select_guideline_lines(
    text: str,
    *,
    terms: list[str],
) -> tuple[list[str], list[str]]:
    normalized_terms = [term for term in terms if len(term) >= 2]
    selected: list[str] = []
    matched_terms: list[str] = []
    for raw_line in text.replace("\r\n", "\n").split("\n"):
        line = " ".join(raw_line.split())
        if not line:
            continue
        line_lower = line.lower()
        line_matches = [
            term
            for term in normalized_terms
            if term.lower() in line_lower
        ]
        if not line_matches:
            continue
        selected.append(line[:500])
        for term in line_matches:
            if term not in matched_terms:
                matched_terms.append(term)
        if len(selected) >= 12:
            break
    if selected:
        return selected, matched_terms
    return _first_non_empty_lines(text, limit=6), []


def _fallback_dataset_overview_summary(
    *,
    payload: Mapping[str, object],
    guideline_context: Mapping[str, object],
) -> str:
    dataset = _as_mapping(payload.get("dataset"))
    summary = _as_mapping(payload.get("summary"))
    filename = str(dataset.get("filename") or dataset.get("source_id") or "선택한 데이터")
    row_count_raw = summary.get("row_count")
    column_count_raw = summary.get("column_count")
    row_count = row_count_raw if isinstance(row_count_raw, int) else 0
    column_count = column_count_raw if isinstance(column_count_raw, int) else 0
    context_text = str(guideline_context.get("content") or "")
    first_line = (
        _first_non_empty_lines(context_text, limit=1)
        or ["선택한 지침에서 데이터 설명 근거를 확인했습니다."]
    )[0]
    return (
        f"{filename}은(는) 총 {row_count:,}행, {column_count:,}개 컬럼으로 구성된 데이터입니다. "
        f"선택한 가이드라인 근거상 {first_line}"
    )


def _fallback_dataset_overview_points(
    guideline_context: Mapping[str, object],
) -> list[str]:
    content = str(guideline_context.get("content") or "")
    points = _first_non_empty_lines(content, limit=3)
    return points or ["선택한 가이드라인에서 데이터 설명 근거를 확인했습니다."]


def _coerce_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _first_non_empty_lines(text: str, *, limit: int = 3) -> list[str]:
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").split("\n"):
        line = " ".join(raw_line.split())
        if not line:
            continue
        lines.append(line[:180])
        if len(lines) >= limit:
            break
    return lines


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _nested_get(
    payload: Mapping[str, object],
    first_key: str,
    second_key: str,
) -> object:
    first_value = _as_mapping(payload.get(first_key))
    return first_value.get(second_key)
