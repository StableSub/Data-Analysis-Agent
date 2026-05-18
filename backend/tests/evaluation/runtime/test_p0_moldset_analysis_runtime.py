from __future__ import annotations

import pytest

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.schemas import (
    AnalysisOutputPayload,
    AnalysisPlan,
    ExpectedOutputSpec,
    MetadataSnapshot,
    MetricSpec,
    SandboxExecutionResult,
    VisualizationHint,
)
from backend.app.modules.preprocess.processor import PreprocessProcessor
from backend.app.modules.preprocess.schemas import ScaleOperation
from eval_cases import RAW_DIR, require_dataset_path
from moldset_p0_oracles import (
    expected_defect_rate_by_part,
    expected_defect_reason_counts,
    expected_label_distribution,
    header,
)
from runtime_assertions import assert_float_close, assert_table_close, assert_used_columns

pd = pytest.importorskip("pandas")

pytestmark = pytest.mark.skipif(
    not RAW_DIR.exists(),
    reason="evaluation/raw datasets are local benchmark artifacts",
)


def _analysis_plan(
    *,
    required_columns: list[str],
    expected_table_columns: list[str],
    minimum_rows: int,
    require_group_axis: bool = False,
) -> AnalysisPlan:
    return AnalysisPlan(
        analysis_type="descriptive",
        objective="P0 deterministic benchmark oracle validation",
        required_columns=required_columns,
        used_columns=required_columns,
        group_by=expected_table_columns[:1] if require_group_axis else [],
        metrics=[MetricSpec(name="count", aggregation="count", alias="count")],
        expected_output=ExpectedOutputSpec(
            require_summary=True,
            require_table=bool(expected_table_columns),
            require_raw_metrics=True,
            expected_table_columns=expected_table_columns,
            allow_empty_table=False,
            minimum_rows=minimum_rows,
            require_group_axis=require_group_axis,
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
        empty_result_policy="success_with_empty_summary",
        metadata_snapshot=MetadataSnapshot(columns=header(), row_count=2607),
        codegen_strategy="llm_codegen",
    )


def test_analysis_processor_accepts_p0_label_distribution_payload() -> None:
    expected = expected_label_distribution()
    plan = _analysis_plan(
        required_columns=["PassOrFail"],
        expected_table_columns=[],
        minimum_rows=0,
    )
    payload = AnalysisOutputPayload(
        summary="총 2607건 중 정상 2555건, 불량 52건입니다.",
        raw_metrics=expected,
        used_columns=["PassOrFail"],
    )

    result = AnalysisProcessor().validate_execution_result(
        SandboxExecutionResult(ok=True, stdout_json=payload),
        plan,
    )

    assert result.execution_status == "success"
    assert result.quality_status == "partial"
    assert_float_close(result.raw_metrics["defect_rate_pct"], expected["defect_rate_pct"])
    assert_used_columns(result.used_columns, ["PassOrFail"])


def test_analysis_processor_accepts_p0_product_defect_table_payload() -> None:
    expected = expected_defect_rate_by_part()
    plan = _analysis_plan(
        required_columns=["PART_NAME", "PassOrFail"],
        expected_table_columns=["PART_NAME", "total_count", "defect_count", "defect_rate_pct"],
        minimum_rows=4,
        require_group_axis=True,
    )
    payload = AnalysisOutputPayload(
        summary="제품별 불량률을 계산했습니다.",
        table=expected,
        raw_metrics={"part_count": len(expected)},
        used_columns=["PART_NAME", "PassOrFail"],
    )

    result = AnalysisProcessor().validate_execution_result(
        SandboxExecutionResult(ok=True, stdout_json=payload),
        plan,
    )

    assert result.execution_status == "success"
    assert result.quality_status == "complete"
    assert_table_close(
        result.table,
        expected,
        key_column="PART_NAME",
        metric_columns=["total_count", "defect_count", "defect_rate_pct"],
    )


def test_analysis_processor_accepts_p0_defect_reason_table_payload() -> None:
    expected = expected_defect_reason_counts()
    plan = _analysis_plan(
        required_columns=["Reason", "PassOrFail"],
        expected_table_columns=["Reason", "defect_count"],
        minimum_rows=3,
        require_group_axis=True,
    )
    payload = AnalysisOutputPayload(
        summary="불량 사유별 건수를 계산했습니다.",
        table=expected,
        raw_metrics={"reason_count": len(expected)},
        used_columns=["Reason", "PassOrFail"],
    )

    result = AnalysisProcessor().validate_execution_result(
        SandboxExecutionResult(ok=True, stdout_json=payload),
        plan,
    )

    assert result.execution_status == "success"
    assert result.quality_status == "complete"
    assert_table_close(
        result.table,
        expected,
        key_column="Reason",
        metric_columns=["defect_count"],
    )


def test_preprocess_processor_standardizes_process_columns_without_protected_columns() -> None:
    source = require_dataset_path("moldset_labeled.csv")
    scale_columns = ["Injection_Time", "Filling_Time", "Plasticizing_Time", "Cycle_Time"]
    protected_columns = ["PassOrFail", "PART_NAME", "PART_NO", "PART_FACT_SERIAL", "TimeStamp"]
    df = pd.read_csv(source, usecols=[*scale_columns, *protected_columns])
    operation = ScaleOperation(op="scale", columns=scale_columns, method="standardize")

    processed = PreprocessProcessor().apply_operations(df, [operation])

    assert set(operation.columns).isdisjoint(protected_columns)
    for column in scale_columns:
        assert_float_close(processed[column].mean(), 0.0, tolerance=1e-9, context=f"{column}.mean")
        assert_float_close(processed[column].std(ddof=0), 1.0, tolerance=1e-9, context=f"{column}.std")
    for column in protected_columns:
        assert processed[column].equals(df[column])
