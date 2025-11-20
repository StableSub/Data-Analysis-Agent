import { useState } from 'react';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { 
  SimplifiedChatEmpty,
  SimplifiedChatWithMessages,
  SimplifiedFileUpload,
  SimplifiedVisualization,
} from './index';

/**
 * 단순화된 레이아웃 화면 갤러리
 */

const screens = [
  { id: 'simple-empty', name: 'AI 챗봇 - 빈 상태', component: SimplifiedChatEmpty, category: '단순화 레이아웃' },
  { id: 'simple-messages', name: 'AI 챗봇 - 대화 중', component: SimplifiedChatWithMessages, category: '단순화 레이아웃' },
  { id: 'simple-upload', name: 'AI 챗봇 - 파일 업로드', component: SimplifiedFileUpload, category: '단순화 레이아웃' },
  { id: 'simple-viz', name: '데이터 시각화', component: SimplifiedVisualization, category: '단순화 레이아웃' },
];

export function SimplifiedGallery() {
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
    <div className="min-h-screen bg-gray-50 dark:bg-[#1c1c1e] p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl text-gray-900 dark:text-white">
              단순화된 레이아웃 화면 갤러리
            </h1>
            <Badge variant="default" className="bg-blue-600">NEW</Badge>
          </div>
          <p className="text-gray-600 dark:text-gray-400">
            새로운 단순화된 레이아웃: 좌측 네비 + 대화창
          </p>
        </div>

        {/* New Simplified Layout */}
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-xl text-gray-900 dark:text-white">
              단순화 레이아웃
            </h2>
            <Badge>최신</Badge>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            새 대화 버튼 + 5개 주요 기능 메뉴. 모든 데이터 관리는 대화창 내에서 처리.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {screens.map(screen => (
              <Card
                key={screen.id}
                className="p-4 hover:shadow-lg transition-shadow cursor-pointer dark:bg-[#2c2c2e] dark:border-white/10"
                onClick={() => setSelectedScreen(screen.id)}
              >
                <div className="aspect-video bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg mb-3 flex items-center justify-center text-4xl">
                  {screen.id === 'simple-empty' ? '🤖' : 
                   screen.id === 'simple-messages' ? '💬' :
                   screen.id === 'simple-upload' ? '📁' : '📊'}
                </div>
                <h3 className="text-gray-900 dark:text-white font-medium mb-1">
                  {screen.name}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  클릭하여 전체 화면 보기
                </p>
              </Card>
            ))}
          </div>
        </div>

        {/* 레이아웃 비교 */}
        <Card className="p-6 bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-900/30">
          <h3 className="text-gray-900 dark:text-white font-medium mb-4">
            📐 새 레이아웃 구조
          </h3>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">좌측 네비게이션 (256px)</h4>
              <ul className="space-y-1 text-sm text-gray-700 dark:text-gray-300">
                <li>✅ 새 대화 버튼 (최상단)</li>
                <li>✅ AI 챗봇</li>
                <li>✅ 데이터 시각화</li>
                <li>✅ 데이터 편집</li>
                <li>✅ 시뮬레이션</li>
                <li>✅ 감사 로그</li>
                <li>✅ 사용자 정보 (하단)</li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">대화 영역 (flex-1)</h4>
              <ul className="space-y-1 text-sm text-gray-700 dark:text-gray-300">
                <li>✅ 헤더 (기능명 + 모델 선택 + 테마)</li>
                <li>✅ 업로드 파일 바 (optional)</li>
                <li>✅ 메시지 영역</li>
                <li>✅ 입력 창 (파일 업로드 버튼 포함)</li>
              </ul>
            </div>
          </div>
        </Card>

        {/* Instructions */}
        <Card className="p-6 mt-6 dark:bg-[#2c2c2e] dark:border-white/10">
          <h3 className="text-gray-900 dark:text-white font-medium mb-2">
            📝 사용 방법
          </h3>
          <ul className="space-y-1 text-sm text-gray-700 dark:text-gray-300">
            <li>• 각 카드를 클릭하면 전체 화면으로 해당 화면을 볼 수 있습니다</li>
            <li>• 우측 상단의 Light/Dark 버튼으로 테마를 전환할 수 있습니다</li>
            <li>• "목록으로" 버튼을 클릭하면 갤러리로 돌아옵니다</li>
            <li>• 스크린샷을 찍어 피그마에서 참고하세요</li>
          </ul>
        </Card>

        {/* Code Example */}
        <Card className="p-6 mt-4 dark:bg-[#2c2c2e] dark:border-white/10">
          <h3 className="text-gray-900 dark:text-white font-medium mb-2">
            💻 실제 앱에서 사용하기
          </h3>
          <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto text-sm">
{`import { SimplifiedApp } from './components/SimplifiedApp';

function App() {
  return <SimplifiedApp />;
}`}
          </pre>
        </Card>
      </div>
    </div>
  );
}
