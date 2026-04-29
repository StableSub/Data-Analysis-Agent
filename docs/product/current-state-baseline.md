# 현재 구현 기준선

## 문서 목적

이 문서는 현재 repository가 실제로 제공하는 데이터 분석 AI 에이전트 기능과 제약을 정리한다.
제품 요구사항은 [제품 요구사항 문서](./prd.md)를 기준으로 보고, 향후 개선 순서는 [구현 로드맵](./roadmap.md)을 함께 본다.

## 현재 제품 성격

현재 구현은 웹 기반 데이터 분석 AI 에이전트다.
사용자는 데이터셋을 업로드하고 자연어 질문을 입력하며, backend는 전처리, 분석, RAG, 시각화, 리포트 흐름을 조합해 응답한다.

## 현재 주요 기능

- CSV 중심 데이터셋 업로드와 샘플 조회
- SSE 기반 채팅 실행과 세션 히스토리
- 전처리 제안과 approval/resume 흐름
- 분석 실행과 결과 저장
- RAG/guideline 기반 문서 검색 보조
- 시각화 생성
- 리포트 생성과 승인 흐름
- trace/logging 기반 실행 이력 추적

## 현재 아키텍처 기준

현재 architecture 문서는 실제 데이터 분석 런타임을 설명한다.

- `docs/architecture/request-lifecycle.md`: dataset 선택 여부에 따른 workflow 분기
- `docs/architecture/shared-state.md`: workflow state 계약과 SSE-facing output
- `docs/architecture/orchestration/workflows.md`와 `docs/architecture/modules/*.md`: preprocess, analysis, RAG, guideline, visualization, report 상세
- `docs/system/api-spec.md`: 현재 FastAPI public route 목록
- `docs/system/backend-structure.md`: 백엔드 module/orchestration 구조
- `docs/system/frontend-structure.md`: Workbench 프론트엔드 구조

## 재사용 가능한 기반

### 채팅과 세션 실행

`chats` API, SSE stream, pending approval, resume, history 흐름은 현재 분석 실행의 주 진입점이다.
분석 질문 실행, 승인 대기, 중단 후 재개, 세션 복원 검증은 이 경로를 기준으로 한다.

### RAG와 guideline 문서 관리

guideline 업로드, 활성화, 삭제, RAG 검색 기반 evidence summary 흐름이 존재한다.
현재는 분석 답변과 리포트 생성을 보조하는 문서 근거 계층으로 사용된다.

### Workbench UI 구조

현재 Workbench는 데이터셋 업로드, 선택된 source, 질문 입력, 실행 상태, approval card, 결과 패널, 세션 복원 흐름을 갖고 있다.

### Trace와 로그

trace/logging 구조는 실행 단계, approval/resume, 오류, 최종 결과를 추적하는 기반이다.
`trace_id`, `session_id`, `run_id`, `stage`를 기준으로 raw event log와 trace summary를 확인한다.

## 현재 제약

- 입력 데이터는 CSV 중심이다.
- orchestration은 `source_id`와 데이터셋 선택 여부를 중심으로 분기한다.
- selected-dataset 질문은 preprocess 판단을 먼저 거친 뒤 analysis 또는 RAG로 이동한다.
- 최종 답변은 `merged_context` 기반으로 생성되며, 별도 answer evidence contract는 아직 제한적이다.
- RAG는 문서형 retrieval summary에 강하고, 표 데이터 row/column provenance는 더 보강이 필요하다.
- 프론트엔드 type/lint script는 별도로 제공되지 않고 `npm --prefix frontend run build`가 주요 검증 명령이다.

## 검증 기준

- 문서/아키텍처 변경: `PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py`
- 프론트엔드 변경: `npm --prefix frontend run build`
- 백엔드 workflow 변경: 관련 `backend/tests/*.py`를 확인하고 실행한다.
- 코드 파일 수정 후 가능한 경우 `graphify update .`로 로컬 그래프를 갱신한다.
