# 문서

프로젝트 문서는 역할에 따라 분리한다.
AI 개발 기본 컨텍스트는 짧게 유지하고, 제품 요구사항·현재 구현 기준·아키텍처 참조·개발/검증 기준을 폴더별로 나눈다.

숨김 폴더인 `.obsidian/`, `.omc/`는 Obsidian/OMC 도구 설정과 상태 저장용이며, 독자가 읽는 프로젝트 문서 체계에는 포함하지 않는다.

## 문서 소유권

| 문서 영역 | 소유하는 판단 | 기준 코드/검증 |
|---|---|---|
| 루트 `AGENTS.md` | AI 작업 순서, 공통 규칙, 검증 루프 | child `AGENTS.md`, 실제 코드, docs harness |
| `product/` | 제품 목표, 현재 기준선, 개선 우선순위 | 현재 runtime 동작과 팀 합의 |
| `architecture/` | workflow, state, API, backend/frontend 구조 | `backend/app/`, `frontend/src/app/`, `backend/tests/test_architecture_docs.py` |
| `development/` | 로컬 실행, 환경 변수, 검증 명령 | `dev.sh`, `frontend/package.json`, pytest 명령 |
| `team/` | AI 협업 방식, 역할, 리뷰/검증 규칙 | 루트 `AGENTS.md`, 팀 합의 문서 |
| `testing/` | 벤치마크와 품질 게이트 | `backend/tests/`, docs harness, 품질 기준 문서 |
| `reference/` | 제안서, 발표 분석 등 외부 입력 | 발표/제안 자료, 제품·기술 판단의 참고 근거 |

문서와 코드가 다르면 코드를 기준으로 문서를 갱신한다. 문서 drift 검증은 아래 명령을 기준으로 한다.

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
```

## 계층 구조

| 폴더 | 대상 | 내용 |
|------|------|------|
| `architecture/` | 개발자/AI | 현재 코드 기준 구현 참조 문서 |
| `development/` | 개발자/AI | 로컬 실행, 환경 변수, 검증 기준 |
| `product/` | 팀 전체 | 데이터 분석 AI 에이전트 제품 요구사항, 현재 구현 기준선, 개선 로드맵 |
| `team/` | 팀 전체/AI | 협업 정책, 역할 분담, 리뷰/검증, 프롬프트 패턴 |
| `testing/` | 개발자/AI | 벤치마크 명세와 품질 게이트 |
| `reference/` | 발표·외부 | 제안서, 발표 분석 등 외부 입력 문서 |

## AI 개발 프로토콜

팀원이 AI에게 작업을 맡기기 전 읽혀야 하는 기준 문서는 루트 `AGENTS.md`다.
`AGENTS.md`는 공통 작업 순서, graphify 확인 방식, 수정 전 원칙, 검증 루프를 정의한다.

제품 방향과 현재 구현 상태는 아래 문서를 기준으로 확인한다.

- [제품 요구사항](./product/prd.md)
- [현재 구현 기준선](./product/current-state-baseline.md)
- [구현 로드맵](./product/roadmap.md)

로컬 실행과 환경 변수는 아래 문서를 기준으로 확인한다.

- [로컬 실행 환경](./development/local-environment.md)
- [환경 변수](./development/environment-variables.md)

AI 개발 기본 문서는 아래 순서로 읽는다.

1. 루트 `AGENTS.md`
2. 작업 영역의 child `AGENTS.md`
3. [제품 요구사항](./product/prd.md)과 [현재 구현 기준선](./product/current-state-baseline.md)
4. [질문 흐름](./architecture/request-lifecycle.md)
5. [공유 상태](./architecture/shared-state.md)
6. 필요한 경우 `architecture/orchestration/`과 `architecture/modules/` 상세 문서

`reference/`는 기본 컨텍스트가 아니라 발표, 제안서, 외부 입력을 확인할 때 읽는다.
`team/`은 팀 운영 방식과 AI 협업 규칙을 확인할 때 읽고, `testing/`은 품질 기준이나 벤치마크 기준을 확인할 때 읽는다.

## 문서 freshness 체크리스트

- [ ] 관련 child `AGENTS.md`를 확인했다.
- [ ] 제품 판단 변경 여부를 `docs/product/` 기준으로 확인했다.
- [ ] workflow/state/API/frontend 구조 변경 여부를 architecture 문서 기준으로 확인했다.
- [ ] 실행 명령이나 포트가 바뀌면 `docs/development/`를 갱신했다.
- [ ] 품질 기준이나 벤치마크 기준이 바뀌면 `docs/testing/`을 갱신했다.
- [ ] 팀 작업 방식이나 리뷰 기준이 바뀌면 `docs/team/`을 갱신했다.
- [ ] docs harness를 실행했다.

## 디렉터리 구조

```text
docs/
├── README.md                    # docs 전체 진입점
├── architecture/                # 현재 구현 참조 문서
│   ├── README.md
│   ├── AGENTS.md
│   ├── ai-agent/                # Trace 및 로깅
│   ├── components/              # 워크플로우 컴포넌트별 상세
│   ├── system/                  # 백엔드/프론트엔드 구조, API
│   ├── request-lifecycle.md
│   └── shared-state.md
│
├── development/                 # 로컬 실행 환경과 환경 변수
│   ├── README.md
│   ├── local-environment.md
│   └── environment-variables.md
│
├── product/                     # 제품 요구사항, 현재 기준선, 개선 로드맵
│   ├── README.md
│   ├── prd.md
│   ├── current-state-baseline.md
│   └── roadmap.md
│
├── team/                        # 팀 협업과 AI 작업 기준
│   ├── README.md
│   ├── agent-prompt-playbook.md
│   ├── ai-coding-policy.md
│   ├── review-and-verification.md
│   └── roles-and-ownership.md
│
├── testing/                     # 벤치마크와 품질 게이트
│   ├── README.md
│   ├── benchmark-spec.md
│   └── quality-gates.md
│
└── reference/                   # 외부 입력 문서
    ├── README.md
    ├── 산학캡스톤_프로젝트_제안서.pdf
    └── presentation-ai-analysis.md
```

## 문서 제목 변경 기준

- 너무 짧거나 약어만 있는 제목은 의미가 바로 드러나게 확장한다.
- 영어/한글이 섞인 제목은 한글 중심으로 통일한다.
- `개요`, `구조`, `설계`, `전략`, `기록`처럼 문서 성격이 드러나는 표현을 우선 사용한다.
