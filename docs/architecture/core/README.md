# Backend core 구조

`backend/app/core/`는 FastAPI 런타임 전반에서 공유하는 최소 infra 계층이다. 현재는 DB 세션/SQLAlchemy Base와 LLM 호출 wrapper, prompt registry가 여기에 있다. feature business rule은 `backend/app/modules/`에 두고, workflow 간 상태·분기 계약은 `backend/app/orchestration/`이 소유한다.

## 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/core/__init__.py` | core package marker다. 현재 export 로직은 없다. |
| `backend/app/core/db.py` | SQLite `engine`, `SessionLocal`, declarative `Base`, FastAPI dependency `get_db()`를 정의한다. |
| `backend/app/core/ai/__init__.py` | `LLMGateway`, `PromptRegistry`를 core AI package public surface로 export한다. |
| `backend/app/core/ai/llm_gateway.py` | LangChain `init_chat_model` 기반 LLM wrapper다. 일반 invoke, stream, structured output 호출을 한 지점으로 모은다. |
| `backend/app/core/ai/prompt_registry.py` | 문자열 prompt를 key-value dict로 보관하고 `load_prompt()`로 조회한다. |

## Hotspot: `backend/app/core/db.py`

- 주요 심볼: `DATABASE_URL`, `engine`, `SessionLocal`, `Base`, `get_db()`.
- 입력: FastAPI dependency injection이 `get_db()`를 호출하면 SQLAlchemy `Session`이 생성된다.
- 출력: request 처리 중 사용할 DB session을 yield하고, dependency 종료 시 `db.close()`로 닫는다.
- 연결 관계:
  - `backend/app/main.py`가 `Base.metadata.create_all(bind=engine)`로 모델 테이블 생성을 수행한다.
  - `backend/app/modules/*/dependencies.py`와 `backend/app/orchestration/dependencies.py`가 `get_db()`를 통해 repository/service를 조립한다.
- 주의점:
  - DB migration tool은 없고 startup 시점의 `metadata.create_all`에 의존한다.
  - `DATABASE_URL` 기본값은 `sqlite:///./app.db`이고, SQLite용 `check_same_thread=False`가 적용된다.

## Hotspot: `backend/app/core/ai/llm_gateway.py`

- 주요 class: `LLMGateway`.
- 주요 method: `_build_model()`, `invoke()`, `stream()`, `invoke_structured()`.
- 입력: `model_id`, LangChain message sequence, optional structured schema.
- 출력: LangChain chat model 응답 또는 Pydantic schema로 검증된 structured result.
- 연결 관계:
  - `backend/app/orchestration/ai.py`가 intent/general/data answer 생성에 사용한다.
  - `backend/app/modules/analysis/run_service.py`, `backend/app/modules/preprocess/planner.py`, `backend/app/modules/visualization/planner.py`, `backend/app/modules/rag/ai.py`, `backend/app/modules/reports/ai.py` 같은 AI-heavy module이 같은 gateway/prompt style을 공유한다.
- 주의점:
  - default model은 호출자에서 넘기는 `default_model` 또는 gateway 기본값인 `gpt-5-nano` 흐름을 따른다.
  - `invoke_structured()`는 `method="function_calling"`으로 structured output을 만든다.

## Hotspot: `backend/app/core/ai/prompt_registry.py`

- 주요 class: `PromptRegistry`.
- 주요 method: `load_prompt(key)`.
- 입력: prompt key 문자열.
- 출력: 등록된 prompt 문자열.
- 연결 관계:
  - 각 AI module이 module-local `PROMPTS = PromptRegistry({...})` 형태로 prompt를 관리한다.
- 주의점:
  - key가 없으면 `KeyError`가 발생한다. prompt key 변경은 해당 module의 호출부와 함께 확인해야 한다.

## 발견한 문제점 / 확인 필요 사항

- 관찰: 현재 core config 파일은 없다. 실제 설정 기준은 `backend/app/main.py`, 환경 변수 로딩, 각 module 상수에 분산되어 있다.
- 관찰: `backend/app/core/db.py`는 `sqlite:///./app.db`를 기본 DB로 직접 둔다. 배포/데모 환경에서 다른 DB를 쓰는 경우 실제 설정 경로를 별도로 확인해야 한다.
- 리스크: migration layer가 없고 `Base.metadata.create_all()`에 의존하므로, model field 변경이 누적될 때 문서만으로 schema 변경 절차를 판단하면 안 된다.
- 리스크: `LLMGateway`는 호출 provider/model 세부 동작을 숨기므로, model별 structured output 제약이나 prompt version 차이는 호출 module 문맥까지 같이 확인해야 한다.
