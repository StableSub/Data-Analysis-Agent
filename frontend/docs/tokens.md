# tokens.md — Gen-UI Workbench Design Token Spec
> 추출 기준: `/src/styles/theme.css`, `.genui-scope` 범위. 모든 값은 코드 그대로.
> 최종 갱신: P0–P5 전 컴포넌트 반영 완료.

---

## 1. Color Tokens

| 토큰명 | Light | Dark | Tailwind Ref |
|---|---|---|---|
| `--genui-surface` | `#f9fafb` | `#09090b` | zinc-50 / zinc-950 |
| `--genui-panel` | `#ffffff` | `#18181b` | white / zinc-900 |
| `--genui-card` | `#ffffff` | `#27272a` | white / zinc-800 |
| `--genui-border` | `#e4e4e7` | `#27272a` | zinc-200 / zinc-800 |
| `--genui-border-strong` | `#d4d4d8` | `#3f3f46` | zinc-300 / zinc-700 |
| `--genui-text` | `#09090b` | `#fafafa` | zinc-950 / zinc-50 |
| `--genui-muted` | `#71717a` | `#a1a1aa` | zinc-500 / zinc-400 |
| `--genui-focus-ring` | `#3b82f6` | `#60a5fa` | blue-500 / blue-400 |

### 1-A. Status Tokens

| 토큰명 | Light | Dark | Tailwind Ref |
|---|---|---|---|
| `--genui-success` | `#10b981` | `#34d399` | emerald-500 / emerald-400 |
| `--genui-warning` | `#f59e0b` | `#fbbf24` | amber-500 / amber-400 |
| `--genui-error` | `#ef4444` | `#f87171` | red-500 / red-400 |
| `--genui-running` | `#3b82f6` | `#60a5fa` | blue-500 / blue-400 |
| `--genui-needs-user` | `#8b5cf6` | `#a78bfa` | violet-500 / violet-400 |

> `--genui-running`과 `--genui-focus-ring`은 Light에서 동일 값(`#3b82f6`). 의도적 설계.

### 1-B. Shadow Tokens

| 토큰명 | Light | Dark |
|---|---|---|
| `--genui-shadow-sm` | `0 1px 2px 0 rgb(0 0 0 / 0.05)` | `0 1px 2px 0 rgb(0 0 0 / 0.3)` |
| `--genui-shadow-md` | `0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)` | `0 4px 6px -1px rgb(0 0 0 / 0.5)` |

### 1-C. Status 오버레이 패턴 (사용 컴포넌트별)

| 용도 | 값 | 사용처 |
|---|---|---|
| Chip/Badge 배경 | `--genui-{status}/10` | GenUIChip, DecisionChips, StatusBadge, ToolCallListItem |
| Chip/Badge 테두리 | `--genui-{status}/20` | GenUIChip, DecisionChips, ToolCallListItem |
| DecisionChips BLOCKED 테두리 | `--genui-needs-user/25` | DecisionChips |
| GateBar 컨테이너 테두리 | `--genui-needs-user/30` | GateBar |
| PipelineBar progress-line 배경 | `color-mix(in srgb, {color} 18~20%, transparent)` | PipelineBar |
| PipelineTracker active-row 배경 | `--genui-{status}/5~8` + 테두리 `/15~20` | PipelineTracker StepRow |
| AssistantReport error 테두리 | `--genui-error/30` | AssistantReportMessage |
| AssistantReport streaming 테두리 | `--genui-running/40` | AssistantReportMessage |
| AssistantReport needs-user 테두리 | `--genui-needs-user/50` | AssistantReportMessage |
| EvidenceFooter pill hover 테두리 | `--genui-muted/60` | EvidenceFooter Pill |
| MCPPanel server error badge 배경 | `--genui-error/10` 테두리 `/20` | MCPPanel ServerRow |

### 1-D. PipelineBar 전용 색상 매핑 (P0)

| variant | 색상 토큰 | 텍스트 클래스 |
|---|---|---|
| `ingest` | `var(--genui-running)` | `text-[var(--genui-running)]` |
| `running` | `var(--genui-running)` | `text-[var(--genui-running)]` |
| `needs-user` | `var(--genui-needs-user)` | `text-[var(--genui-needs-user)]` |
| `failed` | `var(--genui-error)` | `text-[var(--genui-error)]` |
| `completed` | `var(--genui-success)` | `text-[var(--genui-success)]` |
| `hidden` | `transparent` | — (렌더링 안 함) |

---

## 2. Typography Scale

> font-family (`.genui-scope`): `ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`
> Code/Mono: `font-mono` (system monospace stack)

| 역할 | Size | Line-height | Weight | Letter-spacing | 클래스 |
|---|---|---|---|---|---|
| Display / Gallery H1 | 30px (`text-3xl`) | 1.2 | 700 | — | `text-3xl font-bold` |
| Heading / Section | 18px (`text-lg`) | 1.4 | 600 | — | `text-lg font-semibold` |
| Sub-heading | 14px (`text-sm`) | 1.4 | 600 | — | `text-sm font-semibold` |
| Body | 14px (`text-sm`) | `leading-relaxed` ≈ 1.625 | 400 | — | `text-sm` |
| Body Input | 15px (`text-[15px]`) | `leading-relaxed` | 400 | — | `text-[15px] leading-relaxed` |
| Body Small | 12px (`text-xs`) | 1.5 | 400 | — | `text-xs` |
| Caption / Muted | 10px (`text-[10px]`) | 1.4 | 400-600 | — | `text-[10px] text-[var(--genui-muted)]` |
| Label Small | 11px (`text-[11px]`) | 1.4 | 400 | — | `text-[11px]` |
| PipelineBar text | 11px (`text-[11px]`) | `leading-none` | 600 (stage) / 400 (msg) | — | `text-[11px] font-semibold` / `text-[11px]` |
| DecisionChip label | 10px (`text-[10px]`) | `leading-none` | 600 (value) / 400 (stage) | — | `text-[10px] font-semibold` |
| EvidenceFooter pill | 10px (`text-[10px]`) | `leading-none` | 500 (key) / 600 (value) | — | `text-[10px] font-medium` / `font-semibold` |
| Badge / Chip | 10px | 1 | 600-700 | `tracking-wider` | `text-[10px] font-bold uppercase tracking-widest` |
| PipelineTracker badge | 9px (`text-[9px]`) | `leading-none` | 700 | `tracking-widest` | `text-[9px] font-bold uppercase` |
| Button Primary | 14px (`text-sm`) | 1 | 600 | — | `text-sm font-semibold` |
| Button Secondary | 12px (`text-xs`) | 1 | 500 | — | `text-xs font-medium` |
| Code Block | 11px (`text-[11px]`) | `leading-relaxed` | 400 | — | `text-[11px] font-mono` |
| Brand "HARU" (default) | 14px | 1.15 | 800 | `0.14em` | inline style |
| Brand "HARU" (compact) | 12px | 1 | 800 | `0.12em` | inline style |
| Brand subtitle | 9px | 1.4 | 500 | `0.04~0.06em` | inline style |
| Elapsed (tabular) | 11px (`text-[11px]`) | `leading-none` | 400 | — | `text-[11px] tabular-nums font-mono` |

---

## 3. Layout & Spacing

### 3-A. 전체 레이아웃 (WorkbenchLayout, 1440px 기준)

| 영역 | 크기 | 클래스 |
|---|---|---|
| Header (top bar) | `h-12` = **48px** | `h-12 flex-shrink-0` |
| **Sub-header (3열 통일)** | `h-10` = **40px** | `h-10 flex-shrink-0 border-b` |
| Left Panel (open) | `w-72` = **288px** | `w-72` / `min-w-[18rem]` |
| Left Panel (closed) | `w-0` | animated `transition-all duration-300` |
| Center (max content) | `max-w-3xl` = **768px** | `max-w-3xl mx-auto` |
| Right Panel | `w-[400px]` = **400px** | `w-[400px]`, `hidden xl:flex` |
| Right Panel visibility | xl breakpoint 이상만 표시 | — |
| CommandBar max-width | `max-w-3xl` = **768px** | `max-w-3xl mx-auto px-4 py-4` |
| GateBar max-width | `max-w-md` = **448px** | `max-w-md mx-auto` |
| Top nav bar | `h-10` = **40px** | `h-10 border-b` (App.tsx RootLayout) |

### 3-B. Sub-header h-10 그리드 (P2 통일)

> 3개 컬럼의 서브헤더가 수평으로 정렬되어 동일한 `h-10 = 40px` 높이를 공유.

| 컬럼 | 서브헤더 내용 | 클래스 |
|---|---|---|
| **Left** | `Sparkles` 아이콘 + "History" 라벨 | `h-10 border-b px-4 gap-2 flex items-center` |
| **Center** | `DecisionChips` (Route 라벨 + 최대 5개 칩) | `h-10 border-b px-4 gap-3 flex items-center` |
| **Right** | `Details | Agent` 탭 버튼 2개 (TopTabBtn) | `h-10 border-b px-3 flex items-end` |

### 3-C. Spacing Scale (실사용값)

| Tailwind | px | 사용처 |
|---|---|---|
| `p-1` / `gap-1` | 4px | 아이콘 내부 패딩, 소형 gap |
| `gap-1.5` | 6px | PipelineBar 텍스트 gap, DecisionChips 칩 간격, EvidenceFooter pill 간격 |
| `p-2` / `gap-2` | 8px | 버튼 내부, 인라인 요소 gap |
| `gap-2.5` | 10px | PipelineTracker icon-label gap, CopilotPanel item gap |
| `p-3` / `gap-3` | 12px | GateBar 내부, ToolCallDetail 패딩, PipelineTracker row 패딩 |
| `p-4` / `gap-4` | 16px | 카드 내부, 섹션 패딩, CommandBar 수평 패딩 |
| `p-5` / `gap-5` | 20px | 갤러리 카드, 패널 내부 |
| `p-6` / `gap-6` | 24px | 섹션 간 gap, 큰 카드 패딩 |
| `p-8` / `gap-8` | 32px | 갤러리 페이지 외부 패딩 |
| `space-y-8` | 32px | Center 섹션 간 수직 간격 |
| `pb-32` | 128px | Center content bottom-padding (CommandBar 공간) |
| `pt-8` | 32px | Center content top-padding |

### 3-D. Border Radius Scale (실사용값)

| 클래스 | px | 사용처 |
|---|---|---|
| `rounded` | 4px | 인라인 코드 배경, 키 라벨, Submit 작은 버튼 |
| `rounded-md` | 6px | DecisionChips 칩, EvidenceFooter pill, MCPPanel transport badge, 세그먼트 컨트롤 |
| `rounded-lg` | 8px | PipelineTracker StepRow, ToolCallListItem 행, MCPPanel 로그 엔트리, 갤러리 섹션 카드 |
| `rounded-xl` | 12px | CardShell, Dropzone, AssistantReportMessage, AttachMenuPopover, PipelineBarPreview 모의 헤더 |
| `rounded-2xl` | 16px | GateBar 전체, AttachMenuPopover |
| `rounded-[26px]` | 26px | CommandBar 메인 컨테이너 (pill) |
| `rounded-full` | 9999px | 아바타, 아이콘 버튼, 배지/칩, StatusBadge, MCPPanel 서버 상태 pill |
| `rounded-sm` | 2px | PipelineBar progress-line 끝 처리 |

### 3-E. z-index 계층 (실사용값)

| 레이어 | z-index | 사용처 |
|---|---|---|
| Top nav | `z-50` | App.tsx RootLayout nav bar |
| GateBar + CommandBar | `z-30` | WorkbenchLayout sticky bottom |
| Header | `z-20` | WorkbenchLayout session header |
| Left/Right panels | `z-10` | WorkbenchLayout aside panels |
| CopilotPanel sticky section | `z-10` | CopilotPanel SectionHeader (sticky top) |
| 기본 콘텐츠 | `z-0` / `isolate` | Center main content |

---

## 4. Animation Tokens

| 이름 | 값 | 사용처 |
|---|---|---|
| `animate-pulse` | Tailwind 기본 | StatusBadge, PipelineBar needs-user line, needs-user StageDot, DecisionChips BLOCKED, ToolCallIndicator |
| `animate-spin` | Tailwind 기본 | Loader2 아이콘 (running 상태 전반) |
| `animate-in` | Tailwind animate utilities | GateBar `slide-in-from-bottom-4 duration-300`, 카드 `fade-in zoom-in-95` |
| PipelineBar shimmer | `motion.div` left `-32%` → `132%`, duration 1.8s, easeInOut, repeat Infinity, delay 0.25s | PipelineBar running variant |
| Accordion | `accordion-down 0.2s ease-out` / `accordion-up 0.2s ease-out` | Radix accordion (theme.css) |
| Sidebar transition | `transition-all duration-300 ease-in-out` | WorkbenchLayout left panel |
| Tab crossfade | `transition-opacity duration-200` (abs overlay) | RightPanelTabs |
| Sub-tab crossfade | `transition-opacity duration-150` | RightPanelTabs Agent sub-pane |

---

## 5. Utility Classes (`.genui-scope` 내)

| 클래스명 | 역할 | CSS |
|---|---|---|
| `.genui-scope` | 최상위 스코프 | font-family + color + background |
| `.genui-surface` | 면 배경 | `background: --genui-surface; color: --genui-text` |
| `.genui-panel` | 패널 배경 + 테두리 | `background: --genui-panel; border: 1px solid --genui-border` |
| `.genui-card` | 카드 배경 + 테두리 + radius + shadow | `background: --genui-card; border; border-radius: 0.5rem; box-shadow: --genui-shadow-sm` |
| `.genui-border` | 일반 테두리 색 | `border-color: --genui-border` |
| `.genui-border-strong` | 강조 테두리 색 | `border-color: --genui-border-strong` |
| `.genui-text` | 기본 텍스트 색 | `color: --genui-text` |
| `.genui-muted` | 보조 텍스트 색 | `color: --genui-muted` |
| `.genui-shadow-sm` / `.genui-shadow-md` | 그림자 | `box-shadow: --genui-shadow-{sm,md}` |
| `.genui-focus:focus-visible` | 포커스 링 | `outline: 2px solid --genui-focus-ring; outline-offset: 2px` |
