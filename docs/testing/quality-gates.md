# 품질 게이트

## 목적

이 문서는 캡스톤 발표 전까지 팀이 PR, 데모 준비, 발표 리허설 전에 확인해야 할 최소 품질 게이트를 정리한다.
현재 repository의 실제 스크립트와 테스트 존재 여부를 기준으로 작성하며, 존재하지 않는 lint/check-types/CI를 통과했다고 주장하지 않는다.

## 공통 원칙

- 품질 게이트는 "좋아 보인다"가 아니라 "실제로 확인했다"를 요구한다.
- 명령이 없으면 없다고 적고, 대체 수동 점검을 정의한다.
- 기능 변경과 문서 변경은 같은 수준의 검증 책임을 가진다.

## 현재 repo 기준 확인된 검증 수단

### 문서/아키텍처

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
```

### 프론트엔드

```bash
npm --prefix frontend run build
```

- `frontend/package.json`에는 현재 `dev`, `build`만 있다.
- 별도 `lint`, `check-types` 스크립트는 현재 없다.

### 백엔드 회귀 확인에 자주 쓰는 명령

```bash
PYTHONPATH=. pytest -q backend/tests/test_main_workflow_analysis_happy_path.py
PYTHONPATH=. pytest -q backend/tests/test_analysis_planning_accuracy_guards.py backend/tests/test_planner_analysis_accuracy_guards.py
```

## 변경 유형별 게이트

## 1. 문서만 수정한 경우

필수:

- [ ] 맞춤법/용어/링크를 직접 읽어 확인했다.
- [ ] 코드 기준 문서라면 관련 구현 경로를 다시 확인했다.
- [ ] 아래 명령을 실행했다.

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
```

추가 수동 점검:

- [ ] 발표 슬라이드에서 그대로 인용해도 오해가 없는 문장인지 확인했다.
- [ ] "예정", "추후", "TODO" 같은 placeholder 표현이 남아 있지 않다.

## 2. 프론트엔드 변경이 포함된 경우

필수:

- [ ] `npm --prefix frontend run build` 성공
- [ ] SSE/approval UI 변경이면 관련 문서 영향 확인
- [ ] 화면에서 핵심 흐름 1회 이상 수동 확인

수동 확인 항목:

- [ ] dataset 선택/질문 입력/응답 표시가 깨지지 않는다.
- [ ] approval card가 있는 경우 상태 문구가 맞다.
- [ ] 데모에서 사용할 브라우저 크기에서 레이아웃이 무너지지 않는다.

## 3. 백엔드/워크플로우 변경이 포함된 경우

필수:

- [ ] 관련 pytest 실행
- [ ] 변경된 API route, payload, status code 영향 확인
- [ ] SSE event나 approval/resume 계약 변경 여부 확인

수동 확인 항목:

- [ ] happy path 1개 이상 재현
- [ ] 대표 실패 path 1개 이상 재현 또는 로그로 검토
- [ ] 문서 drift 여부 확인

## PR 리뷰 게이트

PR을 merge 후보로 올리기 전, 작성자와 리뷰어는 아래를 모두 만족해야 한다.

### 작성자 체크리스트

- [ ] 변경 목적이 제목/설명에서 한 문장으로 드러난다.
- [ ] scope 밖 수정이 있으면 이유를 적었다.
- [ ] 실행한 검증 명령과 결과를 적었다.
- [ ] 미실행 검증이 있으면 왜 못 했는지 적었다.
- [ ] 발표 데모나 문서에 영향이 있으면 명시했다.

### 리뷰어 체크리스트

- [ ] 주장한 검증이 실제 repo 상황과 모순되지 않는다.
- [ ] 문서가 runtime 사실을 잘못 단정하지 않는다.
- [ ] naming, ownership, rollback 가능성이 수용 가능하다.
- [ ] "나중에 고치자"식 리스크가 발표 직전 치명적이지 않은지 확인했다.

## 발표 리허설 게이트

발표 전날과 당일 오전에는 기능 단위가 아니라 데모 흐름 단위로 확인한다.

- [ ] 데모 데이터셋이 준비되어 있다.
- [ ] 일반 질문, 분석 질문, approval 흐름 중 최소 2개가 재현 가능하다.
- [ ] 발표자가 사용할 설명 문장이 현재 구현과 맞다.
- [ ] 실패 시 대체 시나리오가 있다.
- [ ] 핵심 지표/한계/향후 계획 답변이 문서와 일치한다.

## 실패 처리 규칙

품질 게이트에서 하나라도 실패하면 다음 중 하나를 택한다.

1. 즉시 수정 후 재검증
2. 발표 범위에서 제외
3. 알려진 한계로 문서화하고 데모 경로에서 제거

"시간이 없어서 일단 merge"는 발표 직전일수록 금지한다.

## PASS 보고 템플릿

```text
변경 범위:
실행 명령:
- [PASS/FAIL] <command>
수동 확인:
남은 리스크:
```

## 현재 시점의 명시적 제한

- 현재 repo에는 프론트엔드 lint/check-types 전용 스크립트가 없다.
- 이 문서는 CI 파이프라인 존재를 전제하지 않는다.
- 따라서 품질 게이트는 로컬 명령 + 수동 검토 + 문서 일치성 확인을 기준으로 운영한다.
