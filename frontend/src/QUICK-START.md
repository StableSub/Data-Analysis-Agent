# 🚀 빠른 시작 가이드

## 새로운 단순화 레이아웃

**2024.11.10 업데이트**: 좌측 네비 + 대화창 구조로 완전히 재설계했습니다!

### 구조

```
┌─────────────────┬──────────────────────────────┐
│  [+ 새 대화]    │        Header               │
│                 │  (기능명 + 모델 + 테마)      │
├─────────────────┼──────────────────────────────┤
│  📱 AI 챗봇     │                              │
│  📊 데이터시각화 │        대화 영역             │
│  ✏️  데이터편집  │    (메시지 + 파일 업로드)     │
│  🔄 시뮬레이션  │                              │
│  🛡️  감사로그    │                              │
│                 ├──────────────────────────────┤
│                 │        입력 창               │
│                 │    (📎 파일 + 💬 메시지)     │
├─────────────────┴──────────────────────────────┤
│  ��� 사용자 정보                                │
└──────────────────────────────────────────────────┘
```

## 옵션 1: 실제 작동하는 앱 보기

**App.tsx** 파일을 열고 다음과 같이 수정:

```tsx
import { SimplifiedApp } from './components/SimplifiedApp';
import { Toaster } from './components/ui/sonner';

function App() {
  return (
    <>
      <SimplifiedApp />
      <Toaster />
    </>
  );
}

export default App;
```

그 다음:
```bash
npm run dev
```

## 옵션 2: 피그마 참고용 화면 갤러리

**App.tsx** 파일을 열고 다음과 같이 수정:

```tsx
import { SimplifiedGallery } from './components/figma-screens/SimplifiedGallery';

function App() {
  return <SimplifiedGallery />;
}

export default App;
```

## 주요 변경사항

### Before (기존)
- ❌ 3단 레이아웃 (FeatureNav + SessionSidebar + 중앙)
- ❌ 8개 기능 (업로드, 스냅샷, 필터링 등 분리)
- ❌ 복잡한 네비게이션 구조

### After (신규) ✨
- ✅ 2단 레이아웃 (좌측 네비 + 대화창)
- ✅ 5개 주요 기능만 (AI 챗봇, 시각화, 편집, 시뮬레이션, 감사)
- ✅ 데이터 관리는 대화창 내에서 처리
- ✅ 파일 업로드는 입력창에 통합

## 파일 업로드 방법

1. **입력창의 📎 버튼 클릭**
2. **파일 업로드 모달 열림**
3. **파일 선택 또는 드래그&드롭**
4. **업로드된 파일은 상단 파일 바에 표시**

## 각 기능 설명

### 1. AI 챗봇
- 제조 데이터 분석 AI 어시스턴트
- 파일 업로드 후 데이터 분석 요청
- 실시간 AI 응답

### 2. 데이터 시각화
- 차트와 그래프 생성
- 선형, 막대, 원형, 산점도 등

### 3. 데이터 편집
- AI 기반 데이터 수정 및 보정
- 일괄 편집 기능

### 4. 시뮬레이션
- 제조 공정 시뮬레이션
- 예측 분석

### 5. 감사 로그
- 사용자 활동 추적
- 보안 모니터링

## 개발 포인트

### 컴포넌트 구조

```
components/
├── SimplifiedApp.tsx              # 메인 앱
├── layout/
│   └── SimplifiedNav.tsx          # 좌측 네비게이션
└── chat/
    └── SimplifiedChatLayout.tsx   # 대화 레이아웃
```

### 상태 관리

```tsx
const [activeFeature, setActiveFeature] = useState<FeatureType>('chat');
const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
```

## 다음 단계

1. ✅ 기본 레이아웃 완성
2. ⏳ 각 기능별 실제 기능 구현
3. ⏳ Zustand 스토어 연동
4. ⏳ API 통신 추가
5. ⏳ 파일 처리 로직

## 도움이 필요하신가요?

- 📖 상세 가이드: `/FIGMA-SCREENS-GUIDE.md`
- 🎨 화면 갤러리: `SimplifiedGallery` 컴포넌트 사용
- 💻 코드 참고: `/components/SimplifiedApp.tsx`

---

**작성일**: 2024.11.10  
**버전**: 2.0.0 (단순화 레이아웃)
