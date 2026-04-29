# 백엔드 구조

## 문서 목적

이 문서는 백엔드 모듈 구조와 각 모듈의 역할을 설명한다.
현재 기준의 백엔드 구현 구조를 기준으로 정리하며, 기획, 프론트엔드, 백엔드가 함께 참고할 수 있도록 쉬운 언어로 설명한다.

현재 구조는 데이터 분석 AI Agent 런타임 기준이다. `chat`, `orchestration`, `datasets`, `eda`, `analysis`, `preprocess`, `visualization`, `rag`, `guidelines`, trace/logging은 모두 현재 제품 기능을 구성하는 주요 영역으로 본다.

## 갱신 기준

- 기준 코드: `backend/app/main.py`, `backend/app/modules/`, `backend/app/orchestration/`
- 검증 테스트: `backend/tests/test_docs_harness.py`, `backend/tests/test_architecture_docs.py`
- 갱신 트리거: module family 추가/삭제, public router mount 변경, orchestration 책임 변경, 내부 support module 책임 변경

## 백엔드 구조 개요

현재 백엔드는 크게 아래 세 축으로 나뉜다.

- `core`
- `modules`
- `orchestration`

즉, 이 백엔드는 단순히 REST API 파일만 모여 있는 구조가 아니라, 공통 기반 기능, 도메인 기능 모듈, 실행 흐름 조합 계층이 분리된 구조를 가진다.

## 상위 디렉터리 기준 구조

### 1. `core`

`core`는 백엔드 전반에서 공통으로 쓰는 기반 기능을 담당한다.
현재 기준으로는 아래 역할이 포함된다.

- DB 연결
- 공통 AI 호출
- trace / logging

이 계층은 특정 도메인 기능을 직접 수행하기보다, 여러 모듈이 공통으로 사용할 기반 기능을 제공한다.

### 2. `modules`

`modules`는 실제 기능별 도메인 모듈이 모여 있는 영역이다.
데이터셋, 채팅, 분석, 전처리, 시각화, RAG, 지침서 등 주요 기능이 이 안에서 모듈 단위로 관리된다.

즉, 사용자가 실제로 체감하는 대부분의 기능은 이 계층의 모듈들을 통해 제공된다.

### 3. `orchestration`

`orchestration`은 질문을 하나의 실행 흐름으로 연결하는 계층이다.
planner, 전처리, 분석, RAG, 시각화, 리포트 같은 여러 모듈을 상황에 맞게 조합하여 하나의 workflow로 만든다.

이 계층이 있기 때문에 백엔드는 단순 API 집합이 아니라, 질문 흐름을 조합하는 실행 시스템처럼 동작한다.

## 공개 API 모듈

현재 `main.py` 기준으로 공개 API 라우터가 등록된 주요 모듈은 아래와 같다.

- `chat`
- `datasets`
- `eda`
- `analysis`
- `visualization`
- `rag`
- `guidelines`
- `preprocess`

각 모듈의 역할은 아래와 같다.

### `chat`

질문 시작, 승인 이후 재개, 승인 대기 조회, 세션 히스토리와 세션 삭제를 담당한다.
현재 백엔드에서 AI 실행 흐름으로 들어가는 대표 진입점은 이 모듈이다.

### `datasets`

데이터셋 업로드, 목록 조회, 상세 조회, 샘플 조회, 삭제를 담당한다.
사용자가 분석할 데이터를 시스템에 넣고 관리하는 기능이 이 모듈에 있다.

### `eda`

탐색적 데이터 분석과 전처리 추천에 필요한 기능을 담당한다.
전처리 판단을 돕는 기초 분석 역할을 가진다.

### `analysis`

실제 데이터 분석 실행과 관련된 공개 기능을 담당한다.
분석 결과를 만들기 위한 실행 흐름과 연결되는 모듈이다.

### `visualization`

시각화 생성과 관련된 공개 기능을 담당한다.
분석 결과를 차트나 시각 자료로 바꾸는 기능과 연결된다.

### `rag`

데이터셋 또는 지침서 기반의 검색과 설명형 질의응답 기능을 담당한다.
설명형 응답이나 지식 검색이 필요한 상황에서 사용된다.

### `guidelines`

도메인 지침서의 저장과 조회를 담당한다.
분석 과정에서 참고하는 내부 지식의 관리 지점이다.

### `preprocess`

전처리 관련 공개 기능을 담당한다.
전처리 계획과 실행 흐름에 연결되는 모듈이다.

이 문서는 엔드포인트 상세를 설명하는 문서가 아니므로, 구체적인 요청/응답 형식은 `API 개요 및 명세` 문서에서 다룬다.

## 내부 지원 모듈

모든 모듈이 공개 API를 직접 제공하는 것은 아니다.
현재 구조에서 내부 workflow 지원 역할이 큰 모듈은 아래와 같다.

- `planner`
- `profiling`
- `reports`
- `results`

### `planner`

질문을 어떤 경로로 보낼지, 전처리가 필요한지, 분석 계획이 필요한지 등을 판단한다.
즉, 시스템의 route 판단과 계획 수립을 담당하는 내부 지원 모듈이다.

### `profiling`

데이터셋의 구조와 품질 정보를 요약하고, dataset context와 profile을 만드는 역할을 담당한다.
planner와 분석 단계의 입력 준비를 지원한다.

### `reports`

리포트 초안 생성과 최종 저장을 지원한다.
현재 구조에서는 별도 공개 router보다는 내부 workflow의 출력 경로에 가까운 모듈이다.

### `results`

분석 결과 저장 모델과 저장소를 담당한다.
즉, 분석 결과 데이터를 저장하고 다시 참조할 수 있도록 하는 내부 저장 지원 모듈이다.

이 섹션이 중요한 이유는, 백엔드가 공개 API 모듈만으로 이루어진 구조가 아니라 내부 지원 모듈과 함께 동작한다는 점을 보여주기 때문이다.

## 오케스트레이션 계층

`orchestration`은 별도의 도메인 기능 모듈이 아니라, 여러 모듈을 연결해 하나의 실행 흐름으로 만드는 계층이다.

현재 이 계층에는 아래와 같은 역할이 있다.

- `builder`: main workflow 조합
- `client`: Agent 실행 인터페이스
- `intake_router`: 최상위 질문 분기
- `workflows/*`: preprocess, analysis, rag, guideline, visualization, report
- `state`, `utils`: 공통 상태와 보조 로직

즉, 실제 AI Agent 실행은 하나의 모델 호출이 아니라, 이 orchestration 계층이 여러 도메인 모듈을 연결해 만들어 내는 흐름이다.

## 모듈 내부 구성 패턴

대부분의 모듈은 비슷한 내부 구조를 가진다.
대표적인 패턴은 아래와 같다.

- `router`: API 진입점
- `dependencies`: 의존성 주입
- `service`: 핵심 비즈니스 로직
- `repository`: DB 접근
- `models`: ORM 모델
- `schemas`: 요청/응답 스키마

다만 모든 모듈이 완전히 동일한 구조를 따르지는 않는다.
현재 구조에서 눈에 띄는 예외는 아래와 같다.

### `analysis`

기본 패턴 외에도 `processor`, `sandbox`, `run_service`가 포함되어 있다.
즉, 단순 CRUD형 모듈이 아니라 분석 계획 처리와 실행 환경 관리가 함께 들어 있다.

### `preprocess` / `visualization`

두 모듈 모두 `planner` 와 `executor`가 분리되어 있다.
즉, 계획 수립과 실제 실행이 같은 service 안에만 있지 않고 역할이 나뉘어 있다.

### `reports`

공개 router 없이 내부 서비스 중심으로 동작한다.
현재 기준으로는 내부 workflow에서 호출되는 지원 모듈 성격이 강하다.

### `results`

`models` 와 `repository` 중심의 저장 모듈이다.
즉, 결과 저장 구조를 담당하지만 별도 공개 API를 제공하는 모듈은 아니다.

이 문서는 이러한 패턴을 설명하는 문서이며, 파일별 API 설명을 대체하는 문서는 아니다.

## 주요 연결 관계

프론트엔드 요청은 주로 `chat` 또는 `datasets` 같은 공개 API 모듈로 들어온다.
그중에서도 `chat` 모듈은 AgentClient와 orchestration을 연결하는 중심 진입점 역할을 한다.

이후 orchestration은 intake routing, preprocess, analysis, RAG, guideline, visualization, report 계층과 각 도메인 모듈을 조합해 실행 흐름을 만든다.
즉, 질문 하나가 바로 분석 모듈로 가는 것이 아니라, orchestration이 중간에서 route를 정하고 필요한 모듈을 연결한다.

또한 `datasets`, `profiling`, `analysis`, `preprocess`, `visualization`, `reports`, `results`는 각각 독립된 책임을 가지면서도 하나의 분석 흐름 안에서 연결된다.
여기서 중요한 점은 시간 순서보다도, 어떤 모듈이 어떤 역할을 맡고 어떤 계층에서 협력하는지를 이해하는 것이다.

## 이 문서를 읽는 방법

이 문서는 백엔드 전체 구조를 알고 싶을 때 읽는 문서다.
질문의 시간 순서 흐름은 `../architecture/request-lifecycle.md`, 공유 state 계약은 `../architecture/shared-state.md`, 요청 단위 설명은 `api-spec.md` 문서로 이어서 보면 된다.

더 깊은 실행 로직은 `../components/` 문서와 `../ai-agent/trace-and-logging.md`에서 보는 것이 적합하다.
