# 데이터 분석 AI 에이전트 구현 로드맵

## 문서 목적

이 문서는 현재 데이터 분석 AI 에이전트를 기준으로 기능 개선, 정확도 강화, 하네스 확장 우선순위를 정리한다.
제품 요구사항은 [제품 요구사항 문서](./prd.md), 현재 구현 상태는 [현재 구현 기준선](./current-state-baseline.md)을 따른다.

## 개선 원칙

- 현재 데이터 분석 런타임을 기준으로 문서와 코드를 맞춘다.
- architecture 문서는 실제 코드 변경과 같은 시점에 갱신한다.
- 정확도, 근거성, 재현성을 우선한다.
- broad refactor보다 workflow seam별 검증 가능한 개선을 우선한다.

## 기능 개선 축

| 영역 | 현재 상태 | 개선 방향 |
| --- | --- | --- |
| Dataset context | CSV profile/context 기반 | full-profile-aware planning 강화 |
| Routing | intake coarse intent 중심 | selected-dataset 질문 route 정확도 강화 |
| Analysis | SQL/Python 실행 경로 보유 | 오류 원인 분류, repair/replan loop 강화 |
| RAG/guideline | top-k evidence summary 중심 | relevance threshold, evidence sufficiency 검증 |
| 시각화 | analysis result 기반 생성 | chart reason, renderer coverage, artifact 관리 강화 |
| 리포트 | draft/approval/finalize 흐름 | metrics/evidence consistency 검증 강화 |
| trace/logging | raw JSONL과 trace summary 보유 | stage latency, trace chain, lifecycle 검증 강화 |
| 프론트엔드 Workbench | SSE/approval/result panel 보유 | backend stage와 UI state 매핑 강화 |

## 제안 단계

### 1단계: 문서와 현재 런타임 정합성 유지

- README, AGENTS, docs index가 데이터 분석 AI 에이전트를 기준으로 설명하도록 유지한다.
- architecture 문서는 `builder.py`, `state.py`, `client.py`, public route와 같은 실제 코드 기준으로 갱신한다.
- stale 문서 링크와 존재하지 않는 파일 경로를 docs harness로 검증한다.

### 2단계: 정확도 회귀 하네스 추가

- routing case set 추가
- analysis case set 추가
- RAG evidence case set 추가
- selected-dataset 질문의 expected path와 final output contract 검증
- benchmark 결과를 JSON으로 저장하는 runner 추가

### 3단계: 근거와 abstain contract 강화

- 최종 답변용 evidence package를 `merged_context`와 분리한다.
- 근거 부족, 충돌, 선택 데이터셋 범위 이탈 시 abstain reason을 남긴다.
- summary와 raw metric/table 간 수치 일관성 검증을 추가한다.

### 4단계: trace와 UI 관측성 강화

- SSE thought/done 이벤트에 stage metadata를 일관되게 포함한다.
- trace summary와 raw event log를 검증하는 테스트를 추가한다.
- Workbench에 route, columns, code/query, result, latency를 보여주는 trace chain을 노출한다.

### 5단계: 안정성 개선

- analysis error cause를 세분화한다.
- SQL/Python strategy fallback 정책을 검토한다.
- RAG relevance threshold와 no-evidence 처리를 추가한다.
- SSE error/reconnect/resume UX를 보강한다.

## 하네스 우선순위

1. Docs/API route drift harness 유지
2. Main workflow happy path 회귀 테스트
3. Selected-dataset route accuracy 테스트
4. Analysis result consistency 테스트
5. RAG evidence sufficiency 테스트
6. Approval/resume end-to-end 테스트
7. trace/logging lifecycle 테스트
8. Benchmark runner와 aggregate report

## 문서 갱신 순서

1. workflow/state/API가 바뀌면 architecture 문서를 같은 변경에서 갱신한다.
2. 검증 명령이 바뀌면 `docs/development/local-environment.md`와 루트 `AGENTS.md`를 갱신한다.
3. 제품 범위나 우선순위가 바뀌면 `docs/product/prd.md`와 이 문서를 갱신한다.
4. code file 변경 후 가능한 경우 graphify 로컬 그래프를 갱신한다.

## 주요 리스크

- 분석 정확도 회귀가 단위 테스트만으로 숨을 수 있다.
- RAG evidence가 부족해도 최종 답변이 생성될 수 있다.
- 프론트엔드 state와 백엔드 stage가 어긋나 사용자에게 잘못된 진행 상태를 보여줄 수 있다.
- trace/logging은 존재하지만 검증 하네스가 없으면 실패 재현성이 낮아질 수 있다.
