# AGENT 1

**Findings**

`[P1]` 로컬 전처리 승인 대상 `source_id`가 고정되지 않아 다른 데이터셋에 승인/재실행될 수 있음  
왜 잘못됐나: 로컬 approval은 생성 시점의 `source_id`를 캡처하지만, 실제 승인 시에는 현재 선택된 `selectedSourceId`를 사용합니다. 승인 중에 사용자가 데이터셋 선택을 바꾸면, 승인 플래그와 재실행 질문이 원래 approval 대상이 아닌 다른 데이터셋으로 흘러갑니다.  
근거:
- approval payload는 생성 시 `source_id`를 캡처합니다: [useAnalysisPipeline.ts:242]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L242), [useAnalysisPipeline.ts:253]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L253)
- 로컬 approval 생성은 현재 `selectedSourceId` 기준입니다: [useAnalysisPipeline.ts:1456]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1456)~[useAnalysisPipeline.ts:1466]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1466)
- 하지만 승인 시에는 `pendingApproval.source_id`가 아니라 현재 `selectedSourceId`를 업데이트하고, 그 상태로 질문을 다시 보냅니다: [useAnalysisPipeline.ts:1490]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1490)~[useAnalysisPipeline.ts:1500]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1500)
- 그동안 데이터셋 셀렉터는 비활성화되지 않습니다: [Workbench.tsx:742]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/pages/Workbench.tsx#L742)~[Workbench.tsx:745]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/pages/Workbench.tsx#L745)
재현 시나리오:
- 데이터셋 A를 선택한 상태에서 질문을 보내 로컬 preprocess approval을 띄웁니다.
- approval 카드가 열린 상태에서 셀렉터로 데이터셋 B로 바꿉니다.
- `Approve`를 누르면 B에 `preprocessApproved`가 찍히고, 재실행 질문도 B의 `source_id`로 전송됩니다.
검증 제안:
- 두 데이터셋을 업로드한 뒤 위 시나리오로 approval 전후 `selectedSourceId`, `pendingApproval.source_id`, 재전송 요청 body의 `source_id`를 비교해 보세요.
Confidence: 높음

`[P1]` 전처리 성공 후에도 활성 데이터셋이 `output_source_id`로 전환되지 않음  
왜 잘못됐나: 백엔드는 전처리 결과로 새 `output_source_id`를 돌려주는데, 프론트는 새 데이터셋을 목록에 추가만 하고 현재 선택값은 그대로 둡니다. 그러면 직후 후속 질문, retry, 세션 스냅샷이 모두 원본 데이터셋을 계속 가리키게 됩니다.  
근거:
- `done` 처리에서 `preprocess_result.output_source_id`를 받으면 `upsertUploadedDataset(...)`만 호출하고 `setSelectedSourceId(...)`는 호출하지 않습니다: [useAnalysisPipeline.ts:928]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L928)~[useAnalysisPipeline.ts:947]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L947)
- 이후 모든 새 질문은 현재 `selectedSourceId`를 그대로 요청에 실어 보냅니다: [useAnalysisPipeline.ts:1279]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1279)~[useAnalysisPipeline.ts:1284]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1284)
재현 시나리오:
- preprocess approval이 필요한 질문을 보냅니다.
- 전처리가 적용된 뒤 백엔드는 새 `output_source_id`를 반환합니다.
- UI 드롭다운은 여전히 원본 source를 가리키고, 이어서 보내는 질문은 전처리 결과가 아니라 원본 데이터셋으로 전송됩니다.
검증 제안:
- preprocess 완료 후 드롭다운 값과 다음 `/chats/stream` body의 `source_id`를 확인해 보세요.
Confidence: 높음

`[P2]` 세션 복원 시 백엔드 히스토리와 로컬 `selectedSourceId`/시각화 상태가 섞일 수 있음  
왜 잘못됐나: 세션 복원은 백엔드에서 최신 `chatHistory`와 `pendingApproval`만 다시 받아오고, `selectedSourceId`와 `latestVisualizationResult`는 로컬 스냅샷 값을 그대로 유지합니다. 그래서 복원된 세션의 대화 내용은 서버 기준인데, 우측 패널/선택 데이터셋은 예전 로컬 상태를 가리키는 불일치가 생길 수 있습니다.  
근거:
- 복원 시 `nextContext`는 `chatHistory`, `latestAssistantAnswer`, `pendingApproval`, `stateHint`만 갱신하고 `selectedSourceId`, `latestVisualizationResult`는 건드리지 않습니다: [Workbench.tsx:327]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/pages/Workbench.tsx#L327)~[Workbench.tsx:335]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/pages/Workbench.tsx#L335)
- 그 로컬 값이 그대로 restore에 반영됩니다: [useAnalysisPipeline.ts:1682]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1682)~[useAnalysisPipeline.ts:1689]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1689)
재현 시나리오:
- 세션 A에서 시각화를 만든 뒤 다른 데이터셋을 선택하고 스냅샷을 저장합니다.
- 다른 세션으로 갔다가 다시 세션 A를 복원하면, 채팅 히스토리는 서버 기준으로 복원되지만 우측 details/chart나 선택 source는 로컬 스냅샷 값이 남을 수 있습니다.
검증 제안:
- 세션 전환 전후 `chatHistory`, `selectedSourceId`, `latestVisualizationResult`를 콘솔로 비교해 보세요.
Confidence: 중간

`[P2]` `Retry`가 실패한 run의 데이터셋이 아니라 현재 선택된 데이터셋으로 다시 전송됨  
왜 잘못됐나: retry는 실패한 run 컨텍스트를 저장하지 않고 마지막 질문 문자열만 저장합니다. 그래서 사용자가 에러 후 데이터셋 선택을 바꾸면, `Retry`는 같은 질문을 다른 `source_id`로 다시 보냅니다.  
근거:
- 마지막 질문은 문자열만 저장합니다: [useAnalysisPipeline.ts:1438]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1438)
- retry는 그 문자열을 그대로 다시 `handleSend()`에 넘깁니다: [useAnalysisPipeline.ts:1563]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1563)~[useAnalysisPipeline.ts:1568]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1568)
- 실제 요청의 `source_id`는 retry 시점의 현재 `selectedSourceId`입니다: [useAnalysisPipeline.ts:1279]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1279)~[useAnalysisPipeline.ts:1284]( /Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1284)
재현 시나리오:
- 데이터셋 A로 질문을 보내 실패시킵니다.
- 셀렉터를 B로 바꾼 뒤 `Retry`를 누릅니다.
- 동일 질문이 B로 전송됩니다.
검증 제안:
- 실패 직후와 retry 직전의 `selectedSourceId`, retry 요청 body를 비교해 보세요.
Confidence: 높음

**Assumption Checks**
- `pendingApproval.source_id`를 payload에 담는 설계라면, approval과 retry는 “현재 UI 선택값”이 아니라 “approval/run이 만들어졌을 때의 source”에 묶여야 한다고 가정했습니다.
- `preprocess_result.output_source_id`를 백엔드가 돌려주는 이상, 프론트도 그 결과 source를 후속 작업의 기준으로 삼아야 한다고 가정했습니다.
- 세션 복원은 백엔드 히스토리를 authoritative source로 삼아 UI 상태를 맞추는 것이 의도라고 가정했습니다. 만약 제품 의도가 “대화만 서버 기준, 데이터 선택과 우측 패널은 로컬 draft 유지”라면 3번은 downgrade될 수 있습니다.

**Coverage Gaps**
- 이번 검토는 Agent 1 범위의 프론트 파일만 봤고, 백엔드 SSE payload 의미를 코드로 재검증하지는 않았습니다.
- 실제 브라우저 상호작용으로 재현한 것은 아니고, 정적 코드 경로와 상태 전파만 기준으로 봤습니다.
- `frontend/src/app/components/genui/*` 중 시각/문구 레벨의 placeholder 문제는 이번 범위에서 제외했고, `source_id`/session/approval alignment에 직접 연결되는 부분만 봤습니다.

# AGENT 2
1. **Findings**

- [Severity: P1] 전처리 승인 후에도 orchestration이 전처리 산출물 `output_source_id`를 실행 대상 source로 전환하지 않습니다.
  - Why it is wrong  
    전처리 단계는 새 파일과 새 `output_source_id`를 만들어 놓는데, 이후 analysis/rag/visualization/report가 모두 여전히 원본 `state.source_id`를 기준으로 움직입니다. 그래서 state 안에는 `preprocess_result.status="applied"`와 `output_source_id`가 남아 있는데, 실제 계산과 `dataset_context`는 원본 기준으로 유지되는 모순 상태가 됩니다.
  - Evidence  
    [utils.py:6](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/utils.py#L6) 에서 `resolve_target_source_id()`는 `state.source_id`만 반환합니다.  
    [preprocess/executor.py:80](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/preprocess/executor.py#L80) 에서는 전처리 성공 시 `preprocess_result.output_source_id`를 분명히 저장합니다.  
    [analysis.py:77](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/analysis.py#L77) 의 planning/execution은 모두 `resolve_target_source_id(state)`를 사용합니다.  
    [state_view.py:60](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/state_view.py#L60) 의 `build_merged_context()`도 현재 `dataset_context`를 그대로 싣고, 별도로 `preprocess_result`만 추가합니다.  
    그리고 이 동작은 테스트로도 고정돼 있습니다. [test_orchestration_source_selection.py:162](/Users/anjeongseob/Desktop/Project/capstone-project/backend/test_orchestration_source_selection.py#L162) 와 [test_orchestration_source_selection.py:174](/Users/anjeongseob/Desktop/Project/capstone-project/backend/test_orchestration_source_selection.py#L174) 는 “전처리 후에도 raw-source를 계속 사용한다”는 현재 동작을 통과 기준으로 삼고 있습니다.
  - Repro or scenario  
    사용자가 결측치 분석 요청 후 전처리를 승인하면, 시스템은 “전처리를 적용했다”고 말하지만 실제 analysis와 merged_context는 여전히 원본 CSV를 기준으로 동작합니다. 이후 같은 run의 분석/시각화/리포트는 전처리본이 아니라 원본 기준 결과를 낼 수 있습니다.
  - Suggested verification  
    전처리 승인 후 analysis planning, dataset fetch, result persist, merged_context.dataset_context.source_id가 모두 `preprocess_result.output_source_id`를 가리키는지 end-to-end로 검증해야 합니다.
  - Confidence  
    High

- [Severity: P2] `workflow_final_state.final_status`가 성공한 terminal path의 truth를 일관되게 나타내지 않습니다.
  - Why it is wrong  
    `general_question_terminal`과 `data_qa_terminal`은 최종 `output`만 만들고 `final_status="success"`를 설정하지 않습니다. 그래서 실제 응답은 정상 생성됐는데도 workflow snapshot/final_state 기준으로는 성공 여부가 `null`로 남습니다. 상태 전이 요약과 실제 최종 응답이 다른 truth를 말하는 구조입니다.
  - Evidence  
    [builder.py:135](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/builder.py#L135) 의 `general_question_terminal()`은 `output`만 반환합니다.  
    [builder.py:196](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/builder.py#L196) 의 `data_qa_terminal()`도 `output`만 반환합니다.  
    반면 [client.py:109](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/client.py#L109) 는 `workflow_final_state` 로그를 남기고, [client.py:296](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/client.py#L296) 에서 `final_status`를 그대로 snapshot에서 읽어 요약합니다.
  - Repro or scenario  
    데이터셋 없는 일반 질문 경로, 또는 fallback RAG 이후 `data_qa_terminal`로 끝나는 경로는 성공 응답을 보내도 `workflow_final_state.final_status`는 비어 있을 수 있습니다. trace/log consumer가 `final_status`를 truth로 보면 성공 run을 미완료 상태로 오판할 수 있습니다.
  - Suggested verification  
    general-question 성공 경로와 rag/data_qa 성공 경로에서 `workflow_final_state.final_status`가 명시적으로 success인지 확인하는 테스트가 필요합니다.
  - Confidence  
    High

2. **Assumption checks**

- analysis 서브그래프가 재planning으로 `planning_result.need_visualization`이나 `need_report`를 바꿔도, main builder는 이후 분기를 여전히 `handoff` 기준으로 탑니다. [analysis.py:102](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/analysis.py#L102), [builder.py:107](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/builder.py#L107), [builder.py:119](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/builder.py#L119)  
  현재는 `resolve_target_source_id()`가 재planning 자체를 거의 막고 있어서 즉시 드러나진 않지만, source 전환을 바로잡는 순간 `handoff` 재동기화 문제가 같이 표면화될 가능성이 큽니다.
- `source_id`를 “항상 UI 선택 원본을 뜻하는 불변 값”으로 유지하려는 설계 의도일 수는 있습니다. 다만 그 경우 [preprocess/executor.py:82](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/preprocess/executor.py#L82) 의 `output_source_id`와 현재 사용자 문구는 “전처리 후 그 결과로 이어서 분석한다”는 기대를 만들기 때문에, 의도와 사용자 인식이 이미 어긋나 있습니다.

3. **Coverage gaps**

- `python3 -m unittest backend.test_orchestration_source_selection` 는 실행했고 통과했습니다. 다만 이 테스트는 첫 번째 finding을 막는 게 아니라 오히려 현재의 잘못된 source 고정을 승인하는 형태입니다.
- main workflow 전체를 실제 LangGraph interrupt/resume + SSE로 끝까지 재현하는 통합 테스트는 이번 범위에서 돌리지 못했습니다.
- visualization/report 승인 경로까지 포함한 `preprocess -> analysis -> visualization/report -> merge_context -> final answer` end-to-end 검증은 현재 테스트로 보장되지 않습니다.

# AGENT 3

1. Findings

- [Severity: P1] `from-analysis` 시각화 API가 경로 오타로 실제로는 호출 불가합니다.
  - Why it is wrong: 프론트는 `/api/visualization/from-analysis`로 호출하는데, 백엔드는 `/vizualization`로 라우팅하고 있습니다. 별도 alias가 없어서 이 엔드포인트는 404가 납니다.
  - Evidence: [router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/router.py#L14), [api.ts](/Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/lib/api.ts#L428)
  - Repro or scenario: 분석 결과가 저장된 뒤 `createVisualizationFromAnalysis()`를 호출하면 프론트는 `/api/visualization/from-analysis`로 요청하지만 서버에는 그 경로가 없습니다.
  - Suggested verification: 서버 기동 후 `/api/visualization/from-analysis`와 `/vizualization/from-analysis`를 각각 호출해 응답 코드를 비교하면 바로 확인됩니다.
  - Confidence: 0.99

- [Severity: P2] `/from-analysis` 응답의 `source_id`가 데이터셋 source가 아니라 `analysis_result_id`로 오염됩니다.
  - Why it is wrong: `build_from_analysis_result()`는 입력받은 `source_id`를 그대로 응답에 넣는데, 라우터가 여기에 `result.id`를 넘기고 있습니다. 이 값은 분석 결과 ID이지 데이터셋 source가 아니므로, 이 payload를 후속 시각화 흐름에 재사용하면 데이터셋 조회가 깨집니다.
  - Evidence: [router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/router.py#L72), [service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/service.py#L152), [models.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/results/models.py#L8)
  - Repro or scenario: `/from-analysis` 응답의 `source_id`를 다시 dataset lookup에 쓰면 `VisualizationService.resolve_source_path()`는 해당 ID를 찾지 못합니다. revision/replay 류 흐름이 붙는 순간 `dataset_missing`으로 떨어질 가능성이 큽니다.
  - Suggested verification: `/from-analysis` 응답의 `source_id`를 로그로 확인하고, 그 값을 `resolve_source_path()`에 넣어 `None`이 나오는지 확인하면 됩니다.
  - Confidence: 0.91

- [Severity: P2] 시각화 모듈은 앱이 허용하는 Excel 업로드를 실제로는 처리하지 못합니다.
  - Why it is wrong: 워크벤치는 `.xlsx/.xls` 업로드를 허용하지만, 시각화 계획/미리보기는 `.csv`만 허용하고 수동 시각화도 무조건 `read_csv()`를 사용합니다. 따라서 “업로드는 됐는데 시각화만 실패”하는 타입 불일치가 생깁니다.
  - Evidence: [service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/service.py#L63), [service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/service.py#L99), [Workbench.tsx](/Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/pages/Workbench.tsx#L829)
  - Repro or scenario: `.xlsx` 파일 업로드 후 시각화 요청 시 `build_visualization_plan()` 경로는 `unsupported_format`으로 빠지고, 수동 시각화는 `read_csv()` 단계에서 실패할 수 있습니다.
  - Suggested verification: `.xlsx` 업로드 후 시각화 요청과 manual viz 요청을 각각 실행해 에러 코드를 확인하면 됩니다.
  - Confidence: 0.97

- [Severity: P2] scatter 관계 분석에서 series/color 차원을 계획 계층은 요구하지만 시각화 후처리에서 버립니다.
  - Why it is wrong: 분석 계획/코드 생성 계약은 scatter 질문에서 `series` 컬럼을 유지하라고 요구합니다. 그런데 후처리기는 scatter일 때 항상 `series_key=None`으로 고정하고 단일 `ChartSeries`만 만듭니다. 결과적으로 category별 관계를 보라는 질문이 와도 색/시리즈 분리가 사라집니다.
  - Evidence: [run_service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/analysis/run_service.py#L64), [processor.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/analysis/processor.py#L423), [processor.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/processor.py#L137), [processor.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/processor.py#L233)
  - Repro or scenario: “line별 temp-speed 관계를 산점도로 보여줘” 같은 질문에서 table에는 `line`이 있어도 chart payload는 한 개 series로 합쳐져 category 구분이 사라집니다.
  - Suggested verification: scatter + series가 포함된 analysis result fixture를 넣고 생성된 `chart_data.series` 개수와 label을 확인하면 됩니다.
  - Confidence: 0.88

2. Assumption checks

- `/api/visualization/from-analysis`가 현재 UI에서 아직 실사용되지 않는다면 1번은 latent bug일 수는 있습니다. 다만 코드상 계약은 이미 깨져 있습니다.
- grouped scatter를 의도적으로 미지원한 것이라면, planner/codegen prompt와 expected output에서 `series`를 요구하지 않도록 계약을 먼저 맞춰야 합니다.

3. Coverage gaps

- 이번 검토에서 실행한 테스트는 `python3 -m pytest backend/test_analysis_processor.py backend/test_orchestration_source_selection.py backend/test_trace_logging.py -q`였고 모두 통과했습니다.
- 하지만 이 스위트는 `backend/app/modules/visualization/router.py` 경로 매핑, non-CSV visualization path, scatter series 보존을 검증하지 않습니다.
- `planner -> analysis -> visualization/from-analysis`를 실제 HTTP 레벨로 잇는 통합 테스트가 없어 1번, 2번 류의 경계 버그가 그대로 통과하고 있습니다.

# AGENT 4

**Findings**

- [Severity: P1] UTF-8이 아닌 CSV는 업로드 시에는 통과되지만, 이후 profile/EDA/preprocess 경로에서 클라이언트가 이해할 수 있는 검증 오류가 아니라 런타임 오류로 터집니다.
  - Why it is wrong: 업로드 단계는 파일 확장자만 검사하지만, 이후 모든 CSV reader는 `utf-8`을 고정 사용합니다. 그래서 `cp949`나 `euc-kr` 같은 정상 CSV도 업로드는 성공한 뒤, 나중에 `UnicodeDecodeError`로 실패합니다. `/datasets/{source_id}/sample`은 이를 `422`로 변환하지만, EDA와 preprocess는 그렇지 않아 같은 파일이 업로드는 성공하고 이후에는 `500` 성격의 실패를 냅니다.
  - Evidence: [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/datasets/service.py#L42) [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/datasets/service.py#L76) [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/profiling/service.py#L74) [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/profiling/service.py#L171) [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/preprocess/service.py#L110) [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/eda/service.py#L101) [router.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/datasets/router.py#L72) [router.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/preprocess/router.py#L10) [router.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/eda/router.py#L21)
  - Repro or scenario: 로컬에서 `cp949` 인코딩 CSV로 재현했습니다. 파일은 dataset으로 받아들여졌지만, `DatasetProfileService.build_profile()`와 `PreprocessService.apply()`가 둘 다 `UnicodeDecodeError`로 실패했습니다.
  - Suggested verification: `cp949` CSV를 업로드한 뒤 `/eda/{source_id}/profile`과 `/preprocess/apply`를 호출해, 업로드 이후에야 실패하는지 확인하면 됩니다.
  - Confidence: High

- [Severity: P2] EDA summary가 boolean 컬럼과 group-key 컬럼을 categorical에도 중복 집계해서, `type_counts` 합계가 실제 컬럼 수보다 커질 수 있습니다.
  - Why it is wrong: profiling 단계에서 `boolean` 컬럼은 `boolean_columns`와 `categorical_columns` 둘 다에 들어가고, `group_key`도 `group_key_columns`와 `categorical_columns` 둘 다에 들어갑니다. 그런데 EDA summary는 이 리스트 길이를 서로 겹치지 않는 독립 카테고리처럼 그대로 노출합니다.
  - Evidence: [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/profiling/service.py#L98) [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/profiling/service.py#L107) [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/eda/service.py#L402)
  - Repro or scenario: 로컬에서 `flag`, `value` 두 컬럼짜리 CSV로 재현했습니다. profile 결과가 `column_count=2`, `categorical=['flag']`, `boolean=['flag']`로 나와, 하나의 컬럼이 summary에서는 두 번 집계됩니다.
  - Suggested verification: boolean 컬럼 1개와 numeric 컬럼 1개가 있는 dataset으로 `/eda/{source_id}/summary`를 호출해 `column_count`와 `type_counts` 합계를 비교하면 됩니다.
  - Confidence: High

- [Severity: P2] `sample_row_count`가 실제 profiling에 사용된 row 수가 아니라 최대 3으로 잘려 저장되고, 이 값이 preprocess review payload의 `row_count`로도 재사용됩니다.
  - Why it is wrong: profiling은 최대 2000행을 읽어 타입 추론과 결측 통계를 계산하지만, 결과에는 `sample_row_count=min(len(sample_df), 3)`만 저장합니다. EDA summary도 이 값을 그대로 노출하고, preprocess review도 이를 `plan.row_count`로 사용하기 때문에 큰 데이터셋도 사용자에게 “3행 기준”처럼 보일 수 있습니다.
  - Evidence: [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/profiling/service.py#L62) [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/profiling/service.py#L128) [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/eda/service.py#L402) [planner.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/preprocess/planner.py#L113)
  - Repro or scenario: 로컬에서 10행 CSV로 재현했고, 결과 profile은 `row_count=10`, `sample_row_count=3`, `sample_rows_len=3`이었습니다.
  - Suggested verification: 3행보다 큰 CSV로 profile을 만든 뒤 `/eda/{source_id}/summary.sample_row_count` 또는 preprocess approval payload의 `plan.row_count`를 확인하면 됩니다.
  - Confidence: High

- [Severity: P2] Preprocess lineage가 응답에만 잠깐 존재하고 영속 저장되지 않아, 파생 dataset이 재로딩/목록 조회 이후에는 원본과의 관계를 잃습니다.
  - Why it is wrong: `PreprocessService.apply()`는 결과 CSV를 새 `Dataset` row로 저장하지만, `datasets` 테이블에는 부모 source를 가리키는 필드가 없습니다. lineage 정보는 `PreprocessApplyResponse(input_source_id, output_source_id)`에만 있고, 이 응답이 사라지면 `/datasets`나 DB만으로는 어떤 dataset이 어떤 원본에서 파생됐는지 복원할 수 없습니다.
  - Evidence: [models.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/datasets/models.py#L8) [service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/preprocess/service.py#L110) [schemas.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/preprocess/schemas.py#L115)
  - Repro or scenario: preprocess를 한 번 적용한 뒤 클라이언트를 새로고침하거나 `/datasets/`를 다시 조회하면, 결과 파일은 dataset으로 남아 있지만 원본 raw dataset과의 연결은 어디에도 남지 않습니다.
  - Suggested verification: processed dataset을 하나 만든 뒤 `/datasets/` 응답과 DB row를 확인해, output이 어떤 input에서 왔는지 복원 가능한 필드가 있는지 보면 됩니다.
  - Confidence: Medium-High

**Assumption checks**

- `boolean` / `group_key`를 `categorical`과 겹치게 둔 것은 내부 분류 체계로는 의도였을 수 있습니다. 다만 `EDASummaryResponse.type_counts`는 외부에 공개되는 count breakdown이라, 중복 집계라면 명시적 문서화가 없을 경우 오해를 유발합니다.
- `sample_row_count`를 “프로파일링에 사용한 행 수”가 아니라 “미리보기로 보여주는 행 수”로 의도했을 수 있습니다. 그래도 그 값을 preprocess review의 `row_count`로 재사용하는 것은 계약 의미가 어긋납니다.

**Coverage gaps**

- preprocess 이후 downstream analysis가 의도적으로 raw `source_id`를 유지해야 하는지 여부는 orchestration 경계 쪽 설계 판단이 더 커서, 이번 Agent 4 범위에서는 깊게 재판정하지 않았습니다.
- 현재 `datasets`, `profiling`, `preprocess`, `eda`에 대한 직접 테스트는 사실상 없습니다. 존재하는 백엔드 테스트는 orchestration과 trace logging 중심이라, 위 4개 이슈를 막아 주는 회귀 테스트가 없는 상태입니다.

# AGENT 5
**Findings**

1. `[Severity: P1]` 승인된 전처리 결과가 이후 `rag`/`analysis`/`report` 경로에서 전혀 사용되지 않습니다.  
Why it is wrong: 전처리는 새 파일과 `output_source_id`를 만들지만, 이후 소스 해석은 계속 원본 UI 선택 `source_id`만 읽습니다. 그래서 사용자는 “전처리를 승인했으니 이후 분석/리포트가 가공된 데이터 기준으로 진행된다”고 믿게 되지만, 실제 후속 단계는 원본 파일을 계속 참조합니다.  
Evidence: 전처리 실행은 `output_source_id`를 남깁니다([preprocess/executor.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/preprocess/executor.py#L80)). 그런데 실제 source 해석기는 `preprocess_result.output_source_id`를 보지 않고 원본 `state.source_id`만 반환합니다([orchestration/utils.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/orchestration/utils.py#L6)). 이후 `rag`는 그 값을 그대로 사용하고([workflows/rag.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/orchestration/workflows/rag.py#L24)), `analysis`도 같은 값을 씁니다([workflows/analysis.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/orchestration/workflows/analysis.py#L80), [workflows/analysis.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/orchestration/workflows/analysis.py#L173)). `report`는 그 analysis/dataset context를 그대로 소비합니다([workflows/report.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/orchestration/workflows/report.py#L72)).  
Repro or scenario: 결측치 제거/대체가 포함된 질문을 보내 전처리를 승인한 뒤, 이어지는 리포트나 RAG 기반 답변을 확인하면 전처리 출력이 아니라 원본 데이터 기준 결과가 계속 나옵니다.  
Suggested verification: 전처리 승인 전후 row count가 달라지는 CSV로 질문을 만들고, 생성된 `output_source_id` 파일의 통계와 최종 analysis/report 결과를 비교합니다.  
Confidence: High

2. `[Severity: P1]` `resume` API가 `session_id`와 `run_id`의 소속 관계를 검증하지 않아, 한 세션의 승인 대기 실행 결과가 다른 세션 히스토리에 저장될 수 있습니다.  
Why it is wrong: `POST /chats/{session_id}/runs/{run_id}/resume`는 URL에 두 식별자를 모두 받지만, 실제로는 `session_id`가 존재하는지만 확인하고 실행 재개는 `run_id` thread 기준으로 합니다. 그 뒤 최종 assistant 메시지는 URL의 `session_id` 쪽에 저장하므로, 잘못된 조합이 들어오면 세션 히스토리가 섞입니다.  
Evidence: 라우터는 두 값을 모두 받습니다([chat/router.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/chat/router.py#L66)). 서비스는 세션 존재만 확인한 뒤([chat/service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/chat/service.py#L98)) `run_id`로만 resume를 호출합니다([chat/service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/chat/service.py#L125)). `AgentClient`는 실제 thread id를 `run_id` 우선으로 구성합니다([orchestration/client.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/orchestration/client.py#L202)). 마지막엔 결과를 URL에서 받은 세션에 저장합니다([chat/service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/chat/service.py#L317)).  
Repro or scenario: 세션 A와 세션 B를 만들고, B에서 approval interrupt를 발생시킨 뒤 `session_id=A`, `run_id=B`로 resume를 호출하면 B의 결과가 A 대화 히스토리에 저장됩니다.  
Suggested verification: resume integration test에서 서로 다른 `session_id`/`run_id`를 교차 전달하고, 저장된 assistant message의 `session_id`를 확인합니다.  
Confidence: High

3. `[Severity: P2]` 존재하지 않는 `source_id`가 들어와도 오류를 내지 않고 일반 질문 경로로 조용히 떨어집니다.  
Why it is wrong: 사용자가 dataset을 선택했다고 믿고 요청했는데, backend는 dataset lookup 실패를 오류로 올리지 않고 `source_id=None` 상태로 orchestration을 시작합니다. 그 결과 분석이 아니라 일반 답변 경로로 가면서, 잘못된 dataset 참조가 사용자에게 드러나지 않습니다.  
Evidence: 채팅 시작 시 dataset lookup 실패는 그냥 `None`으로 남깁니다([chat/service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/chat/service.py#L35)). orchestration state도 `source_id=None`으로 빌드됩니다([orchestration/client.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/orchestration/client.py#L190)). intake router는 `source_id`가 비면 무조건 `general_question`으로 라우팅합니다([orchestration/intake_router.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/orchestration/intake_router.py#L15)).  
Repro or scenario: 삭제된 dataset의 `source_id`를 들고 `/chats/stream`을 호출하면, “데이터셋을 찾을 수 없습니다”가 아니라 dataset 없는 일반 질문 흐름으로 진행됩니다.  
Suggested verification: 존재하지 않는 `source_id`로 채팅 요청을 보내고, intake handoff가 `general_question`으로 찍히는지 확인합니다.  
Confidence: High

4. `[Severity: P2]` report 생성 실패가 trace summary에서는 성공으로 기록될 수 있어, 실제 final answer와 운영 로그가 서로 다른 사실을 말합니다.  
Why it is wrong: report workflow는 실패 시 `report_result.status="failed"`와 “리포트 생성에 실패했습니다.”라는 fallback 답변을 반환하지만, trace summary는 그 실패를 오류로 승격하지 않습니다. 운영자는 trace를 보면 성공으로 보는데, 사용자는 실패 메시지를 받는 상태가 됩니다.  
Evidence: report workflow 실패 경로는 `output.type="report_answer"`를 유지한 채 실패 payload만 남깁니다([workflows/report.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/orchestration/workflows/report.py#L84), [workflows/report.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/orchestration/workflows/report.py#L199)). snapshot 요약은 `report_result.status="failed"`를 실패로 반영하지 않습니다([orchestration/client.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/orchestration/client.py#L235)). chat done 로그도 preprocess/analysis만 error field로 승격하고 report failure는 무시합니다([chat/service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/chat/service.py#L180), [chat/service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/chat/service.py#L344)). trace summary는 `chat.done`에 `error_message`가 없으면 success로 마감합니다([trace_logging.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/core/trace_logging.py#L299)).  
Repro or scenario: `build_report_draft()` 또는 최종 저장을 실패시키면 사용자는 실패 답변을 받지만 trace summary는 `status: success`로 남을 수 있습니다.  
Suggested verification: report draft/save를 mock failure로 만들어 실행한 뒤, SSE 최종 답변과 trace summary JSON의 `status`/`error`를 비교합니다.  
Confidence: High

5. `[Severity: P2]` chat session 삭제 시 `reports` row가 고아 데이터로 남을 수 있습니다.  
Why it is wrong: `Report.session_id`는 FK cascade를 선언하지만, 현재 SQLite 엔진은 foreign key를 켜지 않습니다. 또 `ChatSession`은 `messages`만 ORM cascade가 있고 `reports` 관계는 없습니다. 그래서 세션 삭제가 리포트 삭제로 실제 연결되지 않습니다.  
Evidence: SQLite 엔진 설정에는 `PRAGMA foreign_keys=ON`이 없습니다([core/db.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/core/db.py#L7)). `Report`는 `ondelete="CASCADE"`를 선언하지만([reports/models.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/reports/models.py#L14)), `ChatSession`은 `messages`에만 ORM cascade를 둡니다([chat/models.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/chat/models.py#L12)). session deletion은 별도 report cleanup 없이 session row만 지웁니다([chat/repository.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/chat/repository.py)).  
Repro or scenario: report를 생성한 세션을 삭제한 뒤 `reports` 테이블을 보면 해당 `session_id`를 가진 row가 남을 수 있습니다.  
Suggested verification: report가 저장된 세션을 삭제한 뒤 DB에서 `reports where session_id = <deleted>`를 조회합니다.  
Confidence: High

6. `[Severity: P2]` dataset/guideline 삭제는 primary delete가 끝난 뒤 RAG cleanup에서 실패하면 500을 반환해, 사용자에게는 “실패”로 보이지만 리소스는 이미 삭제된 상태가 됩니다.  
Why it is wrong: sync delete는 먼저 primary resource를 삭제한 뒤 RAG source cleanup을 수행하는데, cleanup 예외를 잡지 않습니다. 그래서 응답은 500이지만 실제 dataset/guideline row와 파일은 이미 사라집니다. 재시도하면 404가 떠서 사용자 관점 상태가 모순됩니다.  
Evidence: dataset 삭제는 primary delete 후 `rag_service.delete_source()`를 그대로 호출합니다([rag/service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/rag/service.py#L485)). guideline도 동일합니다([rag/service.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/rag/service.py#L533)). 라우터는 이 예외를 처리하지 않고 204/404만 가정합니다([datasets/router.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/datasets/router.py#L61), [guidelines/router.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/guidelines/router.py#L64)).  
Repro or scenario: 파일시스템 권한 문제나 RAG DB 오류로 `delete_source()`가 실패하면 DELETE 응답은 500이지만, dataset/guideline detail은 이미 404가 됩니다.  
Suggested verification: `delete_source()`를 강제로 raise하게 mock한 뒤 DELETE API 응답과 primary row/file 존재 여부를 같이 확인합니다.  
Confidence: Medium-High

**Assumption checks**

- 활성 guideline을 전역 1개로 관리하는 설계는 코드상 일관적입니다([guidelines/repository.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/modules/guidelines/repository.py), [workflows/guideline.py](/Users/anjeongseob/Desktop/Project/Capstone-Project/backend/app/orchestration/workflows/guideline.py#L61)). 이게 제품 요구사항이라면 문제는 아닙니다. 세션별/사용자별 guideline scope를 기대하는 제품이라면 별도 버그가 됩니다.
- `source_id`가 비었을 때 일반 질문 경로로 가는 동작 자체는 의도일 수 있습니다. 다만 “사용자가 dataset을 선택했다고 보낸 요청인데 lookup이 실패한 경우”까지 같은 경로로 처리하는 것이 의도인지 확인이 필요합니다.

**Coverage gaps**

- live SSE 기준으로 approval interrupt/resume을 끝까지 때려보는 통합 테스트는 실행하지 못했습니다.
- RAG cleanup 실패와 report draft/save 실패는 코드 경로로는 명확했지만, 실제 런타임에 강제로 오류를 주입해 보진 못했습니다.
- trace summary mismatch는 실제 실패 trace 파일을 생성해 대조하지는 않았고, 코드 경로 분석 기준입니다.

# AGENT 6

1. Consolidated findings

- [Severity: P1] 전처리 이후의 "실제로 써야 하는 dataset"을 표현하는 단일 truth가 없어 `source_id`가 UI, 승인, 재실행, orchestration, merge 단계마다 드리프트합니다.  
  Combined evidence: 로컬 approval은 생성 시점 `selectedSourceId`를 캡처하지만 승인/재실행 시점에는 다시 현재 선택값을 사용하고([useAnalysisPipeline.ts:1456](/Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1456), [useAnalysisPipeline.ts:1490](/Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1490), [useAnalysisPipeline.ts:1563](/Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1563)), selector는 approval 중에도 잠기지 않습니다([Workbench.tsx:742](/Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/pages/Workbench.tsx#L742)). 전처리 완료 후 프론트는 `output_source_id` dataset을 목록에만 추가하고 후속 요청의 `source_id`는 계속 현재 선택값으로 보냅니다([useAnalysisPipeline.ts:928](/Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L928), [useAnalysisPipeline.ts:1279](/Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/hooks/useAnalysisPipeline.ts#L1279)). 백엔드는 더 나아가 `source_id`를 아예 "현재 UI 선택 dataset"으로 정의하고([utils.py:6](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/utils.py#L6)), 전처리에서 `output_source_id`를 생성해도([executor.py:80](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/preprocess/executor.py#L80)) analysis와 `dataset_context`, `merged_context`, RAG, report는 계속 그 raw `source_id`를 중심으로 움직입니다([analysis.py:80](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/analysis.py#L80), [state_view.py:60](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/state_view.py#L60), [rag.py:23](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/rag.py#L23), [report.py:73](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/report.py#L73)). 현재 테스트도 이 동작을 정답으로 고정합니다([test_orchestration_source_selection.py:160](/Users/anjeongseob/Desktop/Project/capstone-project/backend/test_orchestration_source_selection.py#L160)).  
  Why this is the final interpretation: Agent 1, 2, 5의 개별 지적은 서로 다른 버그가 아니라 같은 루트 원인입니다. 시스템에 `raw source`, `pending approval source`, `processed output source`는 존재하지만, 이를 하나의 authoritative "effective source"로 승격하는 상태 필드가 없습니다. 그래서 approval 전후, 후속 질문, RAG, report, merged context가 모두 각자 다른 규칙으로 source를 해석합니다. Agent 4의 lineage 비영속성은 이 체인을 새로고침 뒤 더 복구 불가능하게 만듭니다.  
  Affected boundaries: Workbench dataset selector ↔ approval/retry, preprocess_result ↔ orchestration state, dataset_context/merged_context ↔ analysis/RAG/report, dataset reload/list ↔ lineage.  
  Suggested verification: 행 수가 바뀌는 CSV 두 개를 올리고, A dataset에서 preprocess approval을 띄운 뒤 B로 selector를 바꿔 승인합니다. 이어서 approval 직전 request body `source_id`, 전처리 완료 후 follow-up request `source_id`, analysis planning input `source_id`, `merged_context.dataset_context.source_id`를 순서대로 비교하면 source drift가 한 번에 드러납니다.

- [Severity: P1] `resume` API가 `session_id`와 `run_id`의 소속 관계를 검증하지 않아, 한 세션의 interrupt된 실행 결과가 다른 세션 히스토리에 저장될 수 있습니다.  
  Combined evidence: resume 라우터는 URL에서 `session_id`와 `run_id`를 모두 받지만([chat/router.py:66](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/router.py#L66)), 서비스는 세션 존재만 확인한 뒤 `run_id`로 그대로 재개합니다([chat/service.py:88](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/service.py#L88)). orchestration thread는 `run_id` 우선으로 결정되고([client.py:202](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/client.py#L202)), 완료된 assistant 메시지는 URL의 세션 쪽에 append됩니다([chat/service.py:317](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/service.py#L317)).  
  Why this is the final interpretation: Agent 2와 Agent 5가 같은 증상을 독립적으로 짚었고, 반대 근거가 없습니다. 이 문제는 UI 가정이나 제품 의도와 무관하게 HTTP 경계에서 바로 재현되는 식별자 무결성 버그입니다.  
  Affected boundaries: `/chats/{session_id}/runs/{run_id}/resume` HTTP contract ↔ LangGraph thread selection ↔ chat history persistence.  
  Suggested verification: 세션 A, 세션 B를 만든 뒤 B에서 interrupt를 발생시키고 `session_id=A`, `run_id=B` 조합으로 resume를 호출해 A 히스토리에 어떤 assistant message가 저장되는지 확인합니다.

- [Severity: P1] 데이터 파일 형식 계약이 경계마다 달라, UI가 허용한 파일이 업로드 단계 또는 업로드 이후 EDA/preprocess 단계에서 뒤늦게 깨집니다.  
  Combined evidence: 프론트는 파일 선택기에서 `.csv,.json,.xlsx,.xls`를 노출합니다([Workbench.tsx:826](/Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/app/pages/Workbench.tsx#L826)), 하지만 백엔드 업로드는 `.csv`만 허용합니다([datasets/service.py:10](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/service.py#L10), [datasets/service.py:83](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/service.py#L83)). CSV라도 reader는 전 구간에서 `utf-8` 고정이라([datasets/service.py:42](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/service.py#L42), [preprocess/service.py:121](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/preprocess/service.py#L121)) 비 UTF-8 CSV는 업로드 후 EDA/profile/preprocess 시점에야 터집니다. EDA는 이를 명시적으로 변환하지 않고([eda/router.py:21](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/eda/router.py#L21)), preprocess도 `UnicodeDecodeError`를 별도 처리하지 않습니다([preprocess/router.py:10](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/preprocess/router.py#L10)).  
  Why this is the final interpretation: Agent 3의 "Excel을 받는 척하지만 시각화가 못 쓴다"와 Agent 4의 "비 UTF-8 CSV가 업로드 후 뒤늦게 깨진다"는 사실상 같은 계약 문제입니다. 시스템이 지원 형식과 인코딩을 업로드 시점에 일관되게 확정하지 않아서, 실패 지점이 단계마다 달라집니다.  
  Affected boundaries: file picker ↔ dataset upload API, dataset storage ↔ profiling/EDA/preprocess readers, locale-specific CSV ↔ downstream pipeline.  
  Suggested verification: `.xlsx`와 `cp949` CSV를 각각 업로드해 `POST /datasets/`, `GET /eda/{source_id}/profile`, `POST /preprocess/apply`를 순서대로 호출하고 어느 단계에서 어떤 에러로 깨지는지 비교합니다.

- [Severity: P2] analysis-result 기반 시각화 계약은 경로와 payload 의미가 모두 어긋나 있어, 실제로 붙이는 순간 unusable한 API가 됩니다.  
  Combined evidence: 프론트는 `/api/visualization/from-analysis`를 호출하지만([api.ts:428](/Users/anjeongseob/Desktop/Project/capstone-project/frontend/src/lib/api.ts#L428)) 백엔드 라우터 prefix는 `/vizualization`입니다([visualization/router.py:14](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/router.py#L14)). 게다가 라우터는 `build_from_analysis_result()`에 dataset `source_id`가 아니라 `analysis_result.id`를 넘겨 응답 payload의 `source_id` 의미까지 오염시킵니다([visualization/router.py:72](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/router.py#L72)).  
  Why this is the final interpretation: Agent 3의 P1/P2 두 건은 따로 떼면 "경로 오타"와 "payload typo"처럼 보이지만, 실제로는 하나의 contract break입니다. 경로를 맞춰도 payload `source_id`가 dataset identity가 아니므로 후속 revision/replay 또는 dataset lookup 연결이 계속 깨집니다.  
  Affected boundaries: frontend analysis-result client ↔ visualization router ↔ dataset/source resolution.  
  Suggested verification: `createVisualizationFromAnalysis()`를 실제 호출해 HTTP status를 확인하고, 라우터를 직접 호출했을 때 응답 `source_id`가 dataset source인지 `analysis_result_id`인지 비교합니다.

- [Severity: P2] 잘못된 `source_id`와 리포트 실패가 둘 다 "fail-open"으로 처리돼, 사용자에게 보이는 진실과 내부 상태/로그의 진실이 어긋납니다.  
  Combined evidence: 채팅 시작 시 dataset lookup 실패는 그냥 `None`으로 남고([chat/service.py:35](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/service.py#L35)), intake router는 `source_id`가 비면 일반 질문 경로로 보냅니다([intake_router.py:15](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/intake_router.py#L15)). 리포트 쪽은 실패해도 `output.type="report_answer"`와 사용자 fallback 문구를 반환하고([report.py:84](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/report.py#L84), [report.py:199](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/report.py#L199)), snapshot 요약과 trace summary는 그 실패를 에러로 승격하지 않습니다([client.py:235](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/client.py#L235), [trace_logging.py:299](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/core/trace_logging.py#L299)).  
  Why this is the final interpretation: Agent 5의 두 findings는 서로 다른 모듈이지만, 공통적으로 "사용자 의도 또는 실패 상태를 명시적으로 surface하지 않고 정상 경로 비슷하게 흘려보낸다"는 문제입니다. 그래서 잘못된 dataset을 들고 보낸 요청도 조용히 general chat로 떨어지고, 리포트 실패도 trace에서는 성공처럼 남을 수 있습니다.  
  Affected boundaries: dataset identity validation ↔ intake routing, report workflow ↔ trace/log summary ↔ operator debugging.  
  Suggested verification: 존재하지 않는 `source_id`로 `/chats/stream`을 호출해 handoff가 `general_question`으로 찍히는지 확인하고, report draft/save를 강제로 실패시킨 뒤 SSE 최종 답변과 trace summary JSON의 `status`/`error`를 비교합니다.

2. Rejected or downgraded findings

- Agent 1의 "세션 복원 시 `selectedSourceId`/시각화 상태가 서버 히스토리와 섞일 수 있다"는 최종 목록에서 제외했습니다. 로컬 draft 상태를 유지하려는 제품 의도일 가능성을 배제할 수 없고, 현재 근거만으로는 명확한 계약 위반보다 설계 결정에 더 가깝습니다.
- Agent 2의 "`workflow_final_state.final_status`가 일부 성공 경로에서 null이다"는 P3 수준 운영 가시성 문제로 하향했습니다. trace consumer에는 불편하지만, 현재 evidence만으로는 사용자 답변 자체가 깨지는 버그보다 한 단계 아래입니다.
- Agent 4의 `type_counts` 중복 집계와 `sample_row_count` 의미 오염은 유지 후보였지만 최종 목록에서는 제외했습니다. 둘 다 품질/정확성 문제는 맞지만, 앞선 P1/P2들처럼 세션 오염이나 잘못된 dataset 사용까지 직접 이어지는 근거는 상대적으로 약했습니다.
- Agent 4의 "preprocess lineage 비영속성"은 별도 finding으로 남기지 않고 첫 번째 consolidated finding의 aggravating factor로 흡수했습니다. 핵심 문제는 lineage 필드 부재 자체보다 "effective source"를 어디에도 승격하지 않는 전체 상태 모델입니다.
- Agent 5의 "세션 삭제 후 reports orphan 가능성", "dataset/guideline 삭제 후 RAG cleanup 실패 시 500 반환"은 실제로 타당하지만 이번 종합본에서는 운영/정리 계층 이슈로 하향했습니다. 현재 사용자 핵심 흐름을 깨는 우선순위는 preprocess/source drift, resume contamination, file-format contract 쪽이 더 높습니다.
- Agent 3의 "scatter series가 시각화 후처리에서 사라진다"는 planner 계약 위반 가능성은 인정하지만, grouped scatter를 제품에서 정말 보장해야 하는지 설계 의도가 불명확해 최종 목록에서 제외했습니다.

3. Final risk map

- 가장 위험한 사용자 흐름 1: 다중 dataset 세션에서 preprocess approval을 띄운 뒤 selector를 바꾸고 승인/재질문하는 흐름.  
  현재 테스트가 막는 것: 없습니다. 오히려 [test_orchestration_source_selection.py:160](/Users/anjeongseob/Desktop/Project/capstone-project/backend/test_orchestration_source_selection.py#L160)은 raw source 유지 동작을 통과 기준으로 고정합니다.  
  현재 테스트가 못 막는 것: approval 대상 source 고정, `output_source_id` 전환, merged context source 일관성, follow-up request source drift.

- 가장 위험한 사용자 흐름 2: interrupt된 run을 다른 세션 URL로 resume하는 흐름.  
  현재 테스트가 막는 것: 없습니다. 저장소의 백엔드 테스트는 orchestration source 선택과 trace logging 위주입니다.  
  현재 테스트가 못 막는 것: `session_id`/`run_id` ownership 검증, cross-session history contamination, resume 이후 SSE와 DB append의 일관성.

- 가장 위험한 사용자 흐름 3: 실제 현업 파일(`.xlsx`, `cp949` CSV)을 업로드해 EDA/preprocess/visualization까지 가는 흐름.  
  현재 테스트가 막는 것: 없습니다. Agent 3이 실행한 테스트와 저장소의 기존 테스트는 analysis processor, source selection, trace logging에만 집중돼 있습니다.  
  현재 테스트가 못 막는 것: 프론트 file picker와 업로드 API의 형식 계약 불일치, UTF-8 고정 reader로 인한 지연 실패, downstream 단계별 에러 코드/문구 불일치.
