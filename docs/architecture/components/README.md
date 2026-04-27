# 워크플로우 컴포넌트 문서

이 디렉터리는 메인 LangGraph workflow와 하위 subgraph의 현재 동작을 컴포넌트별로 설명한다.
각 문서는 node 이름, branch/status, payload contract, approval contract를 실제 구현 파일 기준으로 추적한다.

상위 실행 순서와 전체 state 계약은 각각 [질문 흐름](../request-lifecycle.md), [공유 상태](../shared-state.md)를 기준으로 본다.
이 README는 컴포넌트 문서의 진입점이며, 세부 node/payload 계약은 각 문서가 소유한다.

## 포함 문서

| 문서 | 설명 | 기준 구현 |
|---|---|---|
| [메인 워크플로우](./main-workflow.md) | intake, planner, merge, terminal 분기까지 포함한 최상위 workflow | `backend/app/orchestration/builder.py` |
| [Guideline](./guideline.md) | guideline index 보장, evidence 검색과 요약 | `backend/app/orchestration/workflows/guideline.py` |
| [Preprocess](./preprocess.md) | 데이터셋 profile, 전처리 판단, approval, 실행/취소 | `backend/app/orchestration/workflows/preprocess.py` |
| [Analysis](./analysis.md) | 분석 계획, clarification, 실행, 검증, 결과 저장 | `backend/app/orchestration/workflows/analysis.py` |
| [RAG](./rag.md) | RAG index 보장, context retrieval, insight synthesis | `backend/app/orchestration/workflows/rag.py` |
| [Visualization](./visualization.md) | 시각화 계획, approval, 실행/취소 | `backend/app/orchestration/workflows/visualization.py` |
| [Report](./report.md) | 리포트 draft, approval, revision, finalize/cancel | `backend/app/orchestration/workflows/report.py` |

## 읽는 순서

1. 전체 흐름을 이해하려면 [메인 워크플로우](./main-workflow.md)를 먼저 읽는다.
2. 특정 stage의 node와 payload를 확인하려면 해당 컴포넌트 문서를 읽는다.
3. approval/resume 또는 최종 output shape가 궁금하면 [공유 상태](../shared-state.md)와 함께 확인한다.

## 유지 기준

- `backend/app/orchestration/builder.py`의 node, edge, terminal output이 바뀌면 [메인 워크플로우](./main-workflow.md)를 갱신한다.
- `backend/app/orchestration/workflows/`의 subgraph node, status, payload contract가 바뀌면 해당 컴포넌트 문서를 갱신한다.
- approval stage나 resume decision이 바뀌면 컴포넌트 문서와 [공유 상태](../shared-state.md)를 함께 확인한다.
- 검증은 아래 명령을 기준으로 한다.

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
```
