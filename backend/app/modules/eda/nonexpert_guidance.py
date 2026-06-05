from collections.abc import Mapping, Sequence
from typing import Literal

from .schemas import EDASuggestedQuestion


MAX_SUGGESTED_QUESTIONS = 5
IDENTIFIER_MARKERS = ("unnamed", "serial", "uuid", "token")
IDENTIFIER_SUFFIXES = ("_id", "_no", "_code", " id", " no", " code")
TIME_MARKERS = ("date", "time", "timestamp")
SuggestedQuestionCategory = Literal[
    "overview",
    "quality",
    "comparison",
    "trend",
    "outlier",
    "visualization",
]
SuggestedQuestionPriority = Literal["high", "medium", "low"]


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _as_sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, Sequence) and not isinstance(value, str | bytes) else ()


def _string_list(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def _type_columns(payload: Mapping[str, object]) -> Mapping[str, list[str]]:
    column_types = _as_mapping(payload.get("column_types"))
    raw_type_columns = _as_mapping(column_types.get("type_columns"))
    return {
        str(column_type): _string_list(columns)
        for column_type, columns in raw_type_columns.items()
    }


def _first_nonempty(*groups: Sequence[str]) -> str | None:
    for group in groups:
        for value in group:
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _normalized_column_name(column: str) -> str:
    return column.strip().lower()


def _is_identifier_like(column: str) -> bool:
    normalized = _normalized_column_name(column)
    compact = normalized.replace(" ", "_")
    if not normalized:
        return True
    if normalized == "id" or compact == "index":
        return True
    if any(marker in normalized for marker in IDENTIFIER_MARKERS):
        return True
    return any(compact.endswith(suffix.strip().replace(" ", "_")) for suffix in IDENTIFIER_SUFFIXES)


def _is_time_like(column: str) -> bool:
    normalized = _normalized_column_name(column)
    return any(marker in normalized for marker in TIME_MARKERS)


def _analysis_columns(columns: Sequence[str], *, allow_time: bool = False) -> list[str]:
    return [
        column.strip()
        for column in columns
        if column.strip()
        and not _is_identifier_like(column)
        and (allow_time or not _is_time_like(column))
    ]


def _top_missing_column(payload: Mapping[str, object]) -> str | None:
    quality = _as_mapping(payload.get("quality"))
    top_missing_columns = _as_sequence(quality.get("top_missing_columns"))
    for item in top_missing_columns:
        column = _as_mapping(item).get("column")
        if isinstance(column, str) and column.strip():
            return column.strip()
    return None


def _top_outlier_column(payload: Mapping[str, object], metric_columns: Sequence[str]) -> str | None:
    metric_set = set(metric_columns)
    outliers = _as_mapping(payload.get("outliers"))
    outlier_columns = _as_sequence(outliers.get("columns"))
    for item in outlier_columns:
        column_payload = _as_mapping(item)
        outlier_count = column_payload.get("outlier_count")
        column = column_payload.get("column")
        if (
            isinstance(column, str)
            and column.strip() in metric_set
            and isinstance(outlier_count, int)
            and outlier_count > 0
        ):
            return column.strip()
    return None


def _append_unique(
    questions: list[EDASuggestedQuestion],
    *,
    title: str,
    question: str,
    rationale: str,
    category: SuggestedQuestionCategory,
    priority: SuggestedQuestionPriority = "medium",
) -> None:
    if len(questions) >= MAX_SUGGESTED_QUESTIONS:
        return
    normalized_question = question.strip()
    if not normalized_question:
        return
    if any(item.question == normalized_question for item in questions):
        return
    questions.append(
        EDASuggestedQuestion(
            title=title.strip(),
            question=normalized_question,
            rationale=rationale.strip(),
            category=category,
            priority=priority,
        )
    )


def build_suggested_questions(payload: Mapping[str, object]) -> list[EDASuggestedQuestion]:
    type_columns = _type_columns(payload)
    summary = _as_mapping(payload.get("summary"))
    all_columns = _string_list(summary.get("columns"))
    numeric_columns = _analysis_columns(type_columns.get("numerical", []), allow_time=True)
    datetime_columns = _analysis_columns(type_columns.get("datetime", []), allow_time=True)
    group_key_columns = _analysis_columns(type_columns.get("group_key", []))
    categorical_columns = _analysis_columns(type_columns.get("categorical", []))
    fallback_group_columns = [
        column
        for column in _analysis_columns(all_columns)
        if column not in numeric_columns and column not in datetime_columns
    ]

    metric_column = _first_nonempty(numeric_columns)
    group_column = _first_nonempty(group_key_columns, categorical_columns, fallback_group_columns)
    datetime_column = _first_nonempty(datetime_columns)
    missing_column = _top_missing_column(payload)
    outlier_column = _top_outlier_column(payload, numeric_columns) or metric_column

    questions: list[EDASuggestedQuestion] = []
    _append_unique(
        questions,
        title="데이터 구조 먼저 보기",
        question="이 데이터의 주요 컬럼과 전체 구조를 쉬운 말로 요약해줘.",
        rationale="분석을 시작하기 전에 행, 컬럼, 타입 구성을 먼저 파악할 수 있습니다.",
        category="overview",
        priority="high",
    )

    if missing_column:
        _append_unique(
            questions,
            title="결측치 영향 확인",
            question=f"'{missing_column}' 결측치가 분석 결과에 어떤 영향을 주는지 쉽게 설명해줘.",
            rationale="결측치가 많은 컬럼은 평균, 비율, 그룹 비교 결과를 왜곡할 수 있습니다.",
            category="quality",
            priority="high",
        )

    if group_column and metric_column:
        _append_unique(
            questions,
            title="그룹별 차이 비교",
            question=f"'{group_column}'별 '{metric_column}' 평균과 차이를 비교해줘.",
            rationale="범주 또는 그룹 기준으로 핵심 수치가 어떻게 달라지는지 바로 확인할 수 있습니다.",
            category="comparison",
            priority="high",
        )

    if datetime_column and metric_column:
        _append_unique(
            questions,
            title="시간 흐름 보기",
            question=f"'{datetime_column}' 기준으로 '{metric_column}' 추세와 변화를 보여줘.",
            rationale="날짜나 시간 컬럼이 있으면 증가, 감소, 급변 구간을 먼저 살펴볼 수 있습니다.",
            category="trend",
            priority="medium",
        )

    if outlier_column:
        _append_unique(
            questions,
            title="이상치 확인",
            question=f"'{outlier_column}'에서 이상치가 있는지 확인하고 원인을 추정해줘.",
            rationale="극단값은 입력 오류일 수도 있고 실제 중요한 사례일 수도 있습니다.",
            category="outlier",
            priority="medium",
        )

    if group_column and metric_column:
        _append_unique(
            questions,
            title="차트로 이해하기",
            question=f"'{group_column}'와 '{metric_column}' 관계를 초보자가 이해하기 쉬운 차트로 만들어줘.",
            rationale="표보다 차트가 그룹 차이나 패턴을 더 빠르게 보여줄 수 있습니다.",
            category="visualization",
            priority="low",
        )

    if len(questions) == 1 and all_columns:
        _append_unique(
            questions,
            title="분석 질문 추천",
            question=f"{', '.join(all_columns[:4])} 컬럼을 바탕으로 처음 물어볼 질문 3개를 추천해줘.",
            rationale="분석 목표가 아직 분명하지 않을 때 시작점을 만들 수 있습니다.",
            category="overview",
            priority="medium",
        )

    return questions
