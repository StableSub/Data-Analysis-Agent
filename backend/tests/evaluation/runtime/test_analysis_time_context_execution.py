from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, cast

import pytest

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.run_service import AnalysisRunService
from backend.app.modules.analysis.sandbox import AnalysisSandbox
from backend.app.modules.analysis.schemas import (
    AnalysisPlan,
    ExpectedOutputSpec,
    MetadataSnapshot,
    MetricSpec,
    TimeContext,
    VisualizationHint,
)


class _JsonOnlyCodegenLlm:
    def __init__(self) -> None:
        self.messages: list[Any] = []

    def invoke(self, *, model_id: str | None, messages: list[Any]) -> SimpleNamespace:
        self.messages = messages
        return SimpleNamespace(
            content=json.dumps(
                {
                    "summary": "not executable code",
                    "table": [],
                    "raw_metrics": {},
                    "used_columns": ["TimeStamp", "PassOrFail"],
                },
                ensure_ascii=False,
            )
        )


def _daily_defect_plan() -> AnalysisPlan:
    return AnalysisPlan(
        analysis_type="time_series_defect_by_date",
        objective="Calculate daily defect counts using TimeStamp.",
        required_columns=["TimeStamp", "PassOrFail"],
        used_columns=["TimeStamp", "PassOrFail"],
        metrics=[
            MetricSpec(
                name="defect_count",
                aggregation="sum",
                column="PassOrFail",
                alias="defect_count",
            )
        ],
        time_context=TimeContext(
            time_column="TimeStamp",
            range_type="none",
            grain="day",
        ),
        expected_output=ExpectedOutputSpec(
            require_summary=True,
            require_table=True,
            require_raw_metrics=True,
            expected_table_columns=["date", "defect_count"],
            allow_empty_table=False,
            minimum_rows=1,
            require_time_axis=True,
        ),
        visualization_hint=VisualizationHint(
            preferred_chart="line",
            x="date",
            y="defect_count",
        ),
        empty_result_policy="success_with_empty_table",
        metadata_snapshot=MetadataSnapshot(
            columns=["TimeStamp", "PassOrFail"],
            numeric_columns=["PassOrFail"],
            datetime_columns=["TimeStamp"],
            row_count=2,
        ),
        codegen_strategy="llm_codegen",
    )


def test_time_context_column_is_datetime_coerced_before_generated_code_runs(
    tmp_path,
) -> None:
    dataset_path = tmp_path / "daily.csv"
    dataset_path.write_text(
        "TimeStamp,PassOrFail\n"
        "2026-05-01 01:00:00,1\n"
        "2026-05-01 02:00:00,0\n",
        encoding="utf-8",
    )
    generated_code = "\n".join(
        [
            "daily = (",
            "    df.assign(date=df['TimeStamp'].dt.date.astype(str))",
            "    .groupby('date', as_index=False)['PassOrFail']",
            "    .sum()",
            "    .rename(columns={'PassOrFail': 'defect_count'})",
            ")",
            "print(json.dumps({",
            "    'summary': 'daily defects',",
            "    'table': daily.to_dict('records'),",
            "    'raw_metrics': {'days': len(daily)},",
            "    'used_columns': ['TimeStamp', 'PassOrFail'],",
            "}, ensure_ascii=False))",
        ]
    )
    plan = _daily_defect_plan()

    validated_code = AnalysisProcessor().validate_generated_code(generated_code, plan)
    sandbox_result = AnalysisSandbox(timeout_seconds=5).execute(
        code=validated_code,
        dataset_path=str(dataset_path),
    )
    assert sandbox_result.ok, sandbox_result.stderr
    result = AnalysisProcessor().validate_execution_result(sandbox_result, plan)

    assert result.execution_status == "success"
    assert result.table == [{"date": "2026-05-01", "defect_count": 1}]
    assert json.loads(result.model_dump_json())["used_columns"] == [
        "TimeStamp",
        "PassOrFail",
    ]


def test_json_only_codegen_response_falls_back_to_executable_time_bucket_code(
    tmp_path,
) -> None:
    dataset_path = tmp_path / "daily.csv"
    dataset_path.write_text(
        "TimeStamp,PassOrFail\n"
        "2026-05-01 01:00:00,1\n"
        "2026-05-01 02:00:00,0\n"
        "2026-05-02 03:00:00,1\n",
        encoding="utf-8",
    )
    run_service = AnalysisRunService(default_model="test-model")
    run_service.llm = cast(Any, _JsonOnlyCodegenLlm())
    plan = _daily_defect_plan()

    generated_code = run_service.generate_analysis_code(
        question="날짜별 불량 건수를 분석해줘.",
        analysis_plan=plan,
        model_id="test-model",
    )

    assert "print(json.dumps" in generated_code
    validated_code = AnalysisProcessor().validate_generated_code(
        generated_code,
        plan,
    )
    sandbox_result = AnalysisSandbox(timeout_seconds=5).execute(
        code=validated_code,
        dataset_path=str(dataset_path),
    )
    result = AnalysisProcessor().validate_execution_result(sandbox_result, plan)

    assert result.execution_status == "success"
    assert result.table == [
        {"date": "2026-05-01", "defect_count": 1},
        {"date": "2026-05-02", "defect_count": 1},
    ]


def test_preloaded_json_import_alias_is_normalized_before_validation(
    tmp_path,
) -> None:
    dataset_path = tmp_path / "daily.csv"
    dataset_path.write_text(
        "TimeStamp,PassOrFail\n"
        "2026-05-01 01:00:00,1\n"
        "2026-05-02 02:00:00,1\n",
        encoding="utf-8",
    )
    generated_code = "\n".join(
        [
            "json_mod = __import__('json')",
            "daily = (",
            "    df.assign(date=df['TimeStamp'].dt.date.astype(str))",
            "    .groupby('date', as_index=False)['PassOrFail']",
            "    .sum()",
            "    .rename(columns={'PassOrFail': 'defect_count'})",
            ")",
            "print(json_mod.dumps({",
            "    'summary': 'daily defects',",
            "    'table': daily.to_dict('records'),",
            "    'raw_metrics': {'days': len(daily)},",
            "    'used_columns': ['TimeStamp', 'PassOrFail'],",
            "}, ensure_ascii=False))",
        ]
    )
    plan = _daily_defect_plan()

    validated_code = AnalysisProcessor().validate_generated_code(generated_code, plan)
    assert "__import__" not in validated_code
    assert "json.dumps" in validated_code
    sandbox_result = AnalysisSandbox(timeout_seconds=5).execute(
        code=validated_code,
        dataset_path=str(dataset_path),
    )
    assert sandbox_result.ok, sandbox_result.stderr
    result = AnalysisProcessor().validate_execution_result(sandbox_result, plan)

    assert result.execution_status == "success"
    assert result.table == [
        {"date": "2026-05-01", "defect_count": 1},
        {"date": "2026-05-02", "defect_count": 1},
    ]


def test_non_preloaded_import_call_still_fails_validation() -> None:
    generated_code = "\n".join(
        [
            "math_mod = __import__('math')",
            "print(json.dumps({",
            "    'summary': 'daily defects',",
            "    'table': [{'date': '2026-05-01', 'defect_count': 1}],",
            "    'raw_metrics': {},",
            "    'used_columns': ['TimeStamp', 'PassOrFail'],",
            "}, ensure_ascii=False))",
        ]
    )

    with pytest.raises(ValueError, match="__import__"):
        AnalysisProcessor().validate_generated_code(generated_code, _daily_defect_plan())
