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
            "metric_keywords와 group_keywords는 실제 컬럼명이 아니라 질문에서 추출한 개념 중심 키워드로 작성하라."
        ),
        "plan_draft.system": (
            "너는 데이터 분석 플래너다. "
            "입력으로 주어진 질문 해석 결과, 컬럼 grounding 결과, 데이터셋 메타정보를 바탕으로 "
            "AnalysisPlanDraft 스키마 형식으로만 반환하라. "
            "질문이 모호하면 ambiguity_status를 needs_clarification으로 설정하라. "
            "metrics는 반드시 최소 1개 이상 포함하라."
        ),
        "code_generation.system": (
            "너는 pandas 기반 데이터 분석 코드 생성기다. "
            "반드시 순수 Python 코드만 반환하라. 마크다운 코드블록은 금지한다. "
            "입력 데이터는 dataset_path 변수로 주어진 CSV 파일을 사용한다. "
            "stdout에는 JSON 하나만 출력해야 하며 키는 summary, table, raw_metrics, used_columns 이어야 한다. "
            "허용 라이브러리는 json, math, statistics, pandas, numpy 뿐이다. "
            "네트워크, 파일 쓰기, 위험한 함수 호출은 금지한다."
        ),
        "code_repair.system": (
            "너는 pandas 분석 코드 수정기다. "
            "반드시 순수 Python 코드만 반환하라. 마크다운 코드블록은 금지한다. "
            "기존 AnalysisPlan은 유지하고, 주어진 실패 원인을 반영해 코드만 수정하라. "
            "stdout JSON 계약(summary, table, raw_metrics, used_columns)을 반드시 지켜라."
        ),
    }
)

_CODE_FENCE_RE = re.compile(r"^```(?:python)?\s*|\s*```$", re.MULTILINE)


class AnalysisRunService:
    """LLM-backed analysis planning and code generation service."""

    def __init__(self, *, default_model: str = "gpt-5-nano") -> None:
        self.default_model = default_model
        self.llm = LLMGateway(default_model=default_model)

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
                SystemMessage(content=PROMPTS.load_prompt("question_understanding.system")),
                HumanMessage(
                    content=(
                        f"question:\n{question.strip()}\n\n"
                        f"dataset_meta:\n{self._to_json(metadata.model_dump())}"
                    )
                ),
            ],
        )

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
                        "반드시 dataset_path 변수를 사용해 CSV를 읽어라."
                    )
                ),
            ],
        )
        return self._normalize_code_output(result.content if hasattr(result, "content") else str(result))

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
                        f"analysis_error:\n{self._to_json(error.model_dump())}"
                    )
                ),
            ],
        )
        return self._normalize_code_output(result.content if hasattr(result, "content") else str(result))

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

    def _ensure_plan(self, analysis_plan: AnalysisPlan | dict[str, Any]) -> AnalysisPlan:
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
