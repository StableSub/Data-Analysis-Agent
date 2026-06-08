from __future__ import annotations

import json
from typing import Any, Mapping
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ...core.ai import LLMGateway, PromptRegistry
from .schemas import (
    DerivedColumnOperation,
    DropColumnsOperation,
    DropMissingOperation,
    EncodeCategoricalOperation,
    ImputeOperation,
    OutlierOperation,
    ParseDatetimeOperation,
    PreprocessOperation,
    ScaleOperation,
)

PROMPTS = PromptRegistry(
    {
        "plan.system": (
            "너는 전처리 플래너다. "
            "PreprocessPlan 스키마 형식으로만 반환하고 "
            "지원 연산은 drop_missing, impute, drop_columns, rename_columns, scale, derived_column, parse_datetime, outlier, encode_categorical다. "
            "dataset_profile에 preprocess_recommendations가 있으면 우선 참고하되, 사용자 요청과 데이터 상태에 맞게 조정하라. "
            "전처리가 불필요하면 operations는 빈 배열로 반환하라. "
            "operation별 필수 필드는 다음과 같다. "
            "drop_missing: op, columns, how(any/all). "
            "impute: op, columns, method(mean/median/mode/value), value. "
            "drop_columns: op, columns. "
            "rename_columns: op, rename_from, rename_to. "
            "scale: op, columns, method(standardize/normalize); 판단이 어렵다면 method는 standardize를 사용하라. "
            "derived_column: op, name, source_columns, transform_type(log1p/sum/difference/ratio), params. "
            "parse_datetime: op, columns, format. "
            "outlier: op, columns, method(zscore/iqr), strategy(drop/clip). "
            "encode_categorical: op, columns, method(one_hot/label). "
            "planner_comment에는 판단 근거를 1~2문장으로 남겨라."
        ),
        "decision.system": (
            "질문과 데이터 프로파일을 보고 run_preprocess 또는 skip_preprocess를 반환하라. "
            "단순 집계, 평균 계산, 그룹화, 최근 N개월 필터링, 추세 분석, 비교, 상관 분석, 시각화는 전처리가 아니라 분석이다. "
            "timestamp/date 컬럼을 월, 주, 일 단위로 묶어 집계하는 것은 분석 단계에서 처리할 수 있으므로 전처리로 보지 마라. "
            "월별 추세를 위해 year_month 같은 파생 컬럼을 만들 수 있더라도, 원본 datetime/timestamp 컬럼으로 분석이 가능하면 skip_preprocess를 선택하라. "
            "관계 분석 질문은 기본적으로 원시 x/y 관측치로 처리하며, 평균이나 그룹 요약을 명시적으로 요구하지 않았다면 그 이유만으로 전처리를 실행하지 마라. "
            "결측치 처리, 형변환, 문자열 정리, 정규화, 스케일링, 인코딩, 컬럼명 변경, 파생 컬럼 생성처럼 "
            "데이터를 먼저 정제하거나 변환해야 할 때만 run_preprocess를 선택하라. "
            "명시적인 전처리 요청이 없고 원본 데이터로 바로 분석이 가능하면 skip_preprocess를 선택하라. "
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
    if not get_revision_instruction(revision_request):
        deterministic_plan = build_preprocess_plan_from_recommendations(
            dataset_profile.get("preprocess_recommendations"),
            available_columns=dataset_profile.get("columns"),
        )
        if deterministic_plan is not None:
            return deterministic_plan

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


def build_preprocess_plan_from_recommendations(
    value: Any,
    *,
    available_columns: Any = None,
) -> PreprocessPlan | None:
    if not isinstance(value, list):
        return None

    active_columns_list = _string_list(available_columns)
    active_columns = set(active_columns_list) if active_columns_list else None
    removed_columns: set[str] = set()
    operations: list[PreprocessOperation] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        normalized_item = _normalize_recommendation_columns(
            item,
            active_columns=active_columns,
            removed_columns=removed_columns,
        )
        operation = _recommendation_to_operation(normalized_item)
        if operation is not None:
            operations.append(operation)
            _update_active_columns(operation, active_columns, removed_columns)

    if not operations:
        return None

    return PreprocessPlan(
        operations=operations,
        planner_comment="EDA 추천 항목을 실행 가능한 전처리 계획으로 변환했습니다.",
    )


def _normalize_recommendation_columns(
    item: Mapping[str, Any],
    *,
    active_columns: set[str] | None,
    removed_columns: set[str],
) -> dict[str, Any]:
    normalized = dict(item)
    op = str(item.get("op") or "").strip()
    columns = _filter_existing_columns(
        _recommendation_columns(item),
        active_columns=active_columns,
        removed_columns=removed_columns,
    )
    source_columns = _filter_existing_columns(
        _string_list(item.get("source_columns")),
        active_columns=active_columns,
        removed_columns=removed_columns,
    )

    if op == "derived_column":
        normalized["source_columns"] = source_columns
        if columns:
            normalized["columns"] = columns
            normalized["target_columns"] = columns
        return normalized

    normalized["columns"] = columns
    normalized["target_columns"] = columns
    return normalized


def _filter_existing_columns(
    columns: list[str],
    *,
    active_columns: set[str] | None,
    removed_columns: set[str],
) -> list[str]:
    filtered: list[str] = []
    seen: set[str] = set()
    for column in columns:
        if column in seen:
            continue
        seen.add(column)
        if active_columns is not None:
            if column not in active_columns:
                continue
        elif column in removed_columns:
            continue
        filtered.append(column)
    return filtered


def _update_active_columns(
    operation: PreprocessOperation,
    active_columns: set[str] | None,
    removed_columns: set[str],
) -> None:
    if operation.op == "drop_columns":
        for column in operation.columns:
            removed_columns.add(column)
            if active_columns is not None:
                active_columns.discard(column)
        return
    if operation.op == "rename_columns":
        for old_column in operation.rename_from:
            removed_columns.add(old_column)
            if active_columns is not None:
                active_columns.discard(old_column)
        if active_columns is not None:
            active_columns.update(operation.rename_to)
        return
    if operation.op == "derived_column" and active_columns is not None:
        active_columns.add(operation.name)


def _recommendation_to_operation(item: Mapping[str, Any]) -> PreprocessOperation | None:
    op = str(item.get("op") or "").strip()
    columns = _recommendation_columns(item)
    raw_params = item.get("params")
    params: dict[str, Any] = dict(raw_params) if isinstance(raw_params, dict) else {}

    if op == "drop_missing" and columns:
        return DropMissingOperation.model_validate(
            {"op": "drop_missing", "columns": columns, "how": "any"}
        )
    if op == "impute" and columns:
        method = str(params.get("method") or item.get("method") or "median")
        if method not in {"mean", "median", "mode", "value"}:
            method = "median"
        return ImputeOperation.model_validate(
            {"op": "impute", "columns": columns, "method": method, "value": params.get("value")}
        )
    if op == "drop_columns" and columns:
        return DropColumnsOperation.model_validate(
            {"op": "drop_columns", "columns": columns}
        )
    if op == "scale" and columns:
        method = str(params.get("method") or item.get("method") or "standardize")
        if method not in {"standardize", "normalize"}:
            method = "standardize"
        return ScaleOperation.model_validate(
            {"op": "scale", "columns": columns, "method": method}
        )
    if op == "encode_categorical" and columns:
        method = str(params.get("method") or item.get("method") or "one_hot")
        if method not in {"one_hot", "label"}:
            method = "one_hot"
        return EncodeCategoricalOperation.model_validate(
            {"op": "encode_categorical", "columns": columns, "method": method}
        )
    if op == "parse_datetime" and columns:
        date_format = params.get("format")
        return ParseDatetimeOperation.model_validate(
            {
                "op": "parse_datetime",
                "columns": columns,
                "format": str(date_format) if isinstance(date_format, str) else None,
            }
        )
    if op == "outlier" and columns:
        method = str(params.get("method") or item.get("method") or "iqr")
        strategy = str(params.get("strategy") or item.get("strategy") or "clip")
        if method not in {"zscore", "iqr"}:
            method = "iqr"
        if strategy not in {"drop", "clip"}:
            strategy = "clip"
        return OutlierOperation.model_validate(
            {"op": "outlier", "columns": columns, "method": method, "strategy": strategy}
        )
    if op == "derived_column":
        source_columns = _string_list(item.get("source_columns"))
        name = str(item.get("target_column") or "").strip()
        if not name and columns:
            name = columns[0]
        transform_type = item.get("transform_type")
        if (
            name
            and source_columns
            and transform_type in {"log1p", "sum", "difference", "ratio"}
        ):
            return DerivedColumnOperation.model_validate(
                {
                    "op": "derived_column",
                    "name": name,
                    "source_columns": source_columns,
                    "transform_type": transform_type,
                    "params": params,
                }
            )
    return None


def _recommendation_columns(item: Mapping[str, Any]) -> list[str]:
    columns = _string_list(item.get("columns"))
    if columns:
        return columns
    return _string_list(item.get("target_columns"))


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item or "").strip())]


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
    recommendations_raw = dataset_profile.get("preprocess_recommendations")
    top_recommendations: list[dict[str, Any]] = []
    if isinstance(recommendations_raw, list):
        top_recommendations = [
            item
            for item in recommendations_raw
            if isinstance(item, dict)
        ][:5]
    summary = (
        planner_comment
        or reason_summary.strip()
        or "전처리 계획을 검토한 뒤 승인 여부를 결정해 주세요."
    )
    row_count = dataset_profile.get("sample_row_count")
    affected_columns = _collect_affected_columns(plan.operations)
    guidance = _build_preprocess_guidance(
        affected_columns=affected_columns,
        planner_comment=planner_comment,
        reason_summary=reason_summary,
        top_missing_columns=top_missing_columns,
        top_recommendations=top_recommendations,
    )

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
            "top_recommendations": top_recommendations,
            "affected_columns": affected_columns,
            "guidance": guidance,
            "row_count": int(row_count) if isinstance(row_count, int) else None,
        },
    }


def _build_preprocess_guidance(
    *,
    affected_columns: list[str],
    planner_comment: str,
    reason_summary: str,
    top_missing_columns: list[dict[str, Any]],
    top_recommendations: list[dict[str, Any]],
) -> dict[str, str]:
    columns_label = _format_column_label(affected_columns)
    missing_columns = [
        str(item.get("column") or "").strip()
        for item in top_missing_columns
        if str(item.get("column") or "").strip()
    ]
    recommendation_reasons = [
        str(item.get("reason") or "").strip()
        for item in top_recommendations
        if str(item.get("reason") or "").strip()
    ]

    why_source = (
        reason_summary.strip()
        or planner_comment
        or (recommendation_reasons[0] if recommendation_reasons else "")
    )
    if missing_columns:
        why_this_matters = (
            f"{columns_label} 컬럼에 결측치가 있어 분석 기준이나 집계 대상에서 "
            "빠지는 행이 생길 수 있습니다."
        )
    elif why_source:
        why_this_matters = f"{columns_label} 컬럼 전처리가 필요한 이유: {why_source}"
    else:
        why_this_matters = (
            f"{columns_label} 컬럼을 정리하면 같은 의미의 값이 하나의 기준으로 계산됩니다."
        )

    expected_impact = (
        f"{columns_label} 기준 분석에서 비어 있거나 형식이 다른 값을 줄여 "
        "양품/불량 비율, 불량 사유, 제품별 생산량 같은 결과를 더 안정적으로 계산합니다."
    )
    skip_risk = (
        f"건너뛰면 {columns_label} 값이 비어 있거나 섞인 상태로 남아 "
        "일부 행이 집계에서 누락되거나 잘못된 그룹으로 계산될 수 있습니다."
    )
    return {
        "why_this_matters": why_this_matters,
        "expected_impact": expected_impact,
        "skip_risk": skip_risk,
    }


def _format_column_label(columns: list[str]) -> str:
    cleaned = [column for column in columns if column.strip()]
    if not cleaned:
        return "선택된"
    if len(cleaned) == 1:
        return cleaned[0]
    preview = ", ".join(cleaned[:3])
    if len(cleaned) <= 3:
        return preview
    return f"{preview} 외 {len(cleaned) - 3}개"


def _collect_affected_columns(operations: list[PreprocessOperation]) -> list[str]:
    columns: list[str] = []
    for operation in operations:
        operation_columns = getattr(operation, "columns", None)
        if isinstance(operation_columns, list):
            columns.extend(operation_columns)
        elif operation.op == "rename_columns":
            columns.extend(operation.rename_from)
            columns.extend(operation.rename_to)
        elif operation.op == "derived_column":
            columns.append(operation.name)
    return list(dict.fromkeys(str(column) for column in columns if str(column).strip()))
