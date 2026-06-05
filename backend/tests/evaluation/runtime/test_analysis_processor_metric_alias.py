from __future__ import annotations

import pytest

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.schemas import (
    AnalysisOutputPayload,
    AnalysisPlanDraft,
    FilterCondition,
    MetadataSnapshot,
    MetricSpec,
    SandboxExecutionResult,
    SortSpec,
    TimeContext,
    VisualizationHint,
)


def test_metric_alias_used_for_visualization_is_not_treated_as_source_column() -> None:
    processor = AnalysisProcessor()
    metadata = MetadataSnapshot(
        columns=["PassOrFail"],
        numeric_columns=[],
        categorical_columns=["PassOrFail"],
        row_count=2607,
    )
    draft = AnalysisPlanDraft(
        analysis_type="descriptive",
        objective="PassOrFail 라벨 분포",
        group_by=["PassOrFail"],
        metrics=[
            MetricSpec(
                name="PassOrFail count",
                aggregation="count",
                column="PassOrFail",
                alias="PassOrFail_count",
            )
        ],
        visualization_hint=VisualizationHint(preferred_chart="none"),
        ambiguity_status="clear",
    )

    plan = processor.validate_and_finalize_plan(draft, metadata)

    assert plan.used_columns == ["PassOrFail"]
    assert plan.visualization_hint.y == "PassOrFail_count"
    assert "PassOrFail_count" in plan.expected_output.expected_table_columns

    result = processor.validate_execution_result(
        SandboxExecutionResult(
            ok=True,
            stdout_json=AnalysisOutputPayload(
                summary="PassOrFail 라벨 분포입니다.",
                table=[
                    {"PassOrFail": "0", "PassOrFail_count": 2555},
                    {"PassOrFail": "1", "PassOrFail_count": 52},
                ],
                raw_metrics={"total_count": 2607},
                used_columns=["PassOrFail"],
            ),
        ),
        plan,
    )

    assert result.execution_status == "success"
    assert result.quality_status == "complete"


def test_positive_value_metric_rejects_same_column_filter() -> None:
    processor = AnalysisProcessor()
    metadata = MetadataSnapshot(
        columns=["PART_NAME", "PassOrFail"],
        numeric_columns=["PassOrFail"],
        categorical_columns=["PART_NAME"],
        row_count=2607,
    )
    draft = AnalysisPlanDraft(
        analysis_type="descriptive",
        objective="제품별 불량률",
        filters=[FilterCondition(column="PassOrFail", operator="eq", value=1)],
        group_by=["PART_NAME"],
        metrics=[
            MetricSpec(
                name="defect_rate",
                aggregation="rate",
                column="PassOrFail",
                positive_value=1,
                alias="defect_rate",
            )
        ],
        visualization_hint=VisualizationHint(preferred_chart="bar"),
        ambiguity_status="clear",
    )

    with pytest.raises(
        ValueError,
        match="positive value cannot be combined with filters",
    ):
        processor.validate_and_finalize_plan(draft, metadata)


def test_indicator_sum_metric_positive_value_is_normalized() -> None:
    processor = AnalysisProcessor()
    metadata = MetadataSnapshot(
        columns=["TimeStamp", "PART_NO", "PART_NAME", "EQUIP_NAME", "PassOrFail"],
        numeric_columns=["PassOrFail"],
        datetime_columns=["TimeStamp"],
        categorical_columns=["PART_NO", "PART_NAME", "EQUIP_NAME"],
        row_count=2607,
    )
    draft = AnalysisPlanDraft(
        analysis_type="defect_rate_by_group",
        objective="제품별 불량률과 불량 건수를 계산합니다.",
        group_by=["PART_NO", "PART_NAME", "EQUIP_NAME"],
        metrics=[
            MetricSpec(
                name="defect_rate",
                aggregation="rate",
                column="PassOrFail",
                positive_value=1,
                alias="defect_rate",
            ),
            MetricSpec(
                name="defective_count",
                aggregation="sum",
                column="PassOrFail",
                positive_value=1,
                alias="defective_count",
            ),
            MetricSpec(
                name="total_count",
                aggregation="count",
                column=None,
                alias="total_count",
            ),
        ],
        sort_by=[SortSpec(column="defect_rate", direction="desc")],
        time_context=TimeContext(
            time_column="TimeStamp",
            range_type="none",
            grain="month",
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
        ambiguity_status="clear",
    )

    plan = processor.validate_and_finalize_plan(draft, metadata)

    defective_count = next(
        metric for metric in plan.metrics if metric.alias == "defective_count"
    )
    assert defective_count.aggregation == "sum"
    assert defective_count.column == "PassOrFail"
    assert defective_count.positive_value is None
    assert {"PART_NO", "PART_NAME", "EQUIP_NAME", "PassOrFail", "TimeStamp"} <= set(
        plan.used_columns
    )
