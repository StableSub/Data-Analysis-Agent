# API Wiring Log — 프론트엔드 ↔ 백엔드 연동 명세서

> **최종 갱신**: 2026-02-26
> **브랜치**: `feature/agui-migration`
> **프론트엔드 API 클라이언트**: `frontend/src/lib/api.ts`
> **오케스트레이션 Hook**: `frontend/src/app/hooks/useAnalysisPipeline.ts`
> **백엔드 Base URL**: `VITE_API_BASE_URL` 환경변수 또는 기본값 `http://localhost:8000`

---

## 1. 엔드포인트 매핑 테이블

| # | Method | Backend Endpoint | 프론트 함수 (`api.ts`) | 호출 위치 (`useAnalysisPipeline.ts`) | 용도 |
|---|--------|-----------------|----------------------|-------------------------------------|------|
| 1 | `POST` | `/datasets/` | `uploadFile(file, onProgress)` | `startUpload()` | 파일 업로드 (XHR + progress) |
| 2 | `GET` | `/datasets/{source_id}/sample` | `fetchSample(sourceId)` | `runIntake()` | 스키마 + 샘플 행 조회 |
| 3 | `POST` | `/chats/` | `sendChat(req)` | `runAnalysis()`, `handleSend()` | 데이터셋 분석 / 후속 질문 |
| 4 | `POST` | `/rag/query` | `queryRag(req)` | `runRagPhase()` | RAG 검색 + 답변 생성 |
| 5 | `POST` | `/preprocess/apply` | `applyPreprocess(req)` | `resumeAfterApproval()` | 전처리 연산 적용 |
| 6 | `POST` | `/report/` | `createReport(req)` | `runReportPhase()` | 최종 리포트 생성 |
| 7 | `POST` | `/vizualization/manual` | `createManualViz(req)` | *(향후 연동 예정)* | 수동 차트 생성 |
| 8 | `POST` | `/export/csv` | `exportCsv(resultId)` | *(향후 연동 예정)* | CSV 파일 다운로드 |

---

## 2. 각 API 상세 — Request / Response / UI 바인딩

### 2.1 파일 업로드 (`POST /datasets/`)

**호출 시점**: 사용자가 Dropzone에 파일을 드롭하거나 "Upload Dataset" 버튼 클릭 시

**Request**:
```
Content-Type: multipart/form-data
Body: FormData { file: File }
```

**Response** (`DatasetResponse`):
```json
{
  "id": 42,
  "source_id": "abc123-def456",
  "filename": "sales_Q3.csv",
  "storage_path": "/storage/datasets/abc123-def456.csv",
  "filesize": 14200000
}
```

**UI 바인딩**:
| 응답 필드 | 바인딩 대상 | 설명 |
|-----------|-----------|------|
| `id` | `pipeline.datasetId` | 후속 preprocess API 호출 시 사용 |
| `source_id` | `pipeline.sourceId` | sample/chat/rag 호출 시 식별자 |
| `filename` | `pipeline.fileName` → Header 타이틀, InlineUploadProgress, EvidenceFooter `.data` | 파일명 전역 표시 |
| (upload progress) | `pipeline.uploadProgress` → PipelineBar `.percent`, InlineUploadProgress `.progress` | XHR progress 이벤트에서 실시간 갱신 |

**상태 전이**: `empty` → `uploading` (업로드 시작) → `running` (업로드 완료 후 자동)

---

### 2.2 샘플 조회 (`GET /datasets/{source_id}/sample`)

**호출 시점**: 업로드 완료 직후, `runIntake()` 단계에서 자동 호출

**Request**:
```
GET /datasets/{source_id}/sample
(No body)
```

**Response** (`SampleResponse`):
```json
{
  "source_id": "abc123-def456",
  "columns": ["id", "region", "price", "date_sold"],
  "rows": [
    {"id": 1, "region": "North", "price": 100, "date_sold": "2024-01-01"},
    {"id": 2, "region": "South", "price": null, "date_sold": "2024-01-02"}
  ]
}
```

**UI 바인딩**:
| 응답 필드 | 바인딩 대상 | 설명 |
|-----------|-----------|------|
| `columns.length` | EvidenceFooter `.scope` (예: `5x4`) | 컬럼 수 |
| `rows.length` | EvidenceFooter `.scope` | 샘플 행 수 |
| `columns`, `rows` | AssistantReportMessage (running) `.sections` — "Loaded dataset schema — N sample rows x M columns" | 분석 진행 메시지 |

**ToolCallEntry 로깅**: `fetch_sample` (status: running → completed, result: "N columns, M sample rows")

---

### 2.3 채팅 분석 (`POST /chats/`)

**호출 시점**:
- **자동**: `runAnalysis()` — 샘플 조회 완료 후 자동 호출
- **수동**: `handleSend(message)` — 사용자가 CommandBar에서 메시지 전송 시

**Request** (`ChatRequest`):
```json
{
  "question": "Analyze this dataset. Identify any missing values, data quality issues, and recommend preprocessing steps.",
  "source_id": "abc123-def456",
  "session_id": null,
  "model_id": null
}
```
> 후속 질문 시: `session_id`에 이전 응답의 `session_id` 포함

**Response** (`ChatResponse`):
```json
{
  "answer": "The dataset contains 14,500 rows with 24 columns. I found 142 missing values in the 'Region' column (0.98%)...",
  "session_id": 7
}
```

**UI 바인딩**:
| 응답 필드 | 바인딩 대상 | 설명 |
|-----------|-----------|------|
| `answer` | AssistantReportMessage (running) `.sections[2].items[1]` | 분석 결과 요약 텍스트 |
| `answer` | HITL 판단 로직 (`detectPreprocessNeeds()`) | "missing", "null", "impute" 등 키워드 감지 → needs-user 전환 |
| `session_id` | `pipeline.sessionId` | 후속 chat/report API 호출 시 세션 식별자 |

**상태 전이**: `answer`에 전처리 키워드 감지 시 → `needs-user` (파이프라인 일시정지)

---

### 2.4 RAG 검색 (`POST /rag/query`)

**호출 시점**: `runRagPhase()` — chat 분석 완료 후 (또는 HITL 승인 후)

**Request** (`RagQueryRequest`):
```json
{
  "query": "Analyze patterns and anomalies in the dataset",
  "top_k": 5,
  "source_filter": ["abc123-def456"]
}
```

**Response** (`RagResponse`):
```json
{
  "answer": "Based on retrieved documents...",
  "retrieved_chunks": [
    {
      "source_id": "abc123-def456",
      "chunk_id": 3,
      "score": 0.89,
      "snippet": "Q3 sales showed a 15% increase in the North region..."
    }
  ],
  "executed_at": "2026-02-26T10:05:00Z"
}
```
> **204 No Content**: RAG 데이터 없을 시 — 정상 처리, "No matching documents"로 기록

**UI 바인딩**:
| 응답 필드 | 바인딩 대상 | 설명 |
|-----------|-----------|------|
| `retrieved_chunks.length` | EvidenceFooter `.rag` (예: `5 chunks`) | RAG 상태 표시 |
| `retrieved_chunks[].snippet` | AssistantReportMessage (success) `.sections` — "Retrieved Evidence" 섹션 | 최종 리포트에 근거 표시 |
| `retrieved_chunks[].score` | AssistantReportMessage (success) `.sections` — 각 chunk 앞에 스코어 표시 | 관련도 점수 |

---

### 2.5 전처리 적용 (`POST /preprocess/apply`)

**호출 시점**: `resumeAfterApproval(true)` — 사용자가 GateBar에서 Approve 또는 Edit 후 Submit 시

**Request** (`PreprocessApplyRequest`):
```json
{
  "dataset_id": 42,
  "operations": [
    {
      "op": "impute",
      "params": {
        "column": "Region",
        "strategy": "mode",
        "fill_value": "auto"
      }
    }
  ]
}
```
> `op` 가능값: `"drop_missing"` | `"impute"` | `"drop_columns"` | `"rename_columns"` | `"scale"` | `"derived_column"`

**Response** (`PreprocessApplyResponse`):
```json
{
  "dataset_id": 42
}
```

**UI 바인딩**:
| 응답 | 바인딩 대상 | 설명 |
|------|-----------|------|
| 성공 | DecisionChips `Preprocess` → `"DONE"` | 전처리 칩 상태 갱신 |
| 성공 | PipelineTracker `preprocess` → `"success"` | 파이프라인 스텝 완료 |
| 실패 | state → `"error"`, errorMessage 바인딩 | 에러 상태 전환 |

---

### 2.6 리포트 생성 (`POST /report/`)

**호출 시점**: `runReportPhase()` — RAG 완료 후 마지막 단계

**Request** (`ReportCreateRequest`):
```json
{
  "session_id": 7
}
```

**Response** (`ReportResponse`):
```json
{
  "report_id": "rpt-abc123",
  "session_id": 7,
  "summary_text": "Analysis complete. The dataset contains 14,500 rows with 24 columns. Key findings include..."
}
```

**UI 바인딩**:
| 응답 필드 | 바인딩 대상 | 설명 |
|-----------|-----------|------|
| `summary_text` | AssistantReportMessage (success) `.sections[0].content` | 최종 리포트 본문 |
| `report_id` | Timeline milestone `.subtext` | 리포트 ID 표시 |

**상태 전이**: 성공 시 → `success` (파이프라인 완료)

---

## 3. 파이프라인 상태 머신 다이어그램

```
┌─────────┐
│  empty   │ ← 초기 상태 / reset
└────┬─────┘
     │ startUpload(file) 또는 startWithSample()
     ▼
┌──────────┐   uploadFile() XHR progress
│ uploading │ ─────────────────────────────┐
└────┬──────┘                              │ (실시간 진행률)
     │ upload 완료                         │
     ▼                                     │
┌──────────┐                               │
│ running  │ ← runPipeline() 자동 시작      │
│          │   1. fetchSample()            │
│          │   2. sendChat()               │
│          │   3. queryRag()               │
│          │   4. createReport()           │
└──┬───┬───┘                               │
   │   │                                   │
   │   │ detectPreprocessNeeds() = true     │
   │   ▼                                   │
   │ ┌────────────┐                        │
   │ │ needs-user │ ← 파이프라인 일시정지    │
   │ └──┬────┬────┘                        │
   │    │    │                             │
   │    │    │ Approve / Edit              │
   │    │    ▼                             │
   │    │  ┌──────────┐                    │
   │    │  │ running  │ ← resumeAfterApproval()
   │    │  │          │   applyPreprocess()
   │    │  │          │   → queryRag()
   │    │  │          │   → createReport()
   │    │  └──┬───────┘
   │    │     │
   │    │     ▼
   │    │  ┌─────────┐
   │    │  │ success │ ← 파이프라인 완료
   │    │  └─────────┘
   │    │
   │    │ Reject
   │    ▼
   │  running → queryRag() → createReport() → success
   │
   │ API 에러 발생 시 (어느 단계에서든)
   ▼
┌─────────┐
│  error  │ ← transitionToError()
└────┬────┘
     │ handleRetry()
     ▼
   running (파이프라인 재시작)
```

---

## 4. ToolCallEntry 로깅 체계

파이프라인 각 API 호출마다 자동으로 `ToolCallEntry`가 생성되어 **CopilotPanel > Tools 탭**에 표시됩니다.

| 단계 | tool name | status 흐름 | args (요약) | result (요약) |
|------|-----------|------------|------------|-------------|
| Intake | `fetch_sample` | running → completed/failed | `{ source_id }` | `"N columns, M sample rows"` |
| Analysis | `chat_analysis` | running → completed/failed | `{ source_id, question }` | 답변 앞 100자 |
| HITL | `preprocess_apply` | running → completed/failed | `{ dataset_id, column }` | `"Preprocessing applied"` |
| RAG | `rag_query` | running → completed/failed | `{ source_id, top_k }` | `"N chunks retrieved"` |
| Report | `create_report` | running → completed/failed | `{ session_id }` | 요약 앞 80자 |
| Follow-up | `chat_followup` | running → completed/failed | `{ question, session_id }` | 답변 앞 80자 |

각 entry에 포함되는 필드:
- `id`: `crypto.randomUUID()`
- `startedAt`: API 호출 시작 시각
- `duration`: 완료 시 `(Date.now() - t0) / 1000` 초
- `args`: request params를 JSON.stringify
- `result`: response 요약 텍스트

---

## 5. 에러 처리

| 에러 발생 지점 | 프론트 반응 | UI 표시 |
|---------------|-----------|---------|
| `uploadFile()` 네트워크 오류 | state → `error` | AssistantReportMessage (error variant) + PipelineBar (failed) |
| `fetchSample()` 404 | state → `error` | `"fetch_sample failed"` 에러 메시지 |
| `sendChat()` 500 | state → `error` | 분석 실패 메시지 표시 |
| `queryRag()` 204 | **정상 처리** | `"No matching documents"` — RAG 스킵, 계속 진행 |
| `queryRag()` 500 | state → `error` | RAG 실패 메시지 |
| `applyPreprocess()` 실패 | state → `error` | 전처리 적용 실패 메시지 |
| `createReport()` 실패 | state → `error` | 리포트 생성 실패 메시지 |

모든 에러 시:
- 해당 ToolCallEntry의 `status`가 `"failed"`로 갱신
- Timeline에 failed milestone 추가
- PipelineTracker에서 해당 스텝이 `"failed"` 표시
- DecisionChips에서 해당 스테이지가 `"FAILED"` 표시

---

## 6. GenUI 컴포넌트 → 데이터 소스 매핑

| GenUI 컴포넌트 | 주요 props | 데이터 소스 (hook 반환값) |
|---------------|-----------|------------------------|
| `AssistantReportMessage` | `sections`, `evidence` | `pipeline.reportSections`, `pipeline.evidence` |
| `CopilotPanel` | `runStatus`, `toolCalls`, `pipelineSteps` | `pipeline.runStatus`, `pipeline.toolCalls`, `pipeline.pipelineSteps` |
| `DecisionChips` | `chips` | `pipeline.decisionChips` |
| `EvidenceFooter` | `data`, `scope`, `compute`, `rag` | `pipeline.evidence` (fileName, sampleData, elapsedSeconds, ragResponse 기반) |
| `PipelineBar` | `variant`, `stage`, `message`, `elapsed`, `percent` | `pipeline.state`, `pipeline.runningSubPhase`, `pipeline.elapsedSeconds`, `pipeline.uploadProgress` |
| `StatusBadge` | `status` | `pipeline.state` |
| `TimelineItem` | `status`, `title`, `subtext`, `timestamp` | `pipeline.milestones`, `pipeline.history` |
| `ToolCallIndicator` | `status`, `label` | `pipeline.toolCalls` 중 `status === "running"` 인 항목 |
| `GateBar` | `onApprove`, `onReject`, `onSubmitChange` | `pipeline.handleApprove`, `pipeline.handleReject`, `pipeline.handleEditInstruction` |
| `MCPPanel` | `rawLogs` | `pipeline.rawLogs` |
| `Dropzone` | `onDrop`, `progress` | `handleDrop()` → `pipeline.startUpload(file)`, `pipeline.uploadProgress` |
| `WorkbenchCommandBar` | `onSend`, `onStop` | `pipeline.handleSend`, `pipeline.handleCancel` |

---

## 7. 환경 설정

| 변수 | 기본값 | 설명 |
|------|-------|------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | 백엔드 API base URL |

**CORS 허용 Origins** (백엔드 `main.py`):
- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:5173`
- `http://127.0.0.1:5173`

---

## 8. 참고: 아직 연동되지 않은 기능

| 기능 | 엔드포인트 | 상태 | 비고 |
|------|-----------|------|------|
| 수동 시각화 | `POST /vizualization/manual` | api.ts에 함수 정의됨, UI 미연결 | 향후 Visualization 스테이지 확장 시 |
| CSV 내보내기 | `POST /export/csv` | api.ts에 함수 정의됨, UI 미연결 | 향후 Download 버튼 연결 시 |
| 세션 히스토리 | `GET /chats/{session_id}/history` | api.ts 미정의 | 향후 채팅 히스토리 복원 시 |
| 데이터셋 목록 | `GET /datasets/` | api.ts 타입 정의됨, 함수 미정의 | 향후 데이터셋 선택 UI 시 |
| 데이터셋 삭제 | `DELETE /datasets/{source_id}` | 미정의 | 향후 데이터 관리 UI 시 |
| RAG 소스 삭제 | `DELETE /rag/sources/{source_id}` | 미정의 | 향후 RAG 관리 UI 시 |
