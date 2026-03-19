from __future__ import annotations

import json
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ...core.ai import PromptRegistry, StructuredOutputRunner
from .schemas import PreprocessOperation

PROMPTS = PromptRegistry(
    {
        "plan.system": (
            "너는 전처리 플래너다. "
            "PreprocessPlan 스키마 형식으로만 반환하고 "
            "지원 연산은 drop_missing, impute, drop_columns, rename_columns, scale, derived_column다. "
            "전처리가 불필요하면 operations는 빈 배열로 반환하라. "
            "operations는 op+파라미터로 구성하며 "
            "planner_comment에는 판단 근거를 1~2문장으로 남겨라."
        ),
        "decision.system": (
            "데이터 프로파일을 보고 run_preprocess 또는 skip_preprocess를 반환하라. "
            "reason_summary에는 판단 근거를 1문장으로 남겨라."
        ),
    }
)


class PreprocessPlan(BaseModel):
    operations: list[PreprocessOperation] = Field(default_factory=list)
    planner_comment: str = ""


class PreprocessDecision(BaseModel):
    step: Literal["run_preprocess", "skip_preprocess"] = Field(...)
    reason_summary: str = ""


def build_preprocess_plan(
    *,
    user_input: str,
    source_id: str | None,
    dataset_profile: dict,
    revision_request: str,
    model_id: str | None,
    default_model: str,
) -> PreprocessPlan:
    runner = StructuredOutputRunner(default_model=default_model)
    profile_json = json.dumps(dataset_profile, ensure_ascii=False)
    revision_text = f"\nrevision_request={revision_request}" if revision_request else ""
    return runner.invoke(
        schema=PreprocessPlan,
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("plan.system")),
            HumanMessage(
                content=(
                    f"user_input={user_input}\n"
                    f"source_id={source_id}\n"
                    f"dataset_profile={profile_json}"
                    f"{revision_text}"
                )
            ),
        ],
    )


def decide_preprocess(
    *,
    user_input: str,
    dataset_profile: dict,
    model_id: str | None,
    default_model: str,
) -> PreprocessDecision:
    runner = StructuredOutputRunner(default_model=default_model)
    profile_json = json.dumps(dataset_profile, ensure_ascii=False)
    return runner.invoke(
        schema=PreprocessDecision,
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("decision.system")),
            HumanMessage(content=f"user_input={user_input}\n{profile_json}"),
        ],
    )
