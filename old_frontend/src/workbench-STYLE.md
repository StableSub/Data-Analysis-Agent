# 🤖 workbench 스타일 UI 가이드

## 🎉 새로운 기능 (v3.0)

**2024.11.10 업데이트** - workbench + ChatGPT 스타일로 완전히 재설계했습니다!

### ✨ 주요 특징

```
┌─────────────────┬──────────────────────────────┐
│  [+ 새 대화]    │        Header               │
│                 │  (기능명 + 모델 + 테마)      │
├─ 기능 메뉴 ─────┼──────────────────────────────┤
│  📱 AI 챗봇     │  📌 선택된 소스 (2개)        │
│  📊 데이터시각화 │  ☑ data.csv  ☑ manual.pdf  │
│  ✏️  데이터편집  ├──────────────────────────────┤
│  🔄 시뮬레이션  │                              │
│  🛡️  감사로그    │      💬 대화 영역             │
├─ 소스 (3) ─────┤                              │
│  ☑ data.csv    │                              │
│  ☑ metrics.xlsx│                              │
│  ☐ manual.pdf  │                              │
├─ 대화 기록 (5)─┼──────────────────────────────┤
│  오늘           │  [📎] [입력창...] [전송]     │
│  - 불량률 분석  │                              │
│  어제           │                              │
│  - 품질 검사    │                              │
└─────────────────┴──────────────────────────────┘
```

## 🚀 빠른 시작

### 1. 실제 앱 실행

```tsx
// App.tsx
import { WorkbenchApp } from './components/WorkbenchApp';
import { Toaster } from './components/ui/sonner';

function App() {
  return (
    <>
      <WorkbenchApp />
      <Toaster />
    </>
  );
}

export default App;
```

<!-- 갤러리/목업 섹션은 제거되었습니다. 실제 워크벤치 앱을 기준으로 설명합니다. -->

## 📁 파일 업로드 시스템

### 두 가지 타입

#### 1️⃣ 데이터셋 (CSV, XLSX, XLS)
- **용도**: 데이터 분석, 시각화, 통계 처리
- **아이콘**: 🗄️ Database
- **색상**: 파란색 계열
- **처리**: 구조화된 데이터로 파싱 및 분석

#### 2️⃣ 문서 (PDF, DOCX, TXT, MD)
- **용도**: RAG를 통한 참조 자료 (매뉴얼, 가이드 등)
- **아이콘**: 📄 Document
- **색상**: 보라색 계열
- **처리**: 텍스트 추출 후 벡터 임베딩

### 업로드 방법

```tsx
// WorkbenchUpload 컴포넌트 사용
<WorkbenchUpload
  onClose={() => setShowUpload(false)}
  onUpload={(file, type) => {
    // type: 'dataset' | 'document'
    handleFileUpload(file, type);
  }}
/>
```

## 🗂️ 소스 파일 관리

### 체크박스 선택 시스템

```tsx
// SourceFiles 컴포넌트
<SourceFiles
  files={[
    { id: '1', name: 'data.csv', type: 'dataset', size: 1024, selected: true },
    { id: '2', name: 'manual.pdf', type: 'document', size: 2048, selected: false },
  ]}
  onToggle={(fileId) => {
    // 파일 선택/해제
    toggleFileSelection(sessionId, fileId);
  }}
  onRemove={(fileId) => {
    // 파일 삭제
    removeFile(sessionId, fileId);
  }}
/>
```

### 선택된 파일 표시

대화 영역 상단에 선택된 소스 파일이 배지로 표시됩니다:

```
📌 분석 중인 소스: [🗄️ data.csv] [📄 manual.pdf]
```

## 💬 대화 기록 관리

### 자동 저장

모든 대화는 Zustand + LocalStorage로 자동 저장됩니다.

```tsx
// 세션 생성
const sessionId = createSession('chat');

// 메시지 추가
addMessage(sessionId, {
  role: 'user',
  content: '데이터 분석해줘',
});

// 파일 추가
addFile(sessionId, {
  name: 'data.csv',
  size: 1024,
  type: 'dataset',
});
```

### 대화 목록

```tsx
<ChatHistory
  sessions={[
    { id: '1', title: '불량률 분석', updatedAt: new Date(), messageCount: 12 },
    { id: '2', title: '품질 검사', updatedAt: new Date(), messageCount: 8 },
  ]}
  activeSessionId="1"
  onSelect={(id) => setActiveSession(id)}
  onDelete={(id) => deleteSession(id)}
  onRename={(id, title) => updateSessionTitle(id, title)}
/>
```

## 🎨 컴포넌트 구조

```
components/
├── WorkbenchApp.tsx                 # 메인 앱 (실제 작동)
├── layout/
│   └── WorkbenchNav.tsx            # 좌측 네비게이션
├── chat/
│   ├── WorkbenchUpload.tsx         # 파일 업로드 모달
│   ├── SourceFiles.tsx              # 소스 파일 목록
│   └── ChatHistory.tsx              # 대화 기록
└── pages/
    ├── Chat.tsx                    # /chat 라우트
    ├── Preprocess.tsx              # /preprocess 라우트
    └── Datasets.tsx                # /datasets 라우트 (업로드)
```

## 📦 상태 관리 (Zustand)

### Store 구조

```typescript
interface AppState {
  // 세션 관리
  sessions: ChatSession[];
  activeSessionId: string | null;
  createSession: (feature) => string;
  setActiveSession: (id) => void;
  deleteSession: (id) => void;
  updateSessionTitle: (id, title) => void;
  
  // 메시지 관리
  addMessage: (sessionId, message) => void;
  
  // 파일 관리
  addFile: (sessionId, file) => void;
  removeFile: (sessionId, fileId) => void;
  toggleFileSelection: (sessionId, fileId) => void;
}
```

### 사용 예시

```tsx
import { useStore } from '../store/useStore';

function MyComponent() {
  const {
    sessions,
    activeSessionId,
    createSession,
    addMessage,
    addFile,
  } = useStore();
  
  const handleNewChat = () => {
    const sessionId = createSession('chat');
    console.log('새 세션 생성:', sessionId);
  };
  
  return <button onClick={handleNewChat}>새 대화</button>;
}
```

## 🎯 핵심 기능

### 1. 새 대화 생성

```tsx
const handleNewChat = () => {
  const sessionId = createSession(activeFeature);
  // 자동으로 activeSessionId가 새 세션으로 변경됨
};
```

### 2. 파일 업로드 & 선택

```tsx
// 1단계: 파일 업로드
addFile(sessionId, {
  name: 'data.csv',
  size: 1024,
  type: 'dataset',
});

// 2단계: 선택/해제
toggleFileSelection(sessionId, fileId);

// 3단계: 선택된 파일만 AI가 참조
const selectedFiles = session.files.filter(f => f.selected);
```

### 3. 대화 기록 전환

```tsx
// 이전 대화로 돌아가기
setActiveSession('previous-session-id');

// 모든 메시지와 파일이 복원됨
const session = sessions.find(s => s.id === activeSessionId);
console.log(session.messages, session.files);
```

## 🎨 UI 특징

### workbench 스타일
- ✅ 소스 파일 체크박스 선택
- ✅ 데이터셋 vs 문서 구분
- ✅ 접을 수 있는 섹션

### ChatGPT 스타일
- ✅ 좌측 대화 기록
- ✅ 새 대화 버튼
- ✅ 이름 변경 / 삭제 기능

### 추가 개선사항
- ✅ 다크 모드 지원
- ✅ 선택된 소스 배지 표시
- ✅ 날짜별 대화 그룹화
- ✅ LocalStorage 자동 저장

## 🔄 기존 버전과의 차이

### Before (v2.0 - SimplifiedApp)
```
❌ 세션 관리 없음 (새 대화 시 모든 내용 사라짐)
❌ 파일 선택 기능 없음
❌ 대화 기록 저장 안됨
❌ 단순한 파일 업로드
```

### After (v3.0 - WorkbenchApp)
```
✅ 완전한 세션 관리 (대화 기록 보존)
✅ 파일 체크박스 선택
✅ LocalStorage 자동 저장
✅ 데이터셋 vs 문서 구분 업로드
✅ 대화 이름 변경 / 삭제
✅ 접을 수 있는 소스/히스토리 섹션
```

## 📝 TODO

- [ ] 실제 파일 파싱 구현 (CSV/XLSX)
- [ ] PDF/DOCX 텍스트 추출
- [ ] RAG 구현 (문서 임베딩)
- [ ] 실제 AI API 연동
- [ ] 파일 용량 검증
- [ ] 드래그 앤 드롭 개선
- [ ] 대화 검색 기능
- [ ] 대화 내보내기 (JSON, MD)

## 🎓 사용 가이드

### 1. 새 대화 시작
1. 좌측 상단 "새 대화" 버튼 클릭
2. 새 세션이 생성되고 빈 대화창 표시

### 2. 파일 업로드
1. 입력창 왼쪽 📎 버튼 클릭
2. "데이터셋" 또는 "문서" 탭 선택
3. 파일 드래그 또는 "파일 선택" 클릭
4. 좌측 "소스" 섹션에 파일 추가됨

### 3. 소스 선택
1. 좌측 "소스" 섹션에서 체크박스 클릭
2. 선택된 파일만 대화 영역 상단에 배지로 표시
3. AI는 선택된 파일만 참조

### 4. 대화 기록 관리
1. 좌측 "대화 기록" 섹션에서 이전 대화 클릭
2. 모든 메시지와 파일이 복원됨
3. 더보기 (⋮) 메뉴로 이름 변경 / 삭제

## 💡 팁

- **Shift + Enter**: 줄바꿈
- **Enter**: 메시지 전송
- **체크박스**: 파일 선택/해제
- **섹션 헤더 클릭**: 접기/펼치기

---

**제작일**: 2024.11.10  
**버전**: 3.0.0 (workbench Style)  
**기술 스택**: React + TypeScript + Zustand + Tailwind CSS
