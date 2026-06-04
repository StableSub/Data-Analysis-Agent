from collections.abc import Mapping


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _as_text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _as_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _as_float(value: object) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return 0.0


def build_deterministic_ai_summary(payload: Mapping[str, object]) -> dict[str, str | list[str]]:
    summary = _as_mapping(payload.get("summary"))
    quality = _as_mapping(payload.get("quality"))
    stats = _as_mapping(payload.get("stats"))
    correlations = _as_mapping(payload.get("top_correlations"))
    outliers = _as_mapping(payload.get("outliers"))

    row_count = _as_int(summary.get("row_count"))
    column_count = _as_int(summary.get("column_count"))
    structure_summary = (
        f"총 {row_count}행, {column_count}개 컬럼 데이터입니다. "
        "먼저 결측치와 분석 기준이 될 컬럼을 확인하세요."
    )

    quality_issues = _build_quality_issues(quality)
    key_insights = _build_key_insights(stats, correlations, outliers)

    return {
        "structure_summary": structure_summary,
        "quality_issues": quality_issues
        or ["품질 이슈가 충분히 감지되지 않았습니다. 원본 컬럼 의미를 먼저 확인하세요."],
        "key_insights": key_insights
        or ["특별히 급한 신호는 없습니다. 분석 목적에 맞는 기준 컬럼을 정하고 다음 질문을 입력하세요."],
    }


def _build_quality_issues(quality: Mapping[str, object]) -> list[str]:
    missing_total = _as_int(quality.get("missing_total"))
    missing_ratio = _as_float(quality.get("missing_ratio"))
    if missing_total <= 0:
        return ["눈에 띄는 결측치는 없습니다. 바로 분석 질문을 정해도 괜찮습니다."]

    top_missing_columns = _as_list(quality.get("top_missing_columns"))
    first_missing = _as_mapping(top_missing_columns[0]) if top_missing_columns else {}
    column = _as_text(first_missing.get("column"))
    if column:
        return [f"결측치가 총 {missing_total}개 있습니다. 특히 '{column}' 컬럼을 먼저 확인하세요."]
    return [
        f"결측치가 총 {missing_total}개 있으며 전체 결측률은 {missing_ratio:.1%}입니다. "
        "분석 기준 컬럼에 몰려 있는지 먼저 확인하세요."
    ]


def _build_key_insights(
    stats: Mapping[str, object],
    correlations: Mapping[str, object],
    outliers: Mapping[str, object],
) -> list[str]:
    insights: list[str] = []
    stats_columns = _as_list(stats.get("columns"))
    if stats_columns:
        first_stat = _as_mapping(stats_columns[0])
        column = _as_text(first_stat.get("column"))
        if column:
            insights.append(
                f"대표 수치 컬럼은 '{column}'입니다. 값 범위가 예상과 맞는지 "
                "평균, 최솟값, 최댓값을 먼저 확인하세요."
            )

    pairs = _as_list(correlations.get("pairs"))
    if pairs:
        first_pair = _as_mapping(pairs[0])
        left = _as_text(first_pair.get("column_1"))
        right = _as_text(first_pair.get("column_2"))
        correlation = _as_float(first_pair.get("correlation"))
        if left and right:
            insights.append(
                f"'{left}'와 '{right}'는 함께 움직이는 경향이 있습니다(상관계수 {correlation:.2f}). "
                "둘 다 같은 의미를 담는지 확인하세요."
            )

    outlier_columns = _as_list(outliers.get("columns"))
    if outlier_columns:
        first_outlier = _as_mapping(outlier_columns[0])
        column = _as_text(first_outlier.get("column"))
        count = _as_int(first_outlier.get("outlier_count"))
        if column and count > 0:
            insights.append(
                f"'{column}' 컬럼에서 이상치 {count}개가 보입니다. "
                "입력 오류인지 실제 특이 사례인지 확인하세요."
            )

    return insights
