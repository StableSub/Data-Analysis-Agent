from __future__ import annotations

import json
from typing import Any, Mapping
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ...core.ai import LLMGateway, PromptRegistry
from .schemas import PreprocessOperation

PROMPTS = PromptRegistry(
    {
        "plan.system": (
            "너는 전처리 플래너다. "
            "PreprocessPlan 스키마 형식으로만 반환하고 "
            "지원 연산은 drop_missing, impute, drop_columns, rename_columns, scale, "
            "derived_column, encode_categorical, parse_datetime, outlier다. "
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


def get_revision_instruction(revision_request: Mapping[str, Any] | str | None) -> str:
    if isinstance(revision_request, dict):
        if revision_request.get("stage") == "preprocess":
            instruction = revision_request.get("instruction")
            if isinstance(instruction, str):
                return instruction.strip()
        return ""
    return str(revision_request or "").strip()


def build_preprocess_decision(
    *,
    user_input: str,
    dataset_profile: dict[str, Any],
    handoff: Mapping[str, Any] | None,
    model_id: str | None,
    default_model: str,
) -> dict[str, Any]:
    if isinstance(handoff, dict) and "ask_preprocess" in handoff:
        ask_preprocess = bool(handoff.get("ask_preprocess", False))
        return {
            "step": "run_preprocess" if ask_preprocess else "skip_preprocess",
            "reason_summary": (
                "사용자 요청에 따라 전처리를 수행합니다."
                if ask_preprocess
                else "사용자 요청에 따라 전처리를 생략합니다."
            ),
        }

    llm = LLMGateway(default_model=default_model)
    profile_json = json.dumps(dataset_profile, ensure_ascii=False)
    decision = llm.invoke_structured(
        schema=PreprocessDecision,
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("decision.system")),
            HumanMessage(content=f"user_input={user_input}\n{profile_json}"),
        ],
    )
    return decision.model_dump()


def build_preprocess_plan(
    *,
    user_input: str,
    source_id: str,
    dataset_profile: dict[str, Any],
    revision_request: Mapping[str, Any] | str | None,
    model_id: str | None,
    default_model: str,
) -> PreprocessPlan:
    llm = LLMGateway(default_model=default_model)
    profile_json = json.dumps(dataset_profile, ensure_ascii=False)
    revision_text = (
        f"\nrevision_request={get_revision_instruction(revision_request)}"
        if get_revision_instruction(revision_request)
        else ""
    )
    return llm.invoke_structured(
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


def build_preprocess_review_payload(
    *,
    source_id: str,
    dataset_profile: dict[str, Any],
    plan: PreprocessPlan,
    reason_summary: str,
) -> dict[str, Any]:
    missing_rates = dataset_profile.get("missing_rates")
    top_missing_columns: list[dict[str, Any]] = []
    if isinstance(missing_rates, dict):
        sorted_items = sorted(
            (
                (str(column), float(rate))
                for column, rate in missing_rates.items()
                if isinstance(rate, (int, float)) and float(rate) > 0
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        top_missing_columns = [
            {"column": column, "missing_rate": rate}
            for column, rate in sorted_items[:5]
        ]

    planner_comment = plan.planner_comment.strip()
    summary = (
        planner_comment
        or reason_summary.strip()
        or "전처리 계획을 검토한 뒤 승인 여부를 결정해 주세요."
    )
    row_count = dataset_profile.get("sample_row_count")

    return {
        "stage": "preprocess",
        "kind": "plan_review",
        "title": "Preprocess plan review",
        "summary": summary,
        "source_id": source_id,
        "plan": {
            "operations": [operation.model_dump() for operation in plan.operations],
            "planner_comment": planner_comment,
            "top_missing_columns": top_missing_columns,
            "affected_columns": _collect_affected_columns(plan.operations),
            "row_count": int(row_count) if isinstance(row_count, int) else None,
        },
    }


def _collect_affected_columns(operations: list[PreprocessOperation]) -> list[str]:
    columns: list[str] = []
    for operation in operations:
        if operation.op in {
            "drop_missing",
            "impute",
            "drop_columns",
            "scale",
            "encode_categorical",
            "parse_datetime",
            "outlier",
        }:
            columns.extend(operation.columns)
        elif operation.op == "rename_columns":
            columns.extend(operation.rename_from)
            columns.extend(operation.rename_to)
        elif operation.op == "derived_column":
            columns.append(operation.name)
    return list(dict.fromkeys(str(column) for column in columns if str(column).strip()))
