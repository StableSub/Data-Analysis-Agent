# 테스트와 품질 문서

이 디렉터리는 제품 품질을 판단하기 위한 벤치마크 명세와 품질 게이트를 설명한다.
개별 테스트 코드의 상세 구현보다, 어떤 기준으로 성공/실패를 판단하고 어떤 회귀를 막아야 하는지에 집중한다.

## 포함 문서

| 문서 | 역할 | 언제 읽는가 |
|---|---|---|
| [벤치마크 명세](./benchmark-spec.md) | 데이터셋 질문, 기대 경로, 결과 평가 기준 | 분석 품질을 시나리오 단위로 평가할 때 |
| [품질 게이트](./quality-gates.md) | 문서, backend, frontend, workflow 검증 기준 | 작업 완료 전 필수 확인 항목을 정할 때 |

## 읽는 순서

1. 작업 완료 기준을 정할 때 [품질 게이트](./quality-gates.md)를 먼저 읽는다.
2. 분석 정확도나 end-to-end 평가가 필요하면 [벤치마크 명세](./benchmark-spec.md)를 확인한다.
3. 검증 명령 자체가 바뀌면 `docs/development/local-environment.md`도 함께 갱신한다.

## 유지 기준

- 새 회귀 테스트나 품질 기준이 생기면 [품질 게이트](./quality-gates.md)에 반영한다.
- benchmark case, expected path, 평가 지표가 바뀌면 [벤치마크 명세](./benchmark-spec.md)를 갱신한다.
- 문서 변경 검증은 아래 명령을 기준으로 한다.

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
```
