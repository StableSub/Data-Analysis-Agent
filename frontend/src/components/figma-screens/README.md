# 피그마 디자인 참고용 화면 컴포넌트

이 폴더에는 피그마 디자인 작업을 위한 각 화면 상태별 정적 컴포넌트가 포함되어 있습니다.

## 🎨 빠른 시작

### 방법 1: 갤러리 모드 (추천)

모든 화면을 한 곳에서 확인하고 선택할 수 있습니다:

```tsx
// App.tsx
import { ScreenGallery } from './components/figma-screens/ScreenGallery';

function App() {
  return <ScreenGallery />;
}
```

### 방법 2: 개별 화면 확인

특정 화면만 보고 싶을 때:

```tsx
// App.tsx
import { ChatEmptyState } from './components/figma-screens';

function App() {
  return <ChatEmptyState />;
}
```

## 📱 화면 목록

### AI 챗봇 (4개)
| 파일명 | 설명 | 주요 상태 |
|--------|------|----------|
| `ChatEmptyState.tsx` | 빈 상태 | 메시지 없음, 모델 선택, 예시 질문 |
| `ChatWithMessages.tsx` | 대화 진행 중 | 여러 메시지, 재생성 버튼 |
| `ChatStreaming.tsx` | 스트리밍 중 | AI 응답 생성, 중지 버튼 |
| `ChatWithAgent.tsx` | Agent 위젯 열림 | 우측 Agent 패널, 실시간 상태 |

### 데이터 업로드 (3개)
| 파일명 | 설명 | 주요 상태 |
|--------|------|----------|
| `UploadDefault.tsx` | 기본 상태 | 드래그&드롭 영역, 최근 파일 |
| `UploadDragOver.tsx` | 드래그 오버 | 파일 드래그 중 하이라이트 |
| `UploadSuccess.tsx` | 업로드 성공 | 성공 카드, 분석 시작 버튼 |

### Coming Soon 페이지 (6개)
| 파일명 | 기능명 |
|--------|--------|
| `ComingSoonSnapshot` | 데이터 스냅샷 |
| `ComingSoonFilter` | 데이터 필터링 |
| `ComingSoonVisualization` | 데이터 시각화 |
| `ComingSoonEdit` | 데이터 편집 |
| `ComingSoonSimulation` | 시뮬레이션 |
| `ComingSoonAudit` | 감사 로그 |

## 🎭 다크 모드

모든 컴포넌트는 다크 모드를 지원합니다:

```tsx
// 방법 1: 갤러리에서 토글 버튼 사용
<ScreenGallery /> // 우측 상단 Light/Dark 버튼

// 방법 2: 직접 적용
<div className="dark">
  <ChatEmptyState />
</div>
```

## 📸 피그마에서 사용하는 방법

1. **갤러리 모드 실행**
   ```bash
   # App.tsx에서 ScreenGallery 사용
   npm run dev
   ```

2. **화면 선택 및 캡처**
   - 갤러리에서 원하는 화면 클릭
   - Light/Dark 모드 전환
   - 브라우저 개발자 도구로 원하는 해상도 설정
   - 스크린샷 캡처 (Cmd/Ctrl + Shift + 5)

3. **피그마로 가져오기**
   - 캡처한 이미지를 피그마에 드래그
   - 디자인 참고 자료로 활용

## 🎯 각 화면의 핵심 포인트

### AI 챗봇 - 빈 상태
- 로봇 아이콘 (80×80px)
- 모델 선택 드롭다운
- 3개 예시 질문 카드 (호버 효과)
- 4개 기능 아이콘

### AI 챗봇 - 대화 진행 중
- 사용자/AI 메시지 구분 (우측/좌측)
- 메시지 그룹핑
- 시간 표시
- 재생성 버튼

### AI 챗봇 - 스트리밍
- 깜빡이는 커서 (▋)
- 진행 중 표시
- 중지 버튼 (빨간색)
- 입력 비활성화

### AI 챗봇 - Agent 위젯
- 우측 320px 패널
- 처리 상태 요약
- 활성 기능 목록
- 최근 활동 타임라인

### 데이터 업로드 - 기본
- 드래그&드롭 영역 (border-dashed)
- 파일 선택 버튼
- 최근 업로드 3개 표시

### 데이터 업로드 - 드래그 오버
- 파란색 하이라이트
- 배경색 변경
- "파일을 여기에 놓으세요" 메시지

### 데이터 업로드 - 성공
- 녹색 성공 카드
- 체크 아이콘
- 분석 시작 / 다른 파일 선택 버튼

### Coming Soon 페이지
- 큰 아이콘 (80×80px)
- "곧 출시 예정" 제목
- 예정 기능 리스트
- 개발 중 메시지

## 💡 팁

1. **반응형 확인**: 브라우저 개발자 도구의 디바이스 모드 사용
2. **스크롤 캡처**: 긴 화면은 브라우저 확장 프로그램 사용
3. **컴포넌트 재사용**: 각 화면은 실제 컴포넌트를 사용하므로 스타일이 정확함
4. **상태별 캡처**: 같은 화면의 다양한 상태를 모두 캡처하여 인터랙션 파악

## 📦 파일 구조

```
figma-screens/
├── README.md              # 이 문서
├── index.tsx              # 모든 화면 export
├── ScreenGallery.tsx      # 갤러리 컴포넌트
├── ChatEmptyState.tsx     # AI 챗봇 - 빈 상태
├── ChatWithMessages.tsx   # AI 챗봇 - 대화 중
├── ChatStreaming.tsx      # AI 챗봇 - 스트리밍
├── ChatWithAgent.tsx      # AI 챗봇 - Agent
├── UploadDefault.tsx      # 업로드 - 기본
├── UploadDragOver.tsx     # 업로드 - 드래그
├── UploadSuccess.tsx      # 업로드 - 성공
└── ComingSoonPages.tsx    # Coming Soon 6개
```
