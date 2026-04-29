# BACKEND MODULES 지식 베이스

## 개요
기능 단위로 나뉜 백엔드 모듈 영역이다. API-facing 모듈과 내부 support engine이 함께 있으므로 module family마다 형태가 다르다.

## 관련 노트
- [[AGENTS|프로젝트 지식 베이스]]
- [[backend/app/orchestration/AGENTS|Orchestration 지식 베이스]]
- [[docs/architecture/README|아키텍처 문서 안내]]
- [[docs/architecture/modules/analysis|Analysis module]]
- [[docs/architecture/modules/rag-and-guidelines|RAG and guidelines modules]]
- [[docs/architecture/modules/preprocess-and-visualization|Preprocess and visualization modules]]
- [[docs/architecture/modules/chat-report-export|Chat/report/export modules]]

## 확인 위치
| 작업 | 위치 | 참고 |
|---|---|---|
| Analysis core | `analysis/` | deterministic 로직과 LLM이 결합된 가장 큰 모듈 |
| Dataset metadata/profile | `profiling/`, `datasets/` | 공유 context와 upload/sample 경계 |
| Retrieval/indexing | `rag/` | FAISS/query/index 생명주기 |
| Mutation flow | `preprocess/` | approval과 dataset transformation |
| Visualization flow | `visualization/` | planner/processor/executor 분리 |
| 사용자 런타임 진입 | `chat/` | session과 workflow invocation seam |
| 문서/최종 출력 | `reports/`, `results/` | report draft와 저장된 analysis artifact |

## 규칙
- repo 분리를 보존한다. module은 기능 동작을, orchestration은 기능 간 계약을 담당한다.
- module 형태가 섞여 있음을 전제한다.
  - public/API module: `router.py`, `service.py`, `schemas.py`
  - AI-heavy module: `planner.py`, `processor.py`, `executor.py`, `run_service.py`, `ai.py`, `sandbox.py`
- deterministic validation/rule 로직은 router가 아니라 processor나 service에 둔다.
- 별도 parallel contract를 만들기보다 `backend/app/core/`의 공유 infra와 `backend/app/orchestration/`의 공유 workflow state를 재사용한다.

## 갱신 기준
- public router, prefix, request/response schema가 바뀌면 `docs/system/api-spec.md`를 같은 변경에서 갱신한다.
- module 책임이나 내부 디렉터리 패턴이 바뀌면 `docs/system/backend-structure.md`를 갱신한다.
- workflow state에 실리는 payload 형태가 바뀌면 `backend/app/orchestration/AGENTS.md`와 `docs/architecture/shared-state.md`를 함께 확인한다.

## 금지 패턴
- 명시적으로 요청받지 않았다면 module code에 넓은 exception/fallback/retry 계층을 추가하지 않는다.
- 모든 module을 CRUD slice로 취급하지 않는다. `profiling/`, `reports/`, `results/` 같은 내부 engine은 public-router module이 아니다.
- filesystem/index/persistence 관심사를 무관한 feature module에 섞지 않는다. 소유 module에 둔다.
- `backend/tests/` 밖에 최상위 테스트를 만들지 않는다.

## 고유 스타일
- `analysis/`는 가장 강한 rule engine이다. `processor.py`는 deterministic하게, `service.py`는 orchestration-oriented하게 유지한다.
- `rag/`는 API service code와 infra-heavy indexing 관심사가 섞여 있다.
- `profiling/`에는 router가 없다. planner/analysis/reporting이 사용하는 공유 support logic이다.
- `reports/`는 module family처럼 동작하지만 내부 finalization logic에 가깝다.

## 참고
- 특히 주의할 hotspot은 `analysis/`, `eda/`, `preprocess/`, `visualization/`, `rag/`다.
- module 변경이 workflow state 형태나 최종 answer payload를 바꾸면 같은 변경에서 `backend/app/orchestration/`과 문서를 함께 갱신한다.
