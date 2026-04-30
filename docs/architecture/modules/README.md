# Backend modules 구조

`backend/app/modules/`는 기능 단위 backend module 계층이다. public FastAPI router를 가진 module과 orchestration 내부에서만 쓰이는 support engine이 함께 있다. module은 기능 동작과 persistence를 소유하고, module 사이 실행 순서와 shared state handoff는 `backend/app/orchestration/`이 담당한다.

## 문서 분할

| 문서 | 포함 module | 읽는 상황 |
|---|---|---|
| [Analysis module](./analysis.md) | `analysis/`, `results/` 일부 연결 | AI 분석 계획·코드 생성·실행 결과 저장을 이해할 때 |
| [Dataset, EDA, profiling](./data-and-profile.md) | `datasets/`, `eda/`, `profiling/` | 업로드된 데이터셋, profile, EDA API를 이해할 때 |
| [RAG and guidelines](./rag-and-guidelines.md) | `rag/`, `guidelines/` | dataset/guideline indexing, retrieval, evidence synthesis를 이해할 때 |
| [Preprocess and visualization](./preprocess-and-visualization.md) | `preprocess/`, `visualization/` | approval 기반 전처리와 시각화 생성 흐름을 이해할 때 |
| [Chat, report, results](./chat-report-export.md) | `chat/`, `reports/`, `results/` | runtime API 진입, report draft service, stored artifact를 이해할 때 |

## Module family 요약

| family | public route | 핵심 책임 | 주요 연결 |
|---|---|---|---|
| `analysis/` | `/analysis` | 자연어 질문을 분석 계획과 실행 코드로 변환하고 sandbox 결과를 저장한다. | `orchestration/workflows/analysis.py`, `results/`, `visualization/` |
| `chat/` | `/chats` | session/history/SSE/resume API와 `AgentClient` 호출 seam을 담당한다. | `orchestration/client.py`, frontend SSE consumer |
| `datasets/` | `/datasets` | dataset upload/list/detail/sample와 file storage를 담당한다. | `profiling/`, `analysis/`, `rag/`, `visualization/` |
| `eda/` | `/eda` | profile 기반 요약, 품질, 통계, 상관, outlier, insight API를 제공한다. | `profiling/`, `preprocess/` |
| `guidelines/` | `/guidelines` | guideline PDF upload/list/activate/delete와 원본 파일 저장을 담당한다. | `rag/`, guideline orchestration workflow |
| `preprocess/` | `/preprocess` | 데이터 정제/변환 계획과 적용을 담당한다. | `orchestration/workflows/preprocess.py`, `profiling/` |
| `profiling/` | 없음 | dataset profile 계산 support engine이다. | `eda/`, `preprocess/`, `analysis/` |
| `rag/` | `/rag` | FAISS index, embedding, retrieval, answer/evidence context를 담당한다. | `orchestration/workflows/rag.py`, guideline workflow |
| `reports/` | 없음 | report draft 생성과 저장 service를 담당한다. | `orchestration/workflows/report.py` |
| `results/` | 없음 | analysis/chart/view snapshot 저장 model과 repository를 제공한다. | `analysis/`, `visualization/` |
| `visualization/` | `/vizualization` | manual/from-analysis chart data와 workflow visualization result를 만든다. | `orchestration/workflows/visualization.py`, `analysis/` |

## 전체 파일 카탈로그 위치

- `analysis/` 파일은 [Analysis module](./analysis.md)에 정리한다.
- `datasets/`, `eda/`, `profiling/` 파일은 [Dataset, EDA, profiling](./data-and-profile.md)에 정리한다.
- `rag/`, `guidelines/` 파일은 [RAG and guidelines](./rag-and-guidelines.md)에 정리한다.
- `preprocess/`, `visualization/` 파일은 [Preprocess and visualization](./preprocess-and-visualization.md)에 정리한다.
- `chat/`, `reports/`, `results/` 파일은 [Chat, report, results](./chat-report-export.md)에 정리한다.
- package marker인 `backend/app/modules/__init__.py`는 feature modules package임을 나타내는 package 진입 파일이다.

## 책임 경계

- module 내부 router/service/schema/repository는 해당 기능의 request/response/persistence와 deterministic rule을 소유한다.
- `backend/app/orchestration/`은 module을 호출하는 순서, approval interrupt, final output packaging을 소유한다.
- frontend-facing 최종 SSE event shape는 module router가 아니라 `backend/app/modules/chat/service.py`와 `backend/app/orchestration/client.py`의 결합 결과다.

## 발견한 문제점 / 확인 필요 사항

- 관찰: module family마다 형태가 다르다. 예를 들어 `profiling/`과 `results/`는 public router가 없는 support engine이고, `chat/`은 orchestration 진입 API다.
- 관찰: 시각화 route prefix는 실제 코드상 `/vizualization`이다. 문서나 frontend에서 정리된 철자인 `/visualization`으로 바꾸어 쓰면 현재 runtime과 어긋난다.
- 리스크: `analysis/`, `preprocess/`, `visualization/`, `rag/`, `eda/`는 AI 호출과 deterministic validation이 같이 있어 문서가 오래되면 후속 Codex 작업자가 책임 경계를 잘못 판단할 가능성이 높다.
- 리스크: public router module과 support-only module이 같은 `modules/` 아래 있으므로, “모든 module은 route를 가진다”는 전제로 API 문서를 만들면 누락 또는 과장이 생긴다.
