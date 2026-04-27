# 품질 게이트

## 목적

이 문서는 현재 저장소에서 실제로 수행 가능한 검증만 기준으로 PR 승인 게이트를 정의한다.
캡스톤 발표 전에는 “무엇을 검증했고 무엇은 아직 수동 확인인지”를 분명히 남기는 것이 목표다.

## 현재 저장소 기준 사실

- 프론트엔드 package script: `dev`, `build`만 존재 (`frontend/package.json`)
- 문서 drift 검증 테스트 존재: `backend/tests/test_architecture_docs.py`, `backend/tests/test_docs_harness.py`
- 백엔드 주요 workflow 회귀 테스트 일부 존재: `backend/tests/test_main_workflow_analysis_happy_path.py`, `backend/tests/test_analysis_planning_accuracy_guards.py`, `backend/tests/test_planner_analysis_accuracy_guards.py`
- 전역 CI에서 `lint`, `check-types`가 자동으로 돈다고 확인된 근거는 현재 없다

## 변경 유형별 게이트

### 1. 문서-only 변경

최소 게이트:

- `PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py`
- 변경 문서 내 링크/파일 경로 수동 확인

추가 확인:

- architecture 문서라면 실제 코드 경로가 현재 구현과 맞는지 확인
- 팀 운영 문서라면 존재하지 않는 자동화/CI를 주장하지 않았는지 확인

### 2. 프론트엔드 변경

최소 게이트:

- `npm --prefix frontend run build`

권장 수동 게이트:

- Workbench 주요 흐름 실행
- SSE 수신, approval 카드, error UI 확인

주의:

- `lint`, `check:types` 통과를 주장하지 않는다
- `tsconfig` 제외 범위를 모른 채 “전체 타입 안전”이라고 표현하지 않는다

### 3. 백엔드 workflow/API 변경

최소 게이트:

- 관련 pytest 실행
- 문서 계약이 바뀌면 architecture 문서 동시 갱신

권장 조합:

```bash
PYTHONPATH=. pytest -q backend/tests/test_main_workflow_analysis_happy_path.py
PYTHONPATH=. pytest -q backend/tests/test_analysis_planning_accuracy_guards.py backend/tests/test_planner_analysis_accuracy_guards.py
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
```

## PR 리뷰 게이트

### 작성자 제출 전

- [ ] 변경 유형을 문서-only / frontend / backend / mixed 중 하나로 표시했다
- [ ] 실행한 검증 명령을 PR 본문에 적었다
- [ ] 실패했지만 허용한 항목이 있으면 이유를 적었다
- [ ] 발표에서 설명할 리스크를 한 줄로 요약했다

### 리뷰어 승인 전

- [ ] 변경 범위가 설명과 일치한다
- [ ] 검증 명령이 실제 저장소에 존재한다
- [ ] “자동”, “항상”, “완전” 같은 과장 표현이 없다
- [ ] 데모 흐름에 영향이 있으면 수동 확인 결과가 있다

## release 전 최종 게이트

발표 직전 기준 최소 묶음:

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
PYTHONPATH=. pytest -q backend/tests/test_main_workflow_analysis_happy_path.py
PYTHONPATH=. pytest -q backend/tests/test_analysis_planning_accuracy_guards.py backend/tests/test_planner_analysis_accuracy_guards.py
npm --prefix frontend run build
```

## PASS / HOLD 기준

### PASS

- 변경 유형에 맞는 최소 게이트를 모두 통과
- 수동 확인이 필요한 항목을 명시
- 문서와 발표 메시지가 현재 구현과 모순되지 않음

### HOLD

- 없는 스크립트/CI를 근거로 품질을 주장함
- SSE·approval·report 흐름 변경 후 수동 확인이 없음
- architecture/API 문서가 코드와 어긋남
- 발표 시연 핵심 흐름에 영향이 있는데 책임 소유자가 불명확함

## 발표용 framing

품질 게이트의 핵심 메시지는 “완벽한 자동화”가 아니라 **재현 가능한 최소 검증 체계**다.
발표에서는 자동 테스트, 빌드 검증, 수동 데모 체크를 구분해서 설명한다.
