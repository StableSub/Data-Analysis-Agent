from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from ...core.ai import LLMGateway, PromptRegistry
from .deterministic_grouped_metrics import build_grouped_metric_code
from .deterministic_quality import (
    build_logical_group_count_code,
    build_quality_status_summary_code,
)
from .deterministic_outlier import build_numeric_outlier_code
from .schemas import (
    AnalysisError,
    AnalysisPlan,
    AnalysisPlanDraft,
    ColumnGroundingResult,
    MetadataSnapshot,
    QuestionUnderstanding,
)

PROMPTS = PromptRegistry(
    {
        "question_understanding.system": (
            "너는 데이터 분석 질문 해석기다. "
            "사용자 질문을 QuestionUnderstanding 스키마로 구조화하라. "
            "질문이 모호하면 ambiguity_status를 needs_clarification으로 설정하고 clarification_message를 작성하라. "
            "metric_keywords와 group_keywords는 실제 컬럼명이 아니라 질문에서 추출한 개념 중심 키워드로 작성하라. "
            "질문에 3월, 2월, 이번 달처럼 상대적으로 해석 가능한 월/기간 표현이 있고 dataset_meta의 시간 범위 안에서 자연스럽게 해석 가능하면 불필요한 clarification을 만들지 마라."
        ),
        "plan_draft.system": (
            "너는 데이터 분석 플래너다. "
            "입력으로 주어진 질문 해석 결과, 컬럼 grounding 결과, 데이터셋 메타정보를 바탕으로 "
            "AnalysisPlanDraft 스키마 형식으로만 반환하라. "
            "질문이 모호하면 ambiguity_status를 needs_clarification으로 설정하라. "
            "metrics는 반드시 최소 1개 이상 포함하라. "
            "결측치 현황, missing value, missing rate, 전처리 계획 요청에서는 "
            "column, columns, column_name, column_names, column_type, data_type, feature_type 같은 "
            "추상 축을 group_by, filters, visualization_hint.x, visualization_hint.series에 넣지 마라. "
            "사용자가 차트나 그래프를 명시적으로 요청하지 않았다면 visualization_hint.preferred_chart는 none으로 두어라. "
            "컬럼별 결측 현황은 실제 컬럼들을 metric으로 열거해서 표현하고, 메타 수준 분류는 summary/objective 설명으로만 다뤄라. "
            "관계 분석(scatter, correlation, relationship) 질문에서는 우선 원본 수치 컬럼 2개를 직접 사용하라. "
            "관계 분석 질문에서는 사용자가 평균, 그룹별 평균, 요약을 명시적으로 요구하지 않았다면 group_by를 기본적으로 비워 두고 원시 행 단위 x/y 포인트를 사용하라. "
            "line, material_type 같은 범주형 컬럼이 있으면 집계 기준으로 쓰기보다 series/color 구분으로 우선 사용하라. "
            "파생 컬럼(derived_columns)은 원본 컬럼만으로 질문에 답할 수 없을 때만 추가하라. "
            "특히 ratio, arithmetic 같은 파생 컬럼은 사용자가 명시적으로 요청하지 않았다면 만들지 마라. "
            "관계 분석 질문에서는 correlation, slope, regression 같은 추가 관계 지표(metric)를 기본적으로 만들지 마라. "
            "사용자가 명시적으로 상관계수나 회귀계수를 요청한 경우가 아니면, 원본 두 컬럼과 scatter 시각화에 필요한 최소 metric만 사용하라. "
            "월별/주별/일별 추세 질문에서는 timestamp/date 컬럼을 분석 단계에서 버킷팅하여 집계하라. 이 때문에 preprocess 파생 컬럼이 필요하다고 가정하지 마라. "
            "라인별 평균 불량률 추세 같은 질문이면 time bucket + series(line) + avg metric 구조로 계획하라."
        ),
        "code_generation.system": (
            "너는 pandas 기반 데이터 분석 코드 생성기다. "
            "반드시 순수 Python 코드만 반환하라. 마크다운 코드블록은 금지한다. "
            "입력 데이터는 dataset_path 변수와 이미 로드된 pandas DataFrame df, 그리고 json/pd로 주어진다. "
            "가능하면 df를 직접 사용하고, dataset_path를 다시 가공하거나 파일 경로를 다루지 마라. "
            "stdout에는 JSON 하나만 출력해야 하며 키는 summary, table, raw_metrics, used_columns 이어야 한다. "
            "raw_metrics는 항상 JSON object(dict)여야 하며 절대 null로 출력하지 마라. 값이 없으면 빈 객체 {}를 사용하라. "
            "pandas fillna(value=None), fillna(None), fillna()는 금지한다. JSON null 보존이 필요하면 where(pd.notna(...), None)을 사용하라. "
            "used_columns에는 df에서 실제로 읽은 원본 데이터셋 컬럼만 포함하라. "
            "month, year_month, ratio, temp_speed_ratio 같은 파생/임시/helper 컬럼은 used_columns에 넣지 마라. "
            "코드 안에서 import 문은 사용하지 마라. 필요한 JSON 출력은 이미 제공된 json을 사용하라. "
            "추가 파일 읽기/쓰기, 환경 변수 접근, 프로세스 실행, 네트워크 호출은 금지한다. "
            "analysis_plan.time_context.relative_range_resolved가 있으면 start/end를 그대로 사용하고, now/today/current month를 다시 계산하지 마라. "
            "metric.positive_value가 null이 아니면 해당 metric은 컬럼 값이 positive_value와 같은 행의 비율이다. "
            "그룹별 계산에서는 그룹 전체 행을 분모로 두고 positive_value 일치 행을 분자로 사용하라. "
            "time_context.grain이 month이고 relative_expr가 last 3 months 계열이면, 현재 진행 중인 월은 제외하고 최근 3개 완료월만 사용하라. "
            "월별/주별/일별 추세는 전처리 없이 분석 코드 안에서 datetime 컬럼을 to_datetime 후 버킷팅해서 처리하라. "
            "analysis_plan.derived_columns에 정의된 파생 컬럼이 있으면, 코드에서 그 name을 그대로 사용하라. 임의로 month, year_month 같은 다른 이름으로 바꾸지 마라. "
            "analysis_plan.visualization_hint.preferred_chart가 scatter이고 x/y가 주어지면, table은 집계 평균 1행이 아니라 원본 관측치 기반의 점 데이터로 구성하라. "
            "즉 table 각 row에는 visualization_hint.x, visualization_hint.y, 그리고 series가 있으면 그 컬럼을 포함하라. "
            "사용자가 평균이나 집계를 명시적으로 요청하지 않았다면 scatter 질문에서 x/y를 avg로 집계하지 마라. "
            "relationship/scatter 질문에서 line, material_type 같은 범주형 컬럼이 있더라도 그 컬럼으로 groupby하여 평균 3점, 5점 같은 요약 scatter를 만들지 마라. "
            "추세 질문에서 line 같은 series 컬럼이 있으면 month/date 버킷과 함께 groupby하여 시리즈별 평균값을 계산하라. "
            "dataset_meta나 analysis_plan에 이미 존재하는 컬럼이 있으면 해당 컬럼이 없다고 가정하지 마라."
        ),
        "code_repair.system": (
            "너는 pandas 분석 코드 수정기다. "
            "반드시 순수 Python 코드만 반환하라. 마크다운 코드블록은 금지한다. "
            "기존 AnalysisPlan은 유지하고, 주어진 실패 원인을 반영해 코드만 수정하라. "
            "stdout JSON 계약(summary, table, raw_metrics, used_columns)을 반드시 지켜라. "
            "raw_metrics는 항상 JSON object(dict)여야 하며 절대 null로 출력하지 마라. 값이 없으면 빈 객체 {}를 사용하라. "
            "pandas fillna(value=None), fillna(None), fillna()는 금지한다. JSON null 보존이 필요하면 where(pd.notna(...), None)을 사용하라. "
            "used_columns에는 df에서 실제로 읽은 원본 데이터셋 컬럼만 포함하라. "
            "month, year_month, ratio, temp_speed_ratio 같은 파생/임시/helper 컬럼은 used_columns에 넣지 마라. "
            "입력 데이터는 dataset_path 변수와 이미 로드된 pandas DataFrame df, 그리고 json/pd로 주어진다. "
            "코드 안에서 import 문은 사용하지 마라. 필요한 JSON 출력은 이미 제공된 json을 사용하라. "
            "추가 파일 읽기/쓰기, 환경 변수 접근, 프로세스 실행, 네트워크 호출은 금지한다. "
            "analysis_plan.time_context.relative_range_resolved가 있으면 start/end를 그대로 사용하고, now/today/current month를 다시 계산하지 마라. "
            "metric.positive_value가 null이 아니면 해당 metric은 컬럼 값이 positive_value와 같은 행의 비율이다. "
            "그룹별 계산에서는 그룹 전체 행을 분모로 두고 positive_value 일치 행을 분자로 사용하라. "
            "time_context.grain이 month이고 relative_expr가 last 3 months 계열이면, 현재 진행 중인 월은 제외하고 최근 3개 완료월만 사용하라. "
            "월별/주별/일별 추세는 분석 코드 안에서 datetime 컬럼 버킷팅으로 처리하라. "
            "analysis_plan.derived_columns에 정의된 파생 컬럼이 있으면, 코드에서 그 name을 그대로 사용하라. 임의로 month, year_month 같은 다른 이름으로 바꾸지 마라. "
            "scatter 시각화 질문이면 table을 원본 x/y 점들로 유지하고, 평균 1행이나 그룹 평균 몇 개 점으로 축약하지 마라. "
            "relationship/scatter 질문에서 series 컬럼은 색상/시리즈 구분용으로 유지하고, 사용자가 명시적으로 요청하지 않았다면 groupby 평균 scatter로 바꾸지 마라."
        ),
    }
)

_CODE_FENCE_RE = re.compile(r"^```(?:python)?\s*|\s*```$", re.MULTILINE)


class AnalysisRunService:
    """LLM-backed analysis planning and code generation service."""

    def __init__(self, *, default_model: str = "gpt-5-nano") -> None:
        self.default_model = default_model
        self.llm = LLMGateway(default_model=default_model)

    # 질문을 분석 가능한 의미 구조로 바꾼다.
    def build_question_understanding(
        self,
        *,
        question: str,
        dataset_meta: MetadataSnapshot | dict[str, Any],
        model_id: str | None = None,
    ) -> QuestionUnderstanding:
        metadata = self._ensure_metadata_snapshot(dataset_meta)
        return self.llm.invoke_structured(
            schema=QuestionUnderstanding,
            model_id=model_id,
            messages=[
                SystemMessage(
                    content=PROMPTS.load_prompt("question_understanding.system")
                ),
                HumanMessage(
                    content=(
                        f"question:\n{question.strip()}\n\n"
                        f"dataset_meta:\n{self._to_json(metadata.model_dump())}"
                    )
                ),
            ],
        )

    # 질문 해석 결과를 바탕으로 분석 계획 초안을 만든다.
    def build_analysis_plan_draft(
        self,
        *,
        question: str,
        question_understanding: QuestionUnderstanding | dict[str, Any],
        column_grounding: ColumnGroundingResult | dict[str, Any],
        dataset_meta: MetadataSnapshot | dict[str, Any],
        model_id: str | None = None,
    ) -> AnalysisPlanDraft:
        understanding = self._ensure_question_understanding(question_understanding)
        grounding = self._ensure_column_grounding(column_grounding)
        metadata = self._ensure_metadata_snapshot(dataset_meta)
        return self.llm.invoke_structured(
            schema=AnalysisPlanDraft,
            model_id=model_id,
            messages=[
                SystemMessage(content=PROMPTS.load_prompt("plan_draft.system")),
                HumanMessage(
                    content=(
                        f"question:\n{question.strip()}\n\n"
                        f"question_understanding:\n{self._to_json(understanding.model_dump())}\n\n"
                        f"column_grounding:\n{self._to_json(grounding.model_dump())}\n\n"
                        f"dataset_meta:\n{self._to_json(metadata.model_dump())}"
                    )
                ),
            ],
        )

    # 최종 AnalysisPlan을 바탕으로 실제 pandas 분석 코드를 생성한다.
    def generate_analysis_code(
        self,
        *,
        question: str,
        analysis_plan: AnalysisPlan | dict[str, Any],
        model_id: str | None = None,
    ) -> str:
        plan = self._ensure_plan(analysis_plan)
        result = self.llm.invoke(
            model_id=model_id,
            messages=[
                SystemMessage(content=PROMPTS.load_prompt("code_generation.system")),
                HumanMessage(
                    content=(
                        f"question:\n{question.strip()}\n\n"
                        f"analysis_plan:\n{self._to_json(plan.model_dump())}\n\n"
                        "df는 이미 로드되어 있으므로 기본적으로 df를 직접 사용하라. "
                        "dataset_path로 CSV를 다시 읽거나 df 존재 여부를 검사하는 방어 로직을 만들지 마라."
                    )
                ),
            ],
        )
        code = self._normalize_code_output(
            result.content if hasattr(result, "content") else str(result)
        )
        return self._replace_json_payload_with_deterministic_code(code, plan)

    # 기존 코드가 실패했을 때 에러를 반영해서 코드만 다시 생성한다.
    def repair_analysis_code(
        self,
        *,
        question: str,
        analysis_plan: AnalysisPlan | dict[str, Any],
        previous_code: str,
        analysis_error: AnalysisError | dict[str, Any],
        model_id: str | None = None,
    ) -> str:
        plan = self._ensure_plan(analysis_plan)
        error = self._ensure_analysis_error(analysis_error)
        result = self.llm.invoke(
            model_id=model_id,
            messages=[
                SystemMessage(content=PROMPTS.load_prompt("code_repair.system")),
                HumanMessage(
                    content=(
                        f"question:\n{question.strip()}\n\n"
                        f"analysis_plan:\n{self._to_json(plan.model_dump())}\n\n"
                        f"previous_code:\n{previous_code}\n\n"
                        f"analysis_error:\n{self._to_json(error.model_dump())}\n\n"
                        "df는 이미 로드되어 있으므로 기본적으로 df를 직접 사용하라. "
                        "dataset_path로 CSV를 다시 읽거나 df 존재 여부를 검사하는 방어 로직을 만들지 마라."
                    )
                ),
            ],
        )
        code = self._normalize_code_output(
            result.content if hasattr(result, "content") else str(result)
        )
        return self._replace_json_payload_with_deterministic_code(code, plan)

    def _normalize_code_output(self, value: str) -> str:
        code = str(value or "").strip()
        code = _CODE_FENCE_RE.sub("", code).strip()
        return code

    def _replace_json_payload_with_deterministic_code(
        self,
        code: str,
        plan: AnalysisPlan,
    ) -> str:
        if not _is_json_payload_only(code):
            return code
        fallback = build_deterministic_analysis_code(plan)
        return fallback or code

    def _to_json(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, default=str)

    def _ensure_question_understanding(
        self,
        question_understanding: QuestionUnderstanding | dict[str, Any],
    ) -> QuestionUnderstanding:
        if isinstance(question_understanding, QuestionUnderstanding):
            return question_understanding
        return QuestionUnderstanding.model_validate(question_understanding)

    def _ensure_column_grounding(
        self,
        column_grounding: ColumnGroundingResult | dict[str, Any],
    ) -> ColumnGroundingResult:
        if isinstance(column_grounding, ColumnGroundingResult):
            return column_grounding
        return ColumnGroundingResult.model_validate(column_grounding)

    def _ensure_metadata_snapshot(
        self,
        dataset_meta: MetadataSnapshot | dict[str, Any],
    ) -> MetadataSnapshot:
        if isinstance(dataset_meta, MetadataSnapshot):
            return dataset_meta
        return MetadataSnapshot.model_validate(dataset_meta)

    def _ensure_plan(
        self, analysis_plan: AnalysisPlan | dict[str, Any]
    ) -> AnalysisPlan:
        if isinstance(analysis_plan, AnalysisPlan):
            return analysis_plan
        return AnalysisPlan.model_validate(analysis_plan)

    def _ensure_analysis_error(
        self,
        analysis_error: AnalysisError | dict[str, Any],
    ) -> AnalysisError:
        if isinstance(analysis_error, AnalysisError):
            return analysis_error
        return AnalysisError.model_validate(analysis_error)


def _is_json_payload_only(code: str) -> bool:
    try:
        payload = json.loads(code)
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict)


def build_deterministic_analysis_code(plan: AnalysisPlan) -> str | None:
    outlier_code = build_numeric_outlier_code(plan)
    if outlier_code is not None:
        return outlier_code
    grouped_metric_code = build_grouped_metric_code(plan)
    if grouped_metric_code is not None:
        return grouped_metric_code
    quality_code = build_quality_status_summary_code(plan)
    if quality_code is not None:
        return quality_code
    logical_group_count_code = build_logical_group_count_code(plan)
    if logical_group_count_code is not None:
        return logical_group_count_code
    time_bucket_code = _build_time_bucket_aggregation_code(plan)
    if time_bucket_code is not None:
        return time_bucket_code
    group_by_code = _build_simple_group_by_metric_code(plan)
    if group_by_code is not None:
        return group_by_code
    return _build_scatter_points_code(plan)


def _build_time_bucket_aggregation_code(plan: AnalysisPlan) -> str | None:
    if not plan.time_context or not plan.time_context.time_column:
        return None
    if plan.group_by:
        return None
    time_column = plan.time_context.time_column
    time_alias = _time_axis_alias(plan.time_context.grain)
    if time_alias is None:
        return None

    filter_lines = _build_filter_lines(plan)
    if filter_lines is None:
        return None
    metric_lines = _build_metric_lines(plan)
    if metric_lines is None:
        return None

    used_columns = [
        column
        for column in plan.required_columns
        if column in plan.metadata_snapshot.columns
    ]
    if time_column not in used_columns:
        used_columns.append(time_column)

    lines = [
        "work = df.copy()",
        (
            f"work[{time_alias!r}] = pd.to_datetime("
            f"work[{time_column!r}], errors='coerce')"
            f"{_time_bucket_expression(plan.time_context.grain)}"
        ),
        f"work = work[work[{time_alias!r}].notna()].copy()",
        *filter_lines,
        "rows = []",
        f"for bucket_value, group in work.groupby({time_alias!r}, dropna=False, sort=True):",
        f"    row = {{{time_alias!r}: str(bucket_value)}}",
        *metric_lines,
        "    rows.append(row)",
        "total_count = int(len(work))",
        _total_defect_line(plan),
        "date_values = [row.get('date') for row in rows if row.get('date')]",
        "summary = (",
        "    f\"기간 {date_values[0]}부터 {date_values[-1]}까지 \"",
        "    f\"총 {total_count}건 중 불량 {total_defects}건을 집계했습니다.\"",
        "    if date_values",
        "    else f\"집계 가능한 데이터가 없습니다. 총 {total_count}건을 확인했습니다.\"",
        ")",
        "raw_metrics = {",
        "    'total_count': total_count,",
        "    'total_defects': total_defects,",
        "}",
        "print(json.dumps({",
        "    'summary': summary,",
        "    'table': rows,",
        "    'raw_metrics': raw_metrics,",
        f"    'used_columns': {used_columns!r},",
        "}, ensure_ascii=False))",
    ]
    return "\n".join(lines)


def _build_simple_group_by_metric_code(plan: AnalysisPlan) -> str | None:
    if plan.time_context is not None or plan.expected_output.require_time_axis:
        return None
    if len(plan.group_by) != 1 or len(plan.metrics) != 1:
        return None
    group_column = plan.group_by[0]
    metric = plan.metrics[0]
    if group_column not in plan.metadata_snapshot.columns:
        return None
    if metric.column and metric.column not in plan.metadata_snapshot.columns:
        return None
    if metric.aggregation not in {"count", "sum", "avg", "mean", "rate"}:
        return None
    if metric.aggregation in {"sum", "avg", "mean", "rate"} and not metric.column:
        return None
    if metric.aggregation == "rate" and metric.positive_value is None:
        return None

    filter_lines = _build_filter_lines(plan)
    if filter_lines is None:
        return None
    used_columns = _used_source_columns(plan, [group_column, metric.column])
    alias = metric.alias
    lines = [
        "work = df.copy()",
        *filter_lines,
        "rows = []",
        f"for group_value, group in work.groupby({group_column!r}, dropna=False, sort=True):",
        (
            "    group_key = None if pd.isna(group_value) "
            "else str(group_value)"
        ),
        f"    row = {{{group_column!r}: group_key}}",
    ]
    if metric.aggregation == "count":
        if metric.column:
            lines.append(
                f"    metric_value = int(group[{metric.column!r}].count())"
            )
        else:
            lines.append("    metric_value = int(len(group))")
    elif metric.aggregation == "sum":
        lines.extend(
            [
                f"    metric_raw = group[{metric.column!r}].sum()",
                "    metric_value = (",
                "        int(metric_raw)",
                "        if pd.notna(metric_raw) and float(metric_raw).is_integer()",
                "        else float(metric_raw)",
                "    )",
            ]
        )
    elif metric.aggregation in {"avg", "mean"}:
        lines.extend(
            [
                f"    metric_raw = group[{metric.column!r}].mean()",
                "    metric_value = float(metric_raw) if pd.notna(metric_raw) else None",
            ]
        )
    elif metric.aggregation == "rate":
        lines.extend(
            [
                (
                    f"    numerator = "
                    f"(group[{metric.column!r}] == {metric.positive_value!r}).sum()"
                ),
                "    metric_value = float(numerator / len(group)) if len(group) else 0.0",
            ]
        )
    else:
        return None

    lines.extend(
        [
            f"    row[{alias!r}] = metric_value",
            "    rows.append(row)",
            "total_count = int(len(work))",
            "summary = f\"총 {total_count}건을 기준으로 그룹별 지표를 계산했습니다.\"",
            "raw_metrics = {",
            "    'total_count': total_count,",
            f"    'group_count': int(len(rows)),",
            "}",
            "print(json.dumps({",
            "    'summary': summary,",
            "    'table': rows,",
            "    'raw_metrics': raw_metrics,",
            f"    'used_columns': {used_columns!r},",
            "}, ensure_ascii=False))",
        ]
    )
    return "\n".join(lines)


def _build_scatter_points_code(plan: AnalysisPlan) -> str | None:
    hint = plan.visualization_hint
    if hint.preferred_chart != "scatter" or not hint.x or not hint.y:
        return None
    columns = [hint.x, hint.y]
    if hint.series:
        columns.append(hint.series)
    if any(column not in plan.metadata_snapshot.columns for column in columns):
        return None
    if plan.group_by or plan.metrics:
        return None
    filter_lines = _build_filter_lines(plan)
    if filter_lines is None:
        return None
    used_columns = _used_source_columns(plan, columns)
    lines = [
        "work = df.copy()",
        *filter_lines,
        f"point_columns = {columns!r}",
        "points = work[point_columns].where(pd.notna(work[point_columns]), None)",
        "rows = points.to_dict(orient='records')",
        "summary = f\"총 {len(rows)}개 관측치로 산점도 데이터를 구성했습니다.\"",
        "raw_metrics = {'row_count': int(len(rows))}",
        "print(json.dumps({",
        "    'summary': summary,",
        "    'table': rows,",
        "    'raw_metrics': raw_metrics,",
        f"    'used_columns': {used_columns!r},",
        "}, ensure_ascii=False))",
    ]
    return "\n".join(lines)


def _used_source_columns(
    plan: AnalysisPlan,
    candidates: Sequence[str | None],
) -> list[str]:
    available = set(plan.metadata_snapshot.columns)
    columns: list[str] = []
    for column in [*plan.required_columns, *candidates]:
        if column and column in available and column not in columns:
            columns.append(column)
    return columns


def _time_axis_alias(grain: str | None) -> str | None:
    if grain == "hour":
        return "hour"
    if grain == "day":
        return "date"
    if grain == "week":
        return "week"
    if grain == "month":
        return "month"
    if grain == "quarter":
        return "quarter"
    if grain == "year":
        return "year"
    return None


def _time_bucket_expression(grain: str | None) -> str:
    if grain == "hour":
        return ".dt.strftime('%Y-%m-%d %H:00:00')"
    if grain == "week":
        return ".dt.to_period('W').astype(str)"
    if grain == "month":
        return ".dt.to_period('M').astype(str)"
    if grain == "quarter":
        return ".dt.to_period('Q').astype(str)"
    if grain == "year":
        return ".dt.year.astype('Int64').astype(str)"
    return ".dt.strftime('%Y-%m-%d')"


def _build_filter_lines(plan: AnalysisPlan) -> list[str] | None:
    lines: list[str] = []
    for condition in plan.filters:
        if condition.operator == "not_null":
            lines.append(
                f"work = work[work[{condition.column!r}].notna()].copy()"
            )
        elif condition.operator == "eq":
            lines.append(
                f"work = work[work[{condition.column!r}] == {condition.value!r}].copy()"
            )
        else:
            return None
    return lines


def _build_metric_lines(plan: AnalysisPlan) -> list[str] | None:
    lines: list[str] = []
    for metric in plan.metrics:
        alias = metric.alias
        if metric.aggregation == "count":
            if metric.column:
                lines.append(
                    f"    row[{alias!r}] = int(group[{metric.column!r}].count())"
                )
            else:
                lines.append(f"    row[{alias!r}] = int(len(group))")
        elif metric.aggregation == "sum" and metric.column:
            lines.extend(
                [
                    f"    {alias}_value = group[{metric.column!r}].sum()",
                    (
                        f"    row[{alias!r}] = int({alias}_value) "
                        f"if pd.notna({alias}_value) and "
                        f"float({alias}_value).is_integer() "
                        f"else float({alias}_value)"
                    ),
                ]
            )
        elif (
            metric.aggregation == "rate"
            and metric.column
            and metric.positive_value is not None
        ):
            lines.extend(
                [
                    (
                        f"    {alias}_numerator = "
                        f"(group[{metric.column!r}] == {metric.positive_value!r}).sum()"
                    ),
                    (
                        f"    row[{alias!r}] = "
                        f"float({alias}_numerator / len(group)) if len(group) else 0.0"
                    ),
                ]
            )
        else:
            return None
    return lines


def _total_defect_line(plan: AnalysisPlan) -> str:
    for metric in plan.metrics:
        if metric.column and metric.positive_value is not None:
            return (
                f"total_defects = int((work[{metric.column!r}] == "
                f"{metric.positive_value!r}).sum())"
            )
    for metric in plan.metrics:
        if metric.column and metric.aggregation == "sum":
            return f"total_defects = int(work[{metric.column!r}].sum())"
    return "total_defects = 0"
