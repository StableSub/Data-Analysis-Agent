# 아키텍처 문서 안내

이 디렉터리는 현재 런타임 구조를 코드 기준으로 따라가기 쉽게 정리한 문서 진입점이다. 목표는 사용자가 질문을 넣었을 때 어떤 경로로 실행이 진행되고, 어떤 상태가 오가며, 각 backend 영역이 어떤 책임을 가지는지 빠르게 파악할 수 있게 만드는 것이다.

제품 요구사항과 개선 우선순위는 [제품 요구사항](../product/prd.md), [현재 구현 기준선](../product/current-state-baseline.md), [구현 로드맵](../product/roadmap.md)을 먼저 본다.

## 읽는 순서

1. [Backend end-to-end workflow](./backend-workflow.md)
2. [공유 workflow state](./shared-state.md)
3. [질문 흐름](./request-lifecycle.md)
4. Backend 구조 문서
   - [Core backend foundation](./core/README.md)
   - [Backend modules](./modules/README.md)
   - [Backend orchestration](./orchestration/README.md)
   - [Orchestration workflow wrappers](./orchestration/workflows.md)
5. Module family 문서
   - [Analysis module](./modules/analysis.md)
   - [Dataset, EDA, profiling modules](./modules/data-and-profile.md)
   - [RAG and guidelines modules](./modules/rag-and-guidelines.md)
   - [Preprocess and visualization modules](./modules/preprocess-and-visualization.md)
   - [Chat, report, export, results modules](./modules/chat-report-export.md)
6. System-level 문서
   - [API 개요 및 명세](../system/api-spec.md)
   - [백엔드 구조](../system/backend-structure.md)
   - [프론트엔드 구조](../system/frontend-structure.md)
   - [SSE error contract](../system/api-sse-error-contract.md)
7. AI agent 운영 문서
   - [Trace and logging](../ai-agent/trace-and-logging.md)

## 원천 문서와 기준 코드

| 문서 | 소유하는 내용 | 주요 기준 코드 |
|---|---|---|
| [Backend end-to-end workflow](./backend-workflow.md) | `main.py` router mount부터 chat/SSE, `AgentClient`, main graph, final done event까지의 전체 흐름 | `backend/app/main.py`, `backend/app/modules/chat/service.py`, `backend/app/orchestration/client.py`, `backend/app/orchestration/builder.py` |
| [Core backend foundation](./core/README.md) | DB session/Base, LLM gateway, prompt registry | `backend/app/core/db.py`, `backend/app/core/ai/llm_gateway.py`, `backend/app/core/ai/prompt_registry.py` |
| [Backend modules](./modules/README.md) | module family index와 route/support-engine 책임 경계 | `backend/app/modules/` |
| [Backend orchestration](./orchestration/README.md) | shared state, main graph, client, intake, dependency 조립 | `backend/app/orchestration/` |
| [Orchestration workflow wrappers](./orchestration/workflows.md) | subgraph node/route/approval contract | `backend/app/orchestration/workflows/` |
| [공유 workflow state](./shared-state.md) | state key, approval/output payload, shared context | `backend/app/orchestration/state.py`, `backend/app/orchestration/client.py` |
| [질문 흐름](./request-lifecycle.md) | 사용자 질문 runtime flow와 node/edge/terminal 분기 | `backend/app/orchestration/builder.py`, `backend/app/orchestration/intake_router.py` |

## 각 문서가 답하는 질문

- `backend-workflow.md`
  - `POST /chats/stream` 요청은 어떤 순서로 workflow와 SSE event가 되는가?
  - dataset이 선택된 질문과 일반 질문은 어디서 갈라지는가?
  - `done` event는 어떤 파일들의 결합으로 만들어지는가?
- `core/README.md`
  - DB session, SQLAlchemy Base, LLM gateway, prompt registry는 어디에 있는가?
- `modules/README.md`
  - 어떤 module이 public router를 가지고, 어떤 module이 support engine인가?
  - 실제 route prefix는 무엇인가?
- `orchestration/README.md`
  - main graph node/edge, shared state key, approval interrupt, final answer packaging은 어디서 관리되는가?
- `orchestration/workflows.md`
  - preprocess/visualization/report approval contract와 analysis clarification path는 어떻게 다른가?

## 갱신 기준

- `backend/app/main.py` router mount나 public route가 바뀌면 `backend-workflow.md`, module family 문서, system API 문서를 함께 확인한다.
- `backend/app/orchestration/builder.py` node/edge/terminal이 바뀌면 `backend-workflow.md`, `request-lifecycle.md`, `orchestration/README.md`를 함께 확인한다.
- `backend/app/orchestration/state.py` key나 payload shape가 바뀌면 `shared-state.md`, `orchestration/README.md`, 관련 workflow 문서를 함께 확인한다.
- `backend/app/modules/*` 내부 책임이나 file layout이 바뀌면 해당 module family 문서를 갱신한다.

## 발견한 문제점 / 확인 필요 사항

- 관찰: 기존 architecture component/system 문서 위치가 작업 트리에서 변경된 상태다. 이 README는 현재 존재하는 `docs/system/`과 `docs/ai-agent/` 위치로 연결한다.
- 관찰: `docs/architecture/AGENTS.md`에는 예전 component/system 경로 언급이 남아 있다. 이번 문서 세트는 새 backend catalog를 제공하지만 기존 지침 파일 자체는 변경하지 않았다.
- 리스크: architecture docs 검증 테스트는 새 `docs/system/`, `docs/architecture/modules/`, `docs/architecture/orchestration/` 경로를 기준으로 한다. 경로를 바꾸면 테스트와 active context 문서를 함께 갱신해야 한다.
