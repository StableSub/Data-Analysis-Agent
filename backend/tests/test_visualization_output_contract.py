from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.app.modules.analysis.schemas import (
    AnalysisExecutionResult,
    AnalysisPlan,
    ChartData,
    ChartSeries,
    ExpectedOutputSpec,
    MetadataSnapshot,
    VisualizationHint,
    VisualizationOutput,
)

from backend.app.modules.visualization.executor import (
    _build_python_code,
    _build_unavailable_result,
    execute_visualization_plan,
)
from backend.app.modules.visualization.schemas import VisualizationResultPayload
from backend.app.modules.visualization.service import VisualizationService


class _FakeVisualizationProcessor:
    def build_from_analysis_result(self, *, analysis_plan: AnalysisPlan, analysis_result: AnalysisExecutionResult) -> VisualizationOutput:
        return VisualizationOutput(
            status="generated",
            chart_data=ChartData(
                chart_type="bar",
                x=["0", "1"],
                series=[ChartSeries(name="PassOrFail_count", y=[2555, 52])],
                caption="양품/불량 분포",
            ),
        )


class _FakeVisualizationService:
    def __init__(self, dataset_path: Path) -> None:
        self.dataset_path = dataset_path
        self.frame = pd.read_csv(dataset_path)

    def load_sample_frame(self, source_id: str, *, nrows: int) -> tuple[pd.DataFrame | None, str]:
        return self.frame.head(nrows), "loaded"

    def resolve_source_path(self, source_id: str) -> Path:
        return self.dataset_path


def _analysis_plan() -> AnalysisPlan:
    return AnalysisPlan(
        analysis_type="descriptive",
        objective="양품/불량 분포",
        required_columns=["PassOrFail"],
        used_columns=["PassOrFail"],
        expected_output=ExpectedOutputSpec(
            require_summary=True,
            require_table=True,
            require_raw_metrics=True,
            expected_table_columns=["PassOrFail", "PassOrFail_count"],
            allow_empty_table=False,
            minimum_rows=1,
            require_group_axis=True,
        ),
        visualization_hint=VisualizationHint(preferred_chart="bar"),
        empty_result_policy="success_with_empty_summary",
        metadata_snapshot=MetadataSnapshot(columns=["PassOrFail"], row_count=2607),
        codegen_strategy="llm_codegen",
    )


def test_analysis_visualization_result_includes_canonical_charts_list() -> None:
    service = VisualizationService(
        repository=None,  # type: ignore[arg-type]
        reader=None,  # type: ignore[arg-type]
        processor=_FakeVisualizationProcessor(),  # type: ignore[arg-type]
    )

    result = service.build_from_analysis_result(
        source_id="benchmark-moldset-labeled",
        analysis_plan=_analysis_plan(),
        analysis_result=AnalysisExecutionResult(
            execution_status="success",
            summary="양품/불량 분포입니다.",
            table=[{"PassOrFail": "0", "PassOrFail_count": 2555}],
            raw_metrics={"total_count": 2607},
            used_columns=["PassOrFail"],
        ),
    )

    payload = VisualizationResultPayload.model_validate(result)
    assert payload.chart is not None
    assert payload.chart_data is not None
    assert payload.charts is not None
    assert len(payload.charts) == 1
    assert payload.charts[0] == payload.chart_data


def test_unavailable_visualization_result_matches_result_contract() -> None:
    result = _build_unavailable_result(source_id="source-1", summary="데이터 없음")

    payload = VisualizationResultPayload.model_validate(result)
    assert payload.status == "unavailable"
    assert payload.source_id == "source-1"
    assert payload.summary == "데이터 없음"


def test_execute_visualization_plan_includes_empty_canonical_charts_for_artifact_result(tmp_path: Path) -> None:
    dataset_path = tmp_path / "source.csv"
    pd.DataFrame(
        [
            {"PassOrFail": "0", "PassOrFail_count": 2555},
            {"PassOrFail": "1", "PassOrFail_count": 52},
        ]
    ).to_csv(dataset_path, index=False)

    result = execute_visualization_plan(
        visualization_service=_FakeVisualizationService(dataset_path),  # type: ignore[arg-type]
        visualization_plan={
            "status": "planned",
            "source_id": "source-1",
            "chart_type": "bar",
            "x_key": "PassOrFail",
            "y_key": "PassOrFail_count",
        },
        approved_plan=None,
        max_sample_rows=100,
        max_points=100,
    )

    payload = VisualizationResultPayload.model_validate(result)
    assert payload.status == "generated"
    assert payload.artifact is not None
    assert payload.charts == []


def test_matplotlib_chart_code_pins_light_background() -> None:
    code = _build_python_code(
        dataset_path="/tmp/source.csv",
        chart_type="bar",
        x_key="PassOrFail",
        y_key="PassOrFail_count",
        output_filename="chart.png",
        max_points=120,
        x_is_datetime=False,
    )

    assert "plt.style.use('default')" in code
    assert "facecolor='white'" in code
    assert "ax.set_facecolor('white')" in code
    assert "transparent=False" in code
    assert "#111827" in code
    assert "#E5E7EB" in code
