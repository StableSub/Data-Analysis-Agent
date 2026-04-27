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
  - dataset upload, selected source, chat run, SSE stream, approval resume, 결과 상태를 관리한다.
  - backend workflow output shape가 바뀌면 이 파일을 먼저 확인한다.
- `frontend/src/app/hooks/useWorkbenchSessionStore.ts`
  - workbench session을 localStorage에 저장하고 복원한다.

## 백엔드 API 연결

- `frontend/src/lib/api.ts`
  - frontend API client와 request/response type이 모여 있다.
  - 기본 API base URL은 `http://localhost:8000`이며 `VITE_API_BASE_URL`로 override할 수 있다.
  - 현재 backend 시각화 경로는 `/visualization`이 아니라 `/vizualization`이다.

## UI 구성 위치

- `frontend/src/app/components/genui/`: workbench 제품 UI와 panel 계열 컴포넌트
- `frontend/src/app/components/ui/`: 여러 화면에서 재사용되는 UI primitive
- `frontend/src/app/components/ui/chart.tsx`: chart primitive

`components/ui/`는 영향 범위가 크므로 필요한 경우에만 수정한다.

backend output/event shape가 바뀌면 이 문서와 함께 `useAnalysisPipeline.ts`, `frontend/src/lib/api.ts`, 관련 GenUI renderer를 확인한다.
