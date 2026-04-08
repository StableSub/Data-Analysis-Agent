from __future__ import annotations

import ast
import re
from typing import Any, Iterable

from .sandbox import validate_analysis_source_code
from .schemas import (
    AnalysisError,
    AnalysisExecutionResult,
    AnalysisPlan,
    AnalysisPlanDraft,
    ColumnGroundingResult,
    DerivedColumnSpec,
    ErrorStage,
    ExpectedOutputSpec,
    FilterCondition,
    MetadataSnapshot,
    MetricSpec,
    QuestionUnderstanding,
    SandboxExecutionResult,
    SortSpec,
    TimeContext,
    VisualizationHint,
)

_OUTPUT_KEYS = {"summary", "table", "raw_metrics", "used_columns"}
_TIME_AXIS_BY_GRAIN = {
    "hour": "hour",
    "day": "date",
    "week": "week",
    "month": "month",
    "quarter": "quarter",
    "year": "year",
}
_IDENTIFIER_RE = re.compile(r"[^a-zA-Z0-9_]+")
_SYNTHETIC_DIMENSION_TOKENS = {
    "column",
    "columns",
    "column_name",
    "column_names",
    "column_type",
    "data_type",
    "feature_type",
}
_NORMALIZED_SYNTHETIC_DIMENSION_TOKENS = {
    _IDENTIFIER_RE.sub("", token.lower()) for token in _SYNTHETIC_DIMENSION_TOKENS
}


# 분석 계획과 실행 결과를 검증 및 정규화
class AnalysisProcessor:
    """Analysis deterministic validation and normalization layer."""

    # 질문에서 추출한 용어를 실제 데이터셋 컬럼명에 연결한다.
    def ground_columns(
        self,
        question_understanding: QuestionUnderstanding | dict[str, Any],
        dataset_meta: MetadataSnapshot | dict[str, Any],
    ) -> ColumnGroundingResult:
        understanding = self._ensure_question_understanding(question_understanding)
        metadata = self._ensure_metadata_snapshot(dataset_meta)
        columns = metadata.columns
        resolved: dict[str, str] = {}
        unresolved: list[str] = []

        # metric/group/filter/time 관련 용어를 컬럼 후보로 수집한다.
        terms = list(understanding.metric_keywords) + list(understanding.group_keywords)
        if understanding.time_context and understanding.time_context.time_column:
            terms.append(understanding.time_context.time_column)
        for condition in understanding.filter_conditions:
            terms.append(condition.column)

        # 질문 용어와 실제 컬럼명을 가능한 범위에서 매칭한다.
        seen: set[str] = set()
        for term in terms:
            cleaned = str(term or "").strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            matched = self._match_column(cleaned, columns)
            if matched:
                resolved[cleaned] = matched
            else:
                unresolved.append(cleaned)

        # 시간 컬럼이 명시되지 않았다면 기본 datetime 컬럼을 보완한다.
        if understanding.time_context and not understanding.time_context.time_column:
            default_time = self._resolve_default_time_column(metadata)
            if default_time:
                resolved["__time__"] = default_time

        confidence = None
        if seen:
            confidence = round(len(resolved) / len(seen), 2)
        return ColumnGroundingResult(
            resolved_columns=resolved,
            unresolved_terms=unresolved,
            confidence=confidence,
        )

    # LLM이 생성한 초안을 검증하여 실행 가능한 최종 AnalysisPlan으로 변환한다.
    def validate_and_finalize_plan(
        self,
        plan_draft: AnalysisPlanDraft | dict[str, Any],
        dataset_meta: MetadataSnapshot | dict[str, Any],
        column_grounding: ColumnGroundingResult | dict[str, Any] | None = None,
    ) -> AnalysisPlan:
        draft = self._ensure_plan_draft(plan_draft)
        metadata = self._ensure_metadata_snapshot(dataset_meta)
        grounding = self._ensure_column_grounding(column_grounding)

        if draft.ambiguity_status != "clear":
            raise ValueError(
                draft.clarification_message or "analysis plan draft is ambiguous"
            )
        if not draft.metrics:
            raise ValueError("analysis plan draft requires at least one metric")

        draft = self._sanitize_synthetic_dimensions(draft)
        resolved_columns = grounding.resolved_columns if grounding else {}
        derived_names = {column.name for column in draft.derived_columns}

        # 필터, 그룹, metric, 시간 조건을 각각 정규화한다.
        filters = [
            self._normalize_filter(condition, metadata, resolved_columns, derived_names)
            for condition in draft.filters
        ]
        group_by = [
            self._resolve_column_name(column, metadata, resolved_columns, derived_names)
            for column in draft.group_by
        ]
        metrics = [
            self._normalize_metric(metric, metadata, resolved_columns)
            for metric in draft.metrics
        ]
        derived_columns = [
            self._normalize_derived_column(column, metadata, resolved_columns)
            for column in draft.derived_columns
        ]
        sort_by = [
            self._normalize_sort(sort_spec, metadata, metrics, group_by, derived_names)
            for sort_spec in draft.sort_by
        ]
        time_context = self._normalize_time_context(
            draft.time_context,
            metadata,
            resolved_columns,
        )

        visualization_hint = self._build_visualization_hint(
            draft=draft,
            group_by=group_by,
            metrics=metrics,
            time_context=time_context,
        )
        # 분석 수행에 필요한 필수 컬럼과 기대 출력 형식을 계산한다.
        required_columns = self._build_required_columns(
            filters=filters,
            group_by=group_by,
            metrics=metrics,
            derived_columns=derived_columns,
            time_context=time_context,
            visualization_hint=visualization_hint,
            derived_names=derived_names,
        )
        if not required_columns:
            raise ValueError("analysis plan requires at least one source column")

        expected_output = self._build_expected_output(
            draft=draft,
            group_by=group_by,
            metrics=metrics,
            time_context=time_context,
            visualization_hint=visualization_hint,
        )

        # 최종 AnalysisPlan 반환
        return AnalysisPlan(
            analysis_type=draft.analysis_type,
            objective=draft.objective,
            required_columns=required_columns,
            used_columns=list(required_columns),
            filters=filters,
            group_by=group_by,
            metrics=metrics,
            derived_columns=derived_columns,
            sort_by=sort_by,
            time_context=time_context,
            expected_output=expected_output,
            visualization_hint=visualization_hint,
            empty_result_policy="success_with_empty_summary",
            metadata_snapshot=metadata,
            codegen_strategy="llm_codegen",
        )

    # 생성된 코드가 안전하고 실행 계약에 맞는지 사전 검사한다.
    def validate_generated_code(
        self,
        generated_code: str,
        analysis_plan: AnalysisPlan | dict[str, Any],
    ) -> str:
        plan = self._ensure_plan(analysis_plan)
        code = str(generated_code or "").strip()
        if not code:
            raise ValueError("generated code is empty")

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise ValueError(f"generated code is not valid python: {exc}") from exc

        validate_analysis_source_code(code, require_print=True)

        # 결과 JSON 출력을 위한 필수 키가 코드에 포함되어 있는지 확인한다.
        missing_keys = [key for key in _OUTPUT_KEYS if key not in code]
        if missing_keys:
            raise ValueError(
                f"generated code is missing output keys: {', '.join(missing_keys)}"
            )

        # 분석 계획에서 요구한 컬럼이 코드에 반영되었는지 점검한다.
        for required_column in plan.required_columns:
            if required_column not in code:
                raise ValueError(
                    f"generated code does not reference required column: {required_column}"
                )

        return code

    # sandbox 실행 결과를 검증하여 성공/실패 상태로 정리한다.
    def validate_execution_result(
        self,
        sandbox_result: SandboxExecutionResult | dict[str, Any],
        analysis_plan: AnalysisPlan | dict[str, Any],
    ) -> AnalysisExecutionResult:
        plan = self._ensure_plan(analysis_plan)
        result = self._ensure_sandbox_result(sandbox_result)

        # 실행 자체가 실패했거나 JSON 출력이 없으면 즉시 실패 처리한다.
        if not result.ok or result.stdout_json is None:
            return AnalysisExecutionResult(
                execution_status="fail",
                error_stage="sandbox_execution",
                error_message=result.message
                or result.error_type
                or "analysis execution failed",
            )

        # 출력 payload가 AnalysisPlan의 결과 계약을 만족하는지 검사한다.
        payload = result.stdout_json
        error = self._validate_output_payload(payload, plan)
        if error is not None:
            return AnalysisExecutionResult(
                execution_status="fail",
                error_stage="result_validation",
                error_message=error,
            )

        execution_result = AnalysisExecutionResult(
            execution_status="success",
            summary=payload.summary,
            table=payload.table,
            raw_metrics=payload.raw_metrics,
            used_columns=payload.used_columns,
        )
        return self.normalize_empty_result(execution_result, plan)

    # 결과가 빈 테이블일 때 정책에 따라 처리합니다.
    def normalize_empty_result(
        self,
        execution_result: AnalysisExecutionResult | dict[str, Any],
        analysis_plan: AnalysisPlan | dict[str, Any],
    ) -> AnalysisExecutionResult:
        result = self._ensure_execution_result(execution_result)
        plan = self._ensure_plan(analysis_plan)

        if result.execution_status != "success":
            return result

        if result.table:
            return result

        if plan.empty_result_policy == "fail_on_empty":
            return AnalysisExecutionResult(
                execution_status="fail",
                error_stage="result_validation",
                error_message="analysis returned no rows",
            )
        if plan.empty_result_policy == "success_with_empty_summary":
            summary = (
                result.summary or "조건에 맞는 데이터가 없어 빈 결과를 반환했습니다."
            )
            return result.model_copy(update={"summary": summary})
        return result.model_copy(update={"summary": result.summary or ""})

    # 표준 AnalysisError를 만드는 헬퍼
    def build_error(
        self,
        stage: ErrorStage,
        message: str,
        *,
        detail: dict[str, Any] | None = None,
    ) -> AnalysisError:
        return AnalysisError(stage=stage, message=message, detail=detail or {})

    def _validate_output_payload(self, payload: Any, plan: AnalysisPlan) -> str | None:
        if payload.used_columns:
            unexpected_columns = sorted(
                set(payload.used_columns) - set(plan.used_columns)
            )
            if unexpected_columns:
                return f"used_columns contains non-approved columns: {', '.join(unexpected_columns)}"

        if (
            plan.expected_output.require_summary
            and not str(payload.summary or "").strip()
        ):
            return "summary is required"
        if plan.expected_output.require_table and payload.table is None:
            return "table is required"
        if plan.expected_output.require_raw_metrics and payload.raw_metrics is None:
            return "raw_metrics is required"

        table = payload.table or []
        if len(table) < plan.expected_output.minimum_rows and not (
            plan.expected_output.allow_empty_table and len(table) == 0
        ):
            return (
                f"table must contain at least {plan.expected_output.minimum_rows} rows"
            )

        if not table:
            return None

        columns = {str(key) for row in table for key in row.keys()}
        missing_table_columns = [
            column
            for column in plan.expected_output.expected_table_columns
            if column not in columns
        ]
        if missing_table_columns:
            return "table is missing expected columns: " + ", ".join(
                missing_table_columns
            )

        if plan.expected_output.require_time_axis:
            time_axis_column = self._time_axis_output_column(plan.time_context)
            if time_axis_column and time_axis_column not in columns:
                return f"time axis column is missing: {time_axis_column}"

        if plan.expected_output.require_group_axis:
            group_columns = [
                column
                for column in plan.group_by
                if column
                != (plan.time_context.time_column if plan.time_context else None)
            ]
            if not any(column in columns for column in group_columns):
                return "group axis column is missing"

        if (
            plan.expected_output.require_outlier_info
            and "outliers" not in payload.raw_metrics
        ):
            return "outlier information is required"
        return None

    # plan에서 실제 필요한 source column을 계산한다.
    def _build_required_columns(
        self,
        *,
        filters: list[FilterCondition],
        group_by: list[str],
        metrics: list[MetricSpec],
        derived_columns: list[DerivedColumnSpec],
        time_context: TimeContext | None,
        visualization_hint: VisualizationHint | None,
        derived_names: set[str],
    ) -> list[str]:
        required: list[str] = []

        for condition in filters:
            if condition.column not in derived_names:
                required.append(condition.column)
        for column in group_by:
            if column not in derived_names:
                required.append(column)
        for metric in metrics:
            if metric.column and metric.column not in derived_names:
                required.append(metric.column)
        for derived in derived_columns:
            required.extend(derived.source_columns)
        if time_context and time_context.time_column:
            required.append(time_context.time_column)
        if visualization_hint:
            for column in (
                visualization_hint.x,
                visualization_hint.y,
                visualization_hint.series,
            ):
                if column and column not in derived_names:
                    required.append(column)

        return list(dict.fromkeys(required))

    # 질문 의도에 맞는 결과 형태를 자동으로 정한다.
    def _build_expected_output(
        self,
        *,
        draft: AnalysisPlanDraft,
        group_by: list[str],
        metrics: list[MetricSpec],
        time_context: TimeContext | None,
        visualization_hint: VisualizationHint,
    ) -> ExpectedOutputSpec:
        is_scatter_relationship = (
            visualization_hint.preferred_chart == "scatter"
            and bool(visualization_hint.x)
            and bool(visualization_hint.y)
        )

        if is_scatter_relationship:
            table_columns = [visualization_hint.x, visualization_hint.y]
            if visualization_hint.series:
                table_columns.append(visualization_hint.series)
        else:
            table_columns = list(group_by)
        time_axis_column = self._time_axis_output_column(time_context)
        if (
            not is_scatter_relationship
            and time_axis_column
            and time_axis_column not in table_columns
        ):
            table_columns.append(time_axis_column)
        if not is_scatter_relationship:
            table_columns.extend(metric.alias for metric in metrics)

        normalized_objective = draft.objective.lower()
        require_outlier_info = (
            "outlier" in normalized_objective or "이상치" in draft.objective
        )
        group_axis_columns = [
            column
            for column in group_by
            if column != (time_context.time_column if time_context else None)
        ]
        return ExpectedOutputSpec(
            require_summary=True,
            require_table=True,
            require_raw_metrics=require_outlier_info,
            expected_table_columns=list(dict.fromkeys(table_columns)),
            allow_empty_table=True,
            minimum_rows=0,
            require_group_axis=bool(group_axis_columns),
            require_time_axis=bool(time_axis_column),
            require_outlier_info=require_outlier_info,
        )

    # 시각화 힌트를 자동 보정한다.
    def _build_visualization_hint(
        self,
        *,
        draft: AnalysisPlanDraft,
        group_by: list[str],
        metrics: list[MetricSpec],
        time_context: TimeContext | None,
    ) -> VisualizationHint:
        if draft.visualization_hint.preferred_chart != "none":
            return draft.visualization_hint

        time_axis_column = self._time_axis_output_column(time_context)
        if time_axis_column and metrics:
            series_column = next(
                (column for column in group_by if column != time_axis_column), None
            )
            return VisualizationHint(
                preferred_chart="line",
                x=time_axis_column,
                y=metrics[0].alias,
                series=series_column,
                caption=draft.visualization_hint.caption,
            )

        if group_by and metrics:
            return VisualizationHint(
                preferred_chart="bar",
                x=group_by[0],
                y=metrics[0].alias,
                series=draft.visualization_hint.series,
                caption=draft.visualization_hint.caption,
            )

        return draft.visualization_hint

    def _normalize_filter(
        self,
        condition: FilterCondition,
        metadata: MetadataSnapshot,
        resolved_columns: dict[str, str],
        derived_names: set[str],
    ) -> FilterCondition:
        column = self._resolve_column_name(
            condition.column,
            metadata,
            resolved_columns,
            derived_names,
        )
        if condition.operator == "between":
            if (
                not isinstance(condition.value, (list, tuple))
                or len(condition.value) != 2
            ):
                raise ValueError("between filter requires a 2-item value")
        if condition.operator in {"is_null", "not_null"}:
            return condition.model_copy(update={"column": column, "value": None})
        return condition.model_copy(update={"column": column})

    def _normalize_metric(
        self,
        metric: MetricSpec,
        metadata: MetadataSnapshot,
        resolved_columns: dict[str, str],
    ) -> MetricSpec:
        normalized_column = None
        if metric.column:
            normalized_column = self._resolve_column_name(
                metric.column, metadata, resolved_columns, set()
            )
        if metric.aggregation != "count" and not normalized_column:
            raise ValueError(f"metric '{metric.name}' requires a source column")
        alias = metric.alias.strip() or metric.name.strip()
        if not alias:
            raise ValueError("metric alias must not be empty")
        return metric.model_copy(update={"column": normalized_column, "alias": alias})

    def _normalize_derived_column(
        self,
        derived_column: DerivedColumnSpec,
        metadata: MetadataSnapshot,
        resolved_columns: dict[str, str],
    ) -> DerivedColumnSpec:
        if not derived_column.name.strip():
            raise ValueError("derived column name must not be empty")
        source_columns = [
            self._resolve_column_name(column, metadata, resolved_columns, set())
            for column in derived_column.source_columns
        ]
        if derived_column.expression_type == "datetime_part":
            part = str(derived_column.params.get("part") or "").strip()
            if part not in {
                "year",
                "month",
                "day",
                "hour",
                "weekday",
                "week",
                "quarter",
            }:
                raise ValueError(
                    "datetime_part derived column requires a valid params.part"
                )
        if derived_column.expression_type == "ratio" and len(source_columns) != 2:
            raise ValueError("ratio derived column requires exactly 2 source columns")
        return derived_column.model_copy(update={"source_columns": source_columns})

    def _normalize_sort(
        self,
        sort_spec: SortSpec,
        metadata: MetadataSnapshot,
        metrics: list[MetricSpec],
        group_by: list[str],
        derived_names: set[str],
    ) -> SortSpec:
        sortable_columns = {
            *metadata.columns,
            *group_by,
            *(metric.alias for metric in metrics),
            *derived_names,
        }
        if sort_spec.column not in sortable_columns:
            raise ValueError(f"sort column is not available: {sort_spec.column}")
        return sort_spec

    def _normalize_time_context(
        self,
        time_context: TimeContext | None,
        metadata: MetadataSnapshot,
        resolved_columns: dict[str, str],
    ) -> TimeContext | None:
        if time_context is None:
            return None

        normalized_time_column = time_context.time_column
        if not normalized_time_column:
            normalized_time_column = resolved_columns.get(
                "__time__"
            ) or self._resolve_default_time_column(metadata)
        elif normalized_time_column:
            normalized_time_column = self._resolve_column_name(
                normalized_time_column,
                metadata,
                resolved_columns,
                set(),
            )

        if time_context.range_type == "absolute" and not (
            time_context.start or time_context.end
        ):
            raise ValueError("absolute time range requires start or end")
        if time_context.range_type == "relative" and not time_context.relative_expr:
            raise ValueError("relative time range requires relative_expr")

        intraday = time_context.intraday_filter
        if intraday is not None:
            for hour in [intraday.start_hour, intraday.end_hour]:
                if hour is not None and not 0 <= hour <= 23:
                    raise ValueError("intraday filter hours must be between 0 and 23")

        if (
            time_context.grain or time_context.range_type != "none" or intraday
        ) and not normalized_time_column:
            raise ValueError("time-based analysis requires a time column")

        return time_context.model_copy(update={"time_column": normalized_time_column})

    def _sanitize_synthetic_dimensions(
        self,
        draft: AnalysisPlanDraft,
    ) -> AnalysisPlanDraft:
        if not self._is_missing_value_overview_request(draft):
            return draft

        filters = [
            condition
            for condition in draft.filters
            if not self._is_synthetic_dimension(condition.column)
        ]
        group_by = [
            column for column in draft.group_by if not self._is_synthetic_dimension(column)
        ]
        visualization_hint = draft.visualization_hint
        if (
            self._is_synthetic_dimension(visualization_hint.x)
            or self._is_synthetic_dimension(visualization_hint.series)
        ):
            visualization_hint = visualization_hint.model_copy(
                update={
                    "preferred_chart": "none",
                    "x": None,
                    "y": None,
                    "series": None,
                }
            )

        return draft.model_copy(
            update={
                "filters": filters,
                "group_by": group_by,
                "visualization_hint": visualization_hint,
            }
        )

    def _is_missing_value_overview_request(self, draft: AnalysisPlanDraft) -> bool:
        haystack = f"{draft.analysis_type} {draft.objective}".lower()
        keywords = ("missing", "imputation", "impute", "결측", "전처리 계획")
        return any(keyword in haystack for keyword in keywords)

    def _is_synthetic_dimension(self, value: str | None) -> bool:
        if value is None:
            return False
        normalized = self._normalize_identifier(value)
        return normalized in _NORMALIZED_SYNTHETIC_DIMENSION_TOKENS

    def _resolve_column_name(
        self,
        column_name: str,
        metadata: MetadataSnapshot,
        resolved_columns: dict[str, str],
        derived_names: set[str],
    ) -> str:
        raw_value = str(column_name or "").strip()
        if not raw_value:
            raise ValueError("column name must not be empty")
        if raw_value in derived_names:
            return raw_value
        if raw_value in metadata.columns:
            return raw_value
        grounded = resolved_columns.get(raw_value)
        if grounded:
            return grounded
        matched = self._match_column(raw_value, metadata.columns)
        if matched:
            return matched
        if self._is_synthetic_dimension(raw_value):
            raise ValueError(f"planning used synthetic grouping dimension: {raw_value}")
        raise ValueError(f"column not found in dataset metadata: {raw_value}")

    def _match_column(self, term: str, columns: Iterable[str]) -> str | None:
        normalized_term = self._normalize_identifier(term)
        exact_match: str | None = None
        for column in columns:
            if term == column:
                return column
            if normalized_term == self._normalize_identifier(column):
                exact_match = column
        return exact_match

    def _resolve_default_time_column(self, metadata: MetadataSnapshot) -> str | None:
        if len(metadata.datetime_columns) == 1:
            return metadata.datetime_columns[0]
        return None

    def _normalize_identifier(self, value: str) -> str:
        return _IDENTIFIER_RE.sub("", str(value or "").lower())

    def _time_axis_output_column(self, time_context: TimeContext | None) -> str | None:
        if not time_context or not time_context.grain:
            return None
        return _TIME_AXIS_BY_GRAIN.get(time_context.grain, time_context.grain)

    def _ensure_question_understanding(
        self,
        question_understanding: QuestionUnderstanding | dict[str, Any],
    ) -> QuestionUnderstanding:
        if isinstance(question_understanding, QuestionUnderstanding):
            return question_understanding
        return QuestionUnderstanding.model_validate(question_understanding)

    def _ensure_column_grounding(
        self,
        column_grounding: ColumnGroundingResult | dict[str, Any] | None,
    ) -> ColumnGroundingResult | None:
        if column_grounding is None:
            return None
        if isinstance(column_grounding, ColumnGroundingResult):
            return column_grounding
        return ColumnGroundingResult.model_validate(column_grounding)

    def _ensure_plan_draft(
        self, plan_draft: AnalysisPlanDraft | dict[str, Any]
    ) -> AnalysisPlanDraft:
        if isinstance(plan_draft, AnalysisPlanDraft):
            return plan_draft
        return AnalysisPlanDraft.model_validate(plan_draft)

    def _ensure_plan(self, plan: AnalysisPlan | dict[str, Any]) -> AnalysisPlan:
        if isinstance(plan, AnalysisPlan):
            return plan
        return AnalysisPlan.model_validate(plan)

    def _ensure_metadata_snapshot(
        self,
        dataset_meta: MetadataSnapshot | dict[str, Any],
    ) -> MetadataSnapshot:
        if isinstance(dataset_meta, MetadataSnapshot):
            return dataset_meta
        return MetadataSnapshot.model_validate(dataset_meta)

    def _ensure_sandbox_result(
        self,
        sandbox_result: SandboxExecutionResult | dict[str, Any],
    ) -> SandboxExecutionResult:
        if isinstance(sandbox_result, SandboxExecutionResult):
            return sandbox_result
        return SandboxExecutionResult.model_validate(sandbox_result)

    def _ensure_execution_result(
        self,
        execution_result: AnalysisExecutionResult | dict[str, Any],
    ) -> AnalysisExecutionResult:
        if isinstance(execution_result, AnalysisExecutionResult):
            return execution_result
        return AnalysisExecutionResult.model_validate(execution_result)
