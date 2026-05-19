from __future__ import annotations

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.schemas import (
    AnalysisOutputPayload,
    AnalysisPlanDraft,
    MetadataSnapshot,
    MetricSpec,
    SandboxExecutionResult,
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
