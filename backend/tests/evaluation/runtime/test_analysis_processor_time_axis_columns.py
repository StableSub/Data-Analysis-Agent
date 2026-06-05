from __future__ import annotations

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.schemas import (
    AnalysisOutputPayload,
    AnalysisPlanDraft,
    DerivedColumnSpec,
    MetadataSnapshot,
    MetricSpec,
    SandboxExecutionResult,
    SortSpec,
    TimeContext,
    VisualizationHint,
)


def test_month_time_axis_output_column_is_not_treated_as_source_column() -> None:
    processor = AnalysisProcessor()
    metadata = MetadataSnapshot(
        columns=["TimeStamp", "Reason", "PassOrFail"],
        datetime_columns=["TimeStamp"],
        categorical_columns=["Reason", "PassOrFail"],
        row_count=10,
    )
    draft = AnalysisPlanDraft(
        analysis_type="time_series_visualization",
        objective="월별 생산량과 불량 발생 추이",
        metrics=[
            MetricSpec(
                name="production_volume",
                aggregation="count",
                column=None,
                alias="production_volume",
            ),
            MetricSpec(
                name="defect_occurrence",
                aggregation="count",
                column="Reason",
                alias="defect_occurrence",
            ),
        ],
        sort_by=[SortSpec(column="TimeStamp", direction="asc")],
        time_context=TimeContext(
            time_column="TimeStamp",
            range_type="none",
            grain="month",
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
        ambiguity_status="clear",
    )

    plan = processor.validate_and_finalize_plan(draft, metadata)

    assert plan.required_columns == ["Reason", "TimeStamp"]
    assert plan.used_columns == ["Reason", "TimeStamp"]
    assert plan.visualization_hint.x == "month"
    assert plan.visualization_hint.y == "production_volume"
    assert plan.expected_output.expected_table_columns == [
        "month",
        "production_volume",
        "defect_occurrence",
    ]

    result = processor.validate_execution_result(
        SandboxExecutionResult(
            ok=True,
            stdout_json=AnalysisOutputPayload(
                summary="월별 생산량과 불량 발생 추이입니다.",
                table=[
                    {
                        "month": "2026-05",
                        "production_volume": 10,
                        "defect_occurrence": 2,
                    }
                ],
                raw_metrics={},
                used_columns=["TimeStamp", "Reason"],
            ),
        ),
        plan,
    )

    assert result.execution_status == "success"
    assert result.quality_status == "complete"


def test_day_time_axis_group_by_alias_is_not_treated_as_source_column() -> None:
    processor = AnalysisProcessor()
    metadata = MetadataSnapshot(
        columns=["TimeStamp", "PassOrFail"],
        datetime_columns=["TimeStamp"],
        numeric_columns=["PassOrFail"],
        row_count=10,
    )
    draft = AnalysisPlanDraft(
        analysis_type="daily_defect_count",
        objective="일별 불량 건수",
        group_by=["date"],
        metrics=[
            MetricSpec(
                name="defect_count",
                aggregation="count",
                column="PassOrFail",
                alias="defect_count",
            )
        ],
        sort_by=[SortSpec(column="date", direction="asc")],
        time_context=TimeContext(
            time_column="TimeStamp",
            range_type="none",
            grain="day",
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
        ambiguity_status="clear",
    )

    plan = processor.validate_and_finalize_plan(draft, metadata)

    assert plan.group_by == []
    assert plan.required_columns == ["PassOrFail", "TimeStamp"]
    assert plan.used_columns == ["PassOrFail", "TimeStamp"]
    assert plan.sort_by == [SortSpec(column="date", direction="asc")]
    assert plan.visualization_hint.x == "date"
    assert plan.visualization_hint.y == "defect_count"
    assert plan.expected_output.expected_table_columns == ["date", "defect_count"]
    assert plan.expected_output.require_time_axis is True
    assert plan.expected_output.require_group_axis is False

    result = processor.validate_execution_result(
        SandboxExecutionResult(
            ok=True,
            stdout_json=AnalysisOutputPayload(
                summary="일별 불량 건수입니다.",
                table=[{"date": "2026-05-01", "defect_count": 2}],
                raw_metrics={},
                used_columns=["TimeStamp", "PassOrFail"],
            ),
        ),
        plan,
    )

    assert result.execution_status == "success"
    assert result.quality_status == "complete"


def test_real_visualization_axis_columns_remain_required_source_columns() -> None:
    processor = AnalysisProcessor()
    metadata = MetadataSnapshot(
        columns=["Injection_Time", "Cycle_Time", "PassOrFail"],
        numeric_columns=["Injection_Time", "Cycle_Time"],
        categorical_columns=["PassOrFail"],
        row_count=10,
    )
    draft = AnalysisPlanDraft(
        analysis_type="relationship",
        objective="Injection_Time과 Cycle_Time 관계",
        metrics=[
            MetricSpec(
                name="row_count",
                aggregation="count",
                column=None,
                alias="row_count",
            )
        ],
        visualization_hint=VisualizationHint(
            preferred_chart="scatter",
            x="Injection_Time",
            y="Cycle_Time",
            series="PassOrFail",
        ),
        ambiguity_status="clear",
    )

    plan = processor.validate_and_finalize_plan(draft, metadata)

    assert plan.required_columns == ["Injection_Time", "Cycle_Time", "PassOrFail"]
    assert plan.used_columns == ["Injection_Time", "Cycle_Time", "PassOrFail"]
    assert plan.expected_output.expected_table_columns == [
        "Injection_Time",
        "Cycle_Time",
        "PassOrFail",
    ]


def test_daily_defect_time_series_accepts_derived_defect_flag_metric_without_group_by() -> None:
    processor = AnalysisProcessor()
    metadata = MetadataSnapshot(
        columns=["TimeStamp", "PassOrFail"],
        numeric_columns=["PassOrFail"],
        datetime_columns=["TimeStamp"],
        row_count=2607,
    )
    draft = AnalysisPlanDraft(
        analysis_type="daily_defect_time_series",
        objective=(
            "Compute daily defect counts from TimeStamp; defect defined as "
            "PassOrFail != 1."
        ),
        group_by=[],
        metrics=[
            MetricSpec(
                name="defect_count",
                aggregation="sum",
                column="defect_flag",
                alias="defect_count",
            ),
        ],
        derived_columns=[
            DerivedColumnSpec(
                name="defect_flag",
                expression_type="arithmetic",
                source_columns=["PassOrFail"],
                params={
                    "operator": "!=",
                    "value": 1,
                    "true_value": 1,
                    "false_value": 0,
                },
            )
        ],
        sort_by=[SortSpec(column="date", direction="asc")],
        time_context=TimeContext(
            time_column="TimeStamp",
            range_type="none",
            grain="day",
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
        ambiguity_status="clear",
    )

    plan = processor.validate_and_finalize_plan(draft, metadata)

    assert plan.group_by == []
    assert plan.used_columns == ["PassOrFail", "TimeStamp"]
    assert plan.metrics[0].column == "defect_flag"
    assert plan.visualization_hint.x == "date"
    assert plan.visualization_hint.y == "defect_count"
    assert plan.expected_output.expected_table_columns == [
        "date",
        "defect_count",
    ]
