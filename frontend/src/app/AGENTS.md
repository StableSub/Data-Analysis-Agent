# FRONTEND APP 지식 베이스

## 개요
실제 app shell과 Workbench runtime이다. `src/app`은 route, hook, app-specific component, workbench-specific helper를 담당한다.

## 관련 노트
- [[AGENTS|프로젝트 지식 베이스]]
- [[CLAUDE|Claude 작업 가이드]]
- [[docs/architecture/README|아키텍처 문서 안내]]
- [[docs/architecture/request-lifecycle|질문 흐름]]
- [[docs/architecture/shared-state|공유 상태]]
- [[backend/app/orchestration/AGENTS|Orchestration 지식 베이스]]

## 확인 위치
| 작업 | 위치 | 참고 |
|---|---|---|
| 프론트엔드 진입 shell | `App.tsx`, `pages/Workbench.tsx` | `/`와 `/chat` 모두 여기로 들어온다 |
| 메인 pipeline runtime | `hooks/useAnalysisPipeline.ts` | SSE, approval, dataset activation, run/session 상태 |
| Session persistence | `hooks/useWorkbenchSessionStore.ts` | Workbench session 저장/복원 |
| API 계약 | `../lib/api.ts` | 백엔드 request/response 타입 |
| GenUI Workbench | `components/genui/` | custom Workbench surface와 panel |
| 공유 app primitive | `components/ui/` | 영향 범위가 큰 wrapper/primitive |
| Visualization rendering | `components/visualization/` | chart/result payload rendering |

## 규칙
- `src/app`이 실제 frontend app tree다. 루트 `src/components/workbench`는 legacy/shared 영역이며 main runtime이 아니다.
- stateful orchestration은 hook과 normalization helper에 둔다. pipeline/session logic을 presentation component 전반에 흩뿌리지 않는다.
- `components/ui/`는 shared primitive로, `components/genui/`는 Workbench-specific product UI로 다룬다.
- frontend 계약은 `/vizualization` 같은 기존 특이점까지 포함해 backend output name을 가깝게 따른다.

## 갱신 기준
- `useAnalysisPipeline.ts`, `../lib/api.ts`, SSE event handling, approval/resume UI가 바뀌면 `docs/system/frontend-structure.md`를 같은 변경에서 갱신한다.
- backend output/event shape가 바뀌면 GenUI result renderer와 API type을 함께 확인한다.
- 수동 실행 포트나 package script가 바뀌면 루트 `AGENTS.md`, `README.md`, 관련 `docs/system/*.md`를 갱신한다.

## 금지 패턴
- `WorkbenchApp.tsx`가 있다고 가정하지 않는다. 실제 root는 `App.tsx` → `pages/Workbench.tsx`다.
- `src/components/**/*` 또는 `src/store/**/*`에 TypeScript coverage가 있다고 믿지 않는다. `tsconfig.json`이 이를 제외한다.
- 존재하지 않는 package script로 lint/typecheck 성공을 주장하지 않는다. `package.json`은 `dev`와 `build`만 정의한다.
- `components/ui/`의 shared primitive를 가볍게 수정하지 않는다. 변경 영향이 많은 화면에 퍼진다.

## 고유 스타일
- `useAnalysisPipeline.ts`는 매우 큰 orchestration hook이다. 많은 UI 동작이 이 파일에 모인다.
- `components/genui/`에는 Figma/generated-workbench naming과 token pattern이 남아 있다.
- `components/ui/`는 wrapper-heavy하며 feature code보다 vendor/shared-primitive 영역에 가깝다.

## 참고
- Frontend 수동 dev 포트는 `3000`이고, `dev.sh` 기본값은 `5173`이다.
- backend output/event shape가 바뀌면 `useAnalysisPipeline.ts`, `../lib/api.ts`, 관련 GenUI renderer를 함께 확인한다.
