# Migration Log — GenUI Workbench 통합 및 자동화 에이전트 전환

> 기록 일자: 2026-02-26
> 브랜치: `feature/agui-migration`

---

## 1. 새로운 GenUI 기반 워크벤치 도입

피그마 디자인을 기반으로 설계된 **GenUI 컴포넌트 시스템**을 전면 도입했다.

- **컴포넌트 위치:** `frontend/src/app/components/genui/`
- **주요 컴포넌트 (27개):**
  - `WorkbenchLayout` — 3-column 레이아웃 쉘 (Left History / Center Canvas / Right Panel)
  - `PipelineBar` — 상단 인라인 파이프라인 상태 스트립
  - `CopilotPanel` — 에이전트 Tool Call 목록 + Pipeline Steps
  - `DetailsPanel` — 단계별 세부 액션 패널
  - `GateBar` — Human-in-the-loop 승인/거부/수정 바
  - `AssistantReportMessage` — 에이전트 리포트 메시지 카드
  - `Dropzone`, `StatusBadge`, `TimelineItem`, `DecisionChips`, `EvidenceFooter` 등

---

## 2. 기획 방향 전환 — 완전 자동화 AI 에이전트 컨셉으로 UX 통합

### 제거된 기능
| 항목 | 이유 |
|------|------|
| 사용자 수동 전처리 화면 (`DataPreprocessing`) | AI 에이전트가 자동으로 수행하는 컨셉으로 UX 통합 |
| `/preprocess` 라우트 | 수동 전처리 화면 제거에 따라 함께 폐기 |
| 상단 탭 네비게이션 (Workbench Preview / Components / LLM Samples / Foundations) | 프로덕션 앱에 불필요한 개발용 탭 제거 |

### 기획 의도
사용자가 CSV를 업로드하면 **에이전트가 알아서 전처리 → RAG 검색 → 시각화 → 리포트**까지 자동으로 수행한다.
사용자는 필요한 경우에만 **Human-in-the-Loop 승인** 게이트에서 개입한다.
별도의 수동 전처리 단계를 거칠 필요가 없다.

---

## 3. 변경된 라우팅 구조

### Before (제거됨)
```
/                → Workbench Preview (탭 네비게이션 포함)
/foundations     → Foundations 디자인 토큰 페이지
/gallery         → Components Gallery 페이지
/samples         → LLM Samples 페이지
/preprocess      → 사용자 수동 전처리 페이지
```

### After (현재)
```
/       → GenUI Workbench (분석 세션 메인 화면)
/chat   → GenUI Workbench (동일, 채팅 URL 진입 지원)
```

**파일:** `frontend/src/app/App.tsx`
탭 네비게이션을 담당하던 `RootLayout`을 제거하고, `WorkbenchRoot`(h-screen 래퍼)만 남겼다.

---

## 4. 5상태 Mock 파이프라인 흐름

CSV 파일 드롭 시 아래 시퀀스로 UI 상태가 전환된다.

```
[empty]
  │  사용자가 Dropzone에 CSV 드롭 or "Try Sample" 클릭
  ▼
[uploading]  ─── 업로드 진행 바 (0% → 100%, ~2.5초)
  │  완료 시 자동 전환
  ▼
[running / preprocessing]  ─── "자동 전처리 중…"
  │  Preprocess 파이프라인 단계 실행 중
  │  PipelineBar stage: "Preprocess"
  │  Tool: detect_missing (running)
  │
  │  (2초 뒤 runningPhase: "rag" 로 자동 전환)
  ▼
[running / rag]  ─── "RAG 분석 중…"
  │  Preprocess 완료, RAG 단계 실행 중
  │  PipelineBar stage: "RAG"
  │  Tool: rag_retrieve (running)
  │
  │  (running 진입 후 3.5초 뒤 자동 전환, history < 3일 때)
  ▼
[needs-user]  ─── Human-in-the-Loop 승인 게이트
  │  GateBar 노출: Approve / Reject / Edit Instruction
  ├─ Approve → [running] → (2.5초) → [error] (Mock 시나리오)
  ├─ Reject  → [running]
  └─ Edit    → [running] → (2.5초) → [success]
```

### 상태별 UI 반영 요소

| 상태 | PipelineBar | CopilotPanel Steps | Center ToolCallIndicator |
|------|-------------|-------------------|--------------------------|
| `uploading` | Ingest / 업로드 % | — | — |
| `running/preprocessing` | Preprocess / 자동 전처리 중… | Preprocess running | detect_missing running |
| `running/rag` | RAG / RAG 분석 중… | RAG running | rag_retrieve running |
| `needs-user` | Preprocess / Awaiting approval | Preprocess needs-user | propose_imputation needs-user |
| `error` | Preprocess / Failed | Viz failed | — |

---

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `src/app/App.tsx` | RootLayout + 4개 라우트 → WorkbenchRoot + `/`, `/chat` 2개 라우트로 단순화 |
| `src/app/pages/Workbench.tsx` | `runningPhase` 상태 추가, preprocessing→rag 2초 전환 useEffect, 관련 Mock 데이터·함수 보완 |
| `frontend/MIGRATION_LOG.md` | 본 문서 (신규 생성) |
