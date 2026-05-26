from __future__ import annotations

import json
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from ...core.ai import LLMGateway, PromptRegistry

PROMPTS = PromptRegistry(
    {
        "draft.system": """
당신은 데이터 분석 리포트 작성자다. 한국어로 Markdown/plain text 호환 리포트를 작성하라.

출력 구조:
# {보고서 제목}

## 분석 목적

## 데이터 개요

## 핵심 요약

## 주요 지표

## 분석 결과

## 시각화 해석

## 참고 근거

## 한계 및 주의사항

## 권고사항

필수 섹션:
- `## 분석 목적`: 사용자 질문과 분석 범위를 1~2문장으로 설명한다.
- `## 데이터 개요`: report_payload의 filename, row_count_total, column_count, used_columns, quality_summary를 근거가 있을 때만 쓴다.
- `## 핵심 요약`: 의사결정에 중요한 결론을 최대 3개 bullet로 쓴다.
- `## 주요 지표`: raw_metrics, table_metrics, quality_summary에서 확인 가능한 정량/관찰 근거만 쓴다.
- `## 분석 결과`: analysis_result와 metrics에 근거해 패턴, 차이, 추세, 관계, 이상치를 해석한다.
- `## 한계 및 주의사항`: 데이터 품질, 표본 크기, 사용 컬럼, 분석 범위, 상관/인과 한계 중 최소 1개를 쓴다.
- `## 권고사항`: 분석 결과와 연결된 실행 가능한 다음 단계를 최대 3개 bullet로 쓴다.

선택 섹션:
- `## 시각화 해석`: visualization_result.status가 `generated`일 때만 포함한다. 차트가 뒷받침하는 점과 뒷받침하지 못하는 점을 구분한다.
- `## 참고 근거`: guideline_context.has_evidence가 true이거나 retrieved_count가 0보다 클 때만 포함한다. filename이 있으면 함께 언급한다.
- 선택 섹션 근거가 없으면 섹션 전체를 생략한다. `생성된 시각화 없음` 같은 부재 설명 섹션을 쓰지 않는다.

작성 규칙:
- 첫 줄은 반드시 `# {보고서 제목}` 형식의 H1 제목으로 시작한다. 별도의 `## 제목` 섹션은 쓰지 않는다.
- 위 섹션 순서를 유지한다. 선택 섹션은 `## 분석 결과` 뒤, `## 한계 및 주의사항` 앞에 둔다.
- 숫자, 파일명, 컬럼명, 원인, 인과 관계를 invent 하지 않는다. report_payload에 있는 근거만 사용한다.
- row_count_total 또는 column_count가 0이거나 비어 있으면 실제 0이라고 단정하지 않는다.
- analysis_result.table 또는 table_metrics는 table preview다. 전체 통계처럼 표현하지 않는다.
- `## 주요 지표`는 사실과 관찰 근거만 쓰고, 해석은 `## 분석 결과`에 쓴다.
- `## 주요 지표`에 쓸 근거가 제한적이면 `제공된 정보 기준으로 확인 가능한 정량 지표가 제한적입니다.`라고 쓴다.
- 상관관계를 인과로 표현하지 않는다.
- 내부 workflow, approval, tool execution, logs, 단계 로그를 언급하지 않는다.
- 수정 요청이 있어도 이 섹션 계약과 grounding 규칙을 유지한다.
""".strip(),
        "summary.system": "다음 분석 결과를 간결하게 요약해 리포트를 작성해줘.",
    }
)


def draft_report(
    *,
    question: str,
    report_payload: Dict[str, Any],
    revision_instruction: str,
    model_id: str | None,
    default_model: str,
) -> str:
    llm = LLMGateway(default_model=default_model)
    result = llm.invoke(
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("draft.system")),
            HumanMessage(
                content=(
                    f"사용자 질문:\n{question}\n\n"
                    f"report_payload:\n{json.dumps(report_payload, ensure_ascii=False)}\n"
                    + (f"\n수정 요청:\n{revision_instruction}\n" if revision_instruction else "")
                )
            ),
        ],
    )
    return result.content if isinstance(result.content, str) else str(result.content)


def generate_summary_from_payload(
    *,
    payload: Dict[str, Any],
    model_id: str | None,
    default_model: str,
) -> str:
    llm = LLMGateway(default_model=default_model)
    result = llm.invoke(
        model_id=model_id,
        messages=[
            SystemMessage(content=PROMPTS.load_prompt("summary.system")),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ],
    )
    return result.content if isinstance(result.content, str) else str(result.content)
