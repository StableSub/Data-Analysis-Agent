# interactions.md — Gen-UI Workbench Interaction Map
> 추출 기준: `Workbench.tsx` 이벤트 핸들러, `WorkbenchLayout.tsx`, `RightPanelTabs.tsx`, `GateBar.tsx`, 전 컴포넌트.
> 포맷: **클릭 대상** → `상태/UI 변화` (한 줄 또는 다단계)
> 최종 갱신: P0–P5 전 인터랙션 반영 완료.

---

## 1. HistoryPanel 토글

| 클릭 대상 | 상태 변화 |
|---|---|
| Header 좌단 `SidebarClose` (open 상태) | `isLeftPanelOpen: true → false` → `w-72 → w-0`, `opacity-100 → 0`, `border-r-0` |
| Header 좌단 `SidebarOpen` (closed 상태) | `isLeftPanelOpen: false → true` → `w-0 → w-72`, `opacity-0 → 100` |

트랜지션: `transition-all duration-300 ease-in-out`

---

## 2. RightPanelTabs — 탭 전환

| 클릭 대상 | 상태 변화 |
|---|---|
| "Details" 탭 버튼 | `activeTab → "details"`, agentSubTab 유지 |
| "Agent" 탭 버튼 | `activeTab → "agent"`, `copilotHasNew → false` (NEW dot 제거) |
| Agent 탭 "Tools" 세그먼트 | `agentSubTab → "tools"`, toolsContent 표시 |
| Agent 탭 "MCP" 세그먼트 | `agentSubTab → "mcp"`, mcpContent 표시, `mcpHasNew → false` |

탭 전환: `transition-opacity duration-200` (abs overlay, opacity 교차)
서브탭 전환: `transition-opacity duration-150`

---

## 3. CommandBar 액션

| 클릭 대상 | 상태 변화 |
|---|---|
| `+` (Plus) 버튼 | `isAttachMenuOpen: !prev` (모델 메뉴 동시에 닫힘), 아이콘 `rotate-45` |
| 외부 클릭 (attach/모델 메뉴 open 시) | 해당 메뉴 close (`mousedown` 리스너) |
| Model Selector 버튼 | `isModelMenuOpen: !prev` |
| 모델 항목 클릭 | `selectedModel → 선택`, `isModelMenuOpen → false` |
| Send (`SendHorizontal`) | `value.trim() && !disabled && !streaming` → `onSend(value)`, `value → ""` |
| `Enter` 키 (textarea) | `!shiftKey` + 동일 조건 → Send 동작 |
| `Shift+Enter` | 줄바꿈 삽입 (기본 동작) |
| Stop (■) (streaming 상태) | `onStop()` → `setState("needs-user")` |
| Mic 버튼 | 기능 없음 (플레이스홀더) |

### AttachMenuPopover 아이템 클릭

| 아이템 | 상태 변화 |
|---|---|
| "Upload dataset" | `onUploadDataset()` → `handleStateChange("uploading")`, 메뉴 닫힘 |
| "Add photos & files" | `onAddFiles()` (no-op), 메뉴 닫힘 |
| "Use sample dataset" | `onUseSample()` → `handleStateChange("uploading")`, 메뉴 닫힘 |

---

## 4. Dropzone 액션 (Empty 화면)

| 클릭 대상 | 상태 변화 |
|---|---|
| "Upload Dataset" 버튼 | `handleStateChange("uploading")` |
| "Try Sample Dataset" 버튼 | `handleStateChange("uploading")` |
| 드래그 hover | `status → "dragover"` (border 색상 변경) |
| 드래그 drop | `onDrop(files)` → `handleStateChange("uploading")` |

---

## 5. Upload 자동 진행 (state 전환)

| 조건 | 전환 |
|---|---|
| `state === "uploading"` 진입 | `uploadProgress: 0` 초기화, 50ms interval |
| `uploadProgress += 2` per tick | `progress: 0 → 100` (약 2.5초) |
| `uploadProgress >= 100` | `setState("running")`, interval 정리 |

---

## 6. Running 자동 HITL 전환

| 조건 | 전환 |
|---|---|
| `state === "running"` + `history.length < 3` | 3500ms 후 `setState("needs-user")` |
| `history.length >= 3` | 자동 전환 없음 (반복 approve 후) |

---

## 7. HITLGateBar — Approve / Reject / Submit

### Approve & Continue

```
클릭 "Approve & Continue"
→ handleApprove()
→ setHistory([...prev, { status:"completed", title:"Approved Imputation" }])
→ setState("running")
→ [2500ms 후] setState("error")
→ GateBar 사라짐 (state !== "needs-user")
→ PipelineBar variant → "running" → "failed" (자동)
→ DecisionChips 갱신 (RUNNING → ERROR)
```

### Reject

```
클릭 "Reject"
→ handleReject()
→ setHistory([...prev, { status:"failed", title:"Rejected Changes" }])
→ setState("running")
→ GateBar 사라짐
```

### Modify with instructions → Submit

```
클릭 "Modify with instructions..." (collapsed)
→ isEditing: false → true
→ textarea 확장 (autoFocus, animate-in fade-in zoom-in-95 duration-200)

textarea 입력 후 Submit 또는 Enter
→ value.trim() 체크
→ onSubmitChange(text) → handleEditInstruction(text)
→ setHistory([...prev, { status:"completed", title:"User Edit", subtext: text }])
→ setState("running")
→ [2500ms 후] setState("success")
→ GateBar 사라짐

Cancel 클릭 또는 onBlur(빈 값)
→ isEditing: true → false → textarea 접힘
```

---

## 8. P0 — PipelineBar 인터랙션

### "View details →" 링크 클릭

| 조건 | 동작 |
|---|---|
| variant = running / needs-user / failed + `onViewDetails` 존재 | `focusDetails()` 호출 |
| variant = hidden / completed / ingest | 링크 표시 안 됨 |

```
클릭 "View details →"
→ focusDetails()
→ setRightTab("details")
→ highlightDetails banner 표시 (1.1초)
→ detailsPanelRef.scrollIntoView
```

### PipelineBar 상태 자동 갱신

| Workbench state 변화 | PipelineBar 반응 |
|---|---|
| empty → uploading | hidden → ingest (percent 0→100) |
| uploading → running | ingest → running (shimmer 시작) |
| running → needs-user | running → needs-user (60% 고정, pulse) |
| needs-user → running (approve) | needs-user → running |
| running �� error | running → failed (28% 고정, 빨강) |
| → success | → completed (progress line 제거) |

### Elapsed 타이머

```
state === "running" || "needs-user" 진입 시
→ setInterval(1초) → elapsedSeconds++
→ formatElapsed(s) → "MM:SS" 형식
→ PipelineBar elapsed prop으로 전달

state 변경 시 (다른 상태)
→ clearInterval, elapsedSeconds → 0
```

---

## 9. P2 — DecisionChips 네비게이션

### 칩 클릭

| 칩 value | 동작 |
|---|---|
| `BLOCKED` | `onNavigate → focusDetails()` (Right Details 포커스) |
| `FAILED` | `onNavigate → focusDetails()` |
| 기타 (ON, DONE, QUEUED, RUNNING, Full, Quick QA) | `onNavigate → handleTabChange("agent")` (Agent 탭 전환) |

### 칩 Hover

```
마우스 hover 시
→ native `title` attribute로 tooltip 표시
→ defaultTooltip(stage, value) + navSuffix(" · click to view details")
→ 커스텀 tooltip 있으면 chipTooltips[stage-value] 사용
```

### 칩 키보드

```
tabIndex=0 (navigable 시)
→ Enter 또는 Space 키 → onNavigate() 호출
→ focus-visible: outline 2px --genui-focus-ring
```

---

## 10. P3 — EvidenceFooter 네비게이션

### Pill 클릭

| Pill | 네비게이션 |
|---|---|
| Data | `onDataNavigate → focusDetails()` |
| Scope | `onScopeNavigate → focusDetails()` |
| Compute | `onComputeNavigate → handleTabChange("agent")` |
| RAG | `onRagNavigate → handleTabChange("agent")` |

### Pill Hover

```
hover 시
→ border: --genui-muted/60
→ 배경: --genui-panel
→ title tooltip: "Key: value — click to view"
```

### Pill 키보드

```
tabIndex=0 (navigable 시)
→ Enter 또는 Space → onNavigate() 호출
```

---

## 11. P4 — Milestone Log 네비게이션

### TimelineItem 클릭 (History)

| item status | 동작 |
|---|---|
| `failed` | `onClick=focusDetails` → Right Details 포커스 |
| `needs-user` | `onClick=focusDetails` → Right Details 포커스 |
| 기타 (completed, running, normal) | `onClick=undefined` (클릭 불가) |

### statusBadge (nav hint)

```
status=failed → statusBadge="Error"
status=needs-user → statusBadge="Awaiting"

hover 시 → "→ View in Details" 텍스트 표시 (opacity 0→100)
```

---

## 12. P5 — MCPPanel 인터랙션

### Collapsible 섹션

| 클릭 대상 | 변화 |
|---|---|
| Servers 섹션 헤더 | `serversOpen: !prev`, `ChevronDown ↔ ChevronUp` |
| Recent Actions 헤더 | `actionsOpen: !prev` |
| Raw Stream / Logs 헤더 | `rawOpen: !prev` |

### 기본 상태

| 섹션 | 기본값 |
|---|---|
| Servers | open (`useState(true)`) |
| Recent Actions | open (`useState(true)`) |
| Raw Stream / Logs | **closed** (`useState(false)`) — 개발자 전용 |

### Error dot (Raw Logs)

```
rawLogs에 isError=true 엔트리 존재 + rawOpen === false 시
→ Raw Stream 헤더 아이콘에 빨간 dot 표시
→ w-1.5 h-1.5 rounded-full bg-error border-panel
→ rawOpen → true 시 dot 사라짐
```

### RawLogRow 확장/접기

```
헤더 클릭 → open: !prev
→ open=true: payload pre 블록 표시 + Copy 버튼 노출
→ open=false: payload 숨김, Copy 버튼 숨김
```

### Copy 버튼

```
클릭 Copy
→ navigator.clipboard.writeText(payload)
→ copied: true → 아이콘 Check + "Copied" 표시
→ 1800ms 후 → copied: false → 아이콘 Copy + "Copy"
→ stopPropagation (헤더 토글 방지)
```

---

## 13. Error 화면 — focusDetails 네비게이션 (통합)

### 호출 경로 (모든 트리거)

| 트리거 | 컴포넌트 | 컨텍스트 |
|---|---|---|
| Center "Review in Details →" 링크 | AssistantReportMessage(onReviewDetails) | error 화면 |
| Left History failed 아이템 클릭 | TimelineItem(onClick=focusDetails) | error 화면 |
| Left History needs-user 아이템 클릭 | TimelineItem(onClick=focusDetails) | needs-user 화면 |
| Center DecisionChips BLOCKED 칩 클릭 | DecisionChips(onNavigate=focusDetails) | needs-user 화면 |
| Center DecisionChips FAILED 칩 클릭 | DecisionChips(onNavigate=focusDetails) | error 화면 |
| PipelineBar "View details →" 클릭 | PipelineBar(onViewDetails=focusDetails) | running/needs-user/error |
| EvidenceFooter Data/Scope pill 클릭 | EvidenceFooter(onDataNavigate=focusDetails) | running/needs-user/error |

### focusDetails() 실행 순서

```
1. setHighlightDetails(true)
2. setRightTab("details") → Details 탭 강제 전환
3. detailsPanelRef.current.scrollIntoView({ behavior:"smooth", block:"nearest" })
4. setTimeout(() => setHighlightDetails(false), 1100ms)
```

---

## 14. DetailsPanel 내부 액션

| 액션 | 상태 변화 |
|---|---|
| "Cancel" (uploading state) | `handleDetailsAction("cancel-upload")` → `handleStateChange("empty")` |
| "Confirm & Retry" (error state) | `handleDetailsAction("resolve-retry")` → `handleStateChange("running")` |

---

## 15. Agent Tab NEW Dot 규칙

| 이벤트 | 변화 |
|---|---|
| `state` → running/needs-user/error & `rightTab !== "agent"` | `copilotHasNew → true` → Agent 탭에 pulse dot |
| Agent 탭 클릭 | `copilotHasNew → false` → dot 사라짐 |
| Details 탭에서 상태 변화 | dot 유지 (강제 탭 전환 없음) |

---

## 16. CopilotPanel 내부 인터랙션

### Pipeline 섹션 (P1)

| 클릭 대상 | 변화 |
|---|---|
| Pipeline 섹션 헤더 | `pipelineOpen: !prev` |
| PipelineTracker StepRow | `onStepClick(stepId)` (현재 미사용, 확장 가능) |

### Tool Calls 섹션

| 클릭 대상 | 변화 |
|---|---|
| Tool Calls 섹션 헤더 | `toolsOpen: !prev` |
| FilterToggle All/Latest/Errors | `filter → 선택값`, 리스트 재정렬 |
| ToolCallListItem 클릭 | `selectedId: id ↔ null (토글)`, ToolCallDetail 표시/숨김 |
| ToolCallDetail 헤더 | `open: !prev` (args/result 표시/숨김) |

### AwaitingCard (needs-user only)

| 클릭 대상 | 변화 |
|---|---|
| "View in Details" 링크 | `focusDetails()` — nav only (SSOT: no Approve/Reject) |

---

## 17. AssistantReportMessage — Collapse/Expand

| 클릭 대상 | 변화 |
|---|---|
| "Expand" 버튼 (collapsed) | `collapsed: true → false`, 전체 섹션 표시, `maxBodyHeight` 적용 |
| "Collapse" 버튼 (expanded) | `collapsed: false → true`, `collapsedSections`(기본 1)개만 |
| 조건 | `!isStreaming && defaultCollapsed === true` 일 때만 |

---

## 18. Debug 상태 전환 (개발자 전용)

```
Center 우상단 모서리 hover 시 → 5개 dot 버튼 표시 (opacity 0→100)
→ empty / uploading / running / needs-user / error 클릭
→ handleStateChange(선택) → 즉시 state 전환
→ 모든 하위 컴포넌트 연쇄 갱신:
   - PipelineBar variant
   - DecisionChips 칩 구성
   - EvidenceFooter 값
   - Milestone Log (History) 아이템
   - Right Panel 내용
   - CopilotPanel RunStatus + ToolCalls + PipelineSteps
   - MCPPanel rawLogs
   - StatusBadge
   - CommandBar status + placeholder
   - GateBar 표시/숨김
```

---

## SSOT 검증 체크리스트

| 규칙 | 준수 | 위치 |
|---|---|---|
| "Confirm & Retry" CTA | ✅ Right DetailsPanel(error)에만 | `DetailsPanel.tsx` |
| "Approve & Continue" CTA | ✅ GateBar에만 | `GateBar.tsx` |
| "Reject" CTA | ✅ GateBar에만 | `GateBar.tsx` |
| "Submit" (Modify) CTA | ✅ GateBar 내 textarea에만 | `GateBar.tsx` |
| Center error 결정 CTA | ✅ 없음 — "Review in Details →" 링크만 | `AssistantReportMessage(onReviewDetails)` |
| Left History 결정 CTA | ✅ 없음 — `onClick=focusDetails` nav만 | `TimelineItem(onClick)` |
| PipelineBar 결정 CTA | ✅ 없음 — "View details →" nav만 | `PipelineBar(onViewDetails)` |
| DecisionChips 결정 CTA | ✅ 없음 — `onNavigate` nav만 (read-only 태그) | `DecisionChips(onNavigate)` |
| EvidenceFooter 결정 CTA | ✅ 없음 — pill nav만 | `EvidenceFooter(onNavigate)` |
| CopilotPanel AwaitingCard CTA | ✅ 없음 — "View in Details" nav만 | `CopilotPanel AwaitingCard` |
| MCPPanel 결정 CTA | ✅ 없음 — 순수 조회/개발자 뷰 | `MCPPanel.tsx` |
| Dropzone "Try Sample Dataset" | ✅ Center에만 | `Dropzone(onTrySample)` |
