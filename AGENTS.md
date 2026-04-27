# 프로젝트 지식 베이스

**생성일:** 2026-04-11 Asia/Seoul
**Commit:** c9cac08
**Branch:** perf/workbench-performance

## 관련 노트
- [[README|프로젝트 개요]]
- [[CLAUDE|Claude 작업 가이드]]
- [[docs/architecture/README|아키텍처 문서 안내]]
- [[docs/architecture/request-lifecycle|질문 흐름]]
- [[docs/architecture/shared-state|공유 상태]]
- [[backend/app/orchestration/AGENTS|Orchestration 지식 베이스]]
- [[backend/app/modules/AGENTS|Backend Modules 지식 베이스]]
- [[frontend/src/app/AGENTS|Frontend App 지식 베이스]]
- [[docs/architecture/AGENTS|Architecture Docs 지식 베이스]]

## 개요
현재 프로젝트는 웹 기반 데이터 분석 AI 에이전트다. FastAPI/LangGraph 백엔드가 데이터셋 인식 workflow를 실행하고 React/Vite 프론트엔드 Workbench가 SSE로 결과를 소비한다. 제품 방향과 현재 런타임 기준은 `docs/product/prd.md`, `docs/product/current-state-baseline.md`, `docs/product/roadmap.md`를 먼저 확인한다.

## 문서 계층 원칙
- 루트 `AGENTS.md`는 항상 읽히는 최상위 컨텍스트이므로 공통 작업 순서, 핵심 진입점, 검증 명령만 유지한다.
- 영역별 세부 규칙은 child `AGENTS.md`에 둔다. 작업 영역에 child 문서가 있으면 루트보다 구체적인 규칙으로 적용한다.
- 제품 판단은 `docs/product/*`, 런타임 상세는 `docs/architecture/*`, 실행·검증 명령은 `docs/development/*`가 소유한다.
- 문서와 코드가 다르면 코드를 기준으로 문서를 갱신하고, drift 방지는 `backend/tests/test_architecture_docs.py`와 `backend/tests/test_docs_harness.py`로 검증한다.

## 공통 AI 개발 프로토콜
팀원들이 각자 다른 AI 도구를 사용하더라도 같은 기준으로 작업하기 위한 공통 절차다.

### 작업 전 확인 순서
1. `graphify-out/GRAPH_REPORT.md`
   - 아키텍처 또는 코드베이스 질문을 받으면 먼저 핵심 노드, 커뮤니티, 주요 연결 관계를 확인한다.
   - `graphify-out/wiki/index.md`가 존재하면 원본 파일보다 wiki를 우선 탐색한다.
   - `graphify-out`은 로컬 생성물이다. 산출물 전체를 커밋 대상으로 삼지 않는다.
2. 관련 `AGENTS.md`
   - 루트 `AGENTS.md`를 먼저 읽고, 작업 영역에 child `AGENTS.md`가 있으면 추가로 따른다.
   - 주요 child 문서: `backend/app/orchestration/AGENTS.md`, `backend/app/modules/AGENTS.md`, `frontend/src/app/AGENTS.md`, `docs/architecture/AGENTS.md`
3. 관련 `docs/product/*`
   - 제품 요구사항은 `docs/product/prd.md`, 현재 구현 기준은 `docs/product/current-state-baseline.md`, 개선 우선순위는 `docs/product/roadmap.md`를 따른다.
4. 관련 `docs/architecture/*`
    - workflow, state, API, 프론트엔드/백엔드 구조가 얽힌 변경은 architecture 문서를 먼저 확인한다.
5. 실제 코드
    - 문서가 오래되었을 수 있으므로 최종 판단은 현재 코드, 라우터, 타입, 테스트를 기준으로 한다.

### 변경 전 원칙
- 최소 diff로 목표를 달성한다.
- 실제 파일 경로, 라우터 prefix, payload key, npm/pytest 스크립트를 확인한 뒤 수정한다.
- 오래된 문서와 실제 코드가 다르면 코드를 기준으로 문서를 고친다.
- 요구가 여러 방식으로 해석되면 구현 전에 모호한 지점을 드러내고 확인한다.
- 관련 없는 cleanup, 리팩터링, 포맷 변경은 하지 않는다.

### 검증 루프
- 문서/architecture 변경:
  - `PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py`
- 프론트엔드 변경:
  - `npm --prefix frontend run build`
  - `frontend/package.json`에는 `lint` 또는 `check:types` script가 없으므로 이를 통과로 주장하지 않는다.
- 백엔드 workflow 변경:
  - `PYTHONPATH=. pytest -q backend/tests/test_main_workflow_analysis_happy_path.py`
  - `PYTHONPATH=. pytest -q backend/tests/test_analysis_planning_accuracy_guards.py backend/tests/test_planner_analysis_accuracy_guards.py`
- 코드 파일 수정 후:
  - 가능한 경우 `graphify update .`를 실행해 로컬 그래프를 갱신한다.
  - graphify 산출물은 로컬 생성물로 다루며, 필요한 문서 변경만 커밋 대상으로 삼는다.

## 구조
```text
.
├── backend/app/                # 런타임 코드
│   ├── main.py                 # FastAPI 초기화, 라우터 마운트, CORS, metadata.create_all
│   ├── modules/                # 기능 단위 백엔드 모듈
│   └── orchestration/          # LangGraph 조립, 상태 계약, 스트리밍 클라이언트
├── backend/tests/              # 추적되는 pytest suite; 최상위 tests/는 만들지 않는다
├── frontend/src/
│   ├── app/                    # 실제 앱 shell, workbench page, hook, component
│   ├── lib/                    # API wrapper와 payload normalizer
│   └── components/workbench/   # legacy/shared workbench 전용 하위 트리
├── docs/architecture/          # 코드를 따라가는 아키텍처 문서
├── storage/                    # 런타임 dataset, FAISS index, checkpoint, log
└── dev.sh                      # 통합 개발 실행 스크립트; frontend 기본 포트 주의
```

## 확인 위치
| 작업 | 위치 | 참고 |
|---|---|---|
| 백엔드 앱 초기화 | `backend/app/main.py` | 라우터가 중앙 API registry 없이 여기서 직접 마운트된다 |
| 메인 런타임 흐름 | `backend/app/orchestration/builder.py` | 분기와 terminal 동작의 기준 파일 |
| 공유 workflow 상태 | `backend/app/orchestration/state.py` | planner/preprocess/analysis/rag/report 전반의 TypedDict 계약 |
| 스트리밍 실행 이벤트 | `backend/app/orchestration/client.py` | SSE chunk, approval, 최종 payload |
| 최종 답변 구성 | `backend/app/orchestration/ai.py`, `backend/app/orchestration/builder.py` | general/data answer 생성과 merged context 전달 |
| 백엔드 기능 로직 | `backend/app/modules/` | analysis/preprocess/rag/visualization/report 계열 |
| 프론트엔드 진입점 | `frontend/src/main.tsx` → `frontend/src/app/App.tsx` | 이 repo에는 `WorkbenchApp.tsx`가 없다 |
| 프론트엔드 pipeline 런타임 | `frontend/src/app/hooks/useAnalysisPipeline.ts` | Workbench 동작 대부분이 모이는 큰 orchestration hook |
| 프론트엔드 API 계약 | `frontend/src/lib/api.ts` | 요청/응답 타입과 fetch helper |
| 런타임 아키텍처 문서 | `docs/architecture/request-lifecycle.md`, `docs/architecture/shared-state.md` | orchestration 변경과 함께 맞춘다 |

## 코드 지도
| 심볼 / 파일 | 역할 |
|---|---|
| `build_main_workflow` (`backend/app/orchestration/builder.py`) | 메인 LangGraph 조립 |
| `AgentClient` (`backend/app/orchestration/client.py`) | workflow 스트리밍 adapter |
| `answer_data_question` (`backend/app/orchestration/ai.py`) | `merged_context` 기반 최종 데이터 답변 생성 |
| `build_intake_router_workflow` (`backend/app/orchestration/intake_router.py`) | dataset-selected/no-dataset 진입 분리와 handoff 생성 |
| `AnalysisService` (`backend/app/modules/analysis/service.py`) | 분석 planning/execution 연결 계층 |
| `RagService` (`backend/app/modules/rag/service.py`) | index/query 생명주기 |
| `useAnalysisPipeline` (`frontend/src/app/hooks/useAnalysisPipeline.ts`) | 프론트엔드 run/session/pipeline 상태 엔진 |

## 규칙
- 최소 diff를 우선한다. happy path를 먼저 다룬다. 추측성 유연성을 추가하지 않는다.
- 요청과 직접 관련된 파일만 수정한다.
- 백엔드 분리를 보존한다. `modules/`는 기능 동작을, `orchestration/`은 기능 간 workflow 계약을 담당한다.
- 백엔드는 `pyproject.toml`이 아니라 `requirements.txt`를 사용한다.
- DB schema 변경은 `Base.metadata.create_all()`에 의존한다. migration tool은 없다.
- 프론트엔드 실제 앱 코드는 `frontend/src/app`에 있다. `frontend/src/app/components`는 Workbench UI 컴포넌트를 담고, 메인 앱 shell은 `frontend/src/app`을 기준으로 확인한다.

## 금지 패턴 (이 프로젝트)
- 명시적으로 요청받지 않았다면 `try/except`, `try/catch`, 넓은 fallback 로직, retry/backoff, 방어적 validation을 추가하지 않는다.
- 사용자가 범위가 정해진 변경을 요청했을 때 인접 cleanup이나 넓은 refactor를 하지 않는다.
- 새 최상위 `tests/`를 만들지 않는다. 백엔드 테스트는 `backend/tests/`에 둔다.
- 존재하지 않는 프론트엔드 lint/typecheck script를 통과한 검증처럼 말하지 않는다.
- 루트 AGENTS/CLAUDE의 오래된 문서가 현재 트리를 정확히 반영한다고 가정하지 않는다. 실제 경로를 먼저 확인한다.

## 고유 스타일
- 백엔드 런타임은 별도 `api/agent` 계층이 아니라 `modules/chat/router.py`와 orchestration을 통해 진입한다.
- 현재 백엔드/프론트엔드 계약에서 시각화 route는 `/vizualization`으로 표기된다.
- 프론트엔드 package에는 아직 생성/Figma 스타일 naming(`@figma/my-make-file`)과 큰 `genui` 하위 트리가 있다.
- `frontend/tsconfig.json`은 `src/components/**/*`와 `src/store/**/*`를 TS 검사에서 제외한다.

## 명령어
```bash
# 통합 개발 실행
bash dev.sh

# 백엔드
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# 프론트엔드
npm --prefix frontend run dev -- --host 127.0.0.1 --port 3000
npm --prefix frontend run build

# 백엔드 테스트
PYTHONPATH=. pytest -q backend/tests/test_main_workflow_analysis_happy_path.py
PYTHONPATH=. pytest -q backend/tests/test_analysis_planning_accuracy_guards.py backend/tests/test_planner_analysis_accuracy_guards.py
```

## 참고
- `dev.sh`는 frontend 기본 포트로 `5173`을 사용한다. 문서와 수동 실행 명령은 `3000`을 사용한다.
- `frontend/package.json`에는 `dev`와 `build`만 정의되어 있다. `check:types`와 `lint`는 다른 곳에 문서화되어 있어도 script로 구현되어 있지 않다.
- `docs/architecture/`는 런타임 흐름의 보조 기준 문서다. workflow/state 계약이 바뀌면 함께 갱신한다.
- 로컬 규칙은 child AGENTS를 참고한다:
  - `backend/app/orchestration/AGENTS.md`
  - `backend/app/modules/AGENTS.md`
  - `frontend/src/app/AGENTS.md`
  - `docs/architecture/AGENTS.md`

## graphify

이 프로젝트에는 `graphify-out/`에 graphify 지식 그래프가 있다.

규칙:
- 아키텍처 또는 코드베이스 질문에 답하기 전 `graphify-out/GRAPH_REPORT.md`에서 핵심 노드와 community 구조를 확인한다.
- `graphify-out/wiki/index.md`가 있으면 원본 파일 대신 해당 wiki를 탐색한다.
- 이 세션에서 코드 파일을 수정한 뒤에는 가능한 경우 `graphify update .`를 실행해 그래프를 최신 상태로 유지한다(AST 전용, API 비용 없음).
