# 공유 상태

이 문서는 메인 워크플로우와 서브그래프가 공통으로 사용하는 핵심 state 필드를 설명한다. 현재 상태 계약의 기준 코드는 `backend/app/orchestration/state.py`다.

## 관련 노트

- [[architecture/README|아키텍처 문서 안내]]
- [[architecture/request-lifecycle|질문 흐름]]
- [[architecture/components/main-workflow|메인 워크플로우 컴포넌트]]
- [[architecture/components/analysis|Analysis 컴포넌트]]
- [[architecture/components/visualization|Visualization 컴포넌트]]
- [[architecture/components/report|Report 컴포넌트]]
- [[architecture/ai-agent/backend-accuracy-audit|선택 데이터셋 질문 정확성 감사]]

## 상태 계약의 역할

이 시스템은 여러 서브그래프가 같은 실행 컨텍스트 안에서 순차적으로 state를 읽고 갱신하는 구조다. 따라서 각 필드는 단순 저장값이 아니라, 이전 단계의 산출물을 다음 단계로 넘기는 계약 역할을 한다.

## 핵심 공유 필드

### `handoff`

- 의미
  - orchestration이 즉시 사용할 다음 단계와 intent flag
- 주 생성 위치
  - `intake_flow`
- 주 소비 위치
  - 메인 그래프 분기
  - merge_context
  - preprocess / analysis / rag 이후 분기
- 주요 내용
  - `next_step`
  - `ask_analysis`
  - `ask_preprocess`
  - `ask_visualization`
  - `ask_report`
  - `ask_guideline`

### `guideline_context`

- 의미
  - `merge_context` 안에 요약되어 들어가는 guideline evidence 컨텍스트
- 주 생성 위치
  - `merge_context` node
- 주 소비 위치
  - `data_qa_terminal`
  - report
- 주요 내용
  - `guideline_source_id`
  - `guideline_id`
  - `filename`
  - `status`
  - `retrieved_chunks`
  - `retrieved_count`
  - `has_evidence`
  - `evidence_summary`

### `final_status`

- 의미
  - 하위 단계가 현재 실행 상태를 메인 그래프에 알리는 값
- 주 생성 위치
  - analysis
  - report 실패 처리
- 주 소비 위치
  - 메인 그래프 분기
- 대표 값
  - `needs_clarification`
  - `fail`
  - `success`

### `merged_context`

- 의미
  - 최종 데이터 응답이나 report 생성에 사용할 누적 컨텍스트
- 주 생성 위치
  - `merge_context` node
- 주 소비 위치
  - `data_qa_terminal`
  - report
- 주요 입력 소스
  - `request_context`
  - `handoff`
  - `preprocess_result`
  - `rag_result`
  - `guideline_result`
  - `guideline_context`
  - `insight`
  - `analysis_plan`
  - `analysis_result`
  - `visualization_result`

### `output`

- 의미
  - 최종 사용자 응답 타입과 메시지
- 주 생성 위치
  - general question terminal
  - clarification terminal
  - preprocess/report/analysis 실패 처리
  - data_qa terminal
  - report finalize
- 주 소비 위치
  - workflow 종료
  - client streaming
- 대표 타입
  - `general_question`
  - `clarification`
  - `data_qa`
  - `report_answer`
  - `planning_failed`
  - `analysis_failed`
  - `report_failed`
  - `cancelled`

### `pending_approval`

- 의미
  - approval interrupt 시점의 payload
- 주 생성 위치
  - preprocess approval
  - visualization approval
  - report approval
- 주 소비 위치
  - client의 approval event
  - resume 요청 처리
- 주요 내용
  - `stage`
  - `kind`
  - `title`
  - `summary`
  - `source_id`
  - `plan` 또는 `draft`
  - `review`

## 자주 같이 움직이는 필드

- intake 단계
  - `intent`
  - `handoff`
- preprocess 단계
  - `preprocess_decision`
  - `preprocess_plan`
  - `preprocess_result`
  - `pending_approval`
- analysis 단계
  - `question_understanding`
  - `column_grounding`
  - `analysis_plan_draft`
  - `analysis_plan`
  - `analysis_result`
  - `analysis_error`
  - `final_status`
- 응답 정리 단계
  - `rag_result`
  - `guideline_result`
  - `analysis_result`
  - `visualization_result`
  - `merged_context`
  - `output`

## 사용자에게 보이는 상태와의 관계

사용자 UI에 보이는 단계 정보와 SSE payload는 `backend/app/orchestration/client.py`가 workflow 결과를 읽어 이벤트로 내보내는 방식에 더 가깝다. 현재 브랜치에는 문서에서 가정하던 `state_view.py` 파일이 없다.

- `handoff.next_step`
  - intake가 어떤 최상위 경로를 선택했는지 표현
- `preprocess_decision`, `preprocess_plan`, `preprocess_result`
  - 전처리 필요 판단과 결과 표현
- `analysis_result`
  - 분석 성공/실패 표현
  - SQL 실행이면 `execution_engine`, `query_text` 같은 실행 메타데이터 포함
- `clarification_question`
  - clarification 상태 표현
- `rag_result`, `guideline_result`, `insight`
  - 참고 근거 사용 여부 표현
- `visualization_result`, `report_result`, `data_qa_result`, `output`
  - 최종 응답 구성 단계 표현
  - 시각화 결과는 `renderer`, `vega_lite_spec`, legacy `chart/chart_data`, `artifact`를 함께 가질 수 있다

## 관련 구현 위치

- 상태 계약
  - `backend/app/orchestration/state.py`
- 메인 그래프 분기
  - `backend/app/orchestration/builder.py`
- approval stream / final output stream
  - `backend/app/orchestration/client.py`
