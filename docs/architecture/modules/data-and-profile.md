# Dataset, EDA, profiling modules

이 문서는 업로드된 dataset을 저장·조회하고, profile/EDA 정보를 계산하는 backend module을 정리한다. 이 계층은 analysis, preprocess, visualization, rag, report가 공통으로 참조하는 데이터 이해 기반이다.

## `datasets/` 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/modules/datasets/__init__.py` | datasets package marker다. |
| `backend/app/modules/datasets/models.py` | SQLAlchemy model `Dataset`, `SessionSource`를 정의한다. |
| `backend/app/modules/datasets/repository.py` | `DataSourceRepository`가 dataset/session-source persistence 조회와 변경을 담당한다. |
| `backend/app/modules/datasets/router.py` | `APIRouter(prefix="/datasets")`로 upload/list/detail/delete/sample route를 제공한다. |
| `backend/app/modules/datasets/schemas.py` | `DatasetBase`, `DatasetListResponse`, `DatasetSampleResponse` 등 dataset API response model을 정의한다. |
| `backend/app/modules/datasets/service.py` | `DatasetStorage`, `DatasetReader`, `DataSourceService`와 dependency builders를 정의한다. |

## `eda/` 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/modules/eda/__init__.py` | EDA package marker다. |
| `backend/app/modules/eda/ai.py` | EDA profile 기반 AI summary/recommendation 생성과 parsing helper를 담당한다. |
| `backend/app/modules/eda/dependencies.py` | `EDAService`를 dataset repository/reader/profile service와 조립한다. |
| `backend/app/modules/eda/router.py` | `APIRouter(prefix="/eda")`로 profile, summary, quality, columns/types, stats, correlations, outliers, distribution, recommendations, insights route를 제공한다. |
| `backend/app/modules/eda/schemas.py` | EDA summary/quality/type/stats response model을 정의한다. |
| `backend/app/modules/eda/service.py` | `EDAService`가 profile 조회, summary/statistics/correlation/outlier/distribution/recommendation/insight 계산을 담당한다. |

## `profiling/` 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/modules/profiling/__init__.py` | profiling package marker다. |
| `backend/app/modules/profiling/dependencies.py` | `DatasetProfileService` dependency builder/getter를 제공한다. |
| `backend/app/modules/profiling/schemas.py` | `ColumnProfile`, `DatasetProfile`, `ColumnProfileType` schema를 정의한다. |
| `backend/app/modules/profiling/service.py` | `DatasetProfileService`가 컬럼 타입, 결측, 통계, identifier/group-key 후보를 계산한다. |

## Public route 요약

### `backend/app/modules/datasets/router.py`

- `POST /datasets/`: dataset file upload.
- `GET /datasets/`: dataset list.
- `GET /datasets/{dataset_id}`: dataset detail.
- `DELETE /datasets/{source_id}`: source id 기준 dataset 삭제.
- `GET /datasets/{source_id}/sample`: dataset sample rows 조회.

### `backend/app/modules/eda/router.py`

- `GET /eda/{source_id}/profile`: dataset profile.
- `GET /eda/{source_id}/summary`: 요약 counts.
- `GET /eda/{source_id}/quality`: 결측/품질 정보.
- `GET /eda/{source_id}/columns/types`: 컬럼 타입 정보.
- `GET /eda/{source_id}/stats`: 컬럼 통계.
- `GET /eda/{source_id}/correlations/top`: 상위 상관 관계.
- `GET /eda/{source_id}/outliers`: outlier 정보.
- `GET /eda/{source_id}/distribution`: 분포 정보.
- `GET /eda/{source_id}/preprocess-recommendations`: 전처리 추천.
- `GET /eda/{source_id}/insights`: AI 기반 EDA insight.

## Hotspot: `backend/app/modules/datasets/service.py`

### 역할

`datasets/service.py`는 dataset file의 저장 위치, 파일 읽기, DB metadata 생성을 담당한다.

### 주요 class/function

- `DatasetUploadError`: upload validation 실패를 나타내는 domain error다.
- `DatasetStorage`: 업로드 파일을 storage 디렉터리에 저장하고 source id/path를 관리한다.
- `DatasetReader`: CSV/Excel 등 dataset 파일을 pandas DataFrame으로 읽는다.
- `DataSourceService`: router가 사용하는 upload/list/detail/delete/sample use case를 제공한다.
- `_datasets_storage_dir()`, `build_*`, `get_*`: storage/repository/reader/service dependency 조립 함수다.

### 연결 관계

- `backend/app/main.py`에서 `datasets_api.router`가 mount된다.
- `backend/app/orchestration/dependencies.py`가 같은 repository/reader를 analysis, EDA, preprocess, visualization, RAG service 조립에 재사용한다.
- `backend/app/modules/chat/service.py`는 `source_id`로 selected dataset을 찾아 `AgentClient`에 넘긴다.

## Hotspot: `backend/app/modules/eda/service.py`

### 역할

`EDAService`는 profile 기반 EDA API의 중심 service다. raw DataFrame을 직접 읽고 profile service 결과와 결합해 summary/quality/stats/distribution/insight를 만든다.

### 주요 class/function

- error class: `EDANotFoundError`, `EDAInvalidRequestError`, `EDAUnsupportedRequestError`.
- `get_profile`, `get_summary`, `get_quality`, `get_column_types`, `get_stats`, `get_top_correlations`, `get_outliers`, `get_distribution`, `get_preprocess_recommendations`, `get_insights` 계열 method.
- `_safe_float`, `_serialize_label_value`: JSON serialization을 위한 helper.

### 연결 관계

- public EDA router에서 직접 호출된다.
- preprocess workflow의 dataset profiling과 decision/review payload에 간접 기반을 제공한다.
- analysis/reporting이 데이터 컬럼·통계 문맥을 이해하는 support source로 쓰인다.

## Hotspot: `backend/app/modules/profiling/service.py`

### 역할

`DatasetProfileService`는 dataset column profile을 계산하는 support engine이다. public router는 없지만 여러 module이 dataset metadata를 이해할 때 참조한다.

### 주요 기준

- `BOOLEAN_TOKENS`: boolean-like string 탐지 기준.
- `IDENTIFIER_NAME_TOKENS`, `GROUP_KEY_NAME_TOKENS`: 컬럼명 기반 identifier/group key 후보 판단 기준.
- output schema는 `backend/app/modules/profiling/schemas.py`의 `DatasetProfile`, `ColumnProfile`을 따른다.

### 연결 관계

- `backend/app/modules/eda/dependencies.py`에서 EDAService와 연결된다.
- `backend/app/modules/preprocess/dependencies.py`에서 PreprocessService와 연결된다.
- analysis metadata/profile 계층과 사용자 질문 해석에도 간접 영향을 준다.

## 발견한 문제점 / 확인 필요 사항

- 관찰: `profiling/`은 router가 없는 support module이다. API 목록만 보고 backend 구조를 이해하면 이 계층의 중요도를 놓칠 수 있다.
- 관찰: `EDAService`는 profile 계산, 통계, 분포, recommendation, AI insight까지 넓은 API 표면을 가진다. route별 정확한 입력/출력은 `backend/app/modules/eda/router.py`와 schema를 함께 확인해야 한다.
- 리스크: dataset storage path, source id, DB row가 여러 module의 공통 전제다. upload/delete 동작을 변경하면 analysis, rag, preprocess, visualization, report 쪽 path resolution도 함께 확인해야 한다.
- 리스크: profile type inference가 analysis/preprocess/viz 추천에 영향을 주므로, dtype 추론 변경은 UI 표시만이 아니라 AI 계획 품질에도 영향을 줄 수 있다.
