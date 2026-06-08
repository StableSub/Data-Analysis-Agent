from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from .dataset_answer_formatter import build_answer_content

_ANALYTIC_KEYWORDS = (
    "평균",
    "합계",
    "중앙값",
    "최대",
    "최소",
    "상관",
    "관계",
    "비율",
    "분포",
    "비교",
    "분석",
    "예측",
    "추천",
    "원인",
    "mean",
    "sum",
    "median",
    "max",
    "min",
    "correlation",
    "corr",
    "ratio",
    "distribution",
    "compare",
    "analysis",
)

_COMPLEX_DATASET_LOOKUP_KEYWORDS = (
    "삭제",
    "제거",
    "버려",
    "빼야",
    "제외",
    "불필요",
    "전처리",
    "정제",
    "학습",
    "훈련",
    "모델",
    "입력",
    "독립변수",
    "종속변수",
    "라벨",
    "feature",
    "features",
    "drop",
    "remove",
    "delete",
    "exclude",
    "preprocess",
    "clean",
    "cleaning",
    "train",
    "training",
    "model",
    "input",
    "label",
    "target",
)


@dataclass(frozen=True)
class FastDatasetAnswer:
    output: dict[str, object]
    fast_path_result: dict[str, object]


def try_fast_dataset_answer(
    question: str,
    dataset_context: Mapping[str, object],
) -> FastDatasetAnswer | None:
    """Return a metadata-only answer for simple dataset lookup questions."""

    normalized_question = _normalize_question(question)
    if not normalized_question:
        return None
    if dataset_context.get("available") is not True:
        return None

    intent = _detect_dataset_lookup_intent(normalized_question)
    if intent is None:
        return None

    content = build_answer_content(intent, dataset_context)
    if not content:
        return None

    return FastDatasetAnswer(
        output={
            "type": "fast_dataset_answer",
            "content": content,
        },
        fast_path_result={
            "status": "handled",
            "kind": "dataset_answer",
            "operation": intent,
            "eligibility_score": 1.0,
            "blockers": [],
        },
    )


def _normalize_question(question: str) -> str:
    return " ".join(str(question or "").strip().lower().split())


def _detect_dataset_lookup_intent(question: str) -> str | None:
    if _has_complex_dataset_lookup_keyword(question):
        return None
    if _is_interpretive_column_summary_question(question):
        return None

    if _matches_intent(question, "summary"):
        return "summary"

    if any(keyword in question for keyword in _ANALYTIC_KEYWORDS):
        return None

    matched_intents = [
        intent
        for intent in (
            "missing",
            "sample_rows",
            "shape",
            "row_count",
            "column_count",
            "numeric_columns",
            "categorical_columns",
            "datetime_columns",
            "boolean_columns",
            "identifier_columns",
            "column_types",
        )
        if _matches_intent(question, intent)
    ]
    if len(matched_intents) == 1:
        return matched_intents[0]
    if len(matched_intents) > 1:
        return None
    if _matches_intent(question, "columns"):
        return "columns"
    return None


def _has_complex_dataset_lookup_keyword(question: str) -> bool:
    return any(keyword in question for keyword in _COMPLEX_DATASET_LOOKUP_KEYWORDS)


def _is_interpretive_column_summary_question(question: str) -> bool:
    if any(
        phrase in question
        for phrase in (
            "데이터셋 요약",
            "데이터 요약",
            "데이터셋 설명",
            "데이터 설명",
            "dataset summary",
            "describe dataset",
        )
    ):
        return True

    has_column = any(
        keyword in question
        for keyword in ("컬럼", "열", "변수", "column", "columns", "schema")
    )
    if not has_column:
        return False

    return any(
        keyword in question
        for keyword in (
            "주요",
            "전체",
            "모든",
            "전부",
            "목록",
            "리스트",
            "스키마",
            "데이터 타입",
            "자료형",
            "의미",
            "뜻",
            "설명",
            "해석",
            "역할",
            "요약",
            "정리",
            "뭔지",
            "all columns",
            "every column",
            "column list",
            "schema",
            "dtype",
            "dtypes",
            "data type",
            "data types",
            "meaning",
            "describe",
            "explain",
            "summarize",
            "summary",
            "purpose",
            "role",
        )
    )


def _matches_intent(question: str, intent: str) -> bool:
    if intent == "summary":
        return any(
            keyword in question
            for keyword in ("데이터셋 설명", "데이터 설명", "데이터셋 요약", "dataset summary", "describe dataset")
        )
    if intent == "missing":
        return any(keyword in question for keyword in ("결측", "missing", "null", "널", "빈값"))
    if intent == "sample_rows":
        return any(keyword in question for keyword in ("샘플", "예시", "미리보기", "sample", "preview"))
    if intent == "shape":
        has_row = any(keyword in question for keyword in ("행", "row", "rows"))
        has_column_count = any(keyword in question for keyword in ("열", "컬럼", "column", "columns"))
        return (
            (has_row and has_column_count)
            or "행열" in question
            or "행/열" in question
            or "shape" in question
            or "크기" in question
        )
    if intent == "row_count":
        has_row = any(keyword in question for keyword in ("행", "row", "rows"))
        has_count = any(keyword in question for keyword in ("개수", "몇", "count", "how many"))
        has_column = any(keyword in question for keyword in ("열", "컬럼", "column", "columns"))
        return has_row and has_count and not has_column
    if intent == "column_count":
        has_column = any(keyword in question for keyword in ("열", "컬럼", "column", "columns"))
        has_count = any(keyword in question for keyword in ("개수", "몇", "count", "how many"))
        has_row = any(keyword in question for keyword in ("행", "row", "rows"))
        return has_column and has_count and not has_row
    if intent == "numeric_columns":
        return any(keyword in question for keyword in ("숫자형", "수치형", "numeric", "numerical", "number"))
    if intent == "categorical_columns":
        return any(keyword in question for keyword in ("범주형", "카테고리", "categorical", "category"))
    if intent == "datetime_columns":
        return any(keyword in question for keyword in ("날짜", "시간", "일시")) or any(
            _english_token_mentioned(question=question, token=token)
            for token in ("datetime", "date", "time")
        )
    if intent == "boolean_columns":
        return any(keyword in question for keyword in ("불리언", "참거짓", "boolean", "bool"))
    if intent == "identifier_columns":
        return any(keyword in question for keyword in ("식별자", "아이디", "identifier", "id column"))
    if intent == "column_types":
        return any(keyword in question for keyword in ("데이터 타입", "자료형", "dtype", "dtypes", "data type", "data types"))
    if intent == "columns":
        if any(keyword in question for keyword in ("행", "row", "rows", "개수", "count", "shape", "크기")):
            return False
        return any(keyword in question for keyword in ("컬럼", "열", "스키마", "변수", "column", "columns", "schema"))
    return False


def _english_token_mentioned(*, question: str, token: str) -> bool:
    return re.search(rf"(?<![a-z0-9_]){re.escape(token)}(?![a-z0-9_])", question) is not None
