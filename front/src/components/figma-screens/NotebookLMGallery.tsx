import { useState } from 'react';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { NotebookLMEmpty } from './NotebookLMEmpty';
import { NotebookLMWithSources } from './NotebookLMWithSources';

const screens = [
  { id: 'empty', name: '빈 상태', component: NotebookLMEmpty },
  { id: 'sources', name: '소스 파일 + 대화', component: NotebookLMWithSources },
];

export function NotebookLMGallery() {
  const [selectedScreen, setSelectedScreen] = useState<string | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);

  const selectedScreenData = screens.find(s => s.id === selectedScreen);

  if (selectedScreen && selectedScreenData) {
    const Component = selectedScreenData.component;
    return (
      <div className={isDarkMode ? 'dark' : ''}>
        <div className="fixed top-4 right-4 z-50 flex gap-2">
          <Button
            onClick={() => setIsDarkMode(!isDarkMode)}
            variant="outline"
            className="bg-white dark:bg-gray-800 shadow-lg"
          >
            {isDarkMode ? '☀️ Light' : '🌙 Dark'}
          </Button>
          <Button
            onClick={() => setSelectedScreen(null)}
            variant="outline"
            className="bg-white dark:bg-gray-800 shadow-lg"
          >
            ← 목록으로
          </Button>
        </div>
        <Component />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-12 text-center">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="text-6xl">🤖</div>
            <div className="text-left">
              <h1 className="text-4xl text-gray-900 dark:text-white mb-2">
                NotebookLM 스타일
              </h1>
              <div className="flex items-center gap-2">
                <Badge variant="default" className="bg-blue-600">최신</Badge>
                <Badge variant="secondary">v3.0</Badge>
              </div>
            </div>
          </div>
          <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            좌측 네비게이션 + 소스 파일 선택 + 대화 기록 관리
          </p>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <Card className="p-6 bg-white/80 backdrop-blur-sm dark:bg-gray-800/80 border-2">
            <div className="text-4xl mb-4">📁</div>
            <h3 className="font-medium text-gray-900 dark:text-white mb-2">
              스마트 소스 관리
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              데이터셋과 문서를 구분하여 업로드하고, 체크박스로 선택적 분석
            </p>
          </Card>
          
          <Card className="p-6 bg-white/80 backdrop-blur-sm dark:bg-gray-800/80 border-2">
            <div className="text-4xl mb-4">💬</div>
            <h3 className="font-medium text-gray-900 dark:text-white mb-2">
              대화 기록 보존
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              모든 대화가 자동 저장되고, 언제든지 이전 대화로 돌아갈 수 있음
            </p>
          </Card>
          
          <Card className="p-6 bg-white/80 backdrop-blur-sm dark:bg-gray-800/80 border-2">
            <div className="text-4xl mb-4">🎨</div>
            <h3 className="font-medium text-gray-900 dark:text-white mb-2">
              깔끔한 UI/UX
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              NotebookLM과 ChatGPT의 장점을 결합한 직관적인 인터페이스
            </p>
          </Card>
        </div>

        {/* Screens */}
        <div className="mb-12">
          <h2 className="text-2xl text-gray-900 dark:text-white mb-6">화면 둘러보기</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {screens.map(screen => (
              <Card
                key={screen.id}
                className="p-6 hover:shadow-xl transition-all cursor-pointer group bg-white dark:bg-gray-800"
                onClick={() => setSelectedScreen(screen.id)}
              >
                <div className="aspect-video bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl mb-4 flex items-center justify-center text-6xl group-hover:scale-105 transition-transform">
                  {screen.id === 'empty' ? '🚀' : '📊'}
                </div>
                <h3 className="text-xl text-gray-900 dark:text-white mb-2">
                  {screen.name}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                  클릭하여 전체 화면 보기
                </p>
                <Button className="w-full" variant="outline">
                  화면 보기 →
                </Button>
              </Card>
            ))}
          </div>
        </div>

        {/* Architecture */}
        <Card className="p-8 bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20 border-2 border-blue-200 dark:border-blue-900">
          <h2 className="text-2xl text-gray-900 dark:text-white mb-6">🏗️ 구조 설명</h2>
          
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="font-medium text-gray-900 dark:text-white mb-3">좌측 네비게이션</h3>
              <ul className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
                <li>✅ 새 대화 버튼 (최상단)</li>
                <li>✅ 5개 주요 기능 메뉴</li>
                <li>✅ 소스 파일 목록 (접기/펼치기)</li>
                <li>✅ 대화 기록 (날짜별 그룹화)</li>
                <li>✅ 사용자 정보 (하단)</li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium text-gray-900 dark:text-white mb-3">대화 영역</h3>
              <ul className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
                <li>✅ 헤더 (기능명 + 모델 + 테마)</li>
                <li>✅ 선택된 소스 배지 표시</li>
                <li>✅ 메시지 영역</li>
                <li>✅ 입력창 (파일 첨부 버튼)</li>
              </ul>
            </div>
          </div>

          <div className="mt-6 p-4 bg-white/50 dark:bg-black/20 rounded-lg">
            <p className="text-sm text-gray-700 dark:text-gray-300">
              💡 <strong>핵심 기능:</strong> 파일 업로드 시 데이터셋(CSV/XLSX)과 문서(PDF/DOCX)를 
              구분하여 각각 다른 방식으로 처리합니다. 체크박스로 원하는 소스만 선택하여 분석할 수 있습니다.
            </p>
          </div>
        </Card>

        {/* Code Example */}
        <Card className="p-8 mt-6 bg-white dark:bg-gray-800">
          <h2 className="text-2xl text-gray-900 dark:text-white mb-4">💻 사용 방법</h2>
          <pre className="bg-gray-900 dark:bg-black text-gray-100 p-6 rounded-xl overflow-x-auto text-sm">
{`import { NotebookLMApp } from './components/NotebookLMApp';
import { Toaster } from './components/ui/sonner';

function App() {
  return (
    <>
      <NotebookLMApp />
      <Toaster />
    </>
  );
}

export default App;`}
          </pre>
        </Card>

        {/* Footer */}
        <div className="mt-12 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            🎨 NotebookLM 스타일 UI · 📦 Zustand 상태관리 · 💾 LocalStorage 자동저장
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
            제작일: 2024.11.10 · 버전: 3.0.0
          </p>
        </div>
      </div>
    </div>
  );
}
