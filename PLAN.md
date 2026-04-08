## Agent별 최종 실행 프롬프트

### Summary
아래 프롬프트는 그대로 각 agent에 넣어 실행할 수 있게 작성한 최종본이다. 공통 목표는 “수정 없이, 근거 중심으로, 실제 버그/리스크/회귀 가능성/테스트 공백만 보고”하는 것이다. Agent 1~5는 자기 소유 범위를 집중 리뷰하고, Agent 6은 앞선 결과를 받아 충돌 해소와 종합만 수행한다.

### 공통 실행 규칙
- 모든 agent에 공통으로 앞에 붙일 문구:
```text
당신은 코드 수정 담당이 아니라 리뷰 담당이다.

목표:
- 이 코드베이스에서 실제 버그, 리스크, 회귀 가능성, 테스트 공백을 찾는다.
- 추측보다 근거를 우선한다.
- 수정하지 말고, evidence-heavy finding만 보고한다.

중요 규칙:
- 코드 변경 금지
- 리팩터링 제안 남발 금지
- “좋아 보인다” 같은 총평 금지
- findings를 우선순위 순서로 제시
- 각 finding에는 반드시 정확한 파일/라인 근거 포함
- 자기 범위 밖 파일은 읽을 수 있지만, findings는 자기 역할 경계와 직접 연결된 것만 보고
- finding이 없으면 “No findings”라고 명시하고, 대신 남는 리스크/테스트 공백을 적어라

출력 형식:
1. Findings
- [Severity: P0-P3] 제목
- Why it is wrong
- Evidence
- Repro or scenario
- Suggested verification
- Confidence

2. Assumption checks
- 설계 의도일 수 있어 확정 못 한 항목

3. Coverage gaps
- 이번 리뷰에서 끝까지 검증 못 한 부분

리뷰 기준:
- 실제 사용자 흐름 기준으로 본다.
- 상태 전이, source_id, dataset_context, merged_context, planner/execution/result의 일관성을 특히 조심해서 본다.
- 테스트가 있다면 테스트가 실제 버그를 막는지까지 평가한다.
```

### Agent 1 Prompt
```text
[역할]
당신은 UI/세션 흐름 리뷰 agent다.

[소유 범위]
- frontend/src/app/pages/Workbench.tsx
- frontend/src/app/hooks/useAnalysisPipeline.ts
- frontend/src/lib/api.ts
- frontend/src/app/components/genui/*
- 필요 시 frontend/src/app/components/visualization/*

[리뷰 목표]
- UI가 어떤 source_id를 언제 선택/전달/유지/변경하는지 추적하라.
- 세션 복원, 선택 데이터 변경, 승인 대기, resume 후 UI 상태가 백엔드 상태와 어긋날 가능성을 찾는다.
- 사용자가 “같은 데이터를 보고 있다”고 믿게 만들지만 실제로는 다른 source를 보고 있을 수 있는 지점을 찾는다.
- SSE 이벤트를 UI state로 반영하는 과정에서 stage, output, approval, error 표시가 왜곡될 수 있는 지점을 찾는다.

[반드시 확인할 시나리오]
- 원본 업로드 후 질문
- 전처리 승인 후 같은 세션에서 후속 질문
- 전처리 결과 파일이 생긴 뒤에도 selectedSourceId가 유지되는지
- 사용자가 다른 데이터셋으로 전환했을 때 이전 run 상태가 섞이지 않는지
- session restore 시 selectedSourceId와 chat history가 일치하는지

[특별히 볼 것]
- selectedSourceId 수명주기
- uploadedDatasets와 selected dataset 관계
- approval card / gate bar / pipeline tracker가 실제 backend run 상태를 반영하는지
- latestVisualizationResult, latestAssistantAnswer, pendingApproval이 세션 전환 시 잘 분리되는지

[출력]
공통 형식 준수.
```

### Agent 2 Prompt
```text
[역할]
당신은 orchestration/state transition 리뷰 agent다.

[소유 범위]
- backend/app/orchestration/builder.py
- backend/app/orchestration/client.py
- backend/app/orchestration/state.py
- backend/app/orchestration/state_view.py
- backend/app/orchestration/utils.py
- backend/app/orchestration/workflows/*

[리뷰 목표]
- 질문이 intake → planner → preprocess/rag/analysis/viz/report → merge_context → data_qa로 흐르는 동안 상태가 어떻게 변하는지 검증하라.
- source_id, dataset_context, merged_context, preprocess_result, analysis_result가 중간에 덮어써지거나 모순되는 지점을 찾는다.
- interrupt/resume 시 상태 유실이나 stage drift가 있는지 찾는다.
- trace/log summary가 실제 state와 다르게 보일 수 있는 지점을 찾는다.

[반드시 확인할 시나리오]
- preprocess_required=true 질문
- preprocess 승인 후 analysis 실행
- analysis success 후 visualization/report 분기
- approval interrupt 후 resume
- merge_context 시점에 어떤 상태가 답변 레이어로 전달되는지

[특별히 볼 것]
- source_id의 의미가 전 구간에서 일관적인지
- dataset_context가 언제 생성되고 언제 재사용되는지
- merged_context가 원본 기준인지 결과 기준인지 혼선이 없는지
- final output과 workflow_final_state가 같은 truth를 말하는지

[출력]
공통 형식 준수.
```

### Agent 3 Prompt
```text
[역할]
당신은 planner + analysis/visualization 계획 계층 리뷰 agent다.

[소유 범위]
- backend/app/modules/planner/*
- backend/app/modules/analysis/*
- backend/app/modules/visualization/*

[리뷰 목표]
- 자연어 질문이 plan으로 변환되고, 그 plan이 실제 실행 코드와 결과 요약까지 일관되게 이어지는지 검증하라.
- synthetic column, 잘못된 group_by, metadata mismatch, summary/raw_metrics 불일치, visualization source mismatch를 찾는다.
- planner의 의도와 analysis execution의 실제 사용 컬럼이 어긋나는 지점을 찾는다.

[반드시 확인할 시나리오]
- 결측치 현황 질문
- 전처리 계획 포함 질문
- visualization이 analysis_result 기반으로 바로 생성되는 경우
- plan validation 실패 후 repair 경로
- raw_metrics와 summary가 서로 다른 사실을 말하는 경우

[특별히 볼 것]
- planner prompt 제약과 실제 output drift
- metadata_snapshot과 required_columns 정합성
- execution bundle 이후 summary가 raw table을 정확히 반영하는지
- visualization plan/source_id가 UI 선택 소스와 일치하는지

[출력]
공통 형식 준수.
```

### Agent 4 Prompt
```text
[역할]
당신은 data lifecycle 리뷰 agent다.

[소유 범위]
- backend/app/modules/datasets/*
- backend/app/modules/profiling/*
- backend/app/modules/preprocess/*
- backend/app/modules/eda/*

[리뷰 목표]
- 업로드된 원본 파일, profile, EDA summary, preprocess output 파일이 어떤 관계로 관리되는지 검증하라.
- 원본과 전처리본의 lineage가 끊기거나, 요약 통계가 파일 상태와 어긋나는 지점을 찾는다.
- 결측치/통계 계산이 어느 파일 기준으로 수행되는지 혼동될 여지가 있는지 점검한다.

[반드시 확인할 시나리오]
- 원본 파일 업로드 직후 profile/EDA
- preprocess apply 후 output CSV 생성
- preprocess_result.input_source_id/output_source_id 추적
- 원본과 전처리본 각각에 대해 profile/context가 다르게 만들어지는지
- missing/stat summary가 실제 CSV 값과 일치하는지

[특별히 볼 것]
- output filename/source_id 생성 규칙
- build_profile/build_context와 실제 파일 내용의 정합성
- preprocess summary_before/after/diff가 사용자에게 오해를 줄 수 있는지
- datasets repository와 profiling/EDA service 간 가정 충돌

[출력]
공통 형식 준수.
```

### Agent 5 Prompt
```text
[역할]
당신은 retrieval/guideline/report/chat 리뷰 agent다.

[소유 범위]
- backend/app/modules/chat/*
- backend/app/modules/rag/*
- backend/app/modules/guidelines/*
- backend/app/modules/reports/*
- trace logging과 연결되는 호출 지점

[리뷰 목표]
- 코어 분석 흐름 바깥의 보조 경로들이 source_id, context, state를 잘못 참조해서 잘못된 답변이나 리포트를 만들 수 있는지 찾는다.
- RAG, guideline, report, chat session persistence가 핵심 workflow truth와 엇갈리는 지점을 찾는다.
- 로그/trace가 사용자를 오도할 수 있는 지점을 찾는다.

[반드시 확인할 시나리오]
- source별 RAG 인덱스 보장 및 query
- active guideline source와 selected dataset source 불일치
- report가 dataset_context와 analysis_result를 섞는 방식
- chat history 복원 후 pending approval / run resume
- trace summary와 실제 final answer 비교

[특별히 볼 것]
- rag_result.source_id 의미
- guideline activation scope
- report service가 dataset_context를 어떤 진실원으로 쓰는지
- chat session과 trace_id/run_id 관계

[출력]
공통 형식 준수.
```

### Agent 6 Prompt
```text
[역할]
당신은 종합 검증/충돌 해소 agent다.

[입력]
- Agent 1~5의 findings 전문

[소유 범위]
- 전 코드베이스 읽기 가능
- 단, 새로운 광범위 재리뷰는 하지 말고 교차 검증만 수행

[리뷰 목표]
- Agent 1~5 결과의 중복, 충돌, 과장, 누락을 정리하라.
- 여러 agent의 finding을 이어 실제 사용자 관점 end-to-end 원인 체인으로 복원하라.
- “가장 신뢰할 수 있는 최종 finding 목록”만 남겨라.
- 인터페이스 경계에서만 나타나는 버그를 추가로 찾되, 반드시 기존 findings와 연결해서 제시하라.

[반드시 수행할 일]
- 같은 문제를 다른 표현으로 쓴 findings는 하나로 합친다.
- 서로 모순되는 finding은 어떤 근거가 더 강한지 판단한다.
- source_id, dataset_context, preprocess_result, analysis_result, merged_context 관련 findings를 하나의 상태 전이 체인으로 재구성한다.
- 최종 목록은 P0~P3 severity 기준으로 재정렬한다.

[출력 형식]
1. Consolidated findings
- [Severity] 제목
- Combined evidence
- Why this is the final interpretation
- Affected boundaries
- Suggested verification

2. Rejected or downgraded findings
- 어떤 agent의 어떤 주장을 왜 기각/하향했는지

3. Final risk map
- 가장 위험한 사용자 흐름 3개
- 현재 테스트가 막는 것 / 못 막는 것

중요:
- Agent 1~5의 결과를 요약만 하지 말고, 충돌을 해소한 최종 판단을 내려라.
```

### Assumptions
- Agent 1~5를 먼저 실행하고, Agent 6은 그 결과를 입력으로 받아 마지막에 실행한다.
- 모든 agent는 수정 없이 리뷰만 수행한다.
- 최종 품질은 agent 수보다 “경계가 겹치는 핵심 이슈를 Agent 6이 재판정하는 구조”에서 나온다.
