from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ErrorStage = Literal[
    "question_understanding",
    "column_grounding",
    "plan_generation",
    "plan_validation",
    "code_generation",
    "code_validation",
    "sandbox_execution",
    "result_validation",
    "persist_result",
]


class FilterCondition(StrictModel):
    column: str
    operator: Literal[
        "eq",
        "ne",
        "gt",
        "gte",
        "lt",
        "lte",
        "in",
        "between",
        "contains",
        "is_null",
        "not_null",
    ]
    value: Any | None = None


class MetricSpec(StrictModel):
    name: str
    aggregation: Literal[
        "sum",
        "avg",
        "count",
        "count_distinct",
        "min",
        "max",
        "median",
        "rate",
    ]
    column: str | None = None
    alias: str


class SortSpec(StrictModel):
    column: str
    direction: Literal["asc", "desc"]


class DerivedColumnSpec(StrictModel):
    name: str
    expression_type: Literal["datetime_part", "ratio", "arithmetic", "bucketize"]
    source_columns: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)


class IntradayFilter(StrictModel):
    start_hour: int | None = None
    end_hour: int | None = None
    weekdays: list[int] = Field(default_factory=list)
    include_weekends: bool | None = None


class TimeContext(StrictModel):
    time_column: str | None = None
    range_type: Literal["absolute", "relative", "none"] = "none"
    start: datetime | None = None
    end: datetime | None = None
    relative_expr: str | None = None
    relative_range_resolved: dict[str, datetime] | None = None
    grain: Literal["hour", "day", "week", "month", "quarter", "year"] | None = None
    intraday_filter: IntradayFilter | None = None
    timezone: str | None = None


class ExpectedOutputSpec(StrictModel):
    require_summary: bool = True
    require_table: bool = True
    require_raw_metrics: bool = True
    expected_table_columns: list[str] = Field(default_factory=list)
    allow_empty_table: bool = True
    minimum_rows: int = 0
    require_group_axis: bool = False
    require_time_axis: bool = False
    require_outlier_info: bool = False


class VisualizationHint(StrictModel):
    preferred_chart: Literal["line", "bar", "scatter", "hist", "pie", "none"] = "none"
    x: str | None = None
    y: str | None = None
    series: str | None = None
    caption: str | None = None


class MetadataSnapshot(StrictModel):
    columns: list[str] = Field(default_factory=list)
    dtypes: dict[str, str] = Field(default_factory=dict)
    numeric_columns: list[str] = Field(default_factory=list)
    datetime_columns: list[str] = Field(default_factory=list)
    categorical_columns: list[str] = Field(default_factory=list)
    row_count: int | None = None
    timezone: str | None = None


class QuestionUnderstanding(StrictModel):
    analysis_goal: list[str] = Field(default_factory=list)
    metric_keywords: list[str] = Field(default_factory=list)
    group_keywords: list[str] = Field(default_factory=list)
    filter_conditions: list[FilterCondition] = Field(default_factory=list)
    time_context: TimeContext | None = None
    ambiguity_status: Literal["clear", "needs_clarification"]
    clarification_message: str = ""


class ColumnGroundingResult(StrictModel):
    resolved_columns: dict[str, str] = Field(default_factory=dict)
    unresolved_terms: list[str] = Field(default_factory=list)
    confidence: float | None = None


class AnalysisPlanDraft(StrictModel):
    analysis_type: str
    objective: str
    filters: list[FilterCondition] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    metrics: list[MetricSpec] = Field(default_factory=list)
    derived_columns: list[DerivedColumnSpec] = Field(default_factory=list)
    sort_by: list[SortSpec] = Field(default_factory=list)
    time_context: TimeContext | None = None
    visualization_hint: VisualizationHint = Field(default_factory=VisualizationHint)
    ambiguity_status: Literal["clear", "needs_clarification"]
    clarification_message: str = ""


class AnalysisPlan(StrictModel):
    analysis_type: str
    objective: str
    required_columns: list[str] = Field(default_factory=list)
    used_columns: list[str] = Field(default_factory=list)
    filters: list[FilterCondition] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    metrics: list[MetricSpec] = Field(default_factory=list)
    derived_columns: list[DerivedColumnSpec] = Field(default_factory=list)
    sort_by: list[SortSpec] = Field(default_factory=list)
    time_context: TimeContext | None = None
    expected_output: ExpectedOutputSpec
    visualization_hint: VisualizationHint
    empty_result_policy: Literal[
        "success_with_empty_summary",
        "success_with_empty_table",
        "fail_on_empty",
    ]
    metadata_snapshot: MetadataSnapshot
    codegen_strategy: Literal["llm_codegen"]


class AnalysisOutputPayload(StrictModel):
    summary: str
    table: list[dict[str, Any]] = Field(default_factory=list)
    raw_metrics: dict[str, Any] = Field(default_factory=dict)
    used_columns: list[str] = Field(default_factory=list)


class SandboxExecutionResult(StrictModel):
    ok: bool
    stdout_json: AnalysisOutputPayload | None = None
    stderr: str = ""
    error_type: Literal["timeout", "runtime", "invalid_json"] | None = None
    message: str | None = None


class ChartSeries(StrictModel):
    name: str
    y: list[Any] = Field(default_factory=list)


class ChartData(StrictModel):
    chart_type: str
    x: list[Any] = Field(default_factory=list)
    series: list[ChartSeries] = Field(default_factory=list)
    caption: str | None = None


class VisualizationOutput(StrictModel):
    chart_data: ChartData | None = None
    fallback_table: list[dict[str, Any]] | None = None
    status: Literal["generated", "fallback", "unavailable"]


class AnalysisError(StrictModel):
    stage: ErrorStage
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)


class AnalysisExecutionResult(StrictModel):
    execution_status: Literal["success", "fail"]
    summary: str | None = None
    table: list[dict[str, Any]] = Field(default_factory=list)
    raw_metrics: dict[str, Any] = Field(default_factory=dict)
    used_columns: list[str] = Field(default_factory=list)
    error_stage: ErrorStage | None = None
    error_message: str | None = None


FinalStatus = Literal[
    "planning",
    "executing",
    "validating",
    "success",
    "fail",
    "needs_clarification",
]
