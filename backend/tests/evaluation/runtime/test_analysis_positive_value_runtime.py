from __future__ import annotations

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
    VisualizationHint,
)


class _FakeCodegenLlm:
    def __init__(self, code: str) -> None:
        self.code = code
        self.messages: list[Any] = []

    def invoke(self, *, model_id: str | None, messages: list[Any]) -> SimpleNamespace:
        self.messages = messages
        return SimpleNamespace(content=self.code)


def _positive_value_plan() -> AnalysisPlan:
    return AnalysisPlan(
        analysis_type="descriptive",
        objective="제품별 불량률",
        filters=[],
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
        required_columns=["PART_NAME", "PassOrFail"],
        used_columns=["PART_NAME", "PassOrFail"],
        expected_output=ExpectedOutputSpec(
            require_summary=True,
            require_table=True,
            require_raw_metrics=True,
            expected_table_columns=["PART_NAME", "defect_rate"],
            allow_empty_table=False,
            minimum_rows=2,
            require_group_axis=True,
        ),
        visualization_hint=VisualizationHint(
            preferred_chart="bar",
            x="PART_NAME",
            y="defect_rate",
        ),
        empty_result_policy="fail_on_empty",
        metadata_snapshot=MetadataSnapshot(
            columns=["PART_NAME", "PassOrFail"],
            numeric_columns=["PassOrFail"],
            categorical_columns=["PART_NAME"],
            row_count=4,
        ),
        codegen_strategy="llm_codegen",
    )


def test_positive_value_codegen_contract_executes_full_group_denominator(
    tmp_path,
) -> None:
    dataset_path = tmp_path / "defects.csv"
    dataset_path.write_text(
        "PART_NAME,PassOrFail\nA,1\nA,0\nB,1\nB,1\n",
        encoding="utf-8",
    )
    generated_code = "\n".join(
        [
            "rows = []",
            'for part_name, group in df.groupby("PART_NAME", dropna=False):',
            '    defect_count = (group["PassOrFail"] == 1).sum()',
            "    defect_rate = defect_count / len(group) if len(group) else 0",
            '    rows.append({"PART_NAME": str(part_name), "defect_rate": float(defect_rate)})',
            "print(json.dumps({",
            '    "summary": "제품별 불량률입니다.",',
            '    "table": rows,',
            '    "raw_metrics": {"metric": "defect_rate"},',
            '    "used_columns": ["PART_NAME", "PassOrFail"],',
            "}, ensure_ascii=False))",
        ]
    )
    fake_llm = _FakeCodegenLlm(generated_code)
    run_service = AnalysisRunService(default_model="test-model")
    run_service.llm = cast(Any, fake_llm)
    plan = _positive_value_plan()

    code = run_service.generate_analysis_code(
        question="제품별 불량률을 막대그래프로 시각화해줘.",
        analysis_plan=plan,
        model_id="test-model",
    )
    system_prompt = fake_llm.messages[0].content
    human_prompt = fake_llm.messages[1].content
    assert "metric.positive_value" in system_prompt
    assert "그룹 전체 행을 분모" in system_prompt
    assert '"positive_value": 1' in human_prompt

    processor = AnalysisProcessor()
    validated_code = processor.validate_generated_code(code, plan)
    sandbox_result = AnalysisSandbox(timeout_seconds=5).execute(
        code=validated_code,
        dataset_path=str(dataset_path),
    )
    result = processor.validate_execution_result(sandbox_result, plan)

    assert result.execution_status == "success"
    table_by_part = {row["PART_NAME"]: row["defect_rate"] for row in result.table}
    assert table_by_part["A"] == pytest.approx(0.5)
    assert table_by_part["B"] == pytest.approx(1.0)
