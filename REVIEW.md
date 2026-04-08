# AGENT 6
Consolidated findings
[Severity: P1] 전처리 이후의 "실제로 써야 하는 dataset"을 표현하는 단일 truth가 없어 source_id가 UI, 승인, 재실행, orchestration, merge 단계마다 드리프트합니다.
Combined evidence: 로컬 approval은 생성 시점 selectedSourceId를 캡처하지만 승인/재실행 시점에는 다시 현재 선택값을 사용하고(useAnalysisPipeline.ts:1456, useAnalysisPipeline.ts:1490, useAnalysisPipeline.ts:1563), selector는 approval 중에도 잠기지 않습니다(Workbench.tsx:742). 전처리 완료 후 프론트는 output_source_id dataset을 목록에만 추가하고 후속 요청의 source_id는 계속 현재 선택값으로 보냅니다(useAnalysisPipeline.ts:928, useAnalysisPipeline.ts:1279). 백엔드는 더 나아가 source_id를 아예 "현재 UI 선택 dataset"으로 정의하고(utils.py:6), 전처리에서 output_source_id를 생성해도(executor.py:80) analysis와 dataset_context, merged_context, RAG, report는 계속 그 raw source_id를 중심으로 움직입니다(analysis.py:80, state_view.py:60, rag.py:23, report.py:73). 현재 테스트도 이 동작을 정답으로 고정합니다(test_orchestration_source_selection.py:160).
Why this is the final interpretation: Agent 1, 2, 5의 개별 지적은 서로 다른 버그가 아니라 같은 루트 원인입니다. 시스템에 raw source, pending approval source, processed output source는 존재하지만, 이를 하나의 authoritative "effective source"로 승격하는 상태 필드가 없습니다. 그래서 approval 전후, 후속 질문, RAG, report, merged context가 모두 각자 다른 규칙으로 source를 해석합니다. Agent 4의 lineage 비영속성은 이 체인을 새로고침 뒤 더 복구 불가능하게 만듭니다.
Affected boundaries: Workbench dataset selector ↔ approval/retry, preprocess_result ↔ orchestration state, dataset_context/merged_context ↔ analysis/RAG/report, dataset reload/list ↔ lineage.
Suggested verification: 행 수가 바뀌는 CSV 두 개를 올리고, A dataset에서 preprocess approval을 띄운 뒤 B로 selector를 바꿔 승인합니다. 이어서 approval 직전 request body source_id, 전처리 완료 후 follow-up request source_id, analysis planning input source_id, merged_context.dataset_context.source_id를 순서대로 비교하면 source drift가 한 번에 드러납니다.

[Severity: P1] resume API가 session_id와 run_id의 소속 관계를 검증하지 않아, 한 세션의 interrupt된 실행 결과가 다른 세션 히스토리에 저장될 수 있습니다.
Combined evidence: resume 라우터는 URL에서 session_id와 run_id를 모두 받지만(chat/router.py:66), 서비스는 세션 존재만 확인한 뒤 run_id로 그대로 재개합니다(chat/service.py:88). orchestration thread는 run_id 우선으로 결정되고(client.py:202), 완료된 assistant 메시지는 URL의 세션 쪽에 append됩니다(chat/service.py:317).
Why this is the final interpretation: Agent 2와 Agent 5가 같은 증상을 독립적으로 짚었고, 반대 근거가 없습니다. 이 문제는 UI 가정이나 제품 의도와 무관하게 HTTP 경계에서 바로 재현되는 식별자 무결성 버그입니다.
Affected boundaries: /chats/{session_id}/runs/{run_id}/resume HTTP contract ↔ LangGraph thread selection ↔ chat history persistence.
Suggested verification: 세션 A, 세션 B를 만든 뒤 B에서 interrupt를 발생시키고 session_id=A, run_id=B 조합으로 resume를 호출해 A 히스토리에 어떤 assistant message가 저장되는지 확인합니다.

[Severity: P1] 데이터 파일 형식 계약이 경계마다 달라, UI가 허용한 파일이 업로드 단계 또는 업로드 이후 EDA/preprocess 단계에서 뒤늦게 깨집니다.
Combined evidence: 프론트는 파일 선택기에서 .csv,.json,.xlsx,.xls를 노출합니다(Workbench.tsx:826), 하지만 백엔드 업로드는 .csv만 허용합니다(datasets/service.py:10, datasets/service.py:83). CSV라도 reader는 전 구간에서 utf-8 고정이라(datasets/service.py:42, preprocess/service.py:121) 비 UTF-8 CSV는 업로드 후 EDA/profile/preprocess 시점에야 터집니다. EDA는 이를 명시적으로 변환하지 않고(eda/router.py:21), preprocess도 UnicodeDecodeError를 별도 처리하지 않습니다(preprocess/router.py:10).
Why this is the final interpretation: Agent 3의 "Excel을 받는 척하지만 시각화가 못 쓴다"와 Agent 4의 "비 UTF-8 CSV가 업로드 후 뒤늦게 깨진다"는 사실상 같은 계약 문제입니다. 시스템이 지원 형식과 인코딩을 업로드 시점에 일관되게 확정하지 않아서, 실패 지점이 단계마다 달라집니다.
Affected boundaries: file picker ↔ dataset upload API, dataset storage ↔ profiling/EDA/preprocess readers, locale-specific CSV ↔ downstream pipeline.
Suggested verification: .xlsx와 cp949 CSV를 각각 업로드해 POST /datasets/, GET /eda/{source_id}/profile, POST /preprocess/apply를 순서대로 호출하고 어느 단계에서 어떤 에러로 깨지는지 비교합니다.

[Severity: P2] analysis-result 기반 시각화 계약은 경로와 payload 의미가 모두 어긋나 있어, 실제로 붙이는 순간 unusable한 API가 됩니다.
Combined evidence: 프론트는 /api/visualization/from-analysis를 호출하지만(api.ts:428) 백엔드 라우터 prefix는 /vizualization입니다(visualization/router.py:14). 게다가 라우터는 build_from_analysis_result()에 dataset source_id가 아니라 analysis_result.id를 넘겨 응답 payload의 source_id 의미까지 오염시킵니다(visualization/router.py:72).
Why this is the final interpretation: Agent 3의 P1/P2 두 건은 따로 떼면 "경로 오타"와 "payload typo"처럼 보이지만, 실제로는 하나의 contract break입니다. 경로를 맞춰도 payload source_id가 dataset identity가 아니므로 후속 revision/replay 또는 dataset lookup 연결이 계속 깨집니다.
Affected boundaries: frontend analysis-result client ↔ visualization router ↔ dataset/source resolution.
Suggested verification: createVisualizationFromAnalysis()를 실제 호출해 HTTP status를 확인하고, 라우터를 직접 호출했을 때 응답 source_id가 dataset source인지 analysis_result_id인지 비교합니다.

[Severity: P2] 잘못된 source_id와 리포트 실패가 둘 다 "fail-open"으로 처리돼, 사용자에게 보이는 진실과 내부 상태/로그의 진실이 어긋납니다.
Combined evidence: 채팅 시작 시 dataset lookup 실패는 그냥 None으로 남고(chat/service.py:35), intake router는 source_id가 비면 일반 질문 경로로 보냅니다(intake_router.py:15). 리포트 쪽은 실패해도 output.type="report_answer"와 사용자 fallback 문구를 반환하고(report.py:84, report.py:199), snapshot 요약과 trace summary는 그 실패를 에러로 승격하지 않습니다(client.py:235, trace_logging.py:299).
Why this is the final interpretation: Agent 5의 두 findings는 서로 다른 모듈이지만, 공통적으로 "사용자 의도 또는 실패 상태를 명시적으로 surface하지 않고 정상 경로 비슷하게 흘려보낸다"는 문제입니다. 그래서 잘못된 dataset을 들고 보낸 요청도 조용히 general chat로 떨어지고, 리포트 실패도 trace에서는 성공처럼 남을 수 있습니다.
Affected boundaries: dataset identity validation ↔ intake routing, report workflow ↔ trace/log summary ↔ operator debugging.
Suggested verification: 존재하지 않는 source_id로 /chats/stream을 호출해 handoff가 general_question으로 찍히는지 확인하고, report draft/save를 강제로 실패시킨 뒤 SSE 최종 답변과 trace summary JSON의 status/error를 비교합니다.

Rejected or downgraded findings
Agent 1의 "세션 복원 시 selectedSourceId/시각화 상태가 서버 히스토리와 섞일 수 있다"는 최종 목록에서 제외했습니다. 로컬 draft 상태를 유지하려는 제품 의도일 가능성을 배제할 수 없고, 현재 근거만으로는 명확한 계약 위반보다 설계 결정에 더 가깝습니다.
Agent 2의 "workflow_final_state.final_status가 일부 성공 경로에서 null이다"는 P3 수준 운영 가시성 문제로 하향했습니다. trace consumer에는 불편하지만, 현재 evidence만으로는 사용자 답변 자체가 깨지는 버그보다 한 단계 아래입니다.
Agent 4의 type_counts 중복 집계와 sample_row_count 의미 오염은 유지 후보였지만 최종 목록에서는 제외했습니다. 둘 다 품질/정확성 문제는 맞지만, 앞선 P1/P2들처럼 세션 오염이나 잘못된 dataset 사용까지 직접 이어지는 근거는 상대적으로 약했습니다.
Agent 4의 "preprocess lineage 비영속성"은 별도 finding으로 남기지 않고 첫 번째 consolidated finding의 aggravating factor로 흡수했습니다. 핵심 문제는 lineage 필드 부재 자체보다 "effective source"를 어디에도 승격하지 않는 전체 상태 모델입니다.
Agent 5의 "세션 삭제 후 reports orphan 가능성", "dataset/guideline 삭제 후 RAG cleanup 실패 시 500 반환"은 실제로 타당하지만 이번 종합본에서는 운영/정리 계층 이슈로 하향했습니다. 현재 사용자 핵심 흐름을 깨는 우선순위는 preprocess/source drift, resume contamination, file-format contract 쪽이 더 높습니다.
Agent 3의 "scatter series가 시각화 후처리에서 사라진다"는 planner 계약 위반 가능성은 인정하지만, grouped scatter를 제품에서 정말 보장해야 하는지 설계 의도가 불명확해 최종 목록에서 제외했습니다.
Final risk map
가장 위험한 사용자 흐름 1: 다중 dataset 세션에서 preprocess approval을 띄운 뒤 selector를 바꾸고 승인/재질문하는 흐름.
현재 테스트가 막는 것: 없습니다. 오히려 test_orchestration_source_selection.py:160은 raw source 유지 동작을 통과 기준으로 고정합니다.
현재 테스트가 못 막는 것: approval 대상 source 고정, output_source_id 전환, merged context source 일관성, follow-up request source drift.

가장 위험한 사용자 흐름 2: interrupt된 run을 다른 세션 URL로 resume하는 흐름.
현재 테스트가 막는 것: 없습니다. 저장소의 백엔드 테스트는 orchestration source 선택과 trace logging 위주입니다.
현재 테스트가 못 막는 것: session_id/run_id ownership 검증, cross-session history contamination, resume 이후 SSE와 DB append의 일관성.

가장 위험한 사용자 흐름 3: 실제 현업 파일(.xlsx, cp949 CSV)을 업로드해 EDA/preprocess/visualization까지 가는 흐름.
현재 테스트가 막는 것: 없습니다. Agent 3이 실행한 테스트와 저장소의 기존 테스트는 analysis processor, source selection, trace logging에만 집중돼 있습니다.
현재 테스트가 못 막는 것: 프론트 file picker와 업로드 API의 형식 계약 불일치, UTF-8 고정 reader로 인한 지연 실패, downstream 단계별 에러 코드/문구 불일치.