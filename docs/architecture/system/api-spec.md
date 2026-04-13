# API 개요 및 명세

## 문서 목적

이 문서는 핵심 API의 역할과 입출력 기준을 정리한다.
현재 기준의 공개 API를 빠르게 찾고 이해할 수 있도록, 실제 라우터와 실제 경로를 기준으로 역할과 핵심 요청/응답 필드를 정리한다.

## API 설계 원칙

현재 API는 크게 아래 두 축으로 나뉜다.

- 채팅 중심 실행 API
- 기능별 보조 API

주 실행 경로는 `chat` API다.
나머지 `datasets`, `eda`, `analysis`, `preprocess`, `vizualization`, `rag`, `guidelines`는 기능별 공개 API로 동작한다.

이 문서는 모든 schema를 완전히 나열하는 문서가 아니라, “언제 쓰는가”와 “어떤 핵심 필드를 주고받는가”를 중심으로 설명하는 문서다.

## API 그룹 개요

| 그룹 | 용도 | 대표 사용 시점 | 특이사항 |
| --- | --- | --- | --- |
| `chats` | 질문 시작, 승인 대기, 재개, 히스토리 | 사용자가 대화형 분석을 시작할 때 | SSE 스트리밍 사용 |
| `datasets` | 데이터셋 업로드/조회/삭제 | 분석 대상 데이터 관리 시 | `source_id` 기반 |
| `eda` | 탐색적 데이터 분석과 전처리 추천 | 데이터 상태를 먼저 확인할 때 | 조회성 API가 많음 |
| `analysis` | 분석 실행과 저장 결과 조회 | 직접 분석 실행이 필요할 때 | 결과 조회 API 포함 |
| `preprocess` | 전처리 실행 | 승인된 전처리를 적용할 때 | 새 `output_source_id` 생성 |
| `vizualization` | 시각화 생성 | 차트 생성이 필요할 때 | 실제 경로가 `/vizualization` |
| `rag` | 검색 기반 답변과 인덱스 삭제 | 설명형 질의응답 또는 RAG 관리 시 | `204`, `404` 특이 status 사용 |
| `guidelines` | 지침서 업로드/활성화/삭제 | 도메인 지식 관리 시 | 활성화 API 존재 |

`reports`는 현재 공개 router가 없으므로 이 문서의 public API 목록에는 포함하지 않는다.

## 채팅 API

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

### `GET /datasets/{source_id}`

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

업로드는 CSV 기준으로 동작하며, 샘플 조회는 소량 preview 응답을 돌려준다.

## EDA API

EDA API는 `source_id`를 기준으로 데이터 상태를 탐색적으로 조회하는 API 그룹이다.
엔드포인트가 많기 때문에 기능별 하위 그룹으로 이해하는 것이 좋다.

### 프로파일 / 요약

- `GET /eda/{source_id}/profile`
- `GET /eda/{source_id}/summary`
- `GET /eda/{source_id}/quality`

역할:
- 데이터 구조, 기본 요약, 품질 정보를 확인한다.

### 컬럼 / 통계

- `GET /eda/{source_id}/columns/types`
- `GET /eda/{source_id}/stats`

역할:
- 컬럼 타입과 기본 통계를 확인한다.

### 탐색 분석

- `GET /eda/{source_id}/correlations/top`
- `GET /eda/{source_id}/outliers`
- `GET /eda/{source_id}/distribution`

역할:
- 상관관계, 이상치, 분포를 조회한다.

참고:
- `distribution`은 추가 쿼리 파라미터 `column`, `bins`, `top_n`을 받는다.

### 추천 / 요약

- `GET /eda/{source_id}/preprocess-recommendations`
- `GET /eda/{source_id}/insights`

역할:
- 전처리 추천과 AI 기반 요약을 제공한다.

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
- 핵심 응답 특징:
  - 분석 결과 전체 payload를 반환하는 실행형 API

### `GET /analysis/results/{analysis_result_id}`

- 역할: 저장된 분석 결과 조회
- 언제 쓰는가: 이미 실행된 분석 결과를 다시 확인할 때
- 핵심 응답 필드:
  - `analysis_result_id`
  - `source_id`
  - `question`
  - `analysis_type`
  - `analysis_plan_json`
  - `generated_code`
  - `table`
  - `chart_data`
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
- 전처리 연산 예시:
  - drop
  - impute
  - rename
  - scale
  - encode
  - parse datetime
  - outlier 처리
- 핵심 응답 필드:
  - `input_source_id`
  - `output_source_id`
  - `output_filename`
  - `summary_before`
  - `summary_after`
  - `summary_diff`

즉, 전처리 결과는 기존 source를 직접 덮어쓰는 방식이 아니라 새로운 `output_source_id`를 만들어 반환하는 구조다.

## 시각화 API

현재 시각화 API의 실제 prefix는 `/visualization`이 아니라 `/vizualization` 이다.
문서도 현재 구현 기준으로 이 경로를 그대로 사용한다.

### `POST /vizualization/manual`

- 역할: 직접 시각화 생성
- 언제 쓰는가: 데이터셋 기준으로 수동 시각화를 만들 때
- 핵심 요청 필드:
  - `source_id`
  - `chart_type`
  - `columns`
  - `limit`
- 핵심 응답 필드:
  - `chart_type`
  - `data`

### `POST /vizualization/from-analysis`

- 역할: 분석 결과 기반 시각화 생성
- 언제 쓰는가: 이미 실행된 분석 결과를 바탕으로 차트를 만들 때
- 핵심 요청 필드:
  - `analysis_result_id`
- 핵심 응답 필드:
  - `status`
  - `source_id`
  - `summary`
  - `chart`
  - `chart_data`
  - `fallback_table`

이 API는 채팅 기반 시각화 흐름 외에도 직접 시각화를 만드는 용도로 사용할 수 있다.

## RAG API

### `POST /rag/query`

- 역할: 검색 기반 질의응답 실행
- 언제 쓰는가: 설명형 질의응답이나 지식 검색이 필요할 때
- 핵심 요청 필드:
  - `query`
  - `top_k`
  - `source_filter`
- 핵심 응답 필드:
  - `answer`
  - `retrieved_chunks`
  - `executed_at`
- 특이사항:
  - 결과가 없으면 `204 No Content`
  - 인덱스가 없으면 `404`

### `DELETE /rag/sources/{source_id}`

- 역할: 특정 source의 RAG 인덱스 삭제
- 언제 쓰는가: 인덱스를 정리할 때
- 핵심 응답 형태:
  - `204 No Content`

## 지침서 API

### `POST /guidelines/upload`

- 역할: 지침서 업로드
- 언제 쓰는가: 도메인 지식 문서를 등록할 때
- 핵심 응답 필드:
  - `source_id`
  - `guideline_id`
  - `filename`
  - `is_active`

### `GET /guidelines/`

- 역할: 지침서 목록 조회
- 언제 쓰는가: 등록된 지침서를 확인할 때
- 핵심 응답 필드:
  - `total`
  - `items`

### `POST /guidelines/{source_id}/activate`

- 역할: 지침서 활성화
- 언제 쓰는가: 분석에 사용할 활성 지침서를 바꿀 때
- 핵심 응답 필드:
  - `source_id`
  - `is_active`
  - `message`

### `DELETE /guidelines/{source_id}`

- 역할: 지침서 삭제
- 언제 쓰는가: 특정 지침서를 제거할 때
- 핵심 응답 형태:
  - `204 No Content`

## 공통 응답 및 오류 패턴

현재 공개 API에서 공통적으로 알아야 할 특징은 아래와 같다.

- 채팅 API는 일반 JSON이 아니라 SSE 스트림 응답을 포함한다.
- 승인 대기 흐름은 `pending approval 조회 -> resume` 조합으로 이어진다.
- 일부 API는 기능 특성상 `404`, `422`, `500`을 사용한다.
- 결과가 없는 경우 `204 No Content`를 반환하는 API가 있다.
- 인증/권한 계층은 현재 이 문서 범위에서 다루지 않는다.

이 문서는 모든 오류 코드를 완전히 나열하는 문서가 아니라, 호출자가 이해해야 하는 대표 패턴만 정리하는 문서다.

## 이 문서를 읽는 방법

이 문서는 실제 public API를 빠르게 찾고 이해하기 위한 문서다.
실행 흐름은 `시스템 플로우 개요`, 구조는 `시스템 아키텍처`와 `백엔드 구조`, AI 내부 실행 로직은 이후 `AI Agent` 문서를 함께 보면 된다.
