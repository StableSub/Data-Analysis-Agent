from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from ...core.ai import LLMGateway, PromptRegistry
from .schemas import (
    AnalysisError,
    AnalysisPlan,
    AnalysisPlanDraft,
    ColumnGroundingResult,
    MetadataSnapshot,
    QuestionUnderstanding,
)

PROMPTS = PromptRegistry(
    {
        "question_understanding.system": (
            "너는 데이터 분석 질문 해석기다. "
            "사용자 질문을 QuestionUnderstanding 스키마로 구조화하라. "
            "질문이 모호하면 ambiguity_status를 needs_clarification으로 설정하고 clarification_message를 작성하라. "
            "metric_keywords와 group_keywords는 실제 컬럼명이 아니라 질문에서 추출한 개념 중심 키워드로 작성하라. "
            "질문에 3월, 2월, 이번 달처럼 상대적으로 해석 가능한 월/기간 표현이 있고 dataset_meta의 시간 범위 안에서 자연스럽게 해석 가능하면 불필요한 clarification을 만들지 마라."
        ),
        "plan_draft.system": (
            "너는 데이터 분석 플래너다. "
            "입력으로 주어진 질문 해석 결과, 컬럼 grounding 결과, 데이터셋 메타정보를 바탕으로 "
            "AnalysisPlanDraft 스키마 형식으로만 반환하라. "
            "질문이 모호하면 ambiguity_status를 needs_clarification으로 설정하라. "
            "metrics는 반드시 최소 1개 이상 포함하라. "
            "관계 분석(scatter, correlation, relationship) 질문에서는 우선 원본 수치 컬럼 2개를 직접 사용하라. "
            "관계 분석 질문에서는 사용자가 평균, 그룹별 평균, 요약을 명시적으로 요구하지 않았다면 group_by를 기본적으로 비워 두고 원시 행 단위 x/y 포인트를 사용하라. "
            "line, material_type 같은 범주형 컬럼이 있으면 집계 기준으로 쓰기보다 series/color 구분으로 우선 사용하라. "
            "파생 컬럼(derived_columns)은 원본 컬럼만으로 질문에 답할 수 없을 때만 추가하라. "
            "특히 ratio, arithmetic 같은 파생 컬럼은 사용자가 명시적으로 요청하지 않았다면 만들지 마라. "
            "관계 분석 질문에서는 correlation, slope, regression 같은 추가 관계 지표(metric)를 기본적으로 만들지 마라. "
            "사용자가 명시적으로 상관계수나 회귀계수를 요청한 경우가 아니면, 원본 두 컬럼과 scatter 시각화에 필요한 최소 metric만 사용하라. "
            "월별/주별/일별 추세 질문에서는 timestamp/date 컬럼을 분석 단계에서 버킷팅하여 집계하라. 이 때문에 preprocess 파생 컬럼이 필요하다고 가정하지 마라. "
            "라인별 평균 불량률 추세 같은 질문이면 time bucket + series(line) + avg metric 구조로 계획하라."
        ),
        "code_generation.system": (
            "너는 pandas 기반 데이터 분석 코드 생성기다. "
            "반드시 순수 Python 코드만 반환하라. 마크다운 코드블록은 금지한다. "
            "입력 데이터는 dataset_path 변수와 이미 로드된 pandas DataFrame df, 그리고 json/pd로 주어진다. "
            "가능하면 df를 직접 사용하고, dataset_path를 다시 가공하거나 파일 경로를 다루지 마라. "
            "stdout에는 JSON 하나만 출력해야 하며 키는 summary, table, raw_metrics, used_columns 이어야 한다. "
            "raw_metrics는 항상 JSON object(dict)여야 하며 절대 null로 출력하지 마라. 값이 없으면 빈 객체 {}를 사용하라. "
            "used_columns에는 df에서 실제로 읽은 원본 데이터셋 컬럼만 포함하라. "
            "month, year_month, ratio, temp_speed_ratio 같은 파생/임시/helper 컬럼은 used_columns에 넣지 마라. "
            "코드 안에서 import 문은 사용하지 마라. 필요한 JSON 출력은 이미 제공된 json을 사용하라. "
            "추가 파일 읽기/쓰기, 환경 변수 접근, 프로세스 실행, 네트워크 호출은 금지한다. "
            "analysis_plan.time_context.relative_range_resolved가 있으면 start/end를 그대로 사용하고, now/today/current month를 다시 계산하지 마라. "
            "time_context.grain이 month이고 relative_expr가 last 3 months 계열이면, 현재 진행 중인 월은 제외하고 최근 3개 완료월만 사용하라. "
            "월별/주별/일별 추세는 전처리 없이 분석 코드 안에서 datetime 컬럼을 to_datetime 후 버킷팅해서 처리하라. "
            "analysis_plan.derived_columns에 정의된 파생 컬럼이 있으면, 코드에서 그 name을 그대로 사용하라. 임의로 month, year_month 같은 다른 이름으로 바꾸지 마라. "
            "analysis_plan.visualization_hint.preferred_chart가 scatter이고 x/y가 주어지면, table은 집계 평균 1행이 아니라 원본 관측치 기반의 점 데이터로 구성하라. "
            "즉 table 각 row에는 visualization_hint.x, visualization_hint.y, 그리고 series가 있으면 그 컬럼을 포함하라. "
            "사용자가 평균이나 집계를 명시적으로 요청하지 않았다면 scatter 질문에서 x/y를 avg로 집계하지 마라. "
            "relationship/scatter 질문에서 line, material_type 같은 범주형 컬럼이 있더라도 그 컬럼으로 groupby하여 평균 3점, 5점 같은 요약 scatter를 만들지 마라. "
            "추세 질문에서 line 같은 series 컬럼이 있으면 month/date 버킷과 함께 groupby하여 시리즈별 평균값을 계산하라. "
            "dataset_meta나 analysis_plan에 이미 존재하는 컬럼이 있으면 해당 컬럼이 없다고 가정하지 마라."
        ),
        "code_repair.system": (
            "너는 pandas 분석 코드 수정기다. "
            "반드시 순수 Python 코드만 반환하라. 마크다운 코드블록은 금지한다. "
            "기존 AnalysisPlan은 유지하고, 주어진 실패 원인을 반영해 코드만 수정하라. "
            "stdout JSON 계약(summary, table, raw_metrics, used_columns)을 반드시 지켜라. "
            "raw_metrics는 항상 JSON object(dict)여야 하며 절대 null로 출력하지 마라. 값이 없으면 빈 객체 {}를 사용하라. "
            "used_columns에는 df에서 실제로 읽은 원본 데이터셋 컬럼만 포함하라. "
            "month, year_month, ratio, temp_speed_ratio 같은 파생/임시/helper 컬럼은 used_columns에 넣지 마라. "
            "입력 데이터는 dataset_path 변수와 이미 로드된 pandas DataFrame df, 그리고 json/pd로 주어진다. "
            "코드 안에서 import 문은 사용하지 마라. 필요한 JSON 출력은 이미 제공된 json을 사용하라. "
            "추가 파일 읽기/쓰기, 환경 변수 접근, 프로세스 실행, 네트워크 호출은 금지한다. "
            "analysis_plan.time_context.relative_range_resolved가 있으면 start/end를 그대로 사용하고, now/today/current month를 다시 계산하지 마라. "
            "time_context.grain이 month이고 relative_expr가 last 3 months 계열이면, 현재 진행 중인 월은 제외하고 최근 3개 완료월만 사용하라. "
            "월별/주별/일별 추세는 분석 코드 안에서 datetime 컬럼 버킷팅으로 처리하라. "
            "analysis_plan.derived_columns에 정의된 파생 컬럼이 있으면, 코드에서 그 name을 그대로 사용하라. 임의로 month, year_month 같은 다른 이름으로 바꾸지 마라. "
            "scatter 시각화 질문이면 table을 원본 x/y 점들로 유지하고, 평균 1행이나 그룹 평균 몇 개 점으로 축약하지 마라. "
            "relationship/scatter 질문에서 series 컬럼은 색상/시리즈 구분용으로 유지하고, 사용자가 명시적으로 요청하지 않았다면 groupby 평균 scatter로 바꾸지 마라."
        ),
    }
)

_CODE_FENCE_RE = re.compile(r"^```(?:python)?\s*|\s*```$", re.MULTILINE)


class AnalysisRunService:
    """LLM-backed analysis planning and code generation service."""

    def __init__(self, *, default_model: str = "gpt-5-nano") -> None:
        self.default_model = default_model
        self.llm = LLMGateway(default_model=default_model)

    # 질문을 분석 가능한 의미 구조로 바꾼다.
    def build_question_understanding(
        self,
        *,
        question: str,
        dataset_meta: MetadataSnapshot | dict[str, Any],
        model_id: str | None = None,
    ) -> QuestionUnderstanding:
        metadata = self._ensure_metadata_snapshot(dataset_meta)
        return self.llm.invoke_structured(
            schema=QuestionUnderstanding,
            model_id=model_id,
            messages=[
                SystemMessage(
                    content=PROMPTS.load_prompt("question_understanding.system")
                ),
                HumanMessage(
                    content=(
                        f"question:\n{question.strip()}\n\n"
                        f"dataset_meta:\n{self._to_json(metadata.model_dump())}"
                    )
                ),
            ],
        )

    # 질문 해석 결과를 바탕으로 분석 계획 초안을 만든다.
    def build_analysis_plan_draft(
        self,
        *,
        question: str,
        question_understanding: QuestionUnderstanding | dict[str, Any],
        column_grounding: ColumnGroundingResult | dict[str, Any],
        dataset_meta: MetadataSnapshot | dict[str, Any],
        model_id: str | None = None,
    ) -> AnalysisPlanDraft:
        understanding = self._ensure_question_understanding(question_understanding)
        grounding = self._ensure_column_grounding(column_grounding)
        metadata = self._ensure_metadata_snapshot(dataset_meta)
        return self.llm.invoke_structured(
            schema=AnalysisPlanDraft,
            model_id=model_id,
            messages=[
                SystemMessage(content=PROMPTS.load_prompt("plan_draft.system")),
                HumanMessage(
                    content=(
                        f"question:\n{question.strip()}\n\n"
                        f"question_understanding:\n{self._to_json(understanding.model_dump())}\n\n"
                        f"column_grounding:\n{self._to_json(grounding.model_dump())}\n\n"
                        f"dataset_meta:\n{self._to_json(metadata.model_dump())}"
                    )
                ),
            ],
        )

    # 최종 AnalysisPlan을 바탕으로 실제 pandas 분석 코드를 생성한다.
    def generate_analysis_code(
        self,
        *,
        question: str,
        analysis_plan: AnalysisPlan | dict[str, Any],
        model_id: str | None = None,
    ) -> str:
        plan = self._ensure_plan(analysis_plan)
        result = self.llm.invoke(
            model_id=model_id,
            messages=[
                SystemMessage(content=PROMPTS.load_prompt("code_generation.system")),
                HumanMessage(
                    content=(
                        f"question:\n{question.strip()}\n\n"
                        f"analysis_plan:\n{self._to_json(plan.model_dump())}\n\n"
                        "df는 이미 로드되어 있으므로 기본적으로 df를 직접 사용하라. "
                        "dataset_path로 CSV를 다시 읽거나 df 존재 여부를 검사하는 방어 로직을 만들지 마라."
                    )
                ),
            ],
        )
        return self._normalize_code_output(
            result.content if hasattr(result, "content") else str(result)
        )

    # 기존 코드가 실패했을 때 에러를 반영해서 코드만 다시 생성한다.
    def repair_analysis_code(
        self,
        *,
        question: str,
        analysis_plan: AnalysisPlan | dict[str, Any],
        previous_code: str,
        analysis_error: AnalysisError | dict[str, Any],
        model_id: str | None = None,
    ) -> str:
        plan = self._ensure_plan(analysis_plan)
        error = self._ensure_analysis_error(analysis_error)
        result = self.llm.invoke(
            model_id=model_id,
            messages=[
                SystemMessage(content=PROMPTS.load_prompt("code_repair.system")),
                HumanMessage(
                    content=(
                        f"question:\n{question.strip()}\n\n"
                        f"analysis_plan:\n{self._to_json(plan.model_dump())}\n\n"
                        f"previous_code:\n{previous_code}\n\n"
                        f"analysis_error:\n{self._to_json(error.model_dump())}\n\n"
                        "df는 이미 로드되어 있으므로 기본적으로 df를 직접 사용하라. "
                        "dataset_path로 CSV를 다시 읽거나 df 존재 여부를 검사하는 방어 로직을 만들지 마라."
                    )
                ),
            ],
        )
        return self._normalize_code_output(
            result.content if hasattr(result, "content") else str(result)
        )

    def _normalize_code_output(self, value: str) -> str:
        code = str(value or "").strip()
        code = _CODE_FENCE_RE.sub("", code).strip()
        return code

    def _to_json(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, default=str)

    def _ensure_question_understanding(
        self,
        question_understanding: QuestionUnderstanding | dict[str, Any],
    ) -> QuestionUnderstanding:
        if isinstance(question_understanding, QuestionUnderstanding):
            return question_understanding
        return QuestionUnderstanding.model_validate(question_understanding)

    def _ensure_column_grounding(
        self,
        column_grounding: ColumnGroundingResult | dict[str, Any],
    ) -> ColumnGroundingResult:
        if isinstance(column_grounding, ColumnGroundingResult):
            return column_grounding
        return ColumnGroundingResult.model_validate(column_grounding)

    def _ensure_metadata_snapshot(
        self,
        dataset_meta: MetadataSnapshot | dict[str, Any],
    ) -> MetadataSnapshot:
        if isinstance(dataset_meta, MetadataSnapshot):
            return dataset_meta
        return MetadataSnapshot.model_validate(dataset_meta)

    def _ensure_plan(
        self, analysis_plan: AnalysisPlan | dict[str, Any]
    ) -> AnalysisPlan:
        if isinstance(analysis_plan, AnalysisPlan):
            return analysis_plan
        return AnalysisPlan.model_validate(analysis_plan)

    def _ensure_analysis_error(
        self,
        analysis_error: AnalysisError | dict[str, Any],
    ) -> AnalysisError:
        if isinstance(analysis_error, AnalysisError):
            return analysis_error
        return AnalysisError.model_validate(analysis_error)
