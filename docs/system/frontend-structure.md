# 프론트엔드 구조

## 목적

이 문서는 프론트엔드 화면 구조와 백엔드 연동 방식을 설명한다.
현재 구현 기준으로 AI가 frontend 작업을 시작할 때 확인해야 하는 진입점만 정리한다.

현재 frontend는 데이터 분석 Workbench 기준이다. Workbench shell, session store, SSE/approval 흐름, dataset upload/selection, analysis result panels가 주요 작업 진입점이다.

## 갱신 기준

- 기준 코드: `frontend/src/app/App.tsx`, `frontend/src/app/pages/Workbench.tsx`, `frontend/src/app/hooks/useAnalysisPipeline.ts`, `frontend/src/lib/api.ts`
- 검증 명령: `npm --prefix frontend run build`
- 갱신 트리거: Workbench entrypoint 변경, SSE/approval handling 변경, backend API type 변경, result panel/renderer 구조 변경

## 진입점

- `frontend/src/main.tsx`: React 앱을 mount한다.
- `frontend/src/app/App.tsx`: app shell과 route를 구성한다.
- `frontend/src/app/pages/Workbench.tsx`: 현재 workbench의 주요 화면이다.

`WorkbenchApp.tsx`는 현재 repository에 없다.

## 상태와 실행 흐름

- `frontend/src/app/hooks/useAnalysisPipeline.ts`
  - dataset upload, selected source, server dataset bootstrap, chat run, SSE stream, approval resume, 결과 상태를 관리한다.
  - Pre-EDA insights와 chat stream 조회 시 현재 선택된 `guideline_source_id`를 전달해 backend의 selected guideline > active guideline > none 계약에 맞춘다. EDA 응답에 `dataset_overview`가 있으면 Workbench EDA 요약에 표시하고, `suggested_questions`가 있으면 Pre-EDA 보드의 시작 질문으로 정규화한다.
  - 최종 답변의 `evidence_package`/`answer_quality`는 `AssistantReportMessage`에서 evidence pill과 확장 설명으로 표시한다. clarification 또는 실패 응답은 backend `query_feedback`을 우선 표시하고, 없을 때만 로컬 보조 피드백을 표시한다.
  - `approval_required` 상태에서는 `pending_approval`을 본문 승인 카드와 하단 `GateBar`에 모두 전달한다. 하단 `GateBar`는 승인/취소 버튼만 표시하지 않고 승인 대상 제목, 요약, 주요 항목, 초안/preview를 함께 보여준다.
  - Error 상태로 전환하거나 approval resume 요청을 수락하면 stale `pendingApproval`을 지운다. 실제 승인 대기 중인 `needs-user` 상태에서만 자유 입력 전송을 막아 실패 후 복구 질문과 하단 채팅 입력이 다시 동작한다.
  - backend workflow output shape가 바뀌면 이 파일을 먼저 확인한다.
- `frontend/src/app/hooks/useWorkbenchSessionStore.ts`
  - workbench session을 localStorage에 저장하고 복원한다.
  - Workbench 초기 진입 시 `GET /chats/` 결과를 local session 목록과 병합한다.
  - session 선택/초기 복원 중에는 autosave를 잠시 막아 복원 전 context가 대상 session에 저장되지 않게 한다.

## 백엔드 API 연결

- `frontend/src/lib/api.ts`
  - frontend API client와 request/response type이 모여 있다.
  - 기본 API base URL은 `http://127.0.0.1:8000`이며 `VITE_API_BASE_URL`로 override할 수 있다.
  - 현재 backend 시각화 경로는 `/visualization`이 아니라 `/vizualization`이다.
  - Workbench 초기 복원은 `GET /datasets/`와 `GET /chats/`를 함께 호출한다.

## UI 구성 위치

- `frontend/src/app/components/genui/`: workbench 제품 UI와 panel 계열 컴포넌트
- `frontend/src/app/components/genui/GateBar.tsx`: approval resume의 고정 하단 액션 표면이다. 승인/취소/수정 요청 버튼과 함께 현재 승인 대상의 세부 내용을 표시한다.
- `frontend/src/app/components/ui/`: 여러 화면에서 재사용되는 UI primitive
- `frontend/src/app/components/ui/chart.tsx`: chart primitive

`components/ui/`는 영향 범위가 크므로 필요한 경우에만 수정한다.

backend output/event shape가 바뀌면 이 문서와 함께 `useAnalysisPipeline.ts`, `frontend/src/lib/api.ts`, 관련 GenUI renderer를 확인한다.
