# 환경 변수

## 목적

이 문서는 현재 코드에서 확인되는 로컬 개발용 환경 변수만 정리한다.
운영/배포용 추정 변수는 이 문서에 추가하지 않는다.
새 환경 변수는 실제 코드에서 사용되기 전까지 이 문서에 추가하지 않는다.

## 백엔드 `.env`

현재 백엔드 코드에서 직접 사용이 확인되는 값은 아래와 같다.

| 변수 | 용도 | 비고 |
| --- | --- | --- |
| `OPENAI_API_KEY` | OpenAI 모델 호출 | AI 실행에 필요 |
| `TAVILY_API_KEY` | Tavily 검색 연동 | 검색 기능 사용 시 필요 |

현재 로컬 `.env`에 있을 수 있으나 코드 직접 사용이 확인되지 않은 값은 아래와 같다.

| 변수 | 상태 |
| --- | --- |
| `GEMINI_FLASH_API_KEY` | 현재 코드 직접 사용 확인 안 됨 |
| `GEMINI_PRO_API_KEY` | 현재 코드 직접 사용 확인 안 됨 |

## 프론트엔드

| 변수 | 용도 | 기본값 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | 프론트엔드 API client가 호출할 백엔드 base URL | `http://localhost:8000` |

## 개발 스크립트 override

`dev.sh`는 아래 값을 override로 받을 수 있다.

| 변수 | 기본값 |
| --- | --- |
| `BACKEND_HOST` | `127.0.0.1` |
| `BACKEND_PORT` | `8000` |
| `FRONTEND_HOST` | `127.0.0.1` |
| `FRONTEND_PORT` | `5173` |

## 데이터베이스

현재 database URL은 `backend/app/core/db.py`의 `sqlite:///./app.db` 고정값을 따른다.
`DATABASE_URL` 환경 변수는 현재 코드에서 사용하지 않는다.
