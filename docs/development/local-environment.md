# 로컬 실행 환경

## 목적

이 문서는 로컬 개발 환경과 실행 방식을 설명한다.
현재 구현에서 확인되는 데이터 분석 AI Agent 실행 명령과 포트만 기준으로 정리한다.

## 갱신 기준

- 기준 파일: `dev.sh`, `frontend/package.json`, `requirements.txt`, backend pytest 파일
- 검증 명령: 이 문서의 `## 검증 명령` 섹션
- 갱신 트리거: dev server host/port 변경, package script 변경, backend test command 변경, Docker/runtime setup 추가

## 로컬 실행 기준

### 통합 실행

```bash
bash dev.sh
```

`dev.sh`는 backend와 frontend를 함께 실행한다.

기본 포트:

| 대상 | 기본 host | 기본 port |
|---|---:|---:|
| backend | `127.0.0.1` | `8000` |
| frontend | `127.0.0.1` | `5173` |

실행 시 `node_modules`가 없으면 `frontend`에서 `npm install`을 수행한다.

### 백엔드 단독 실행

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

백엔드는 FastAPI 앱이며 진입점은 `backend/app/main.py`다.
라우터는 `main.py`에서 직접 등록된다.

### 프론트엔드 단독 실행

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 3000
```

수동 실행 문서에서는 frontend port `3000`을 사용한다.
다만 `dev.sh`의 기본 frontend port는 `5173`이다.

frontend API base URL은 기본적으로 `http://localhost:8000`이며, 필요하면 `VITE_API_BASE_URL`로 바꾼다.

## 검증 명령

### 프론트엔드 빌드

```bash
npm --prefix frontend run build
```

`frontend/package.json`에는 현재 `dev`와 `build` script만 있다.
`lint`, `check:types` 같은 script가 없으므로 문서나 작업 결과에서 해당 검증을 통과했다고 주장하지 않는다.

검증 명령을 새로 추가하거나 이름을 바꾸면 이 문서와 루트 `AGENTS.md`의 검증 루프를 함께 갱신한다.

### 아키텍처 문서

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py
```

### 백엔드 workflow 주요 회귀 테스트

```bash
PYTHONPATH=. pytest -q backend/tests/test_main_workflow_analysis_happy_path.py
PYTHONPATH=. pytest -q backend/tests/test_analysis_planning_accuracy_guards.py backend/tests/test_planner_analysis_accuracy_guards.py
```

## Docker

현재 repository에서 `Dockerfile` 또는 `docker-compose*.yml`은 확인되지 않는다.
따라서 Docker 실행은 현재 문서화 대상이 아니며, 로컬 실행은 위 명령을 기준으로 한다.

## 개발 환경 주의사항

- backend는 `requirements.txt`를 사용한다. `pyproject.toml` 기준으로 설치하거나 검증하지 않는다.
- DB schema는 현재 `Base.metadata.create_all()`로 생성된다. 별도 migration tool은 없다.
- runtime 데이터와 로그는 `storage/` 아래에 생성된다.
- `dev.sh`는 frontend 기본 port로 `5173`을 사용하지만, 수동 frontend 실행 예시는 `3000`을 사용한다.
