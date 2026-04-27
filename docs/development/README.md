# 개발 문서

이 디렉터리는 로컬에서 프로젝트를 실행하고 검증하기 위한 개발 환경 문서를 모아둔다.
코드 구조나 제품 범위보다, 실제 실행 명령·환경 변수·검증 명령처럼 작업자가 바로 따라야 하는 기준을 소유한다.

## 포함 문서

| 문서 | 역할 | 기준 파일 |
|---|---|---|
| [로컬 실행 환경](./local-environment.md) | backend/frontend 실행 방식, 포트, 검증 명령 | `dev.sh`, `frontend/package.json`, `requirements.txt` |
| [환경 변수](./environment-variables.md) | 현재 코드에서 사용하는 환경 변수와 기본값 | `backend/app/`, `frontend/src/lib/api.ts`, `dev.sh` |

## 읽는 순서

1. 처음 실행하는 경우 [로컬 실행 환경](./local-environment.md)을 먼저 읽는다.
2. API 키나 host/port 설정이 필요하면 [환경 변수](./environment-variables.md)를 확인한다.
3. 문서나 코드 변경 후에는 변경 영역에 맞는 검증 명령을 실행한다.

## 유지 기준

- 실행 명령, 포트, package script가 바뀌면 [로컬 실행 환경](./local-environment.md)을 갱신한다.
- 코드에서 새 환경 변수를 실제로 읽기 시작하면 [환경 변수](./environment-variables.md)에 추가한다.
- 존재하지 않는 `lint`, `check:types` 같은 script를 검증 완료 항목으로 쓰지 않는다.
- 문서 검증은 아래 명령을 기준으로 한다.

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
```
