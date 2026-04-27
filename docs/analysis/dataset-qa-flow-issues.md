# 데이터 업로드 후 질의응답 경로 이슈 분석 보고서

> 작성일: 2026-04-13  
> 분석 범위: 데이터 업로드 → 데이터셋 선택 → `/chats/stream` 기반 데이터 질의응답 경로  
> 분석 기준: 현재 코드베이스 런타임 경로 추적 (`frontend/src/app/hooks/useAnalysisPipeline.ts`, `backend/app/modules/*`, `backend/app/orchestration/*`)  

---

## 목차

1. 분석 대상과 결론
2. 정상 흐름 요약
3. [Critical] 확정 장애
4. [High] 업로드 단계 오류 시나리오
5. [High] 질문 진입 및 workflow handoff 오류 시나리오
6. [Medium] Planner 수정 이후에도 남는 조건부 오류
7. 우선순위 정리

---

## 1. 분석 대상과 결론

이번 분석은 사용자가 CSV를 업로드한 뒤, 해당 데이터셋을 선택한 상태에서 자연어 질문을 입력했을 때의 실제 런타임 경로를 따라가며 어디서 어떤 오류가 발생할 수 있는지를 검증하는 데 목적이 있다.

가장 중요한 결론은 다음과 같다.

- 업로드 경로 자체는 확장자, UTF-8 CSV 가독성, RAG 인덱싱 실패 롤백까지 포함해 비교적 강하게 보호되어 있다.
- 반면 dataset-selected 질문 경로는 planner 단계에서 `LLMGateway.invoke_with_tools()` 호출 계약이 깨져 있어, 현재 코드 상태에서는 **핵심 분기 지점에서 확정적으로 실패할 가능성이 매우 높다.**
- 따라서 현재 시스템의 최우선 장애는 업로드가 아니라 **planner tool-calling integration 누락**이다.

---

## 2. 정상 흐름 요약

### 2-1. 업로드 흐름

1. 프론트엔드 `startUpload(file)` 실행  
   - `frontend/src/app/hooks/useAnalysisPipeline.ts:1615-1713`
2. `uploadFile()`이 `POST /datasets/` 요청 전송  
   - `frontend/src/lib/api.ts:577-608`
3. 백엔드 datasets router 진입  
   - `backend/app/modules/datasets/router.py:14-35`
4. `DatasetRagSyncService.upload_dataset()` 실행  
   - `backend/app/modules/rag/service.py:462-483`
5. 내부에서 `DatasetService.upload_dataset()`로 파일 저장 및 CSV 검증  
   - `backend/app/modules/datasets/service.py:128-153`
6. 저장 성공 후 `RagService.index_dataset(dataset)`로 인덱스 생성  
   - `backend/app/modules/rag/service.py:323-342`
7. 성공 시 dataset metadata 반환, 실패 시 업로드 전체 롤백

### 2-2. 업로드 이후 질문 흐름

1. 프론트엔드가 업로드 성공 후 `selectedSourceId` 저장  
   - `frontend/src/app/hooks/useAnalysisPipeline.ts:1639-1707`
2. `runQuestionStream(question, sourceId)`에서 `/chats/stream` 호출  
   - `frontend/src/app/hooks/useAnalysisPipeline.ts:1715-1779`
3. 백엔드 chat router가 `source_id` 존재 여부 검증  
   - `backend/app/modules/chat/router.py:51-71`
4. `ChatService.ask_stream()`가 dataset 조회 후 workflow 시작  
   - `backend/app/modules/chat/service.py:26-88`
5. `AgentClient._build_state()`가 workflow state 생성  
   - `backend/app/orchestration/client.py:178-202`
6. `intake_flow`가 dataset-selected path로 라우팅  
   - `backend/app/orchestration/intake_router.py:12-60`
7. `dataset_context -> guideline_flow -> planner` 순으로 진행  
   - `backend/app/orchestration/builder.py:192-222`, `284-308`
8. planner 결과에 따라 `dataset_lookup`, `rag`, `analysis`, `clarification`, `general_question`으로 분기

---

## 3. [Critical] 확정 장애

### C-1. Planner의 `invoke_with_tools()` 필수 인자 누락

**현재 상태:**
- `LLMGateway.invoke_with_tools()`는 `tools`를 keyword-only 필수 인자로 요구한다.  
  - `backend/app/core/ai/llm_gateway.py:93-115`
- 하지만 planner의 실제 호출부는 `tools=`를 넘기지 않는다.  
  - `backend/app/modules/planner/service.py:192-206`
- 같은 클래스의 `__init__()`에서는 이미 `self.planner_tools = build_planner_tools()`를 준비하고 있다.  
  - `backend/app/modules/planner/service.py:73-74`

**문제점:**
- dataset이 선택된 질문은 planner 단계에서 route tool selection을 수행해야 하는데, 정작 tool registry를 gateway에 전달하지 않는다.
- 그 결과 Python 레벨에서 즉시 `LLMGateway.invoke_with_tools() missing 1 required keyword-only argument: 'tools'`가 발생한다.

**사용자에게 보이는 결과:**
- planner node는 예외를 잡아서 `planning_failed` 출력으로 변환한다.  
  - `backend/app/orchestration/builder.py:198-216`
- 즉 사용자는 데이터셋을 선택한 정상 질문에서도 planner 단계에서 곧바로 실패 응답을 받게 된다.

**권장 수정 사항:**
1. `PlannerService._build_decision()` 호출부에 `tools=self.planner_tools`를 명시적으로 전달한다.
2. 수정 후 planner route 선택이 실제로 `tool_calls`를 반환하는지 별도 검증이 필요하다.

**관련 파일:**
- `backend/app/core/ai/llm_gateway.py`
- `backend/app/modules/planner/service.py`
- `backend/app/orchestration/builder.py`

---

## 4. [High] 업로드 단계 오류 시나리오

### H-1. 프론트엔드 확장자 가드로 인한 업로드 차단

**현재 상태:**
- 프론트엔드 `startUpload()`는 `.csv` 확장자가 아니면 즉시 에러 상태로 전환한다.  
  - `frontend/src/app/hooks/useAnalysisPipeline.ts:1627-1629`

**문제점:**
- 브라우저 단계에서 차단되므로 백엔드 validation까지 가지 않는다.
- 사용자는 “왜 업로드가 안 되는지”를 서버 응답 없이 프론트 메시지에만 의존하게 된다.

**사용자 영향:**
- `.xlsx`, `.xls`, `.tsv` 등은 현재 즉시 업로드 불가다.

---

### H-2. 빈 파일명 요청

**현재 상태:**
- datasets router는 `file.filename`이 비어 있으면 `400`을 반환한다.  
  - `backend/app/modules/datasets/router.py:19-20`

**사용자 영향:**
- 비정상 multipart 요청이나 파일 메타데이터 손상 시 업로드가 즉시 실패한다.

---

### H-3. CSV 확장자 불일치

**현재 상태:**
- `DatasetService.upload_dataset()`는 `.csv` 외 확장자를 거부한다.  
  - `backend/app/modules/datasets/service.py:135-137`

**문제점:**
- 프론트와 백엔드가 모두 CSV-only 정책을 가지고 있어 의도는 일치하지만, 지원 포맷 확장이 필요할 때 양쪽을 함께 수정해야 한다.

**사용자 영향:**
- 우회 요청이 들어와도 최종적으로 `400 "CSV 파일만 업로드할 수 있습니다."`로 실패한다.

---

### H-4. UTF-8 CSV 가독성 실패

**현재 상태:**
- 파일 저장 직후 `read_csv(..., nrows=5)`로 샘플 가독성을 검증한다.  
  - `backend/app/modules/datasets/service.py:138-147`
- reader는 `UnicodeDecodeError`, `EmptyDataError`, `ParserError`를 `DatasetReadError`로 감싼다.  
  - `backend/app/modules/datasets/service.py:74-83`

**문제점:**
- 파일은 디스크에 먼저 저장되지만, 검증 실패 시 삭제된다.
- 사용자는 업로드가 잠깐 진행된 뒤 최종적으로 실패하는 형태를 보게 된다.

**사용자 영향:**
- UTF-8이 아닌 CSV, 빈 CSV, 구조가 심하게 깨진 CSV는 `UTF-8 CSV만 업로드할 수 있습니다.`로 실패한다.

---

### H-5. 업로드 후 RAG 인덱싱 실패에 따른 전체 롤백

**현재 상태:**
- `DatasetRagSyncService.upload_dataset()`는 dataset 저장 후 곧바로 `rag_service.index_dataset(dataset)`를 호출한다.  
  - `backend/app/modules/rag/service.py:462-483`
- 인덱싱 중 예외가 나면 dataset row와 저장 파일을 함께 삭제한다.

**문제점:**
- 저장 자체는 성공했더라도 인덱싱이 실패하면 업로드 전체가 실패로 처리된다.
- 즉 “파일 저장 성공”과 “질문 가능한 dataset 생성 완료”가 분리되어 있지 않다.

**사용자 영향:**
- 사용자는 업로드 완료 직전 `500`을 볼 수 있고, 업로드 목록에도 dataset이 남지 않는다.

**세부 오류 포인트:**
- 임베딩 생성 실패  
  - `backend/app/modules/rag/service.py:165-167`
- router는 `RagEmbeddingError`를 `500 / EMBEDDING_ERROR`로 매핑  
  - `backend/app/modules/datasets/router.py:30-31`
- 그 외 예외는 `500 / "파일 업로드 중 오류가 발생했습니다."`로 처리  
  - `backend/app/modules/datasets/router.py:32-33`

---

## 5. [High] 질문 진입 및 workflow handoff 오류 시나리오

### H-6. stale `source_id` 또는 존재하지 않는 dataset 선택

**현재 상태:**
- `/chats/stream` 진입 시 chat router가 `source_id` 존재 여부를 먼저 검증한다.  
  - `backend/app/modules/chat/router.py:56-61`

**문제점:**
- 프론트가 오래된 session snapshot을 복원했거나, 업로드 후 dataset이 삭제되었으면 질문 전에 바로 막힌다.

**사용자 영향:**
- `404 "데이터셋을 찾을 수 없습니다."`

---

### H-7. 빈 질문 입력

**현재 상태:**
- `AgentClient._build_state()`는 `question_text`가 비어 있으면 workflow를 시작하지 않고 early answer를 반환한다.  
  - `backend/app/orchestration/client.py:188-191`

**사용자 영향:**
- `질문을 입력해 주세요.`

---

### H-8. dataset context 재구성 실패

**현재 상태:**
- dataset-selected path는 `dataset_context_node()`에서 `build_context(source_id)`를 호출한다.  
  - `backend/app/orchestration/builder.py:192-197`
- profile service는 dataset row, storage path, 실제 파일 존재 여부를 순서대로 확인한다.  
  - `backend/app/modules/profiling/service.py:63-75`

**문제점:**
- 업로드 이후 외부 요인으로 파일이 사라지거나 손상되면, 질문 시점의 context 재구성이 실패할 수 있다.
- 이 노드는 builder 수준에서 별도 예외 처리를 하지 않으므로, profile/build_context 내부 예외가 workflow 전체로 전파될 가능성이 있다.

**사용자 영향:**
- dataset row는 존재하지만 실제 질문 실행은 실패하는 불일치 상태가 생길 수 있다.

---

### H-9. planner 실패가 곧 전체 데이터 질문 실패로 연결됨

**현재 상태:**
- main workflow는 `dataset_context -> guideline_flow -> planner` 순서로 진행된다.  
  - `backend/app/orchestration/builder.py:294-308`
- planner 예외는 모두 `planning_failed` output으로 변환된다.  
  - `backend/app/orchestration/builder.py:198-216`

**문제점:**
- planner는 모든 dataset-backed 질문의 첫 분기점이므로, 이 단계의 장애는 dataset lookup / rag / analysis 전체를 막는다.

**사용자 영향:**
- 현재 코드 상태에서는 가장 빈번하고 가장 먼저 관측될 실패 형태다.

---

## 6. [Medium] Planner 수정 이후에도 남는 조건부 오류

### M-1. Planner tool selection 자체 실패

**현재 상태:**
- planner는 tool call이 비어 있으면 실패한다.  
  - `backend/app/modules/planner/service.py:207-209`
- tool args가 dict가 아니면 실패한다.  
  - `backend/app/modules/planner/service.py:213-215`
- 등록되지 않은 tool name이면 실패한다.  
  - `backend/app/modules/planner/service.py:295-296`

**문제점:**
- `tools` 누락을 수정해도 LLM이 기대한 function-calling 출력을 주지 않으면 여전히 `planning_failed`가 발생한다.

---

### M-2. dataset lookup 분기의 fallback 응답

**현재 상태:**
- `dataset_lookup_terminal()`은 `source_id` 또는 `profile_service`가 없으면 예외 대신 fallback 텍스트를 반환한다.  
  - `backend/app/orchestration/builder.py:168-190`

**문제점:**
- 사용자 경험 측면에서는 graceful하지만, 실제 root cause가 숨겨질 수 있다.

---

### M-3. RAG index 상태 및 evidence 부재

**현재 상태:**
- `ensure_index_for_source()`는 `no_source`, `dataset_missing`, `unsupported_format`, `existing`, `created`, `missing` 같은 상태를 반환한다.  
  - `backend/app/modules/rag/service.py:299-321`
- retrieval은 상태가 `existing` 또는 `created`일 때만 수행된다.  
  - `backend/app/orchestration/workflows/rag.py:40-83`

**문제점:**
- 인덱스가 없거나 evidence가 부족하면 hard fail 대신 “근거를 찾지 못함” 형태로 끝나므로, 사용자는 기능 실패와 evidence 부족을 구분하기 어렵다.

---

### M-4. analysis planning / execution / persistence 실패

**현재 상태:**
- analysis는 planning, execution, validation, persist 단계를 순차적으로 수행한다.  
  - `backend/app/orchestration/workflows/analysis.py:57-267`
- 서비스 레벨에서는 dataset 존재, planner route 적합성, question understanding 존재 여부, codegen/sandbox 결과, persistence 예외 등을 검증한다.  
  - `backend/app/modules/analysis/service.py:76-145`, `237-453`, `501-545`

**대표 오류:**
- `dataset not found`
- `source_id is required for analysis`
- `planner did not route this request to analysis`
- `planner did not provide question understanding`
- code generation / code validation / sandbox execution / result validation / persist 단계 실패

**문제점:**
- planner가 정상화된 이후에는 이 구간이 다음 주요 실패 영역이 된다.

---

## 7. 우선순위 정리

### 최우선 수정 대상 (P0)

1. `PlannerService._build_decision()`의 `tools` 인자 누락 수정  
   - `backend/app/modules/planner/service.py:192-206`

이 문제가 해결되지 않으면 dataset-selected 질문 흐름 전체가 planner 단계에서 멈춘다.

### 그다음 확인해야 할 운영 리스크 (P1)

2. 업로드 후 RAG 인덱싱 실패 시 전체 롤백되는 동작의 사용자 경험 검토  
   - `backend/app/modules/rag/service.py:462-483`
3. stale `source_id` 복원 시 404가 나는 세션 복원 UX 검토  
   - `backend/app/modules/chat/router.py:56-61`
4. dataset file 손실/손상 이후 profile/context 재구성 실패에 대한 방어 전략 검토  
   - `backend/app/modules/profiling/service.py`

### planner 수정 이후 재검증 대상 (P2)

5. planner tool selection 실패율  
6. RAG evidence 부족과 실제 검색 실패의 구분  
7. analysis planning / sandbox / persist 단계 실패율

---

## 최종 요약

현재 코드 기준으로 보면, 업로드 경로는 비교적 잘 방어되어 있고 실패 시에도 대부분 명확한 guard가 존재한다. 반대로 사용자가 dataset을 선택한 뒤 질문하는 핵심 경로는 planner 단계의 tool-calling 계약 누락 때문에 구조적으로 막혀 있다. 따라서 이 시스템의 현재 최우선 장애는 “데이터 업로드”가 아니라 “업로드 이후 dataset-backed 질문 분기”에 있다.
