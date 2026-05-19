from __future__ import annotations

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.schemas import (
    AnalysisOutputPayload,
    AnalysisPlanDraft,
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
