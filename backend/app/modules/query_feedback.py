from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import httpx
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from openai import OpenAIError
from pydantic import BaseModel, Field

from ..core.ai import LLMGateway


IssueType = Literal[
    "missing_column",
    "clarification",
    "planning_error",
    "analysis_error",
]


class QueryFeedbackAction(BaseModel):
    label: str
    description: str
    prompt: str | None = None


class QueryFeedback(BaseModel):
    title: str
    message: str
    actions: list[QueryFeedbackAction] = Field(default_factory=list)


class QueryFeedbackContext(BaseModel):
    user_input: str
    issue_type: IssueType
    stage: str | None = None
    message: str = ""
    missing_column: str | None = None
    operation: str | None = None
    reason_summary: str | None = None
    suggested_action: str | None = None
    related_columns: list[str] = Field(default_factory=list)
    available_columns: list[str] = Field(default_factory=list)


class QueryFeedbackGenerator:
    def __init__(
        self,
        *,
        default_model: str = "gpt-5-nano",
        llm: LLMGateway | None = None,
        timeout_seconds: float = 8,
    ) -> None:
        self.default_model = default_model
        self.llm = llm or LLMGateway(
            default_model=default_model,
            timeout_seconds=timeout_seconds,
        )

    def generate(
        self,
        context: QueryFeedbackContext,
        *,
        model_id: str | None = None,
    ) -> QueryFeedback:
        messages = _build_messages(context)
        try:
            feedback = self.llm.invoke_structured(
                schema=QueryFeedback,
                messages=messages,
                model_id=model_id,
                temperature=0,
            )
        except (
            ConnectionError,
            httpx.HTTPError,
            OpenAIError,
            RuntimeError,
            TimeoutError,
            TypeError,
            ValueError,
        ):
            return _fallback_feedback(context)
        if not isinstance(feedback, QueryFeedback):
            return _fallback_feedback(context)
        if not _is_usable_feedback(feedback):
            return _fallback_feedback(context)
        return _trim_feedback(feedback)


def _build_messages(context: QueryFeedbackContext) -> Sequence[BaseMessage]:
    system = (
        "너는 데이터 분석 초보자를 돕는 질문 개선 코치다. "
        "백엔드가 감지한 오류 맥락을 바탕으로 사용자가 어떻게 질문을 다시 써야 "
        "적절한 분석 답변을 받을 수 있는지 한국어로 설명하라. "
        "내부 예외, 스택트레이스, 재시도 권유만 반복하지 마라. "
        "반드시 QueryFeedback 스키마로만 답하고, actions는 최대 3개로 제한하라. "
        "title, message, label, description은 모두 한국어로 작성하고 컬럼명만 원문을 유지하라. "
        "없는 컬럼을 대체할 실제 후보가 없으면 임의의 컬럼을 만들지 말고, "
        "사용자가 사용 가능한 컬럼 중 하나를 선택해야 한다고 설명하라. "
        "prompt는 사용하지 말고 description에 좋은 질문으로 고치는 방법을 설명하라."
    )
    human = (
        f"user_input:\n{context.user_input.strip()}\n\n"
        f"issue_type:\n{context.issue_type}\n\n"
        f"stage:\n{context.stage or ''}\n\n"
        f"message:\n{context.message.strip()}\n\n"
        f"missing_column:\n{context.missing_column or ''}\n\n"
        f"operation:\n{context.operation or ''}\n\n"
        f"reason_summary:\n{context.reason_summary or ''}\n\n"
        f"suggested_action:\n{context.suggested_action or ''}\n\n"
        f"related_columns:\n{context.related_columns[:8]}\n\n"
        f"available_columns:\n{context.available_columns[:20]}"
    )
    return [SystemMessage(content=system), HumanMessage(content=human)]


def _is_usable_feedback(feedback: QueryFeedback) -> bool:
    if not feedback.title.strip():
        return False
    if not feedback.message.strip():
        return False
    return any(
        action.label.strip() and action.description.strip()
        for action in feedback.actions
    )


def _trim_feedback(feedback: QueryFeedback) -> QueryFeedback:
    actions = [
        QueryFeedbackAction(
            label=action.label.strip(),
            description=action.description.strip(),
            prompt=None,
        )
        for action in feedback.actions
        if action.label.strip() and action.description.strip()
    ][:3]
    return QueryFeedback(
        title=feedback.title.strip(),
        message=feedback.message.strip(),
        actions=actions,
    )


def _fallback_feedback(context: QueryFeedbackContext) -> QueryFeedback:
    if context.issue_type == "missing_column":
        return _missing_column_fallback(context)
    if context.issue_type == "analysis_error":
        return _analysis_error_fallback(context)
    return _clarification_fallback(context)


def _missing_column_fallback(context: QueryFeedbackContext) -> QueryFeedback:
    missing = context.missing_column or "질문에 쓴 컬럼"
    candidates = _column_list(context.related_columns or context.available_columns[:3])
    available = _column_list(context.available_columns[:6])
    description = (
        f"`{missing}` 컬럼이 현재 데이터에 없습니다. "
        f"가까운 실제 컬럼 후보는 {candidates}입니다."
        if candidates
        else f"`{missing}` 컬럼이 현재 데이터에 없습니다."
    )
    if available:
        description = f"{description} 사용 가능한 컬럼 예시는 {available}입니다."
    return QueryFeedback(
        title="없는 컬럼을 실제 컬럼명으로 바꿔 질문하세요",
        message=context.message.strip() or description,
        actions=[
            QueryFeedbackAction(
                label="실제 컬럼명으로 바꾸기",
                description=description,
            ),
            QueryFeedbackAction(
                label="원하는 계산 방식을 함께 쓰기",
                description="상관관계, 평균, 건수, 비율, 이상치 확인처럼 원하는 분석 연산을 컬럼명과 같은 문장에 적어 주세요.",
            ),
        ],
    )


def _analysis_error_fallback(context: QueryFeedbackContext) -> QueryFeedback:
    column = context.missing_column or "대상 컬럼"
    operation = context.operation or "분석"
    reason = context.reason_summary or context.message or (
        "현재 질문의 컬럼, 데이터 타입, 결측 조건 중 일부가 분석 연산과 맞지 않았습니다."
    )
    action = context.suggested_action or (
        "실제 컬럼명, 숫자/날짜/범주 타입, 결측 제외 여부를 질문에 함께 적어 주세요."
    )
    return QueryFeedback(
        title="분석 오류를 피하도록 질문 조건을 구체화하세요",
        message=reason,
        actions=[
            QueryFeedbackAction(
                label="컬럼과 연산을 맞추기",
                description=f"`{column}`에 `{operation}`을 적용할 수 있는지 확인하고 실제 데이터 타입에 맞는 연산을 요청해 주세요.",
            ),
            QueryFeedbackAction(
                label="데이터 조건을 질문에 포함하기",
                description=action,
            ),
        ],
    )


def _clarification_fallback(context: QueryFeedbackContext) -> QueryFeedback:
    available = _column_list(context.available_columns[:6])
    suffix = f" 사용 가능한 컬럼 예시는 {available}입니다." if available else ""
    return QueryFeedback(
        title="분석 기준과 대상 컬럼을 더 구체적으로 적어 주세요",
        message=context.message.strip()
        or "현재 질문만으로는 분석 대상, 기준 컬럼, 계산 방식 중 일부를 확정하기 어렵습니다.",
        actions=[
            QueryFeedbackAction(
                label="대상 컬럼과 계산 방식을 함께 쓰기",
                description=f"건수, 평균, 비율, 이상치, 상관관계처럼 원하는 결과 형태와 대상 컬럼을 한 문장에 적어 주세요.{suffix}",
            ),
            QueryFeedbackAction(
                label="그룹 기준을 명시하기",
                description="제품별, 날짜별, 불량 사유별처럼 비교 기준이 있다면 기준 컬럼을 같이 적어 주세요.",
            ),
        ],
    )


def _column_list(columns: list[str]) -> str:
    return ", ".join(f"`{column}`" for column in columns if column)
