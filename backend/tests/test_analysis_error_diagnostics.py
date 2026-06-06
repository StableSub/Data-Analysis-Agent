from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.sandbox import AnalysisSandbox
from backend.app.modules.analysis.schemas import (
    AnalysisError,
    AnalysisPlan,
    AnalysisPlanDraft,
    DerivedColumnSpec,
    ExpectedOutputSpec,
    FilterCondition,
    MetadataSnapshot,
    MetricSpec,
    SortSpec,
    TimeContext,
    VisualizationHint,
)
from backend.app.modules.analysis.service import AnalysisService
from backend.app.modules.datasets.models import Dataset


def _minimal_plan() -> AnalysisPlan:
    return AnalysisPlan(
        analysis_type="group_by_count",
        objective="불량 사유별 건수를 계산합니다.",
        required_columns=["PassOrFail", "Reason"],
        used_columns=["PassOrFail", "Reason"],
        group_by=["Reason"],
        expected_output=ExpectedOutputSpec(
            require_summary=True,
            require_table=True,
            require_raw_metrics=False,
            expected_table_columns=["Reason", "count"],
            allow_empty_table=True,
            minimum_rows=0,
            require_group_axis=True,
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
        empty_result_policy="success_with_empty_summary",
        metadata_snapshot=MetadataSnapshot(columns=["PassOrFail", "Reason"], row_count=2),
        codegen_strategy="llm_codegen",
    )


def _write_dataset(path: Path) -> None:
    path.write_text("PassOrFail,Reason\n1,가스\n1,미성형\n", encoding="utf-8")


def test_sandbox_schema_validation_records_diagnostic_cause(tmp_path: Path) -> None:
    dataset_path = tmp_path / "data.csv"
    _write_dataset(dataset_path)

    result = AnalysisSandbox(timeout_seconds=5).execute(
        code=(
            "payload = {"
            "'summary': '불량 사유별 건수를 계산했습니다.', "
            "'table': {'Reason': '가스', 'count': 1}, "
            "'raw_metrics': {}, "
            "'used_columns': ['PassOrFail', 'Reason']"
            "}\n"
            "print(json.dumps(payload, ensure_ascii=False))"
        ),
        dataset_path=str(dataset_path),
    )

    assert result.ok is False
    assert result.error_type == "invalid_json"
    assert result.message == "analysis output schema validation failed"
    assert result.diagnostic_message
    assert "table" in result.diagnostic_message
    assert "Input should be a valid list" in result.diagnostic_message
    assert "stdout_excerpt" in result.diagnostic_message


def test_sandbox_normalizes_structured_summary_without_discarding_valid_analysis(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "data.csv"
    _write_dataset(dataset_path)

    result = AnalysisSandbox(timeout_seconds=5).execute(
        code=(
            "payload = {"
            "'summary': {'total_considered': 2, 'defect_rate': 0.5}, "
            "'table': [{'Reason': '가스', 'count': 1}], "
            "'raw_metrics': {'total_considered': 2}, "
            "'used_columns': ['PassOrFail', 'Reason']"
            "}\n"
            "print(json.dumps(payload, ensure_ascii=False))"
        ),
        dataset_path=str(dataset_path),
    )

    assert result.ok is True
    assert result.stdout_json is not None
    assert result.stdout_json.table == [{"Reason": "가스", "count": 1}]
    assert result.stdout_json.raw_metrics == {"total_considered": 2}
    assert "total_considered" in result.stdout_json.summary


def test_analysis_repair_receives_sandbox_schema_diagnostic(tmp_path: Path) -> None:
    dataset_path = tmp_path / "data.csv"
    _write_dataset(dataset_path)
    captured_errors: list[AnalysisError] = []

    class RunService:
        def generate_analysis_code(self, **_: Any) -> str:
            return (
                "payload = {"
                "'summary': '불량 사유별 건수를 계산했습니다.', "
                "'table': {'Reason': '가스', 'count': 1}, "
                "'raw_metrics': {}, "
                "'used_columns': ['PassOrFail', 'Reason']"
                "}\n"
                "print(json.dumps(payload, ensure_ascii=False))"
            )

        def repair_analysis_code(self, **kwargs: Any) -> str:
            error = kwargs["analysis_error"]
            assert isinstance(error, AnalysisError)
            captured_errors.append(error)
            return (
                "payload = {"
                "'summary': '불량 사유별 건수를 계산했습니다.', "
                "'table': [{'Reason': '가스', 'count': 1}], "
                "'raw_metrics': {}, "
                "'used_columns': ['PassOrFail', 'Reason']"
                "}\n"
                "print(json.dumps(payload, ensure_ascii=False))"
            )

    service: Any = object.__new__(AnalysisService)
    service.run_service = RunService()
    service.processor = AnalysisProcessor()
    service.sandbox = AnalysisSandbox(timeout_seconds=5)
    service.max_retries = 1
    dataset = Dataset(
        source_id="source-1",
        filename="data.csv",
        storage_path=str(dataset_path),
    )

    bundle = service._run_code_generation_loop(
        question="PassOrFail=1인 불량 데이터만 대상으로 불량 사유별 건수를 알려줘.",
        dataset=dataset,
        analysis_plan=_minimal_plan(),
        model_id=None,
    )

    assert bundle["final_status"] == "success"
    assert captured_errors
    diagnostic = captured_errors[0].detail.get("diagnostic_message")
    assert isinstance(diagnostic, str)
    assert "table" in diagnostic
    assert "Input should be a valid list" in diagnostic


def test_generated_code_rejects_fillna_without_concrete_value() -> None:
    invalid_code = (
        "table_df = df[['PassOrFail', 'Reason']].copy()\n"
        "table_df = table_df.fillna(value=None)\n"
        "payload = {"
        "'summary': '불량 사유별 건수를 계산했습니다.', "
        "'table': table_df.to_dict(orient='records'), "
        "'raw_metrics': {}, "
        "'used_columns': ['PassOrFail', 'Reason']"
        "}\n"
        "print(json.dumps(payload, ensure_ascii=False))"
    )

    try:
        AnalysisProcessor().validate_generated_code(
            generated_code=invalid_code,
            analysis_plan=_minimal_plan(),
        )
    except ValueError as exc:
        assert "fillna without a concrete value" in str(exc)
        assert "where(pd.notna(...), None)" in str(exc)
    else:
        raise AssertionError("fillna(value=None) should fail code validation")


def test_analysis_repair_receives_code_validation_diagnostic(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "data.csv"
    _write_dataset(dataset_path)
    captured_errors: list[AnalysisError] = []

    class RunService:
        def generate_analysis_code(self, **_: Any) -> str:
            return (
                "table_df = df[['PassOrFail', 'Reason']].copy()\n"
                "table_df = table_df.fillna(value=None)\n"
                "payload = {"
                "'summary': '불량 사유별 건수를 계산했습니다.', "
                "'table': table_df.to_dict(orient='records'), "
                "'raw_metrics': {}, "
                "'used_columns': ['PassOrFail', 'Reason']"
                "}\n"
                "print(json.dumps(payload, ensure_ascii=False))"
            )

        def repair_analysis_code(self, **kwargs: Any) -> str:
            error = kwargs["analysis_error"]
            assert isinstance(error, AnalysisError)
            captured_errors.append(error)
            return (
                "payload = {"
                "'summary': '불량 사유별 건수를 계산했습니다.', "
                "'table': [{'Reason': '가스', 'count': 1}], "
                "'raw_metrics': {}, "
                "'used_columns': ['PassOrFail', 'Reason']"
                "}\n"
                "print(json.dumps(payload, ensure_ascii=False))"
            )

    service: Any = object.__new__(AnalysisService)
    service.run_service = RunService()
    service.processor = AnalysisProcessor()
    service.sandbox = AnalysisSandbox(timeout_seconds=5)
    service.max_retries = 1
    dataset = Dataset(
        source_id="source-1",
        filename="data.csv",
        storage_path=str(dataset_path),
    )

    bundle = service._run_code_generation_loop(
        question="왜 불량이 났는지도 설명해 줄 수 있어?",
        dataset=dataset,
        analysis_plan=_minimal_plan(),
        model_id=None,
    )

    assert bundle["final_status"] == "success"
    assert captured_errors
    assert captured_errors[0].stage == "code_validation"
    diagnostic = captured_errors[0].detail.get("diagnostic_message")
    assert isinstance(diagnostic, str)
    assert "fillna without a concrete value" in diagnostic


def test_open_ended_time_bucket_plan_does_not_fail_plan_validation() -> None:
    metadata = MetadataSnapshot(
        columns=["TimeStamp", "PassOrFail", "Reason", "EQUIP_NAME"],
        dtypes={
            "TimeStamp": "datetime64[ns]",
            "PassOrFail": "int64",
            "Reason": "object",
            "EQUIP_NAME": "object",
        },
        numeric_columns=["PassOrFail"],
        datetime_columns=["TimeStamp"],
        categorical_columns=["Reason", "EQUIP_NAME"],
        row_count=2607,
    )
    draft = AnalysisPlanDraft(
        analysis_type="root_cause_defect_analysis",
        objective="불량 발생 원인을 설명하기 위해 불량률과 시간별 패턴을 함께 확인합니다.",
        group_by=["Reason", "EQUIP_NAME"],
        metrics=[
            MetricSpec(
                name="defect_rate",
                aggregation="rate",
                column="PassOrFail",
                positive_value=1,
                alias="defect_rate",
            )
        ],
        time_context=TimeContext(
            time_column="TimeStamp",
            range_type="absolute",
            grain="day",
        ),
    )

    plan = AnalysisProcessor().validate_and_finalize_plan(
        plan_draft=draft,
        dataset_meta=metadata,
    )

    assert plan.time_context is not None
    assert plan.time_context.time_column == "TimeStamp"
    assert plan.time_context.range_type == "none"
    assert plan.time_context.grain == "day"
    assert "TimeStamp" in plan.required_columns
    assert plan.expected_output.require_time_axis is True


def test_indicator_count_positive_value_normalizes_for_categorical_label() -> None:
    metadata = MetadataSnapshot(
        columns=["PassOrFail", "Reason"],
        dtypes={"PassOrFail": "int64", "Reason": "object"},
        numeric_columns=[],
        categorical_columns=["PassOrFail", "Reason"],
        row_count=2607,
    )
    draft = AnalysisPlanDraft(
        analysis_type="defect_root_cause_exploration",
        objective="불량 건수와 사유별 패턴을 확인합니다.",
        group_by=["Reason"],
        metrics=[
            MetricSpec(
                name="defect_count",
                aggregation="sum",
                column="PassOrFail",
                positive_value=1,
                alias="defect_count",
            )
        ],
    )

    plan = AnalysisProcessor().validate_and_finalize_plan(
        plan_draft=draft,
        dataset_meta=metadata,
    )

    assert plan.metrics[0].aggregation == "sum"
    assert plan.metrics[0].column == "PassOrFail"
    assert plan.metrics[0].positive_value is None


def test_daily_defect_rate_allows_not_null_filter_on_indicator_column() -> None:
    metadata = MetadataSnapshot(
        columns=["TimeStamp", "PassOrFail"],
        dtypes={"TimeStamp": "datetime64[ns]", "PassOrFail": "int64"},
        numeric_columns=["PassOrFail"],
        datetime_columns=["TimeStamp"],
        row_count=2607,
    )
    draft = AnalysisPlanDraft(
        analysis_type="daily_defect_analysis",
        objective=(
            "Compute daily defect counts and daily defect rate based on "
            "PassOrFail (1=defect) using TimeStamp."
        ),
        filters=[
            FilterCondition(column="PassOrFail", operator="not_null", value=None)
        ],
        group_by=["TimeStamp"],
        metrics=[
            MetricSpec(
                name="defect_count_per_day",
                aggregation="sum",
                column="PassOrFail",
                positive_value=1,
                alias="defect_count_per_day",
            ),
            MetricSpec(
                name="total_count_per_day",
                aggregation="count",
                column=None,
                alias="total_count_per_day",
            ),
            MetricSpec(
                name="defect_rate_per_day",
                aggregation="rate",
                column="PassOrFail",
                positive_value=1,
                alias="defect_rate_per_day",
            ),
        ],
        time_context=TimeContext(
            time_column="TimeStamp",
            range_type="none",
            grain="day",
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
    )

    plan = AnalysisProcessor().validate_and_finalize_plan(draft, metadata)

    assert plan.filters == [
        FilterCondition(column="PassOrFail", operator="not_null", value=None)
    ]
    assert plan.metrics[2].positive_value == 1
    assert plan.expected_output.require_time_axis is True


def test_datetime_part_date_alias_normalizes_for_daily_bucket_plan() -> None:
    metadata = MetadataSnapshot(
        columns=["TimeStamp", "PassOrFail"],
        dtypes={"TimeStamp": "datetime64[ns]", "PassOrFail": "int64"},
        numeric_columns=["PassOrFail"],
        datetime_columns=["TimeStamp"],
        row_count=2607,
    )
    draft = AnalysisPlanDraft(
        analysis_type="daily_defect_time_series",
        objective="TimeStamp에서 날짜를 만들어 날짜별 불량 건수를 계산합니다.",
        filters=[FilterCondition(column="PassOrFail", operator="eq", value=1)],
        group_by=["Date"],
        metrics=[
            MetricSpec(
                name="defect_count",
                aggregation="count",
                column=None,
                alias="defect_count",
            )
        ],
        derived_columns=[
            DerivedColumnSpec(
                name="Date",
                expression_type="datetime_part",
                source_columns=["TimeStamp"],
                params={"part": "date"},
            )
        ],
        sort_by=[SortSpec(column="Date", direction="asc")],
        time_context=TimeContext(
            time_column="TimeStamp",
            range_type="none",
            grain="day",
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
    )

    plan = AnalysisProcessor().validate_and_finalize_plan(draft, metadata)

    assert plan.derived_columns[0].params["part"] == "day"
    assert plan.group_by == []
    assert plan.expected_output.require_time_axis is True
    assert plan.sort_by == [SortSpec(column="Date", direction="asc")]


def test_guideline_optional_outlier_recommendation_does_not_make_daily_defect_plan_fail_result_validation() -> None:
    metadata = MetadataSnapshot(
        columns=["TimeStamp", "PassOrFail"],
        dtypes={"TimeStamp": "datetime64[ns]", "PassOrFail": "int64"},
        numeric_columns=["PassOrFail"],
        datetime_columns=["TimeStamp"],
        row_count=2607,
    )
    draft = AnalysisPlanDraft(
        analysis_type="time_series_defect_by_date",
        objective=(
            "일별(TimeStamp 기준) 불량 건수와 불량률을 계산하고, "
            "간단한 추세와 이동평균 제안을 제공하며, "
            "필요하면 3시그마 규칙에 의한 이상치를 표시하는 방법도 계획한다."
        ),
        group_by=["date"],
        metrics=[
            MetricSpec(
                name="defect_count",
                aggregation="sum",
                column="PassOrFail",
                positive_value=1,
                alias="defect_count",
            ),
            MetricSpec(
                name="defect_rate",
                aggregation="rate",
                column="PassOrFail",
                positive_value=1,
                alias="defect_rate",
            ),
            MetricSpec(
                name="total_inspected",
                aggregation="count",
                column=None,
                alias="total_inspected",
            ),
        ],
        sort_by=[SortSpec(column="date", direction="asc")],
        time_context=TimeContext(
            time_column="TimeStamp",
            range_type="none",
            grain="day",
        ),
    )

    plan = AnalysisProcessor().validate_and_finalize_plan(draft, metadata)
    result = AnalysisProcessor().validate_execution_result(
        {
            "ok": True,
            "stdout_json": {
                "summary": (
                    "Date range: 2026-05-01 to 2026-05-02; "
                    "Defect count: 3; Inspected: 10; Defect rate: 0.300000"
                ),
                "table": [
                    {
                        "date": "2026-05-01",
                        "defect_count": 2,
                        "defect_rate": 0.25,
                        "total_inspected": 8,
                    },
                    {
                        "date": "2026-05-02",
                        "defect_count": 1,
                        "defect_rate": 0.5,
                        "total_inspected": 2,
                    },
                ],
                "raw_metrics": {
                    "defect_count_by_date": [
                        {"date": "2026-05-01", "defect_count": 2},
                        {"date": "2026-05-02", "defect_count": 1},
                    ]
                },
                "used_columns": ["PassOrFail", "TimeStamp"],
            },
        },
        plan,
    )

    assert plan.expected_output.require_outlier_info is False
    assert result.execution_status == "success"
    assert result.error_stage is None


def test_explicit_outlier_analysis_still_requires_outlier_metrics() -> None:
    metadata = MetadataSnapshot(
        columns=["TimeStamp", "PassOrFail"],
        dtypes={"TimeStamp": "datetime64[ns]", "PassOrFail": "int64"},
        numeric_columns=["PassOrFail"],
        datetime_columns=["TimeStamp"],
        row_count=2607,
    )
    draft = AnalysisPlanDraft(
        analysis_type="daily_defect_outlier_detection",
        objective="날짜별 불량 건수의 이상치를 찾아줘.",
        group_by=["date"],
        metrics=[
            MetricSpec(
                name="defect_count",
                aggregation="sum",
                column="PassOrFail",
                positive_value=1,
                alias="defect_count",
            )
        ],
        sort_by=[SortSpec(column="date", direction="asc")],
        time_context=TimeContext(
            time_column="TimeStamp",
            range_type="none",
            grain="day",
        ),
    )

    plan = AnalysisProcessor().validate_and_finalize_plan(draft, metadata)
    result = AnalysisProcessor().validate_execution_result(
        {
            "ok": True,
            "stdout_json": {
                "summary": "일별 불량 건수입니다.",
                "table": [{"date": "2026-05-01", "defect_count": 2}],
                "raw_metrics": {"defect_count_by_date": []},
                "used_columns": ["PassOrFail", "TimeStamp"],
            },
        },
        plan,
    )

    assert plan.expected_output.require_outlier_info is True
    assert result.execution_status == "fail"
    assert result.error_stage == "result_validation"
    assert result.diagnostic_message == "outlier information is required"
