# components.md — Gen-UI Workbench Component Spec
> 추출 기준: `/src/app/components/genui/` 각 파일. 수치는 Tailwind 환산 px.
> 최종 갱신: P0–P5 전 컴포넌트 반영 완료.

---

## 1. BrandHeader

**파일**: `BrandHeader.tsx`

| Variant | 표시 내용 | 레이아웃 |
|---|---|---|
| `default` | 로고마크(28×28, `rounded-md shadow-sm`) + "HARU" stacked + subtitle | 수직 스택, `gap-2.5` |
| `compact` | 로고마크(20×20, `rounded`) + "HARU" 인라인 + subtitle (sm 이하 `hidden`) | 수평 인라인, `gap-1.5` |

| 속성 | 값 |
|---|---|
| 로고 배경 | `var(--genui-running)` (blue) |
| 로고 내 "H" 색상 | `text-white` |
| "HARU" (default) | 14px, weight 800, `tracking: 0.14em`, `uppercase` |
| "HARU" (compact) | 12px, weight 800, `tracking: 0.12em`, `uppercase` |
| subtitle (default) | 9px, weight 500, `tracking: 0.06em`, `text-muted` |
| subtitle (compact) | 9px, weight 500, `tracking: 0.04em`, `hidden sm:inline` |

---

## 2. WorkbenchLayout

**파일**: `WorkbenchLayout.tsx`

### Props

| Prop | Type | 설명 |
|---|---|---|
| `header` | `ReactNode` | h-12 세션 헤더 내 좌측 콘텐츠 |
| `pipelineBar` | `ReactNode` | h-12 세션 헤더 내 절대 위치 (P0) |
| `leftPanel` | `ReactNode` | 좌측 History 패널 |
| `centerSubHeader` | `ReactNode` | 중앙 h-10 서브헤더 (DecisionChips 등, P2) |
| `mainContent` | `ReactNode` | 중앙 스크롤 영역 |
| `rightPanel` | `ReactNode` | 우측 패널 (RightPanelTabs) |
| `bottomBar` | `ReactNode` | 하단 CommandBar |
| `gateBar` | `ReactNode` | 하단 GateBar (needs-user 전용) |

### Sub-header 높이 토큰

```ts
const SUB_H = "h-10"; // 40px — Left History / Center Route / Right Tabs 3열 통일
```

### HistoryToggle (헤더 내 버튼)

| 속성 | 값 |
|---|---|
| 크기 | `w-12 h-full` = 48×48px |
| 아이콘 | `SidebarClose`(open) / `SidebarOpen`(closed), `w-5 h-5` |
| 배경 hover | `--genui-surface` |
| 테두리 | 우측 `border-r --genui-border` |

### HistoryPanel (Left Aside)

| 속성 | 값 |
|---|---|
| width open | `w-72` = 288px, `min-w-[18rem]` |
| width closed | `w-0`, `opacity-0`, `border-r-0` |
| 트랜지션 | `transition-all duration-300 ease-in-out` |
| 배경 | `--genui-panel` |
| 그림자 | `shadow-sm` |
| z-index | `z-10` |

### Center Main

| 속성 | 값 |
|---|---|
| 서브헤더 | `h-10 border-b bg-panel px-4 gap-3` (항상 렌더 — 그리드 안정성) |
| 스크롤 영역 | `flex-1 overflow-y-auto p-4 scroll-smooth` |
| Sticky bottom | `flex-shrink-0 sticky bottom-0 z-30` |
| GateBar 래퍼 | `pb-2 px-4 animate-in slide-in-from-bottom-4` |
| CommandBar 래퍼 | `bg-surface/80 backdrop-blur-md border-t shadow` |

### Right Aside

| 속성 | 값 |
|---|---|
| width | `w-[400px]` |
| 가시성 | `hidden xl:flex` |
| z-index | `z-10` |

---

## 3. P0 — PipelineBar (세션 헤더 진행 표시)

**파일**: `PipelineBar.tsx`

### Variants

| variant | 진행 바 | 진행 너비 | 애니메이션 | 렌더 |
|---|---|---|---|---|
| `hidden` | — | — | — | `null` |
| `ingest` | determinate | `0~100%` (prop `percent`) | `transition-all duration-300` | 표시 |
| `running` | indeterminate shimmer | `w-[32%]` 왕복 | `motion.div` 1.8s easeInOut infinite | 표시 |
| `needs-user` | 고정 | `60%` | `animate-pulse` | 표시 |
| `failed` | 고정 | `28%` | 없음 | 표시 |
| `completed` | — | — | — | progress line 없음 (TextStrip만) |

### ProgressLine 치수

| 속성 | 값 |
|---|---|
| 위치 | `absolute bottom-0 left-0 right-0` (parent `<header>` 내부) |
| 높이 | `h-[3px]` |
| 트랙 배경 | `color-mix(in srgb, {color} 18~20%, transparent)` |
| 채움 끝 | `rounded-r-sm` |

### TextStrip

| 속성 | 값 |
|---|---|
| 위치 | `absolute top-0 bottom-[3px] right-4 xl:right-[420px]` |
| 콘텐츠 순서 | `StageDot` · `stage label` · `message` · `stepFraction` · `elapsed` · `"View details →"` |
| 구분자 | `·` (`text-border-strong`), pipe `|` (View details 앞) |
| StageDot | `w-1.5 h-1.5 rounded-full`, running/needs-user: `animate-pulse`, completed: 숨김 |
| stage label | `text-[11px] font-semibold leading-none` + variant별 색상 |
| message | `text-[11px] text-muted max-w-[180px] truncate` |
| stepFraction | `text-[11px] text-muted tabular-nums` |
| elapsed | `text-[11px] text-muted tabular-nums font-mono` |
| View details 링크 | `text-[11px] font-medium` + `ArrowRight w-2.5`, `opacity-70 hover:opacity-100` |
| View details 조건 | running / needs-user / failed + `onViewDetails` 존재 시 |

### Props

```ts
interface PipelineBarProps {
  variant: "hidden" | "ingest" | "running" | "needs-user" | "failed" | "completed";
  stage?: PipelineStage | string;  // "Ingest" | "Preprocess" | "RAG" | ...
  message?: string;
  stepFraction?: string;           // "2/6"
  elapsed?: string;                // "00:21"
  percent?: number;                // 0–100 (ingest only)
  onViewDetails?: () => void;      // nav only (SSOT)
}
```

### PipelineBarPreview (Gallery 전용)

| 속성 | 값 |
|---|---|
| 모의 헤더 | `h-12 rounded-xl border bg-panel overflow-hidden` |
| 세션 타이틀 | `text-sm font-semibold` (mock) |
| 인라인 텍스트 | PreviewTextRow (absolute 대신 flow 레이아웃) |

---

## 4. P1 — PipelineTracker (6-step 세로 트래커)

**파일**: `PipelineTracker.tsx`

### PipelineStep 타입

```ts
interface PipelineStep {
  id: string;
  label: string;              // "Intake" | "Preprocess" | "RAG" | "Visualization" | "Merge" | "Report"
  sublabel?: string;          // "Scanning missing values…"
  status: PipelineStepStatus; // "queued" | "running" | "success" | "failed" | "needs-user"
  toolCount?: number;
}
```

### StepIcon (status별)

| status | 컨테이너 | 아이콘 |
|---|---|---|
| `queued` | `w-5 h-5 rounded-full border-2 border-border bg-surface` | `Clock w-2.5 h-2.5 text-muted` |
| `running` | `w-5 h-5 rounded-full bg-running/15 border-running/30` | `Loader2 w-3 h-3 text-running animate-spin` |
| `success` | `w-5 h-5 rounded-full bg-success/15 border-success/30` | `CheckCircle2 w-3 h-3 text-success` |
| `failed` | `w-5 h-5 rounded-full bg-error/15 border-error/30` | `XCircle w-3 h-3 text-error` |
| `needs-user` | `w-5 h-5 rounded-full bg-needs-user/15 border-needs-user/40 animate-pulse` | `ShieldCheck w-3 h-3 text-needs-user` |

### StepRow 레이아웃

| 속성 | 값 |
|---|---|
| 패딩 | `px-3 py-2` |
| radius | `rounded-lg` |
| gap | `gap-3` (icon ↔ label) |
| 라벨 font | `text-xs font-semibold leading-tight` |
| sublabel font | `text-[10px] leading-snug mt-0.5` |
| active 행 (running) | `bg-running/5 border border-running/15` |
| active 행 (needs-user) | `bg-needs-user/8 border border-needs-user/20` |
| active 행 (failed) | `bg-error/5 border border-error/15` |
| inactive 행 hover | `hover:bg-surface` |
| 배지 | `text-[9px] font-bold px-1.5 py-px rounded border uppercase tracking-widest` |
| toolCount | `text-[9px] text-muted tabular-nums` ("N calls", success 시만) |

### Connector (step 간)

| 속성 | 값 |
|---|---|
| 너비 | `w-px` |
| 높이 | `h-4` |
| active (fromStatus=success) | `bg-success/40` |
| inactive | `bg-border` |
| 위치 | `ml-2.5` (아이콘 중심 정렬) |

### STATUS_BADGE 매핑

| status | label | 색상 조합 |
|---|---|---|
| `queued` | — (표시 안 함) | — |
| `running` | "Running" | `bg-running/10 text-running border-running/20` |
| `success` | "Done" | `bg-success/10 text-success border-success/20` |
| `failed` | "Failed" | `bg-error/10 text-error border-error/20` |
| `needs-user` | "Awaiting" | `bg-needs-user/10 text-needs-user border-needs-user/20` |

---

## 5. P2 — DecisionChips (읽기 전용 라우팅 상태 태그)

**파일**: `DecisionChips.tsx`

### ChipValue 열거

```ts
type ChipValue =
  | "ON" | "SKIP" | "BLOCKED" | "FAILED" | "OFF"
  | "DONE" | "QUEUED" | "RUNNING"
  | "Full" | "Quick QA";
```

### 칩 스타일 매핑

| value | 아이콘 | 배경/텍스트/테두리 |
|---|---|---|
| `ON` | `CheckCircle2 text-success` | `bg-panel text-text border-border` |
| `DONE` | `CheckCircle2` | `bg-success/8 text-success border-success/20` |
| `RUNNING` | `Loader2 animate-spin` | `bg-running/8 text-running border-running/20` |
| `BLOCKED` | `ShieldAlert animate-pulse` | `bg-needs-user/10 text-needs-user border-needs-user/25` |
| `FAILED` | `XCircle` | `bg-error/8 text-error border-error/20` |
| `SKIP` | `MinusCircle opacity-60` | `bg-surface text-muted border-border` |
| `OFF` | `Circle opacity-40` | `bg-surface text-muted border-border opacity-50` |
| `QUEUED` | `Circle opacity-30` | `bg-surface text-muted border-border` |
| `Full` | — | `bg-panel text-text border-border` |
| `Quick QA` | — | `bg-panel text-text border-border` |

### Chip 레이아웃

| 속성 | 값 |
|---|---|
| 패딩 | `px-2 py-1` |
| radius | `rounded-md` |
| 포맷 | `[icon] Stage · VALUE [→]` |
| Stage 텍스트 | `text-muted font-normal` |
| Value 텍스트 | `font-semibold` (ChipValue 색상) |
| 아이콘 크기 | `w-2.5 h-2.5` |
| Nav arrow | `ArrowRight w-2 h-2 opacity-30` (onNavigate 존재 시) |
| Tooltip | native `title` (defaultTooltip 함수 + nav suffix) |
| Click | `onNavigate` → nav only (SSOT: no Approve/Reject) |
| cursor | navigable: `cursor-pointer hover:opacity-80`, readonly: `cursor-default` |
| focus | `focus-visible:outline-2 focus-visible:outline-[--genui-focus-ring]` |

### DecisionChips 컨테이너

| 속성 | 값 |
|---|---|
| 최대 칩 수 | 5개 (`.slice(0,5)`) |
| overflow | `+N` 표시 (5개 초과 시) |
| "Route" 라벨 | `text-[9px] font-bold uppercase tracking-widest text-muted pr-1 border-r` |
| gap | `gap-1.5` (칩 간), `gap-2` (라벨 ↔ 칩) |

---

## 6. P3 — EvidenceFooter (4-pill 근거 표기)

**파일**: `EvidenceFooter.tsx`

### 고정 순서 4 pills

| 순서 | 아이콘 | Key | Prop | 기본값 |
|---|---|---|---|---|
| 1 | `Database w-2.5` | Data | `data` | `"-"` |
| 2 | `Table2 w-2.5` | Scope | `scope` | `"-"` |
| 3 | `Cpu w-2.5` | Compute | `compute` | `"-"` |
| 4 | `BookOpen w-2.5` | RAG | `rag` | `"OFF"` |

### Pill 레이아웃

| 속성 | 값 |
|---|---|
| 패딩 | `px-2 py-0.5` |
| radius | `rounded-md` |
| 배경 | `bg-surface border-border` |
| 포맷 | `[icon] Key · value [→]` |
| Key 텍스트 | `text-muted font-medium` |
| Value 텍스트 | `text-text font-semibold truncate max-w-[9rem]` |
| Nav arrow | `ArrowRight w-2 h-2 text-muted opacity-30` (onNavigate 시) |
| hover (nav) | `hover:border-muted/60 hover:bg-panel` |
| cursor | navigable: `cursor-pointer`, readonly: `cursor-default` |
| Tooltip | native `title` (Key: value + nav suffix) |

### 컨테이너

| 속성 | 값 |
|---|---|
| 레이아웃 | `flex items-center gap-1.5 overflow-x-auto` |
| scrollbar | `scrollbar-width: none` (CSS) |
| 위치 | AssistantReportMessage 푸터 내 / 에러 variant 내 |

### Nav 콜백 (SSOT)

| Pill | 네비게이션 대상 |
|---|---|
| Data / Scope | → Details 패널 (데이터 프로필) |
| Compute / RAG | → Agent > Tools (실행 상태 / tool call) |

---

## 7. P4 — Milestone Log (좌측 History)

**구현 위치**: `Workbench.tsx` 인라인 + `TimelineItem.tsx`

### TimelineItem

**파일**: `TimelineItem.tsx`

| status | 아이콘 | 색상 |
|---|---|---|
| `normal` | `Circle w-3 h-3` | `text-muted` |
| `running` | `Loader2 w-4 h-4 animate-spin` | `text-running` |
| `completed` | `CheckCircle2 w-4 h-4` | `text-success` |
| `failed` | `AlertCircle w-4 h-4` | `text-error` |
| `needs-user` | `PlayCircle w-4 h-4 animate-pulse` | `text-needs-user` |

| 속성 | 값 |
|---|---|
| 행 패딩 | `p-3` |
| radius | `rounded-lg` |
| gap | `gap-3` |
| 선택 배경 | `bg-panel border border-border shadow-sm` |
| hover 배경 | `hover:bg-surface hover:border-border` |
| title font | `text-sm font-medium leading-tight` |
| subtext font | `text-xs text-muted truncate` |
| timestamp font | `text-[10px] text-muted opacity-70 group-hover:opacity-100` |
| statusBadge | `text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded border` |
| statusBadge 색 (failed) | `bg-error/10 text-error border-error/20` |
| statusBadge 색 (needs-user) | `bg-needs-user/10 text-needs-user border-needs-user/20` |
| nav hint (hover) | `"→ View in Details"`, `text-[10px] text-muted opacity-0 group-hover:opacity-100` |
| 클릭 동작 | `onClick` → nav only (SSOT: focusDetails) |

### Milestone 데이터 매핑 (state별)

| state | 마일스톤 항목 |
|---|---|
| `running` | Upload complete → Preprocess plan ready → **Preprocess running** (selected, running) |
| `needs-user` | Upload complete → Missing values detected → **Approval required** (selected, needs-user) |
| `error` | Upload complete → Missing values detected → RAG retrieved → **Visualization failed** (selected, failed) |
| `empty` / `uploading` | skeleton placeholder 또는 uploading TimelineItem |

---

## 8. P5 — MCPPanel (Raw Stream / Logs 아코디언)

**파일**: `MCPPanel.tsx`

### 전체 구조

| 섹션 | 기본 상태 | 내용 |
|---|---|---|
| **Summary Bar** | 항상 표시 | connected/offline/error 카운트 + total tools |
| **Servers** | open | MCPServer 목록 (collapsible) |
| **Recent Actions** | open | MCPAction 목록 (collapsible) |
| **Raw Stream / Logs** | **closed** (개발자 전용) | RawLogEntry 아코디언 (collapsible) |
| **Developer Note** | 항상 표시 | 안내 카드 |

### MCPServer 타입

```ts
interface MCPServer {
  id: string;
  name: string;
  transport: "stdio" | "http" | "sse";
  status: "connected" | "disconnected" | "error";
  toolCount?: number;
  latencyMs?: number;
}
```

### ServerRow 치수

| 속성 | 값 |
|---|---|
| 행 패딩 | `px-3 py-2.5` |
| radius | `rounded-lg` |
| name font | `text-xs font-semibold font-mono truncate` |
| transport badge | `text-[10px] bg-surface border-border px-1 rounded` |
| toolCount | `text-[10px] text-muted` |
| latency | `text-[10px] tabular-nums text-muted` (connected 시) |
| status dot | `w-2 h-2 rounded-full`, connected: `bg-success animate-pulse` |
| status pill | `text-[10px] font-medium px-1.5 py-0.5 rounded-full border` |

### MCPAction 타입 & ActionRow

```ts
interface MCPAction {
  id: string; serverName: string; tool: string;
  status: "success" | "failed" | "running";
  timestamp: string; durationMs?: number;
}
```

| 속성 | 값 |
|---|---|
| 아이콘 | success: `CheckCircle2`, failed: `XCircle`, running: `Loader2 animate-spin` |
| tool font | `text-[11px] font-mono truncate` |
| serverName | `text-[10px] text-muted` |
| timestamp/duration | `text-[10px] tabular-nums text-muted` |

### RawLogEntry & RawLogRow

```ts
interface RawLogEntry {
  id: string;
  label: string;
  payload: string;    // JSON (pretty-printed)
  isError?: boolean;
}
```

| 속성 | 값 |
|---|---|
| 컨테이너 | `border rounded-lg overflow-hidden mx-1 mb-1` |
| header 아이콘 | normal: `Terminal w-3`, error: `AlertTriangle w-3 text-error` |
| label font | `text-[10px] font-mono truncate` |
| label 색 (error) | `text-error` |
| payload | `pre text-[10px] font-mono leading-relaxed max-h-40 overflow-y-auto` |
| Copy 버튼 | `text-[9px]`, copied: `Check text-success + "Copied"` |
| 토글 | `ChevronDown/Up w-3` |

### SectionHeader (공통)

| 속성 | 값 |
|---|---|
| 아이콘 | `Server` / `Activity` / `Terminal` (`w-3 h-3`) |
| 라벨 | `text-[10px] font-bold uppercase tracking-widest text-muted` |
| count badge | `text-[10px] font-bold bg-panel border px-1.5 py-0.5 rounded tabular-nums` |
| error dot | `w-1.5 h-1.5 rounded-full bg-error border-panel` (Raw Logs, 에러 있고 닫힌 상태) |

### Summary Bar

| 속성 | 값 |
|---|---|
| 패딩 | `px-3 py-2.5` |
| 배경 | `bg-panel border-b` |
| dot 크기 | `w-1.5 h-1.5 rounded-full` |
| total tools | `Zap w-3 text-muted` + `text-[10px] tabular-nums` |

### 기본 Mock 데이터

```
Servers: filesystem(stdio/connected/8tools/2ms), brave-search(http/connected/3/94ms),
         postgres-mcp(stdio/disconnected/12), puppeteer(stdio/error/6)
Actions: read_file(success/8ms), web_search(success/423ms),
         write_file(running), query(failed/34ms)
```

### RawLogs (상태별)

| 상태 | 엔트리 |
|---|---|
| Running | `tool_call: detect_missing` + `tool_result: detect_missing` |
| Error | Running 로그 + `tool_call: cast_dtype` + `tool_error: cast_dtype` (isError) |

---

## 9. RightPanelTabs

**파일**: `RightPanelTabs.tsx`

| 탭 ID | 라벨 | 내용 |
|---|---|---|
| `details` | "Details" | DetailsPanel |
| `agent` | "Agent" | 내부 sub-tab (Tools / MCP) |

### TopTabBtn

| 속성 | 값 |
|---|---|
| 탭 바 높이 | `h-10` = 40px (3열 서브헤더 통일) |
| 패딩 | `px-4 py-3` |
| active 색 | `text-text border-b-2 border-text` |
| inactive 색 | `text-muted border-b-2 border-transparent` |
| NEW dot | `w-1.5 h-1.5 rounded-full bg-running animate-pulse` |
| NEW dot 조건 | `agentHasNew && activeTab !== "agent"` |

### AgentSegmentedControl (sub-tab)

| 속성 | 값 |
|---|---|
| 위치 | Agent 탭 활성 시 탭바 바로 아래 |
| 컨테이너 | `px-3 py-2 border-b bg-panel` |
| 토글 배경 | `bg-surface border rounded-md p-0.5 w-full` |
| active 아이템 | `bg-panel shadow-sm text-text` |
| inactive 아이템 | `text-muted hover:text-text` |
| 탭 라벨 | `text-[11px] font-semibold` |
| MCP 신규 dot | `w-1 h-1 rounded-full bg-running animate-pulse absolute top-1 right-1` |

---

## 10. WorkbenchCommandBar

**파일**: `WorkbenchCommandBar.tsx`

### Variants

| status | 변화 |
|---|---|
| `idle` | 기본, Send 비활성(빈 textarea), 입력 가능 |
| `focused` | `ring-1 ring-focus-ring/50`, `shadow-lg`, `border-focus-ring` |
| `streaming` | Stop(■) 버튼 표시 |
| `disabled` | `opacity-60 cursor-not-allowed bg-surface border-dashed` |
| `empty` | idle과 동일 UI, placeholder 변경 |

### 치수

| 속성 | 값 |
|---|---|
| 컨테이너 | `max-w-3xl mx-auto`, `rounded-[26px]`, `bg-panel` |
| textarea | `px-4 pt-4 pb-2`, `text-[15px] leading-relaxed`, `max-h-[200px] min-h-[24px]` |
| Send/Stop 버튼 | `w-8 h-8 rounded-full` |
| Toolbar | `px-3 pb-3 pt-1` |

### Toolbar 구성 (좌→우)

| 위치 | 요소 |
|---|---|
| 좌 ① | `+` AttachMenu (`Plus w-5 p-2 rounded-full`) |
| 좌 ② | Model Selector (`Sparkles + 모델명 + ChevronDown`, `px-3 py-1.5 rounded-full text-xs`) |
| 우 ① | Mic (`w-5 p-2`, value 없고 !streaming 시) |
| 우 ② | Send(`SendHorizontal`) 또는 Stop(`Square`) |

### placeholder (state별)

| state | placeholder |
|---|---|
| `empty` | `"Upload a dataset or ask a question..."` |
| `needs-user` | `"Agent is waiting for approval..."` |
| `error` | `"Type to discuss the error..."` |
| 기타 | `"Ask Gen-UI to analyze, visualize, or transform..."` |

---

## 11. AttachMenuPopover

**파일**: `AttachMenuPopover.tsx`

| 속성 | 값 |
|---|---|
| 위치 | `+` 버튼 위 (`bottom-full mb-3`) |
| width | `w-72` = 288px |
| radius | `rounded-2xl` |
| 배경 | `bg-surface border-border shadow-2xl` |
| 진입 애니메이션 | `fade-in slide-in-from-bottom-2 duration-200` |
| 아이콘 박스 | `w-9 h-9 rounded-lg bg-panel border` |

### 메뉴 아이템 (3개)

| 순서 | 라벨 | 아이콘 | 설명 |
|---|---|---|---|
| 1 | `Upload dataset` | `Upload` | CSV, JSON, Excel (.xlsx) |
| 2 | `Add photos & files` | `ImageIcon` | PNG, JPG, PDF, DOCX |
| 3 | `Use sample dataset` | `Database` | Try with Q3 Sales data |

---

## 12. HITLGateBar

**파일**: `GateBar.tsx`

### 치수

| 속성 | 값 |
|---|---|
| max-width | `max-w-md` = 448px |
| padding | `p-3` |
| gap | `gap-2` (flex-col) |
| radius | `rounded-2xl` |
| 배경 | `bg-surface/95 backdrop-blur-md` |
| border | `border-needs-user/30` |
| shadow | `shadow-xl` |
| 진입 | `animate-in slide-in-from-bottom-4 duration-300` |

### 버튼 스펙

| 버튼 | 라벨 | 스타일 | 패딩 | radius |
|---|---|---|---|---|
| Approve | `"Approve & Continue"` | `bg-needs-user text-white font-semibold` | `px-4 py-3` | `rounded-xl` |
| Reject | `"Reject"` | `bg-surface border text-error hover:bg-error/5` | `px-4 py-2.5` | `rounded-xl` |
| Modify (collapsed) | `"Modify with instructions..."` | ghost, `text-muted` | `px-4 py-2.5` | `rounded-xl` |
| Submit | `"Submit"` | `bg-text text-surface disabled:opacity-50` | `px-3 py-1` | `rounded` |

### SSOT 규칙

- `Approve / Reject / Submit` CTA는 **GateBar에만** 존재
- Center/History에는 **결정 CTA 없음**

---

## 13. AssistantReportMessage

**파일**: `AssistantReportMessage.tsx`

### Variants

| variant | 테두리 | 상태 pill | CTA |
|---|---|---|---|
| `streaming` | `border-running/40` | "Generating..." (blue pulse) | 없음 |
| `final` | `border-border` | "Final" (green) | Expand/Collapse (선택) |
| `final` + `accentVariant="needs-user"` | `border-needs-user/50` | "Final" | Expand/Collapse |
| `error` | `border-error/30` | "Needs Resolution" (red badge) | `onReviewDetails` 링크 OR `onRetry` 버튼 (SSOT) |

### Evidence 통합 (P3)

- `evidence?: EvidenceFooterProps` prop
- **final variant**: 푸터 우측에 EvidenceFooter 렌더
- **error variant**: 에러 메시지 아래 `border-t` 구분선 후 렌더
- **streaming variant**: evidence 미표시 (context 미완성)

### 치수

| 속성 | 값 |
|---|---|
| 최대 너비 | `max-w-[860px]` |
| radius | `rounded-xl` |
| 배경 | `bg-card` |
| Bot 아바타 | `w-7 h-7 rounded-full bg-running text-white` |
| 바디 max-height | prop `maxBodyHeight`, 기본 320px |
| 스크롤 fade | `h-10` gradient `transparent → card` |
| 스트리밍 커서 | `w-[7px] h-[14px] bg-text animate-pulse rounded-[1px]` |

### Error variant 전용

| 요소 | 값 |
|---|---|
| 아이콘 | `AlertTriangle w-5 text-error` |
| badge | `"Needs Resolution"`, `bg-error/8 border-error/30` |
| 네비 링크 | `"Review in Details →"` (center — SSOT) |
| Retry CTA | `"Confirm & Retry"` + `RefreshCw` (Details panel 전용 — SSOT) |

---

## 14. CopilotPanel (Agent > Tools)

**파일**: `CopilotPanel.tsx`

### 구조

| 섹션 | 내용 |
|---|---|
| RunStatus | Phase/Elapsed 2-col grid + progress bar + last tool |
| AwaitingCard | needs-user 상태 시 — nav link only (SSOT) |
| Pipeline (P1) | PipelineTracker 6-step 세로 트래커 (collapsible) |
| Tool Calls | ToolCallListItem 목록 + FilterToggle(All/Latest/Errors) |
| ToolCallDetail | 선택된 item args/result 표시 (slide-in) |

### FilterToggle

| 탭 | 내용 |
|---|---|
| `all` | running/needs-user 상단 고정, 나머지 시간순 |
| `latest` | 마지막 4개 시간순 |
| `errors` | failed + needs-user만 |

### AwaitingCard (SSOT)

| 속성 | 값 |
|---|---|
| 컨테이너 | `mx-3 my-2 rounded-xl border-needs-user/30 bg-needs-user/6 px-3 py-2.5` |
| 라벨 | "Awaiting Decision" (`text-[10px] font-bold uppercase`) |
| nav 링크 | "View in Details" + `ArrowRight` (SSOT: no Approve/Reject) |

---

## 15. DetailsPanel (Right)

**파일**: `DetailsPanel.tsx`

### 상태별 렌더

| state | 내용 |
|---|---|
| `empty` | Getting Started 3-step + Example Artifacts 스켈레톤 2개 |
| `uploading` | File Details + Cancel 버튼 |
| `streaming` | Selected Artifact 카드 (Revenue Analysis) + Download/View Data 버튼 |
| `needs-user` | "Decision Required" 헤더 + ApprovalCard(hideActions=true) |
| `error` | "Resolution Required" + Error Cause + Resolution 라디오 옵션 + **Confirm & Retry 버튼** (SSOT) |

---

## 16. StatusBadge

**파일**: `StatusBadge.tsx`

| status | label | 색상 |
|---|---|---|
| `empty` | "No Dataset" | `bg-muted/20 text-muted border-border` |
| `uploading` | "Uploading..." | `bg-running/10 text-running border-running/20` |
| `running` | "Running" | `bg-running text-white border-transparent` + pulse dot |
| `needs-user` | "Needs Approval" | `bg-needs-user text-white border-transparent animate-pulse` |
| `error` | "Error" | `bg-error/10 text-error border-error/20` |
| `success` | "Ready" | `bg-success/10 text-success border-success/20` |

치수: `px-2.5 py-0.5 rounded-full text-xs font-medium border shadow-sm`

---

## 17. CardShell / CardHeader / CardBody / CardFooter

**파일**: `CardShell.tsx`

| status | 테두리 |
|---|---|
| `default` | `border-border hover:border-border-strong` |
| `running` | `border-running shadow-md` |
| `needs-user` | `border-needs-user shadow-md` |
| `error` | `border-error shadow-sm` |
| `success` | `border-success shadow-sm` |

| 하위 | 패딩 |
|---|---|
| CardHeader | `px-4 py-3 border-b bg-surface/50` |
| CardBody | `p-4 text-sm flex-1 overflow-auto` |
| CardFooter | `px-4 py-3 border-t bg-surface/30` |

---

## 18. GenUIChip

**파일**: `GenUIChip.tsx`

| variant | 색상 |
|---|---|
| `neutral` | `bg-surface border-border text-text` |
| `running` | `bg-running/10 border-running/20 text-running` |
| `success` | `bg-success/10 border-success/20 text-success` |
| `warning` | `bg-warning/10 border-warning/20 text-warning` |
| `error` | `bg-error/10 border-error/20 text-error` |
| `needs-user` | `bg-needs-user/10 border-needs-user/20 text-needs-user` |

치수: `px-2 py-0.5 rounded-full text-xs font-medium border`

---

## 19. ToolCallIndicator (compact)

**파일**: `ToolCallIndicator.tsx`

| status | 아이콘 | 추가 |
|---|---|---|
| `running` | `Loader2 animate-spin` (`running`) | — |
| `completed` | `Check` (`success`) | — |
| `failed` | `X` (`error`) | — |
| `needs-user` | `ShieldCheck animate-pulse` (`needs-user`) | "Awaiting" badge animate-pulse |

Props: `status`, `label`, `sublabel?`

---

## 20. ToolCallListItem

**파일**: `ToolCallListItem.tsx`

| 속성 | 값 |
|---|---|
| 패딩 | `px-3 py-2.5` |
| radius | `rounded-lg` |
| tool name | `text-xs font-mono font-semibold` |
| args | `text-[10px] font-mono text-muted truncate` |
| 선택 상태 | `bg-panel border-border shadow-sm` + `ChevronRight w-3` |
| duration | `text-[10px] tabular-nums text-muted` |

---

## 21. Dropzone

**파일**: `Dropzone.tsx`

### idle 상태

| 속성 | 값 |
|---|---|
| border | `border-2 border-dashed border-border hover:border-border-strong` |
| radius | `rounded-xl` |
| 아이콘 | `UploadCloud w-8 h-8`, 박스 `w-16 h-16 rounded-2xl` |
| Primary CTA | "Upload Dataset" `bg-text text-panel py-2.5 rounded-lg` |
| Secondary CTA | "Try Sample Dataset" `bg-panel border py-2 rounded-lg` |
| Tertiary | "Start from Template" text-only |

### uploading 상태

| 속성 | 값 |
|---|---|
| progress bar | `h-2 rounded-full bg-surface`, fill `bg-running` |
| Cancel 버튼 | text-only `text-muted` |

---

## 22. StreamingText / Skeletons / PipelineProgress

| 컴포넌트 | 파일 | 역할 |
|---|---|---|
| `StreamingText` | `StreamingText.tsx` | 타이핑 효과 + `w-1.5 h-4 bg-running animate-pulse` 커서 |
| `SkeletonLine` | `Skeletons.tsx` | `h-4 bg-surface animate-pulse rounded`, width prop |
| `SkeletonCard` | `Skeletons.tsx` | avatar + 3× SkeletonLine |
| `PipelineProgress` | `PipelineProgress.tsx` | `h-2 rounded-full`, `motion.div` 너비 애니메이션, status 색상 매핑 |
