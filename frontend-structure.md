# Frontend Structure

현재 메인 프론트엔드는 `frontend/src/app/` 아래 구조를 기준으로 동작한다.

이 문서는 현재 활성 Workbench UI 기준 구조 정리 문서다.
이후 별도 요청이 있기 전까지 프론트엔드 코드 수정 시 함께 업데이트하는 것을 기본 원칙으로 한다.

## 1. Entry Flow

- 엔트리: `frontend/src/app/App.tsx`
- 메인 페이지: `frontend/src/app/pages/Workbench.tsx`
- 실제 분석 UI는 `Workbench.tsx` 가 중심이며, 현재 메인 사용자 흐름도 이 페이지 기준이다.

흐름은 대략 아래와 같다.

1. `App.tsx` 가 `Workbench.tsx` 를 렌더링
2. `Workbench.tsx` 가 세션, 레이아웃, 뷰 전환, 좌/중/우 패널을 구성
3. `Workbench.tsx` 내부에서 `useAnalysisPipeline.ts` 를 사용해 업로드, Pre-EDA, 질문 전송, SSE 응답, HITL 상태를 관리
4. 실제 UI 조각은 `components/genui/*` 아래 컴포넌트로 분리되어 렌더링

## 2. Core Page

### `frontend/src/app/pages/Workbench.tsx`

역할:

- 메인 Workbench 화면 조립
- 좌측 세션 패널과 중앙 캔버스 배치
- `current / pre-eda / deep-eda / report` 내부 캔버스 상태 전환
- `WorkbenchCommandBar` 와 `GateBar` 연결
- `useWorkbenchSessionStore` 와 `useAnalysisPipeline` 연결

주요 책임:

- 현재 선택된 dataset/context를 어떤 카드에 보여줄지 결정
- `AssistantReportMessage`, `PreEdaBoard`, `VisualizationResultView` 같은 상위 표현 컴포넌트를 조합
- 로컬 세션 snapshot 저장/복원
- 상단 서브헤더에서 데이터 소스 selector와 상태 칩 레이아웃 폭을 조정하고, dataset 이름이 가능한 한 잘리지 않도록 공간 배분을 관리
- 데이터 소스 selector는 좁은 최대 폭과 별도 chevron 아이콘 영역을 사용한다
- 글로벌 헤더 오른쪽 상단의 dataset pill은 사용하지 않고, 상태 표현은 중앙 서브헤더 오른쪽 끝의 `EDA / Analysis` 2칩으로 단순화한다
- `EDA / Analysis` 칩은 동일한 고정 폭을 가지며, 클릭 시 토글이 아니라 각 뷰(`pre-eda`, 내부 analysis 상태)로 직접 이동한다
- 브라우저 탭 제목은 `HARU AI Data Analyzer`를 사용하고, 글로벌 헤더 왼쪽 브랜드 영역에는 `HADA`만 표시한다
- 글로벌 헤더는 현재 세션 제목, 상태 배지, 추가 설명 subtitle을 렌더링하지 않는다
- 좌측 세션 리스트의 활동 시간은 `YYYY.MM.DD HH시 mm분` 형식으로 표시한다
- 좌측 세션 패널 하단의 별도 안내 footer는 제거되어 있고, 세션 관련 UI는 리스트 영역까지만 렌더링된다
- `current` 뷰는 항상 분석 화면을 뜻하지 않고, 업로드 후 마지막 유효 상태를 기준으로 `pre-eda` 또는 `Analysis` 스냅샷을 보여준다
- `current`가 `Analysis`를 가리킬 때는 최신 카드 1개로 덮어쓰지 않고, `chatHistory`를 기준으로 사용자 질문과 AI 답변을 시간순으로 모두 렌더링한다
- `chatHistory`가 비어 있는 복원/예외 상태에서만 `reportSections` 기반 단일 `Analysis 결과` fallback 카드를 사용한다
- 우측 `Details / Agent` 패널은 제거되었고, 중앙 캔버스가 그 폭까지 확장된다
- 중앙 캔버스의 콘텐츠 최대폭과 하단 입력 바 폭은 우측 패널 제거 이후 더 넓은 기준으로 조정되어, 데이터 보드 화면에서 좌우 빈공간이 과하게 남지 않도록 관리된다

## 3. Pipeline / State

### `frontend/src/app/hooks/useAnalysisPipeline.ts`

프론트엔드 분석 파이프라인의 핵심 훅이다.

역할:

- 파일 업로드 상태 관리
- 서버 Pre-EDA 조회
- SSE 기반 질문/응답 스트림 처리
- tool call / thought step / analysis section 상태 구성
- 전처리 적용, approval, retry, error 상태 관리

주요 state:

- `state`: `empty | uploading | ready | running | needs-user | success | error`
- `uploadedDatasets`
- `selectedSourceId`
- `reportSections`
- `chatHistory`
- `pendingApproval`
- `latestVisualizationResult`
- `selectedPreEdaProfile`

이 훅이 사실상 프론트의 화면 상태 오케스트레이터 역할을 한다.

### `frontend/src/app/hooks/useWorkbenchSessionStore.ts`

역할:

- 로컬 세션 목록/선택/삭제/복원 상태 저장
- Workbench 단위 draft/session context 유지
- 세션의 `active selection` 과 `recent activity` 를 분리해서 관리

현재 특징:

- 단순 선택만으로는 세션 순서가 바뀌지 않음
- 질문 전송/파일 업로드처럼 실제 활동이 발생한 세션만 `activityAt` 기준으로 맨 위로 정렬
- 좌측 패널의 `Current` 표시는 선택된 세션이 아니라 가장 최근 활동 세션 기준으로 동작

## 4. Main GenUI Components

### `frontend/src/app/components/genui/PreEdaBoard.tsx`

역할:

- 업로드 직후의 Pre-EDA 결과를 카드 형태로 렌더링
- 데이터 미리보기
- 기본 통계
- Pre-EDA Summary
- 상관관계 TOP 3
- 분포 시각화
- 이상치 탐지

특징:

- distribution 차트와 tooltip 처리 포함
- 추천 전처리 카드도 함께 포함
- 우측 `Pre-EDA Summary` 는 현재 왼쪽 카드 높이를 강제로 따라가지 않고, 명시적인 기본 높이 + 내부 scroll 구조로 유지된다

### `frontend/src/app/components/genui/AssistantReportMessage.tsx`

역할:

- AI 응답/분석 결과/스트리밍 결과를 카드 형태로 렌더링
- `heading / paragraph / checklist / numbered-list / code` 섹션 렌더링
- 카드 헤더, body scroll, footer, variant(`final / streaming / error`) 레이아웃 관리
- summary 카드처럼 부모 높이를 따라가야 하는 경우를 위해 루트가 `flex-column` 구조로 동작

사용 위치:

- Pre-EDA Summary
- Analysis 결과
- 최종 Analysis 결과
- 채팅 내 assistant 답변
- 에러/승인 대기 카드 일부

### `frontend/src/app/components/genui/ReportContentRenderer.tsx`

역할:

- `AssistantReportMessage` 내부 본문 렌더링 helper
- paragraph / code block / label-value 텍스트 렌더링 담당
- URL / inline code 중심의 안전한 inline renderer 제공

특징:

- 기존의 광범위한 regex markdown parser 대신, code fence와 일반 텍스트를 분리하는 block 중심 구조
- `_snake_case_` 같은 식별자를 italic으로 오인식하지 않도록 underscore 기반 강조 파싱을 사용하지 않음
- `Pre-EDA Summary`, assistant 응답, analysis 카드가 공통으로 이 renderer를 사용

### `frontend/src/app/components/genui/WorkbenchCommandBar.tsx`

역할:

- 하단 입력창
- dataset 업로드 메뉴 진입
- 모델 선택 UI
- 메시지 전송 / stop 버튼

현재 특징:

- 내부 controlled textarea 사용
- IME 조합 입력 처리 포함

### 그 외 자주 쓰이는 컴포넌트

- `ApprovalCard.tsx`: HITL 승인 대기 카드
- `GateBar.tsx`: 승인/수정/취소 입력 바
- `ToolCallIndicator.tsx`: 실행 중 tool 상태 표시
- `EvidenceFooter.tsx`: Data / Scope / Compute / RAG footer
- `CardShell.tsx`: 대부분 카드의 공통 외형

## 5. Visualization

### `frontend/src/app/components/visualization/VisualizationResultView.tsx`

역할:

- 백엔드에서 생성한 시각화 결과를 렌더링
- 차트 타입에 따라 Recharts 기반 출력

### `frontend/src/app/components/ui/chart.tsx`

역할:

- Recharts 공통 wrapper
- `ChartContainer`, `ChartTooltip` 등 공용 chart primitive 제공

## 6. Frontend Lib Layer

### `frontend/src/app/lib/preEdaProfile.ts`

역할:

- 로컬 fallback Pre-EDA 프로파일 생성 로직
- 타입 추론, 통계 계산, 요약 bullet 생성

현재 메인 흐름에서는 서버 Pre-EDA가 우선이고, 이 파일은 fallback 성격이 강하다.

### `frontend/src/app/lib/preprocessRecommendation.ts`

역할:

- 추천 전처리 연산 label/key/helper 제공
- 전처리 추천 렌더링 보조

### `frontend/src/app/lib/pipelineSessionContext.ts`

역할:

- Workbench 세션 snapshot 직렬화/정규화 보조

## 7. UI Primitive Layer

위치:

- `frontend/src/app/components/ui/*`

역할:

- 버튼, 탭, 테이블, 툴팁, 차트, 입력창 등 범용 UI primitive 제공
- `genui/*` 는 이 primitive들을 조합해서 실제 화면 컴포넌트를 만든다

즉 구조적으로는:

- `ui/*`: 재사용 가능한 기본 UI
- `genui/*`: Workbench 전용 조합형 UI
- `pages/*`: 실제 화면 조립
- `hooks/*`: 상태/오케스트레이션
- `lib/*`: 계산/정규화/helper

## 8. Active Rendering Path

현재 가장 중요한 활성 렌더링 경로:

1. `App.tsx`
2. `pages/Workbench.tsx`
3. `hooks/useAnalysisPipeline.ts`
4. `components/genui/PreEdaBoard.tsx`
5. `components/genui/AssistantReportMessage.tsx`
6. `components/genui/WorkbenchCommandBar.tsx`
7. `components/visualization/VisualizationResultView.tsx`

프론트 수정 시 우선적으로 확인해야 할 파일도 이 경로다.

## 9. Structure Notes

- 현재 프론트엔드는 `Workbench.tsx` 와 `useAnalysisPipeline.ts` 의 결합도가 높은 편이다.
- `AssistantReportMessage.tsx` 가 summary/analysis/chat 답변을 넓게 담당하고 있어 영향 범위가 크다.
- 현재는 `AssistantReportMessage.tsx` 가 카드 프레임을 담당하고, 본문 텍스트 렌더링은 `ReportContentRenderer.tsx` 로 분리되어 있다.
- `PreEdaBoard.tsx` 는 단일 파일 안에서 UI와 formatting 책임이 조금 큰 편이라, 추후 복잡도가 더 늘면 분리 여지가 있다.
- 모델 선택 UI는 존재하지만 실제 백엔드 전달 여부는 별도 확인이 필요하다.
- 상단 상태 표현은 예전의 다단계 route 칩이 아니라, 업로드 후 활성화되는 `EDA`와 질의 성공 후 활성화되는 `Analysis` 2단계 칩으로 축약되어 있다.
- 상단 `EDA` 칩은 업로드 후 준비된 `Pre-EDA` 뷰로만 이동하고, `Analysis` 칩은 질의 성공 후 `Analysis` 스냅샷 뷰로만 이동한다.
- 질문 실패 또는 fallback 답변만 있는 경우에는 `Analysis`를 성공 상태로 보지 않으며, `current` 복귀 시 EDA 상태를 유지한다.

## 10. Update Rule

이 문서는 현재 활성 Workbench UI 구조 기준 문서다.

향후 프론트엔드 코드 수정 시 아래 변화가 생기면 같이 업데이트한다.

- 엔트리 경로 변경
- 메인 페이지 책임 변경
- 핵심 훅 역할 변경
- 주요 genui 컴포넌트 추가/삭제
- 시각화/summary/command bar 책임 변경
