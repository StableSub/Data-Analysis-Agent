# GenUI Migration — Stage A 명세서
> 작성일: 2026-02-25
> 목적: 이식 대상 파일 전체 목록, 최종 배치 경로, 발견된 특이사항 기록

---

## 1. 스캔 대상 요약

| 소스 루트 | 파일 수 | 비고 |
|---|---|---|
| `frontend/_temp_genui/src/app/components/genui/` | 27개 (`.tsx`) | 이식 대상 핵심 컴포넌트 |
| `frontend/_temp_genui/src/app/pages/Workbench.tsx` | 1개 | 5-상태 Mock 오케스트레이터 페이지 |
| `frontend/_temp_genui/src/styles/` | 4개 (`.css`) | Stage B 이식 대상 (본 명세에서 참고용 기재) |

---

## 2. 이식할 복사 대상 파일 전체 목록

### 2-A. GenUI 컴포넌트 27종 (Stage C에서 복사)

| # | 소스 파일 | 역할 요약 |
|---|---|---|
| 1 | `ApprovalCard.tsx` | 승인/거절 카드 UI |
| 2 | `AssistantReportMessage.tsx` | 에이전트 리포트 말풍선 (streaming / final / error variant) |
| 3 | `AttachMenuPopover.tsx` | 파일 첨부 팝오버 메뉴 |
| 4 | `BrandHeader.tsx` | 앱 브랜드 헤더 |
| 5 | `CardShell.tsx` | 카드 래퍼 (Header / Body / Footer 슬롯) + `GenUIChip` 의존 |
| 6 | `CopilotPanel.tsx` | 에이전트 우측 패널 (툴콜 목록 + 파이프라인) |
| 7 | `DecisionChips.tsx` | 상태별 결정 칩 바 |
| 8 | `DetailsPanel.tsx` | 상세 정보 우측 패널 |
| 9 | `Dropzone.tsx` | 파일 드롭존 + 샘플 버튼 |
| 10 | `ErrorCard.tsx` | 에러 카드 |
| 11 | `EvidenceFooter.tsx` | 분석 근거(데이터·컴퓨팅·RAG) 푸터 |
| 12 | `GateBar.tsx` | 승인/거절/수정 게이트 바 |
| 13 | `GenUIChip.tsx` | 범용 상태 칩 (variant 기반) |
| 14 | `MCPPanel.tsx` | MCP 로그 패널 |
| 15 | `PipelineBar.tsx` | 상단 파이프라인 진행 바 (motion 의존) |
| 16 | `PipelineProgress.tsx` | 파이프라인 프로그레스 (motion 의존) |
| 17 | `PipelineTracker.tsx` | 파이프라인 단계 트래커 |
| 18 | `RightPanelTabs.tsx` | 우측 패널 탭 컨테이너 (Details / Agent / MCP) |
| 19 | `SessionHeader.tsx` | 세션 헤더 |
| 20 | `Skeletons.tsx` | 스켈레톤 로딩 컴포넌트 |
| 21 | `StatusBadge.tsx` | 상태 배지 (empty / uploading / running / needs-user / error / success) |
| 22 | `StreamingText.tsx` | 스트리밍 텍스트 애니메이션 |
| 23 | `TimelineItem.tsx` | 좌측 히스토리 타임라인 아이템 |
| 24 | `ToolCallIndicator.tsx` | 인라인 툴콜 상태 인디케이터 |
| 25 | `ToolCallListItem.tsx` | 툴콜 목록 아이템 |
| 26 | `WorkbenchCommandBar.tsx` | 하단 채팅 입력 커맨드 바 |
| 27 | `WorkbenchLayout.tsx` | 3-패널 레이아웃 (좌 / 중앙 / 우) |

### 2-B. Mock 오케스트레이터 페이지 (Stage D/E 참고 파일)

| 소스 파일 | 역할 | 최종 배치 단계 |
|---|---|---|
| `_temp_genui/src/app/pages/Workbench.tsx` | 5-상태 Mock 상태머신 전체 포함 | Stage E에서 `frontend/src/pages/Chat.tsx`로 교체 |

### 2-C. 스타일 파운데이션 (Stage B 이식 대상, 참고용 기재)

| 소스 파일 | 주요 내용 |
|---|---|
| `_temp_genui/src/styles/theme.css` | `--genui-*` CSS 변수 (라이트/다크 모드 토큰 완비), `@theme {}` Tailwind v4 블록 |
| `_temp_genui/src/styles/index.css` | 전역 기본 스타일 |
| `_temp_genui/src/styles/fonts.css` | 폰트 선언 |
| `_temp_genui/src/styles/tailwind.css` | Tailwind 진입점 |

---

## 3. 최종 배치될 대상 경로

### 3-A. GenUI 컴포넌트 27종 → 플랫(flat) 배치

```
frontend/src/components/genui/workbench/   ← 신규 생성 디렉토리
├── ApprovalCard.tsx
├── AssistantReportMessage.tsx
├── AttachMenuPopover.tsx
├── BrandHeader.tsx
├── CardShell.tsx
├── CopilotPanel.tsx
├── DecisionChips.tsx
├── DetailsPanel.tsx
├── Dropzone.tsx
├── ErrorCard.tsx
├── EvidenceFooter.tsx
├── GateBar.tsx
├── GenUIChip.tsx
├── MCPPanel.tsx
├── PipelineBar.tsx
├── PipelineProgress.tsx
├── PipelineTracker.tsx
├── RightPanelTabs.tsx
├── SessionHeader.tsx
├── Skeletons.tsx
├── StatusBadge.tsx
├── StreamingText.tsx
├── TimelineItem.tsx
├── ToolCallIndicator.tsx
├── ToolCallListItem.tsx
├── WorkbenchCommandBar.tsx
└── WorkbenchLayout.tsx
```

### 3-B. Mock 오케스트레이터 → Stage E에서 처리

```
frontend/src/pages/Chat.tsx   ← 기존 파일을 Workbench.tsx 기반으로 교체 (Stage E)
```

### 3-C. 기존 genui 디렉토리 현황 (레거시 — Stage F에서 Deprecate, Stage G에서 Delete)

```
frontend/src/components/genui/
├── GateBar/          ← LEGACY (Stage F: @deprecated 표시, Stage G: 삭제)
│   ├── GateBar.tsx
│   └── index.ts
├── Pipeline/         ← LEGACY
│   ├── PipelineTracker.tsx
│   └── index.ts
├── Workbench/        ← LEGACY (구 5-state switch 구현체)
│   ├── Workbench.tsx
│   ├── index.ts
│   └── screens/
│       ├── EmptyScreen.tsx
│       ├── ErrorScreen.tsx
│       ├── NeedsUserScreen.tsx
│       ├── RunningScreen.tsx
│       ├── UploadingScreen.tsx
│       └── index.ts
└── index.ts          ← Stage F에서 workbench/ export로 교체
```

---

## 4. 발견된 특이사항 (수정이 필요한 import 경로 등)

### ⚠️ 특이사항 1: `cn` 유틸리티 — `frontend/src/lib/utils.ts` 미존재

**현황:**
- `_temp_genui` 컴포넌트 27종 전부 `import { cn } from "../../../lib/utils"` 사용
- `frontend/src/lib/utils.ts` 파일이 **없음** (`frontend/src/components/ui/utils.ts`에만 동일 내용 존재)

**깊이 분석 (핵심):**

| 위치 | 파일 경로 | `../../../lib/utils` 해석 결과 |
|---|---|---|
| 소스 | `_temp_genui/src/app/components/genui/*.tsx` | `_temp_genui/src/lib/utils.ts` ✅ 존재 |
| **목표** | `frontend/src/components/genui/workbench/*.tsx` | `frontend/src/lib/utils.ts` ❌ **미존재** |

**결론:** 타겟 디렉토리(`genui/workbench/`)의 깊이가 소스와 동일하게 `src/`로부터 3단계이므로, **상대 경로 `../../../lib/utils`를 컴포넌트 파일에서 수정하지 않아도 된다.** 단, **Stage B에서 `frontend/src/lib/utils.ts`를 생성**해야 한다 (내용은 `frontend/src/components/ui/utils.ts`와 동일 — `clsx` + `twMerge`).

**권장 조치 (Stage B):**
```ts
// frontend/src/lib/utils.ts — 신규 생성
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

---

### ⚠️ 특이사항 2: Workbench.tsx(페이지)의 import 경로 — 2곳 수정 필요

`Workbench.tsx`는 현재 `_temp_genui/src/app/pages/`에 있어서 import 깊이가 컴포넌트와 다르다.

**Stage E에서 `frontend/src/pages/Chat.tsx`로 배치 시 변경 항목:**

| 변경 대상 | 기존 | 변경 후 |
|---|---|---|
| genui 컴포넌트 import 15줄 | `"../components/genui/ComponentName"` | `"../components/genui/workbench/ComponentName"` |
| `cn` import | `"../../lib/utils"` | `"../lib/utils"` (또는 `"@/lib/utils"`) |

---

### ⚠️ 특이사항 3: GenUI CSS 변수 (`--genui-*`) 미이식

**현황:**
- `_temp_genui/src/styles/theme.css`에 `--genui-surface`, `--genui-panel`, `--genui-border`, `--genui-text`, `--genui-muted`, `--genui-running`, `--genui-needs-user`, `--genui-error`, `--genui-success`, `--genui-warning` 등 라이트/다크 토큰 완비
- `frontend/src/styles/globals.css`에 **`--genui-*` 변수 전혀 없음**
- 컴포넌트 전체가 `var(--genui-*)` 인라인 CSS 변수를 광범위하게 사용

**결론:** Stage B에서 `frontend/src/styles/globals.css`에 `--genui-*` 토큰 블록을 병합해야 한다. 컴포넌트 복사 전에 반드시 선행.

---

### ⚠️ 특이사항 4: `motion/react` 라이브러리 — 설치 확인 필요

**현황:**
- `PipelineBar.tsx`, `PipelineProgress.tsx`가 `import { motion } from "motion/react"` 사용
- `frontend/package.json`에 `"motion": "*"` 이미 설치됨 ✅
- `motion/react`는 `motion` 패키지의 서브패스 — 별도 설치 불필요

**결론:** 문제 없음. 이미 호환.

---

### ⚠️ 특이사항 5: shadcn/ui 컴포넌트 — genui 컴포넌트는 의존하지 않음

**현황:**
- genui 27종 파일 어디에도 `../ui/button`, `../ui/dialog` 등 shadcn/ui import 없음
- 외부 의존: `lucide-react`, `motion/react`, `react` 전용
- 내부 의존: 동일 폴더의 sibling import(`./CardShell`, `./GenUIChip` 등) — 플랫 배치 유지 시 수정 불필요

**결론:** shadcn/ui 폴더 비교(Stage C 지침)는 `_temp_genui/src/app/components/ui/` 기준으로만 진행. genui 컴포넌트 자체에는 ui/ 의존성 없음.

---

### ⚠️ 특이사항 6: `vite.config.ts`에 `@` alias 이미 설정됨

```ts
// frontend/vite.config.ts (기존)
'@': path.resolve(__dirname, './src'),
```

**결론:** `@/lib/utils`, `@/components/genui/workbench/...` 형태의 alias import를 언제든 사용 가능. Stage B 이후 `cn` import 통일 시 `@/lib/utils` 방식 권장.

---

## 5. 단계별 선행 조건 요약

| Stage | 필수 선행 작업 |
|---|---|
| **Stage B (테마/유틸)** | `frontend/src/lib/utils.ts` 신규 생성, `--genui-*` CSS 토큰을 `globals.css`에 병합, tailwind.config 관련 `@theme` 블록 병합 |
| **Stage C (컴포넌트 이식)** | Stage B 완료 후, `frontend/src/components/genui/workbench/` 디렉토리 생성, 27개 파일 복사 (import 경로 수정 불필요) |
| **Stage D (Mock 머신)** | `Workbench.tsx`를 참조하여 `useWorkbenchStore` 또는 로컬 상태로 5상태 머신 구현 |
| **Stage E (라우트 교체)** | `frontend/src/pages/Chat.tsx`를 신규 WorkbenchPage로 교체, import 경로 2곳 수정 |
| **Stage F/G (정리)** | 기존 `genui/GateBar/`, `genui/Pipeline/`, `genui/Workbench/` 레거시 디렉토리 Deprecate → Delete |

---

*Stage A 완료 — 이 명세서를 기반으로 Stage B부터 순차 진행.*
