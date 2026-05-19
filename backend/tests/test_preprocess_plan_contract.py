from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.modules.preprocess.planner import PROMPTS, PreprocessPlan


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
