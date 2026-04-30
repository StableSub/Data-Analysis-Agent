# API 개요 및 명세

## 문서 목적

이 문서는 현재 FastAPI app에 mount된 public router를 기준으로 핵심 API의 역할과 경로를 정리한다.
모든 schema를 완전히 나열하지 않고, AI와 개발자가 route drift를 빠르게 확인할 수 있는 수준으로 유지한다.

현재 API는 데이터 분석 런타임 기준이다. 새 public router가 추가되거나 기존 route 계약이 바뀌면 실제 코드 변경과 함께 이 문서를 갱신한다.

## API 설계 원칙

주 실행 경로는 `chats` API다.
나머지 `datasets`, `eda`, `analysis`, `preprocess`, `vizualization`, `rag`, `guidelines`는 기능별 공개 API로 동작한다.

`/vizualization`은 오타처럼 보이지만 현재 backend/frontend 계약의 실제 prefix이므로 문서에서도 그대로 사용한다.

## 갱신 기준

- 기준 코드: `backend/app/main.py`, `backend/app/modules/*/router.py`
- 검증 테스트: `backend/tests/test_docs_harness.py::test_api_spec_lists_all_public_fastapi_routes`
- 갱신 트리거: public router mount, HTTP method/path, SSE event name, 핵심 request/response field 변경

## API 그룹 개요

| 그룹 | 용도 | 대표 사용 시점 | 특이사항 |
| --- | --- | --- | --- |
| `chats` | 질문 시작, 승인 대기, 재개, 히스토리 | 사용자가 대화형 분석을 시작할 때 | SSE 스트리밍 사용 |
| `datasets` | 데이터셋 업로드/조회/삭제 | 분석 대상 데이터 관리 시 | 상세 조회는 `{dataset_id}`, 삭제/샘플은 `{source_id}` 기반 |
| `eda` | 탐색적 데이터 분석과 전처리 추천 | 데이터 상태를 먼저 확인할 때 | 조회성 API가 많음 |
| `analysis` | 분석 실행과 저장 결과 조회 | 직접 분석 실행이 필요할 때 | 결과 조회 API 포함 |
| `preprocess` | 전처리 실행 | 승인된 전처리를 적용할 때 | 새 `output_source_id` 생성 |
| `vizualization` | 시각화 생성 | 차트 생성이 필요할 때 | 실제 경로가 `/vizualization` |
| `rag` | 검색 기반 답변과 인덱스 삭제 | 설명형 질의응답 또는 RAG 관리 시 | `204`, `404` 특이 status 사용 |
| `guidelines` | 지침서 업로드/활성화/삭제 | 도메인 지식 관리 시 | 활성화 API 존재 |

## 채팅 API

### `POST /chats/`

- 역할: 채팅 세션 생성 또는 일반 채팅 요청 처리
- 언제 쓰는가: 스트리밍이 아닌 채팅 진입점이 필요할 때
- 핵심 요청 필드:
  - `message`
  - `session_id`

### `POST /chats/stream`

- 역할: 질문 실행 시작
- 언제 쓰는가: 사용자가 대화형 분석이나 일반 질문을 시작할 때
- 핵심 요청 필드:
  - `question`
  - `session_id`
  - `model_id`
  - `source_id`
  - `trace_id`
- 핵심 응답 형태:
  - SSE 스트림
  - 주요 이벤트: `session`, `thought`, `chunk`, `approval_required`, `done`, `error`

### `POST /chats/{session_id}/runs/{run_id}/resume`

- 역할: 승인 이후 실행 재개
- 언제 쓰는가: 전처리, 시각화, 리포트 승인/수정/취소 이후 흐름을 이어갈 때
- 핵심 요청 필드:
  - `decision`
  - `stage`
  - `instruction`
  - `trace_id`
- 참고:
  - `stage` 값은 `preprocess`, `visualization`, `report`
  - 응답은 `stream`과 동일하게 SSE 스트림으로 반환된다

### `GET /chats/runs/{run_id}/pending-approval`

- 역할: 현재 승인 대기 상태 조회
- 언제 쓰는가: 실행이 중단된 상태에서 어떤 승인 요청이 남아 있는지 확인할 때
- 핵심 응답 필드:
  - `session_id`
  - `run_id`
  - `pending_approval`

### `GET /chats/{session_id}/history`

- 역할: 채팅 히스토리 조회
- 언제 쓰는가: 기존 세션을 복원하거나 대화 내역을 다시 보여줄 때
- 핵심 응답 필드:
  - `session_id`
  - `messages`

### `DELETE /chats/{session_id}`

- 역할: 채팅 세션 삭제
- 언제 쓰는가: 특정 세션을 제거할 때
- 핵심 응답 형태:
  - `204 No Content`

## 데이터셋 API

### `POST /datasets/`

- 역할: 데이터셋 업로드
- 언제 쓰는가: 사용자가 분석 대상 CSV를 등록할 때
- 핵심 응답 필드:
  - `id`
  - `source_id`
  - `filename`
  - `filesize`

### `GET /datasets/`

- 역할: 데이터셋 목록 조회
- 언제 쓰는가: 현재 등록된 데이터셋을 고를 때
- 핵심 응답 필드:
  - `total`
  - `items`

### `GET /datasets/{dataset_id}`

- 역할: 데이터셋 상세 조회
- 언제 쓰는가: 특정 데이터셋 메타정보를 확인할 때
- 핵심 응답 필드:
  - `source_id`
  - `filename`
  - `filesize`

### `DELETE /datasets/{source_id}`

- 역할: 데이터셋 삭제
- 언제 쓰는가: 특정 데이터셋을 제거할 때
- 핵심 응답 형태:
  - `204 No Content`

### `GET /datasets/{source_id}/sample`

- 역할: 데이터셋 샘플 조회
- 언제 쓰는가: 분석 전에 데이터 구조를 빠르게 확인할 때
- 핵심 응답 필드:
  - `source_id`
  - `columns`
  - `rows`

## EDA API

### `GET /eda/{source_id}/profile`
### `GET /eda/{source_id}/summary`
### `GET /eda/{source_id}/quality`

- 역할: 데이터 구조, 기본 요약, 품질 정보를 확인한다.

### `GET /eda/{source_id}/columns/types`
### `GET /eda/{source_id}/stats`

- 역할: 컬럼 타입과 기본 통계를 확인한다.

### `GET /eda/{source_id}/correlations/top`
### `GET /eda/{source_id}/outliers`
### `GET /eda/{source_id}/distribution`

- 역할: 상관관계, 이상치, 분포를 조회한다.
- 참고: `distribution`은 `column`, `bins`, `top_n` 쿼리 파라미터를 받는다.

### `GET /eda/{source_id}/preprocess-recommendations`
### `GET /eda/{source_id}/insights`

- 역할: 전처리 추천과 AI 기반 요약을 제공한다.

## 분석 API

### `POST /analysis/run`

- 역할: 분석 실행
- 언제 쓰는가: 특정 질문과 데이터셋 기준으로 바로 분석을 실행할 때
- 핵심 요청 필드:
  - `question`
  - `source_id`
  - `session_id`
  - `request_context`
  - `guideline_context`
  - `model_id`

### `GET /analysis/results/{analysis_result_id}`

- 역할: 저장된 분석 결과 조회
- 언제 쓰는가: 이미 실행된 분석 결과를 다시 확인할 때
- 핵심 응답 필드:
  - `analysis_result_id`
  - `source_id`
  - `question`
  - `analysis_type`
  - `execution_status`
  - `error_stage`
  - `error_message`

## 전처리 API

### `POST /preprocess/apply`

- 역할: 전처리 실행
- 언제 쓰는가: 승인된 전처리 연산을 실제로 적용할 때
- 핵심 요청 필드:
  - `source_id`
  - `operations`
- 핵심 응답 필드:
  - `input_source_id`
  - `output_source_id`
  - `summary_before`
  - `summary_after`


### `POST /preprocess/apply-recommendation`

- 역할: EDA/AI 추천 기반 전처리 실행
- 언제 쓰는가: 추천된 전처리 operation 묶음을 사용자가 승인해 적용할 때
- 핵심 요청 필드:
  - `source_id`
  - `recommendation`

## 시각화 API

### `POST /vizualization/manual`

- 역할: 직접 시각화 생성
- 언제 쓰는가: 데이터셋 기준으로 수동 시각화를 만들 때
- 핵심 요청 필드:
  - `source_id`
  - `chart_type`
  - `columns`
  - `limit`

### `POST /vizualization/from-analysis`

- 역할: 분석 결과 기반 시각화 생성
- 언제 쓰는가: 이미 실행된 분석 결과를 바탕으로 차트를 만들 때
- 핵심 요청 필드:
  - `analysis_result_id`

## RAG API

### `POST /rag/query`

- 역할: 검색 기반 질의응답 실행
- 언제 쓰는가: 설명형 질의응답이나 지식 검색이 필요할 때
- 핵심 요청 필드:
  - `query`
  - `top_k`
  - `source_filter`

### `DELETE /rag/sources/{source_id}`

- 역할: 특정 source의 RAG 인덱스 삭제
- 언제 쓰는가: 인덱스를 정리할 때
- 핵심 응답 형태:
  - `204 No Content`

## 지침서 API

### `POST /guidelines/upload`

- 역할: 지침서 업로드
- 언제 쓰는가: 도메인 지식 문서를 등록할 때

### `GET /guidelines/`

- 역할: 지침서 목록 조회
- 언제 쓰는가: 등록된 지침서를 확인할 때

### `POST /guidelines/{source_id}/activate`

- 역할: 지침서 활성화
- 언제 쓰는가: 분석에 사용할 활성 지침서를 바꿀 때

### `DELETE /guidelines/{source_id}`

- 역할: 지침서 삭제
- 언제 쓰는가: 특정 지침서를 제거할 때
- 핵심 응답 형태:
  - `204 No Content`

## 공통 응답 및 오류 패턴

- 채팅 API는 일반 JSON이 아니라 SSE 스트림 응답을 포함한다.
- 승인 대기 흐름은 `pending approval 조회 -> resume` 조합으로 이어진다.
- 일부 API는 기능 특성상 `404`, `422`, `500`을 사용한다.
- 결과가 없는 경우 `204 No Content`를 반환하는 API가 있다.
- 인증/권한 계층은 현재 이 문서 범위에서 다루지 않는다.

## 이 문서를 읽는 방법

이 문서는 실제 public API를 빠르게 찾고 drift를 잡기 위한 문서다.
실행 흐름은 `../architecture/request-lifecycle.md`, 상태 계약은 `../architecture/shared-state.md`, 구조는 `backend-structure.md`와 `frontend-structure.md`를 함께 본다.

새 router를 추가한 뒤 이 문서에 route를 누락하면 docs harness가 실패해야 한다. 반대로 route 이름을 보기 좋게 정리하지 말고 실제 prefix와 path를 그대로 기록한다.
