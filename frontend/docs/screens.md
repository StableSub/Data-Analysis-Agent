# screens.md — Gen-UI Workbench Screen States
> 추출 기준: `Workbench.tsx` 실제 렌더 조건. 5개 상태별 레이아웃 매핑.
> 최종 갱신: P0–P5 전 컴포넌트 반영 완료.

---

## 레이아웃 구조 (공통)

```
┌─────────────────────────────────────────────────────────────────┐
│ Header (h-12 = 48px): HistoryToggle │ Session + StatusBadge     │
│                        PipelineBar (P0, absolute)               │
├───────────┬────────────────────────────────┬────────────────────┤
│ Left h-10 │ Center h-10 (Sub-header)       │ Right h-10         │
│ "History" │ DecisionChips (P2)             │ Details | Agent    │
├───────────┼────────────────────────────────┼────────────────────┤
│  Left     │  Center (main)                 │  Right             │
│  w-72     │  flex-1                        │  w-[400px]         │
│  (288px)  │  max-w-3xl content             │  xl:flex           │
│           │  + EvidenceFooter (P3)         │                    │
│  Milestone│  + AssistantReportMessage       │  RightPanelTabs    │
│  Log (P4) │                                │  Details | Agent   │
│  (scroll) │  (scroll)                      │  Tools(P1) | MCP(P5)│
│           ├────────────────────────────────┤                    │
│           │ [GateBar — floating, needs-user]│                    │
│           ├────────────────────────────────┤                    │
│           │ CommandBar (sticky)            │                    │
└───────────┴────────────────────────────────┴────────────────────┘
```

### h-10 서브헤더 3열 그리드 (P2 통일)

| 컬럼 | 내용 | 비고 |
|---|---|---|
| Left | `Sparkles` + "History" | 항상 렌더 |
| Center | `DecisionChips` (Route 라벨 + 최대 5개 칩) | 빈 상태: 빈 row (그리드 안정성) |
| Right | Details \| Agent 탭 바 | 항상 렌더 |

### 스크롤 영역 정의

| 영역 | 스크롤 |
|---|---|
| Left (History) | `flex-1 overflow-y-auto` — 내부만 |
| Center (Content) | `flex-1 overflow-y-auto p-4 scroll-smooth` — 내부만 |
| Right (Panel body) | `flex-1 overflow-y-auto` — 탭 바/세그먼트 컨트롤 고정 |
| AssistantReportMessage 바디 | `overflow-y-auto max-h-{maxBodyHeight}px` — 카드 내부 독립 |
| ToolCallDetail | `max-h-52 overflow-y-auto` — CopilotPanel 내부 |
| MCPPanel Raw Logs | `max-h-40 overflow-y-auto` — 개별 payload |
| GateBar + CommandBar | `flex-shrink-0 sticky bottom-0 z-30` — 스크롤 안 됨 |

---

## Screen 1 — Empty

**진입 조건**: `state === "empty"` (초기 상태)

| 영역 | 컴포넌트 인스턴스 | 비고 |
|---|---|---|
| **Header** | `HistoryToggle` + `"New Session"` + `StatusBadge(empty)` | "No Dataset" |
| **PipelineBar (P0)** | `variant="hidden"` | 렌더 안 함 |
| **Left h-10** | "History" 라벨 | — |
| **Left body** | skeleton 플레이스홀더 2줄 | 아이템 없음 |
| **Center h-10** | 빈 row (DecisionChips 없음) | 그리드 안정성 유지 |
| **Center body** | `Dropzone(status="idle")` | `min-h-[50vh]` 세로 중앙 |
| **Right h-10** | Details \| Agent 탭 바 | — |
| **Right body** | Details 탭 → `DetailsPanel(state="empty")` | Getting Started + Example Artifacts |
| **Bottom** | `WorkbenchCommandBar(status="empty")` | placeholder: "Upload a dataset or ask a question..." |
| **GateBar** | `null` | — |

### CTA 위치 (SSOT)

| CTA | 위치 |
|---|---|
| "Upload Dataset" | Center Dropzone |
| "Try Sample Dataset" | Center Dropzone |
| "Start from Template" | Center Dropzone (tertiary) |

---

## Screen 2 — Uploading

**진입 조건**: `state === "uploading"` → 자동 → Running (약 2.5초)

| 영역 | 컴포넌트 인스턴스 | 비고 |
|---|---|---|
| **Header** | `"New Session"` + `StatusBadge(uploading)` | "Uploading..." |
| **PipelineBar (P0)** | `variant="ingest"`, `percent={uploadProgress}`, `stage="Ingest"`, `message="Parsing file..."`, `stepFraction="1/6"`, `elapsed={formatElapsed}` | determinate 0→100%, 색상 `--genui-running` |
| **Left h-10** | "History" 라벨 | — |
| **Left body** | `TimelineItem(running, "Uploading dataset…", selected)` | — |
| **Center h-10** | 빈 row | — |
| **Center body** | `InlineUploadProgress(progress)` | 3단계 Uploading/Parsing/Validating, `max-w-2xl` |
| **Right** | Details → `DetailsPanel(state="uploading")` | Cancel 버튼 |
| **Bottom** | `WorkbenchCommandBar(status="empty")` | — |
| **GateBar** | `null` | — |

---

## Screen 3 — Running (Streaming)

**진입 조건**: `state === "running"` (Upload 완료 후 or Approve 후)

| 영역 | 컴포넌트 인���턴스 | 비고 |
|---|---|---|
| **Header** | `"Q3 Sales Analysis"` + `StatusBadge(running)` | "Running" pulse dot |
| **PipelineBar (P0)** | `variant="running"`, `stage="Preprocess"`, `message="Scanning columns…"`, `stepFraction="2/6"`, `elapsed={formatElapsed}`, `onViewDetails` | indeterminate shimmer, "View details →" 링크 |
| **Left h-10** | "History" 라벨 | — |
| **Left body (P4)** | Upload complete → Preprocess plan ready → **Preprocess running** (selected) | Milestone Log |
| **Center h-10 (P2)** | `DecisionChips(CHIPS_RUNNING)`: Preprocess=ON, RAG=ON, Viz=ON, Report=ON, Mode=Full | 5개 칩, nav → Agent 탭 |
| **Center body** | `AssistantReportMessage(variant="streaming")` + `EvidenceFooter(P3)` + `ToolCallIndicator(running)` 인라인 pill | evidence: Data=sales_Q3.csv, Scope=14,500×24, Compute=v3·00:03, RAG=OFF |
| **Right** | Details or Agent 탭, Agent NEW dot 표시 | `CopilotPanel(runStatus, toolCalls, pipelineSteps(P1))` |
| **Right Agent > Tools** | RunStatus(Preprocessing, 42%, detect_missing) + Pipeline(6-step) + ToolCallList(3 calls) | P1 PipelineTracker 포함 |
| **Right Agent > MCP (P5)** | `MCPPanel(rawLogs=RAW_LOGS_RUNNING)` | 2개 Raw Log 엔트리 |
| **Bottom** | `WorkbenchCommandBar(status="streaming")` | Stop(■) 활성 |
| **GateBar** | `null` | — |

### CTA 위치 (SSOT)

| CTA | 위치 |
|---|---|
| Stop (■) | CommandBar 우측 |

---

## Screen 4 — Needs-user (HITL)

**진입 조건**: `state === "needs-user"` (Running 3.5초 후 or Stop 버튼)

| 영역 | 컴포넌트 인스턴스 | 비고 |
|---|---|---|
| **Header** | `"Q3 Sales Analysis"` + `StatusBadge(needs-user)` | "Needs Approval" pulse |
| **PipelineBar (P0)** | `variant="needs-user"`, `stage="Preprocess"`, `message="Awaiting approval"`, `stepFraction="2/6"`, `elapsed={formatElapsed}`, `onViewDetails` | 60% 고정, pulse, "View details →" |
| **Left h-10** | "History" 라벨 | — |
| **Left body (P4)** | Upload complete → Missing values detected → **Approval required** (selected, needs-user) | statusBadge="Awaiting", onClick=focusDetails |
| **Center h-10 (P2)** | `DecisionChips(CHIPS_NEEDS_USER)`: Preprocess=**BLOCKED**, RAG=ON, Viz=ON, Report=ON, Mode=Full | BLOCKED 칩: `ShieldAlert animate-pulse`, nav → focusDetails |
| **Center body** | `AssistantReportMessage(variant="final", accentVariant="needs-user")` + `EvidenceFooter(P3)` + `ToolCallIndicator(needs-user)` + 안내 텍스트 | evidence: scope="142 missing" |
| **Right** | Details → `DetailsPanel(state="needs-user")` — Decision Required 헤더 + ApprovalCard(hideActions) | **Confirm 없음** — GateBar에서만 |
| **Right Agent > Tools** | RunStatus(Awaiting, 60%) + AwaitingCard(nav only) + Pipeline(needs-user) + ToolCallList(4) | AwaitingCard "View in Details" 링크 |
| **Right Agent > MCP (P5)** | `MCPPanel(rawLogs=RAW_LOGS_ERROR)` | 4개 엔트리 (에러 포함) |
| **Bottom** | `WorkbenchCommandBar(status="idle")` | placeholder: "Agent is waiting for approval..." |
| **GateBar** | `GateBar(onApprove, onReject, onSubmitChange)` | floating, `max-w-md`, `slide-in-from-bottom-4` |

### CTA 위치 (SSOT)

| CTA | 위치 | 금지 위치 |
|---|---|---|
| "Approve & Continue" | **HITLGateBar** | Center, Left, Right |
| "Reject" | **HITLGateBar** | Center, Left, Right |
| "Submit" (Modify) | **HITLGateBar** 내 textarea | Center, Left, Right |

---

## Screen 5-A — Error (Resolution Required)

**진입 조건**: `state === "error"` (Approve 후 2.5초 or 직접 전환)

| 영역 | 컴포넌트 인스턴스 | 비고 |
|---|---|---|
| **Header** | `"Q3 Sales Analysis"` + `StatusBadge(error)` | "Error" |
| **PipelineBar (P0)** | `variant="failed"`, `stage="Visualization"`, `message="ParseError in 'Price'"`, `stepFraction="4/6"`, `elapsed={formatElapsed}`, `onViewDetails` | 28% 고정, 빨간색, 애니메이션 없음, "View details →" |
| **Left h-10** | "History" 라벨 | — |
| **Left body (P4)** | Upload complete → Missing values detected → RAG retrieved → **Visualization failed** (selected, failed) | statusBadge="Error", onClick=focusDetails |
| **Center h-10 (P2)** | `DecisionChips(CHIPS_ERROR)`: Preprocess=DONE, RAG=DONE, Viz=**FAILED**, Merge=QUEUED, Report=QUEUED | FAILED 칩: `XCircle`, nav → focusDetails |
| **Center body** | `AssistantReportMessage(variant="error")` + `EvidenceFooter(P3)` + `onReviewDetails` 링크 | evidence: scope="col=Price"; **Retry CTA 없음** — 링크만 |
| **Right** | Details 탭 강제 → highlight 배너 + `DetailsPanel(state="error")` | **"Confirm & Retry" 버튼 여기에만** |
| **Right Agent > Tools** | RunStatus(Failed, 28%) + Pipeline(error) + ToolCallList(4, cast_dtype failed) | — |
| **Right Agent > MCP (P5)** | `MCPPanel(rawLogs=RAW_LOGS_ERROR)` | Raw Logs 섹션 error dot 표시 |
| **Bottom** | `WorkbenchCommandBar(status="idle")` | placeholder: "Type to discuss the error..." |
| **GateBar** | `null` | — |

### CTA 위치 (SSOT)

| CTA | 위치 | 금지 위치 |
|---|---|---|
| "Confirm & Retry" | **Right DetailsPanel** (error state) | Center, Left |
| "Review in Details →" (nav) | Center AssistantReportMessage | — (nav only) |

---

## Screen 5-B — Error highlight (focusDetails 호출 시)

`focusDetails()` 함수가 호출되면:

1. `rightTab` → `"details"` 강제 전환
2. `highlightDetails = true` → Right 탭 상단에 `"↓ Resolution Required"` 붉은 배너 표시
   - 배너: `mx-4 mt-3 rounded-lg border-error/40 bg-error/5 text-[10px] font-semibold text-error animate-pulse`
3. `detailsPanelRef.scrollIntoView({ behavior: "smooth", block: "nearest" })`
4. 1100ms 후 `highlightDetails = false` 자동 초기화

### 호출 경로

| 트리거 | 컴포넌트 |
|---|---|
| Center "Review in Details →" 링크 | AssistantReportMessage(onReviewDetails) |
| Left History failed TimelineItem 클릭 | TimelineItem(onClick=focusDetails) |
| Left History needs-user TimelineItem 클릭 | TimelineItem(onClick=focusDetails) |
| Center DecisionChips BLOCKED/FAILED 칩 클릭 | DecisionChips(onNavigate=focusDetails) |
| PipelineBar "View details →" 링크 | PipelineBar(onViewDetails=focusDetails) |

---

## PipelineBar 상태 매핑 (전 화면 요약)

| Workbench state | PipelineBar variant | stage | message | stepFraction | elapsed | percent |
|---|---|---|---|---|---|---|
| `empty` | `hidden` | — | — | — | — | — |
| `uploading` (< 30%) | `ingest` | Ingest | "Parsing file..." | 1/6 | 동적 | `uploadProgress` |
| `uploading` (≥ 30%) | `ingest` | Ingest | "Validating schema..." | 1/6 | 동적 | `uploadProgress` |
| `running` | `running` | Preprocess | "Scanning columns..." | 2/6 | 동적 | — |
| `needs-user` | `needs-user` | Preprocess | "Awaiting approval" | 2/6 | 동적 | — |
| `error` | `failed` | Visualization | "ParseError in 'Price'" | 4/6 | 동적 | — |
| `success` | `completed` | Report | "All steps completed" | 6/6 | — | — |

---

## DecisionChips 상태 매핑 (전 화면 요약)

| state | 칩 구성 |
|---|---|
| `empty` / `uploading` | 빈 배열 → h-10 row 유지, 칩 없음 |
| `running` | Preprocess=ON, RAG=ON, Viz=ON, Report=ON, Mode=Full |
| `needs-user` | Preprocess=**BLOCKED**, RAG=ON, Viz=ON, Report=ON, Mode=Full |
| `error` | Preprocess=DONE, RAG=DONE, Viz=**FAILED**, Merge=QUEUED, Report=QUEUED |

### 칩 Tooltip (커스텀 오버라이드)

| 키 | Tooltip 문구 |
|---|---|
| `Preprocess-BLOCKED` | "Awaiting approval: Impute Missing Values (Region, 142 rows)" |
| `Viz-FAILED` | "Visualization failed: ParseError in 'Price' column — see Details" |
| `Preprocess-DONE` | "Preprocessing completed: 3 tools ran successfully" |
| `RAG-DONE` | "RAG retrieval completed successfully" |

---

## EvidenceFooter 상태 매핑 (전 화면 요약)

| state | Data | Scope | Compute | RAG |
|---|---|---|---|---|
| `running` | sales_Q3.csv | 14,500×24 | v3 · 00:03 | OFF |
| `needs-user` | sales_Q3.csv | 142 missing | v3 · 00:05 | OFF |
| `error` | sales_Q3.csv | col=Price | v3 · 00:06 | OFF |

### Nav 콜백 (공통)

| Pill | 대상 |
|---|---|
| Data / Scope | → `focusDetails()` (Right Details 패널) |
| Compute / RAG | → `handleTabChange("agent")` (Right Agent 탭) |

---

## Pipeline Steps 상태 매핑 (전 화면 요약)

| state | Intake | Preprocess | RAG | Visualization | Merge | Report |
|---|---|---|---|---|---|---|
| `running` | success(2) | **running**(1) | queued | queued | queued | queued |
| `needs-user` | success(2) | **needs-user**(2) | queued | queued | queued | queued |
| `error` | success(2) | success(3) | success(1) | **failed**(1) | queued | queued |

---

## Milestone Log 상태 매핑 (좌측 History, P4)

| state | 이벤트 목록 |
|---|---|
| `running` | ✅ Upload complete · ✅ Preprocess plan ready · 🔄 **Preprocess running** (selected) |
| `needs-user` | ✅ Upload complete · ✅ Missing values detected · 🟣 **Approval required** (selected, statusBadge="Awaiting") |
| `error` | ✅ Upload complete · ✅ Missing values detected · ✅ RAG retrieved · 🔴 **Visualization failed** (selected, statusBadge="Error") |

---

## 공통 스크롤 규칙 요약

| 규칙 | 내용 |
|---|---|
| History list only | 좌측 `aside` 내부 overflow-y-auto (width 고정, h-10 라벨 고정) |
| Center timeline only | `main > div.flex-1.overflow-y-auto.p-4` (GateBar + CommandBar 제외) |
| Right body only | h-10 탭 바 + 세그먼트 컨트롤 고정; 바디만 scroll |
| ReportMessage 내부 | `maxBodyHeight` px cap, 독립 overflow-y-auto, gradient fade |
| GateBar + CommandBar | `sticky bottom-0 z-30` — 절대 스크롤 안 됨 |
| MCPPanel Raw Log payload | `max-h-40 overflow-y-auto` — 개별 엔트리 내부 |
