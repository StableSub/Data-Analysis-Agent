from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.modules.preprocess.planner import (
    PROMPTS,
    PreprocessPlan,
    build_preprocess_plan_from_recommendations,
)


def test_preprocess_plan_accepts_scale_with_method() -> None:
    plan = PreprocessPlan.model_validate(
        {
            "operations": [
                {
                    "op": "scale",
                    "columns": ["Mold_Temperature_12"],
                    "method": "standardize",
                }
            ],
            "planner_comment": "수치형 컬럼을 표준화합니다.",
        }
    )

    operation = plan.operations[0]
    assert operation.op == "scale"
    assert operation.method == "standardize"


def test_preprocess_plan_rejects_scale_without_method() -> None:
    with pytest.raises(ValidationError, match="scale.method"):
        PreprocessPlan.model_validate(
            {
                "operations": [
                    {
                        "op": "scale",
                        "columns": ["Mold_Temperature_12"],
                    }
                ],
                "planner_comment": "수치형 컬럼을 표준화합니다.",
            }
        )


def test_preprocess_plan_prompt_lists_scale_method_contract() -> None:
    prompt = PROMPTS.load_prompt("plan.system")

    assert "scale" in prompt
    assert "method" in prompt
    assert "standardize" in prompt
    assert "normalize" in prompt


def test_recommendation_plan_normalizer_converts_eda_shape_to_operations() -> None:
    plan = build_preprocess_plan_from_recommendations(
        [
            {
                "op": "drop_columns",
                "target_columns": ["Reason"],
                "source_columns": [],
                "target_column": "",
                "transform_type": "",
                "params": {},
                "reason": "결측치가 너무 많습니다.",
                "priority": "high",
            },
            {
                "op": "scale",
                "columns": ["Injection_Time"],
                "source_columns": [],
                "target_column": "",
                "transform_type": None,
                "params": None,
                "reason": "스케일 차이가 큽니다.",
                "priority": "medium",
            },
        ]
    )

    assert plan is not None
    assert len(plan.operations) == 2
    assert plan.operations[0].op == "drop_columns"
    assert plan.operations[0].columns == ["Reason"]
    assert plan.operations[1].op == "scale"
    assert plan.operations[1].columns == ["Injection_Time"]
    assert plan.operations[1].method == "standardize"


def test_recommendation_plan_normalizer_filters_removed_columns() -> None:
    plan = build_preprocess_plan_from_recommendations(
        [
            {
                "op": "drop_columns",
                "target_columns": ["Injection_Time", "Max_Injection_Speed"],
            },
            {
                "op": "drop_columns",
                "target_columns": ["Clamp_Open_Position", "Max_Injection_Speed"],
            },
            {
                "op": "scale",
                "target_columns": [
                    "Injection_Time",
                    "Clamp_Open_Position",
                    "Average_Back_Pressure",
                ],
            },
        ],
        available_columns=[
            "Injection_Time",
            "Max_Injection_Speed",
            "Clamp_Open_Position",
            "Average_Back_Pressure",
        ],
    )

    assert plan is not None
    assert [operation.op for operation in plan.operations] == [
        "drop_columns",
        "drop_columns",
        "scale",
    ]
    dumped_operations = [operation.model_dump() for operation in plan.operations]
    assert dumped_operations[0]["columns"] == ["Injection_Time", "Max_Injection_Speed"]
    assert dumped_operations[1]["columns"] == ["Clamp_Open_Position"]
    assert dumped_operations[2]["columns"] == ["Average_Back_Pressure"]
