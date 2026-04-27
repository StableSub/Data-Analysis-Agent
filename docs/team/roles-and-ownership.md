# 역할과 소유권

## 목적

이 문서는 캡스톤 발표 준비 기간에 팀 내 책임 경계를 명확히 하기 위한 운영 문서다.
GitHub CODEOWNERS 대체가 아니라, 누가 어떤 변경과 검증을 책임지는지 빠르게 합의하기 위한 기준이다.

## 권장 역할

| 역할 | 핵심 책임 | 최종 확인 항목 |
| --- | --- | --- |
| 기술 리드 | 범위 조정, 병합 판단, 발표 메시지 정리 | 변경 우선순위, 위험 수용 여부 |
| 백엔드 오너 | FastAPI, orchestration, 데이터 처리 | API 계약, workflow 회귀 테스트 |
| 프론트엔드 오너 | Workbench, SSE 소비, approval UI | build, 수동 데모 흐름 |
| 문서/QA 오너 | architecture/team/testing 문서, 검증 기록 | 문서 drift, 체크리스트, 발표 근거 |
| 발표 오너 | 데모 순서, 슬라이드 근거, 질의응답 | benchmark/제한사항/강점 framing |

## 저장소 경로별 1차 소유권

| 경로 | 1차 오너 | 2차 리뷰어 | 확인 포인트 |
| --- | --- | --- | --- |
| `backend/app/main.py` | 백엔드 오너 | 기술 리드 | public router 등록 |
| `backend/app/orchestration/` | 백엔드 오너 | 기술 리드 | state, routing, SSE-facing output |
| `backend/app/modules/analysis/` | 백엔드 오너 | 문서/QA 오너 | 분석 정확도, 오류 계약 |
| `backend/app/modules/chat/` | 백엔드 오너 | 프론트엔드 오너 | session/run/SSE/resume 계약 |
| `frontend/src/app/hooks/useAnalysisPipeline.ts` | 프론트엔드 오너 | 백엔드 오너 | SSE event 소비, approval 상태 |
| `frontend/src/app/pages/Workbench.tsx` | 프론트엔드 오너 | 발표 오너 | 데모 UI, 오류/승인 노출 |
| `docs/architecture/` | 문서/QA 오너 | 해당 코드 오너 | 코드 기준 설명 여부 |
| `docs/team/`, `docs/testing/` | 문서/QA 오너 | 기술 리드 | 팀 운영/검증 기준 현실성 |

## 의사결정 규칙

### 단독 결정 가능

- 오탈자, 문장 명확화, 링크 수정
- 구현과 1:1로 맞는 문서 보정
- 데모 흐름에 영향 없는 UI 문구 정리

### 2인 이상 합의 필요

- public API/SSE 계약 변경
- 발표 핵심 메시지 변경
- benchmark 수치 공개 기준 변경
- “완료” 판단에 쓰는 품질 게이트 변경

## PR 소유권 규칙

- 작성자가 곧 소유자는 아니다. 변경된 경로의 1차 오너가 최종 승인 책임을 가진다.
- 문서-only PR이라도 코드 계약을 설명하면 해당 코드 오너가 함께 본다.
- 발표 직전에는 기술 리드 또는 발표 오너가 “슬라이드에 넣어도 되는 표현인지”를 마지막으로 확인한다.

## 발표 준비용 책임 매트릭스

| 항목 | 책임자 | 백업 담당 | 산출물 |
| --- | --- | --- | --- |
| 데모 시나리오 | 발표 오너 | 프론트엔드 오너 | 클릭 순서, 실패 대응 문구 |
| API/SSE 설명 | 백엔드 오너 | 기술 리드 | 이벤트 흐름 설명 |
| 정확도/benchmark 설명 | 문서/QA 오너 | 기술 리드 | 수치표, 제한사항 |
| architecture 슬라이드 | 기술 리드 | 문서/QA 오너 | workflow/state 다이어그램 |
| 질의응답 대응 | 전원 | 기술 리드 | 예상 질문/답변 목록 |

## handoff 체크리스트

- [ ] 변경 목적과 범위를 한 문장으로 전달했다
- [ ] 실행한 검증 명령을 공유했다
- [ ] 아직 남은 리스크를 명시했다
- [ ] 발표에서 사용할 표현/금지 표현을 함께 전달했다

## 발표용 framing

소유권 문서의 핵심은 “누가 만들었는가”보다 **누가 설명하고 방어할 수 있는가**다.
발표에서는 각 영역 담당자가 자신의 수치·계약·제약을 바로 답할 수 있어야 한다.
