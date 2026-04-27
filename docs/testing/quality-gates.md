# 품질 게이트

## 문서 목적

이 문서는 코드·문서 변경을 merge하거나 발표 자료 근거로 사용할 수 있는 최소 품질 게이트를 정의한다.
현재 저장소에 존재하는 검증 수단만 기준으로 하며, 존재하지 않는 CI/lint/typecheck 체계를 가정하지 않는다.

## 현재 기준 검증 수단

| 범위 | 목적 | 현재 기준 명령 | 비고 |
| --- | --- | --- | --- |
| 문서/아키텍처 | 링크, 코드 경로, API route drift 확인 | `PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py` | docs 변경 시 기본 게이트 |
| 프론트엔드 | 타입 포함 번들 수준 검증 | `npm --prefix frontend run build` | 별도 lint/typecheck script는 현재 없음 |
| 백엔드 | 변경 영역 회귀 확인 | 관련 `pytest` 대상 명령 | 수정한 모듈 기준으로 선택 실행 |
| diff 위생 | 공백/충돌/patch 이상 확인 | `git diff --check` | 모든 변경 공통 |

## 변경 유형별 필수 게이트

### 1. 문서만 수정한 경우

- [ ] `git diff --check`
- [ ] `PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py`
- [ ] 문서 안 링크와 코드 경로 수동 확인

### 2. 프론트엔드 포함 변경

- [ ] 문서 게이트(해당 시)
- [ ] `git diff --check`
- [ ] `npm --prefix frontend run build`
- [ ] 변경 화면 수동 확인 또는 스크린샷 증빙

### 3. 백엔드 포함 변경

- [ ] 문서 게이트(해당 시)
- [ ] `git diff --check`
- [ ] 관련 `pytest` 실행
- [ ] API/상태 계약 변경 시 architecture 문서 동시 갱신

## PR 리뷰 게이트

PR은 아래 질문에 모두 답할 수 있어야 한다.

1. **왜 바꿨는가?**
2. **무엇을 검증했는가?**
3. **어떤 리스크가 남았는가?**
4. **발표 자료/데모에 영향이 있는가?**

### PR 본문 필수 항목

- 변경 목적 한 줄
- 변경 파일 범주
- 실행한 검증 명령과 결과
- 남은 리스크 또는 미검증 항목
- 발표 영향도

## 리뷰 차단 조건

아래 항목 중 하나라도 해당하면 merge하지 않는다.

- 검증 명령이 없거나 실행 결과가 빠져 있다.
- 존재하지 않는 lint/typecheck/CI를 통과했다고 적었다.
- architecture/API 문서가 코드와 어긋난다.
- benchmark 수치의 출처가 없다.
- 데모 경로 변경인데 발표 담당 확인이 없다.

## 발표 전 최종 게이트

### H-24 체크

- [ ] 데모에 쓸 브랜치와 커밋을 고정했다.
- [ ] 발표 자료의 시스템 설명이 `docs/architecture/*`와 일치한다.
- [ ] benchmark/정확도 수치가 `./benchmark-spec.md` 기준 출처를 가진다.
- [ ] 예상 질문(정확도, 실패 처리, 승인 흐름)에 대한 근거 파일을 준비했다.

### H-1 체크

- [ ] 데모 핵심 시나리오를 실제로 다시 실행했다.
- [ ] SSE 진행, 승인 카드, 완료/오류 흐름을 확인했다.
- [ ] 최신 변경이 발표 메시지를 깨지 않는지 확인했다.

## 권장 증빙 포맷

```text
Verification:
- PASS | git diff --check
- PASS | PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
- PASS | npm --prefix frontend run build
- NOTE | docs-only change, no backend runtime logic modified
```

## 팀 운영 팁

- 문서 PR도 코드 PR처럼 검증 로그를 남긴다.
- 발표 직전에는 “좋아 보인다”보다 “다시 실행했다”를 우선한다.
- 실패한 검증은 숨기지 말고, 원인과 우회 여부를 함께 기록한다.
