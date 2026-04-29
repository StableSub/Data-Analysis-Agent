# RAG and guidelines modules

`backend/app/modules/rag/`는 dataset/guideline 텍스트를 embedding index로 만들고 검색 context를 제공한다. `backend/app/modules/guidelines/`는 guideline 원본 PDF와 활성 guideline 상태를 관리한다. orchestration에서는 `backend/app/orchestration/workflows/rag.py`와 `backend/app/orchestration/workflows/guideline.py`가 이 계층을 사용한다.

## `rag/` 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/modules/rag/__init__.py` | RAG package marker다. |
| `backend/app/modules/rag/ai.py` | retrieved context 기반 insight synthesis와 answer generation을 담당한다. |
| `backend/app/modules/rag/dependencies.py` | vector storage path, embedder, repository, dataset/guideline RAG service를 조립한다. |
| `backend/app/modules/rag/errors.py` | `RagError`, `RagNotIndexedError`, `RagEmbeddingError`, `RagSearchError`를 정의한다. |
| `backend/app/modules/rag/guideline_repository.py` | guideline RAG source/chunk/context persistence repository다. |
| `backend/app/modules/rag/infra/__init__.py` | RAG infra package marker다. |
| `backend/app/modules/rag/infra/embedding.py` | `E5Embedder`가 document/query embedding을 만든다. |
| `backend/app/modules/rag/infra/vector_store.py` | `FaissStore`가 vector add/search/save/load를 담당한다. |
| `backend/app/modules/rag/models.py` | dataset/guideline RAG source, chunk, context SQLAlchemy model을 정의한다. |
| `backend/app/modules/rag/repository.py` | dataset RAG source/chunk/context repository다. |
| `backend/app/modules/rag/router.py` | `APIRouter(prefix="/rag")`로 query/delete route를 제공한다. |
| `backend/app/modules/rag/schemas.py` | RAG query/retrieved chunk/delete response schema를 정의한다. |
| `backend/app/modules/rag/service.py` | `RagService`, `GuidelineRagService`, `RetrievedChunk`가 indexing, query, context build, source delete를 담당한다. |

## `guidelines/` 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/modules/guidelines/__init__.py` | guidelines package marker다. |
| `backend/app/modules/guidelines/models.py` | `Guideline` SQLAlchemy model을 정의한다. |
| `backend/app/modules/guidelines/repository.py` | guideline create/list/get/activate/delete/latest persistence를 담당한다. |
| `backend/app/modules/guidelines/router.py` | `APIRouter(prefix="/guidelines")`로 upload/list/activate/delete route를 제공한다. |
| `backend/app/modules/guidelines/schemas.py` | guideline list/activation response schema를 정의한다. |
| `backend/app/modules/guidelines/service.py` | guideline file 저장, active guideline 조회, activate/delete use case를 담당한다. |

## Public route 요약

### `backend/app/modules/rag/router.py`

- `POST /rag/query`: dataset RAG query.
- `DELETE /rag/sources/{source_id}`: source id 기준 RAG index/source 삭제.

### `backend/app/modules/guidelines/router.py`

- `POST /guidelines/upload`: guideline PDF upload.
- `GET /guidelines/`: guideline list.
- `POST /guidelines/{source_id}/activate`: guideline 활성화.
- `DELETE /guidelines/{source_id}`: guideline 삭제.

## Hotspot: `backend/app/modules/rag/service.py`

### 역할

`RagService`는 dataset RAG, `GuidelineRagService`는 guideline RAG 흐름을 담당한다. 둘 다 repository와 FAISS vector store, embedder, text chunk context를 연결한다.

### 주요 class/function

- `RetrievedChunk`: 검색 결과 item의 source id, chunk id, score, content를 담는다.
- `RagService.ensure_index_for_source(source_id)`: dataset index가 있으면 existing, 없으면 생성 시도 결과를 반환한다.
- `RagService.index_dataset(...)`: dataset text/chunk를 embedding하고 index/persistence를 만든다.
- `RagService.query(...)`, `query_for_source(...)`: source filter와 top-k 기준으로 검색한다.
- `RagService.build_context(...)`: retrieved chunk를 answer prompt에 넣을 context string으로 만든다.
- `RagService.answer_query(...)`: retrieval과 LLM answer를 묶는 async helper다.
- `GuidelineRagService.index_guideline(...)`, `query(...)`, `build_context(...)`, `delete_source(...)`: guideline 문서용 동일 흐름이다.

### 연결 관계

- `backend/app/orchestration/workflows/rag.py`는 `ensure_index_for_source` → `query_for_source` → `build_context` → `synthesize_insight` 순서로 dataset evidence를 만든다.
- `backend/app/orchestration/workflows/guideline.py`는 active guideline을 찾고 guideline RAG service를 통해 evidence summary를 만든다.
- `backend/app/modules/rag/infra/embedding.py`와 `backend/app/modules/rag/infra/vector_store.py`는 service 내부 infra layer다.

### 주의점

- `rag_index_status.status`는 `existing`, `created`, `dataset_missing`, `unsupported_format` 같은 값으로 downstream thought step과 context 판단에 쓰인다.
- 검색 결과가 없을 때도 `rag_result.evidence_summary`에는 “질문과 직접 연결되는 근거를 찾지 못했습니다.” 같은 no-evidence summary가 실릴 수 있다.
- guideline RAG와 dataset RAG는 model/repository가 분리되어 있으므로 source id collision을 같은 namespace로 가정하면 안 된다.

## Hotspot: `backend/app/modules/rag/infra/embedding.py`

### 역할

`E5Embedder`는 text를 embedding vector로 바꾸는 infra adapter다.

### 주요 method

- `embed_documents(texts)`: 여러 document chunk를 embedding한다.
- `embed_query(text)`: query embedding을 만든다.

### 주의점

- embedding 실패는 `RagEmbeddingError` 계열로 이어질 수 있다.
- RAG 품질 문제를 분석할 때 prompt뿐 아니라 chunk text, embedding query, FAISS result score를 같이 확인해야 한다.

## Hotspot: `backend/app/modules/rag/infra/vector_store.py`

### 역할

`FaissStore`는 FAISS index를 저장/로드하고 검색하는 thin wrapper다.

### 주요 method

- `add(...)`: vector와 metadata를 index에 추가한다.
- `search(...)`: query vector와 top-k를 받아 scored metadata list를 반환한다.
- `save(...)`, `load(...)`: local storage에 index를 저장/복원한다.

### 주의점

- index 파일과 DB chunk/context row가 서로 맞아야 검색 결과를 신뢰할 수 있다.
- source delete 또는 re-index 동작은 vector store와 repository 양쪽 상태를 확인해야 한다.

## Hotspot: `backend/app/modules/guidelines/service.py`

### 역할

`GuidelineService`는 guideline PDF upload/list/active/delete use case를 담당한다. RAG indexing 자체는 `GuidelineRagService`가 담당하지만, active guideline 원본 선택은 guidelines module의 책임이다.

### 연결 관계

- `backend/app/modules/guidelines/router.py`가 public upload/list/activate/delete API로 사용한다.
- `backend/app/orchestration/workflows/guideline.py`는 active guideline source를 확인한 뒤 guideline RAG context를 만든다.

## 발견한 문제점 / 확인 필요 사항

- 관찰: dataset RAG와 guideline RAG는 같은 `rag/` module 아래 있지만 repository/model/storage path가 분리되어 있다. 문서나 코드에서 둘을 같은 source namespace로 단순화하면 실제 동작과 다르다.
- 관찰: `backend/app/orchestration/workflows/guideline.py`는 workflow 내부에서 guideline repository/service를 조립하고 guideline RAG service의 내부 index path 성격 method에 의존하는 부분이 있다. 이는 orchestration-module 경계 확인이 필요한 지점이다.
- 리스크: RAG 검색 결과가 없을 때도 no-evidence summary가 정상 output으로 흘러간다. 후속 answer 생성에서 “근거 없음”과 “실패”를 구분해야 한다.
- 리스크: vector index 파일과 DB row가 불일치하면 검색 결과 신뢰도가 낮아질 수 있다. delete/re-index 관련 변경은 storage와 repository를 동시에 확인해야 한다.
