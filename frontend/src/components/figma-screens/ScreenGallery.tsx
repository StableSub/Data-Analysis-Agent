import { useState } from 'react';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { 
  ChatEmptyState, 
  ChatWithMessages, 
  ChatStreaming, 
  ChatWithAgent,
  UploadDefault,
  UploadDragOver,
  UploadSuccess,
  ComingSoonSnapshot,
  ComingSoonFilter,
  ComingSoonVisualization,
  ComingSoonEdit,
  ComingSoonSimulation,
  ComingSoonAudit,
} from './index';

/**
 * 피그마 디자인 참고용 화면 갤러리
 * 모든 화면을 한 곳에서 확인할 수 있습니다
 */

const screens = [
  // AI 챗봇
  { id: 'chat-empty', name: 'AI 챗봇 - 빈 상태', component: ChatEmptyState, category: 'AI 챗봇' },
  { id: 'chat-messages', name: 'AI 챗봇 - 대화 진행', component: ChatWithMessages, category: 'AI 챗봇' },
  { id: 'chat-streaming', name: 'AI 챗봇 - 스트리밍', component: ChatStreaming, category: 'AI 챗봇' },
  { id: 'chat-agent', name: 'AI 챗봇 - Agent 위젯', component: ChatWithAgent, category: 'AI 챗봇' },
  
  // 데이터 업로드
  { id: 'upload-default', name: '업로드 - 기본', component: UploadDefault, category: '데이터 업로드' },
  { id: 'upload-drag', name: '업로드 - 드래그 오버', component: UploadDragOver, category: '데이터 업로드' },
  { id: 'upload-success', name: '업로드 - 성공', component: UploadSuccess, category: '데이터 업로드' },
  
  // Coming Soon
  { id: 'coming-snapshot', name: '스냅샷', component: ComingSoonSnapshot, category: 'Coming Soon' },
  { id: 'coming-filter', name: '필터링', component: ComingSoonFilter, category: 'Coming Soon' },
  { id: 'coming-viz', name: '시각화', component: ComingSoonVisualization, category: 'Coming Soon' },
  { id: 'coming-edit', name: '편집', component: ComingSoonEdit, category: 'Coming Soon' },
  { id: 'coming-sim', name: '시뮬레이션', component: ComingSoonSimulation, category: 'Coming Soon' },
  { id: 'coming-audit', name: '감사 로그', component: ComingSoonAudit, category: 'Coming Soon' },
];

export function ScreenGallery() {
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
          <h1 className="text-3xl text-gray-900 dark:text-white mb-2">
            피그마 디자인 화면 갤러리
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            각 화면을 클릭하여 전체 화면으로 확인하세요
          </p>
        </div>

        {/* Group by category */}
        {['AI 챗봇', '데이터 업로드', 'Coming Soon'].map(category => (
          <div key={category} className="mb-8">
            <h2 className="text-xl text-gray-900 dark:text-white mb-4">
              {category}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {screens
                .filter(screen => screen.category === category)
                .map(screen => (
                  <Card
                    key={screen.id}
                    className="p-4 hover:shadow-lg transition-shadow cursor-pointer"
                    onClick={() => setSelectedScreen(screen.id)}
                  >
                    <div className="aspect-video bg-gray-200 dark:bg-gray-700 rounded-lg mb-3 flex items-center justify-center">
                      <span className="text-4xl">🖼️</span>
                    </div>
                    <h3 className="text-gray-900 dark:text-white font-medium">
                      {screen.name}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      클릭하여 전체 화면 보기
                    </p>
                  </Card>
                ))}
            </div>
          </div>
        ))}

        {/* Instructions */}
        <Card className="p-6 mt-8 bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-900/30">
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
        <Card className="p-6 mt-4">
          <h3 className="text-gray-900 dark:text-white font-medium mb-2">
            💻 개별 화면 사용 예시
          </h3>
          <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto text-sm">
{`import { ChatEmptyState } from './components/figma-screens';

function App() {
  return <ChatEmptyState />;
}`}
          </pre>
        </Card>
      </div>
    </div>
  );
}
