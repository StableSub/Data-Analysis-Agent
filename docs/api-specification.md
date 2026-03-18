# 백엔드 API 명세서

## 1. 문서 목적

- 이 문서는 현재 코드 기준의 실제 백엔드 API를 기록한 `as-is` 명세서다.
- 기준 시점: `2026-03-18`
- 구현 기준 파일
  - [main.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/main.py)
  - [modules/chat/router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/router.py)
  - [modules/datasets/router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/router.py)
  - [modules/preprocess/router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/preprocess/router.py)
  - [modules/visualization/router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/router.py)
  - [modules/reports/router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/reports/router.py)
  - [modules/export/router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/export/router.py)
  - [modules/rag/router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/rag/router.py)

## 2. 공통 정보

- Base URL: `http://127.0.0.1:8000`
- Swagger UI: `GET /docs`
- OpenAPI JSON: `GET /openapi.json`

### CORS 허용 Origin

- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:5173`
- `http://127.0.0.1:5173`

## 3. 공통 식별자

- `dataset_id`: `datasets` 내부 PK
- `source_id`: dataset 외부 식별자
- `session_id`: chat session PK
- `run_id`: agent 실행 식별자
- `report_id`: report 식별자
- `result_id`: export 대상 분석 결과 식별자

## 4. 핵심 모델

### DatasetBase

```json
{
  "id": 1,
  "source_id": "string",
  "filename": "string",
  "storage_path": "string",
  "filesize": 1234
}
```

### DatasetSampleResponse

```json
{
  "source_id": "string",
  "columns": ["col1", "col2"],
  "rows": [{"col1": "value", "col2": 1}]
}
```

### ChatRequest

```json
{
  "question": "질문",
  "session_id": 1,
  "model_id": "string",
  "source_id": "string"
}
```

### ChatResponse

```json
{
  "answer": "string",
  "session_id": 1,
  "run_id": "string",
  "thought_steps": [],
  "pending_approval": {}
}
```

### PreprocessApplyResponse

```json
{
  "input_source_id": "string",
  "output_source_id": "string",
  "output_filename": "string"
}
```

### ReportBase

```json
{
  "report_id": "string",
  "session_id": 1,
  "summary_text": "string"
}
```

### RagQueryResponse

```json
{
  "answer": "string",
  "retrieved_chunks": [
    {
      "source_id": "string",
      "chunk_id": 0,
      "score": 0.95,
      "snippet": "string"
    }
  ],
  "executed_at": "2026-03-18T00:00:00Z"
}
```

## 5. datasets API

### `POST /datasets/`

- 설명: dataset 업로드
- multipart form
  - `file`
  - `filename` optional
- 응답: `DatasetBase`

### `GET /datasets/`

- 설명: dataset 목록
- query
  - `skip`
  - `limit`
- 응답: `DatasetListResponse`

### `GET /datasets/{dataset_id}`

- 설명: dataset 상세
- 응답: `DatasetBase`

### `GET /datasets/{source_id}/sample`

- 설명: sample row 조회
- query
  - `n_rows`
- 응답: `DatasetSampleResponse`

### `DELETE /datasets/{source_id}`

- 설명: dataset 삭제
- 응답: `204 No Content`

## 6. chats API

### `POST /chats/`

- 설명: 단건 질문
- 요청: `ChatRequest`
- 응답: `ChatResponse`

### `POST /chats/stream`

- 설명: SSE 스트리밍 질문
- 요청: `ChatRequest`
- 응답: `text/event-stream`

SSE 이벤트 이름

- `session`
- `thought`
- `chunk`
- `approval_required`
- `done`
- `error`

### `POST /chats/{session_id}/runs/{run_id}/resume`

- 설명: approval 이후 실행 재개
- 요청: `ResumeRunRequest`
- 응답: `text/event-stream`

### `GET /chats/{session_id}/runs/{run_id}/pending-approval`

- 설명: pending approval 조회
- 응답: `PendingApprovalResponse`

### `GET /chats/{session_id}/history`

- 설명: session history 조회
- 응답: `ChatHistoryResponse`

### `DELETE /chats/{session_id}`

- 설명: session 삭제
- 응답: `204 No Content`

## 7. preprocess API

### `POST /preprocess/apply`

- 설명: direct preprocess 적용
- 요청: operation list + `source_id`
- 응답: `PreprocessApplyResponse`

## 8. visualization API

### `POST /vizualization/manual`

- 설명: 수동 시각화 데이터 조회
- 요청: `ManualVizRequest`
- 응답: chart_type + row data

## 9. report API

### `POST /report/`

- 설명: direct report 생성
- 요청
  - `session_id`
  - `analysis_results`
  - `visualizations`
  - `insights`
- 응답: `ReportBase`

### `GET /report/`

- 설명: session 기준 report 목록
- query: `session_id`
- 응답: `ReportListResponse`

### `GET /report/{report_id}`

- 설명: report 단건 조회
- 응답: `ReportBase`

## 10. export API

### `POST /export/csv`

- 설명: 분석 결과 CSV 내보내기
- 요청: `ExportCsvRequest`
- 응답: `text/csv` attachment

## 11. rag API

### `POST /rag/query`

- 설명: direct RAG 질의
- 요청
  - `query`
  - `top_k`
  - `source_filter`
- 응답
  - 검색 결과 없으면 `204 No Content`
  - 검색 결과 있으면 `RagQueryResponse`

### `DELETE /rag/sources/{source_id}`

- 설명: RAG source 삭제
- 응답: `RagDeleteResponse`

## 12. 유지해야 할 계약

- `/vizualization/manual` 오타 path는 유지한다.
- datasets 응답 핵심 필드
  - `id`
  - `source_id`
  - `filename`
  - `storage_path`
  - `filesize`
- chats 응답 핵심 필드
  - `answer`
  - `session_id`
  - `run_id`
  - `thought_steps`
  - `pending_approval`
- preprocess 응답 핵심 필드
  - `input_source_id`
  - `output_source_id`
  - `output_filename`
- report 응답 핵심 필드
  - `report_id`
  - `session_id`
  - `summary_text`
- rag 응답 핵심 필드
  - `answer`
  - `retrieved_chunks`
  - `executed_at`
