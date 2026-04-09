from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage

from .schemas import RecommendedOperation, PreprocessRecommendation
from ...core.ai import LLMGateway, PromptRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecommendationResult:
    recommendation: PreprocessRecommendation
    generation_mode: Literal["llm", "fallback", "none"]
    warning: str | None = None

PROMPTS = PromptRegistry(
    {
        "summary.system": (
            "당신은 데이터 EDA 결과를 해석하는 분석가다. "
            "반드시 한국어로 작성하고, 반드시 JSON 객체만 반환하라. "
            '키는 "structure_summary", "quality_issues", "key_insights"만 사용하라. '
            '"structure_summary"는 문자열 하나, 나머지 3개 키는 문자열 배열이어야 한다. '
            "각 배열은 1~3개 항목으로 간결하게 작성하라. "
            "원본 데이터 행을 추측하지 말고 제공된 통계/요약만 근거로 사용하라. "
            "가능하면 수치를 직접 인용하라."
        ),
    }
)


def generate_eda_ai_summary(
    *,
    payload: dict[str, Any],
    model_id: str | None,
    default_model: str,
) -> dict[str, Any]:
    llm = LLMGateway(default_model=default_model)
    result = llm.invoke(
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("summary.system")),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ],
    )
    content = result.content if isinstance(result.content, str) else str(result.content)
    return _parse_summary_content(content)


def _parse_summary_content(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return _parse_summary_sections(content)

    return {
        "structure_summary": str(parsed.get("structure_summary", "")).strip(),
        "quality_issues": _coerce_string_list(parsed.get("quality_issues")),
        "key_insights": _coerce_string_list(parsed.get("key_insights")),
    }


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _parse_summary_sections(content: str) -> dict[str, Any]:
    sections: dict[str, list[str]] = {
        "structure_summary": [],
        "quality_issues": [],
        "key_insights": [],
    }
    current_key = "structure_summary"
    heading_map = {
        "데이터 구조 요약": "structure_summary",
        "품질 이슈": "quality_issues",
        "주요 인사이트": "key_insights",
    }

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = line.lstrip("#").strip()
        mapped_key = heading_map.get(normalized)
        if mapped_key is not None:
            current_key = mapped_key
            continue
        cleaned = line.lstrip("-*0123456789. ").strip()
        if cleaned:
            sections[current_key].append(cleaned)

    structure_summary = " ".join(sections["structure_summary"]).strip()
    if not structure_summary:
        structure_summary = content.strip()

    return {
        "structure_summary": structure_summary,
        "quality_issues": sections["quality_issues"],
        "key_insights": sections["key_insights"],
    }

# 전처리 추천
def detect_issues(
    *,
    quality,
    stats,
    correlations,
    column_types,
) -> list[dict]:
    """
    EDA 결과를 기반으로 rule-based 문제 감지

    반환:
    [
        {"issue": "missing_value", "col": "age", "ratio": 0.12},
        {"issue": "skewed", "col": "income", "skew": 2.5},
        ...
    ]
    """
    issues: list[dict] = []

    # 1. 결측치
    for col in quality.columns:
        if col.null_ratio > 0.05:
            issues.append({
                "issue": "missing_value",
                "col": col.column,
                "ratio": col.null_ratio,
            })

    # 2. 왜도 (skewness)
    if stats and stats.columns:
        for col in stats.columns:
            # stats에 skew 없으면 추가 필요
            skew = getattr(col, "skew", None)
            if skew is not None and abs(skew) > 2:
                issues.append({
                    "issue": "skewed",
                    "col": col.column,
                    "skew": skew,
                })

    # 3. 상관관계 (multicollinearity)
    if correlations and correlations.pairs:
        for pair in correlations.pairs:
            if abs(pair.correlation) > 0.9:
                issues.append({
                    "issue": "high_correlation",
                    "cols": [pair.column_1, pair.column_2],
                    "corr": pair.correlation,
                })

    # 4. 범주형 인코딩 필요
    if column_types and column_types.columns:
        for col in column_types.columns:
            if col.inferred_type == "categorical":
                if 2 <= col.unique_count <= 20:
                    issues.append({
                        "issue": "needs_encoding",
                        "col": col.column,
                        "cardinality": col.unique_count,
                    })

    # 5. 스케일 불균형
    if stats and stats.columns:
        values = []
        for col in stats.columns:
            if col.max is not None and col.min is not None:
                values.append((col.column, col.max - col.min))

        if len(values) >= 2:
            positive_ranges = [value for _, value in values if value > 0]
            if len(positive_ranges) >= 2:
                max_range = max(positive_ranges)
                min_range = min(positive_ranges)

                if min_range > 0 and max_range / min_range > 100:
                    cols = [c for c, _ in values]
                    issues.append({
                        "issue": "scale_imbalance",
                        "cols": cols,
                        "ratio": max_range / min_range,
                    })

    return issues

def _issues_to_recommendation(detected_issues: list[dict]) -> PreprocessRecommendation:
    """LLM 실패 시 detected_issues만으로 추천 결과를 구성한다."""
    seen = set()

    if not detected_issues:
        return PreprocessRecommendation(
            operations=[],
            summary="현재 데이터에서 필수 전처리 항목이 감지되지 않았습니다.",
        )

    operations: list[RecommendedOperation] = []
    for issue in detected_issues:
        issue_type = issue.get("issue")

        cols = tuple(issue.get("cols", [issue.get("col")]))
        key = (issue_type, cols)

        if key in seen:
            continue
        seen.add(key)

        if issue_type == "missing_value":
            ratio = issue.get("ratio", 0)
            if ratio >= 0.3:
                op = "drop_missing"
                priority = "high"
            elif ratio > 0.05:
                op = "impute"
                priority = "medium"
            else:
                continue
            operations.append(RecommendedOperation(
                op=op,
                target_columns=[issue["col"]],
                reason=f"결측치 비율 {ratio:.1%} — {'제거' if op == 'drop_missing' else 'median 대체'} 권장",
                priority=priority,
            ))

        elif issue_type == "skewed":
            skew = issue.get("skew", 0)
            operations.append(RecommendedOperation(
                op="outlier",
                target_columns=[issue["col"]],
                reason=f"왜도 {skew:.2f} — IQR 기반 이상치 처리 권장",
                priority="medium",
            ))

        elif issue_type == "high_correlation":
            corr = abs(issue.get("corr", 0))
            priority = "high" if corr > 0.95 else "medium"

            operations.append(RecommendedOperation(
                op="drop_columns",
                target_columns=issue.get("cols", []),
                reason=f"상관계수 {corr:.2f} — 다중공선성 문제, 컬럼 제거 권장",
                priority=priority,
            ))

        elif issue_type == "needs_encoding":
            operations.append(RecommendedOperation(
                op="encode_categorical",
                target_columns=[issue["col"]],
                reason=f"범주형 컬럼 — 인코딩 필요 (고유값 {issue.get('cardinality')}개)",
                priority="medium",
            ))

        elif issue_type == "datetime_candidate":
            operations.append(RecommendedOperation(
                op="parse_datetime",
                target_columns=[issue["col"]],
                reason="날짜 패턴이 감지된 object 컬럼 — datetime 변환 권장",
                priority="low",
            ))

        elif issue_type == "scale_imbalance":
            operations.append(RecommendedOperation(
                op="scale",
                target_columns=issue.get("cols", []),
                reason=f"컬럼 간 스케일 차이 {issue.get('ratio', 0):.0f}배 — standardize 권장",
                priority="medium",
            ))

    summary_parts = []

    if any(op.op in ["drop_missing", "impute"] for op in operations):
        summary_parts.append("결측값 처리가 필요합니다.")

    if any(op.op == "outlier" for op in operations):
        summary_parts.append("이상치 처리가 필요합니다.")

    if any(op.op == "scale" for op in operations):
        summary_parts.append("스케일링을 권장합니다.")

    if any(op.op == "encode_categorical" for op in operations):
        summary_parts.append("범주형 인코딩이 필요합니다.")

    summary = " ".join(summary_parts) if summary_parts else "필수 전처리 항목이 없습니다."
    return PreprocessRecommendation(operations=operations, summary=summary)


# ── 프롬프트 구성 ──────────────────────────────────────────────

def _build_prompt(
    eda_summary: dict,
    detected_issues: list[dict],
    rag_context: str,
) -> str:
    shape = eda_summary.get("shape", {})
    missing = eda_summary.get("missing", {})
    dtypes = eda_summary.get("dtypes", {})

    rag_context = (rag_context or "")[:1500]

    # 결측치 비율 상위 5개만 포함 (토큰 절약)
    row_count = shape.get("rows", 1)
    top_missing = sorted(
        [(col, cnt / row_count) for col, cnt in missing.items() if cnt > 0],
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    missing_summary = ", ".join(f"{col}({ratio:.1%})" for col, ratio in top_missing) or "없음"
    dtype_summary = ", ".join(f"{col}:{dt}" for col, dt in list(dtypes.items())[:10])

    issues_text = "\n".join(
        f"- {i['issue']} | col={i.get('col') or i.get('cols')} | detail={i}"
        for i in detected_issues
    )

    output_schema = json.dumps({
        "operations": [
            {
                "op": "op 값 (drop_missing | impute | drop_columns | scale | encode_categorical | outlier | parse_datetime | derived_column)",
                "target_columns": ["컬럼명"],
                "reason": "추천 근거 (한국어)",
                "priority": "high | medium | low",
            }
        ],
        "summary": "전체 추천 요약 (1-2문장)",
    }, ensure_ascii=False, indent=2)

    return f"""데이터 기본 정보:
- 행/열: {shape.get('rows')}행 {shape.get('cols')}열
- 결측치 상위: {missing_summary}
- 컬럼 타입: {dtype_summary}

감지된 문제 목록:
{issues_text}

참고 문서 (RAG):
{rag_context or '검색 결과 없음'}

위 정보를 바탕으로 필요한 전처리 연산을 추천하세요.
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

{output_schema}"""
 

def recommend(
    eda_summary: dict,
    detected_issues: list[dict],
    rag_context: str,
    default_model: str,
    model_id: str | None = None,  
) -> RecommendationResult:
    """
    EDA 결과와 감지된 문제를 바탕으로 전처리 방안을 추천한다.

    1. detected_issues + rag_context → LLM 프롬프트 구성
    2. LLM 응답 JSON 파싱 → PreprocessRecommendation 반환
    3. 실패 시 rule-based 결과만 반환 (서비스 중단 없음)
    """
    if not detected_issues:
        return RecommendationResult(
            recommendation=PreprocessRecommendation(
                operations=[],
                summary="현재 데이터에서 필수 전처리 항목이 감지되지 않았습니다.",
            ),
            generation_mode="none",
        )

    prompt = _build_prompt(eda_summary, detected_issues, rag_context)
    llm = LLMGateway(default_model=default_model)

    raw = ""

    try:
        result = llm.invoke(
            model_id=model_id,
            messages=[
                SystemMessage(content=(
                    "당신은 데이터 전처리 전문가입니다. "
                    "EDA 분석 결과와 감지된 문제를 바탕으로 필요한 전처리 연산을 추천하세요. "
                    "반드시 JSON 형식으로만 응답하세요."
                )),
                HumanMessage(content=prompt),
            ],
        )
        raw = result.content if isinstance(result.content, str) else str(result.content)
        parsed = json.loads(raw)
        try:
            return RecommendationResult(
                recommendation=PreprocessRecommendation(**parsed),
                generation_mode="llm",
            )
        except Exception as e:
            logger.warning("LLM 응답 스키마 불일치. fallback. error=%s", e)
            return RecommendationResult(
                recommendation=_issues_to_recommendation(detected_issues),
                generation_mode="fallback",
                warning="LLM 응답 형식이 올바르지 않아 rule-based 추천으로 대체했습니다.",
            )

    except json.JSONDecodeError:
        logger.warning("LLM 응답 JSON 파싱 실패. rule-based 결과로 fallback.\nraw=%s", raw)
        return RecommendationResult(
            recommendation=_issues_to_recommendation(detected_issues),
            generation_mode="fallback",
            warning="LLM 응답을 해석하지 못해 rule-based 추천으로 대체했습니다.",
        )

    except Exception as exc:
        logger.warning("LLM 호출 실패. rule-based 결과로 fallback. error=%s", exc)
        return RecommendationResult(
            recommendation=_issues_to_recommendation(detected_issues),
            generation_mode="fallback",
            warning="LLM 추천 생성에 실패해 rule-based 추천으로 대체했습니다.",
        )
