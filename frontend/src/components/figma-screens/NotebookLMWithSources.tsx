import { NotebookLMNav } from '../layout/NotebookLMNav';
import { Moon, Paperclip, Send, Database, FileText, BarChart3, FileEdit, Activity } from 'lucide-react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';

/**
 * NotebookLM 스타일 - 소스 파일 있는 상태
 * 피그마 디자인 참고용
 */
export function NotebookLMWithSources() {
  const mockFiles = [
    { id: '1', name: 'manufacturing_data_2024.csv', type: 'dataset' as const, size: 1234567, selected: true },
    { id: '2', name: 'quality_metrics.xlsx', type: 'dataset' as const, size: 987654, selected: true },
    { id: '3', name: 'production_manual.pdf', type: 'document' as const, size: 2345678, selected: false },
  ];

  const mockSessions = [
    { id: '1', title: '제조 데이터 불량률 분석', updatedAt: new Date(), messageCount: 12 },
    { id: '2', title: '품질 메트릭 시각화', updatedAt: new Date(Date.now() - 86400000), messageCount: 8 },
    { id: '3', title: '공정 최적화 시뮬레이션', updatedAt: new Date(Date.now() - 172800000), messageCount: 5 },
  ];

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-[#1c1c1e]">
      {/* 좌측 네비게이션 */}
      <NotebookLMNav
        onNewChat={() => {}}
        sessions={mockSessions}
        activeSessionId="1"
        onSessionSelect={() => {}}
        onSessionDelete={() => {}}
        onSessionRename={() => {}}
        files={mockFiles}
        onFileToggle={() => {}}
        onFileRemove={() => {}}
      />

      {/* 우측 대화 영역 */}
      <div className="flex-1 flex flex-col bg-white dark:bg-[#1c1c1e]">
        {/* Header */}
        <div className="bg-white dark:bg-[#2c2c2e] border-b border-gray-200 dark:border-white/10 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div>
                <h1 className="text-xl text-gray-900 dark:text-white">AI 챗봇</h1>
                <p className="text-sm text-gray-500 dark:text-[#98989d]">
                  제조 데이터 분석 AI 어시스턴트
                </p>
              </div>
              
              {/* 기능 버튼들 */}
              <div className="flex items-center gap-2 ml-4">
                <button className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-blue-600 dark:bg-[#0a84ff] text-white shadow-sm">
                  <BarChart3 className="w-4 h-4" />
                  <span>데이터 시각화</span>
                </button>
                <button className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-gray-100 dark:bg-white/5 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-white/10 transition-all">
                  <FileEdit className="w-4 h-4" />
                  <span>데이터 편집</span>
                </button>
                <button className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-gray-100 dark:bg-white/5 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-white/10 transition-all">
                  <Activity className="w-4 h-4" />
                  <span>시뮬레이션</span>
                </button>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="px-4 py-2 rounded-lg border border-gray-200 dark:border-white/20 bg-white dark:bg-[#2c2c2e]">
                <span className="text-sm text-gray-900 dark:text-white">GPT-4 Turbo</span>
              </div>
              <Button size="icon" variant="ghost" className="h-10 w-10">
                <Moon className="w-5 h-5" />
              </Button>
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm">
                U
              </div>
            </div>
          </div>
        </div>

        {/* Selected Files Badge */}
        <div className="bg-blue-50 dark:bg-blue-900/10 border-b border-blue-200 dark:border-blue-900/30 px-6 py-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-blue-700 dark:text-blue-300">
              분석 중인 소스:
            </span>
            <Badge variant="secondary" className="gap-1.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
              <Database className="w-3 h-3" />
              manufacturing_data_2024.csv
            </Badge>
            <Badge variant="secondary" className="gap-1.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
              <Database className="w-3 h-3" />
              quality_metrics.xlsx
            </Badge>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* User Message */}
            <div className="flex justify-end">
              <div className="max-w-[70%]">
                <div className="bg-blue-500 dark:bg-[#0a84ff] text-white rounded-2xl px-4 py-3">
                  <p className="text-sm">업로드한 데이터셋에서 불량률이 높은 시간대를 분석해주세요</p>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right">14:30</p>
              </div>
            </div>

            {/* Assistant Message */}
            <div className="flex justify-start">
              <div className="max-w-[70%]">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white flex-shrink-0">
                    🤖
                  </div>
                  <div className="flex-1">
                    <div className="bg-gray-100 dark:bg-[#2c2c2e] rounded-2xl px-4 py-3">
                      <p className="text-sm text-gray-900 dark:text-white mb-3">
                        선택된 2개의 데이터셋을 분석했습니다:
                      </p>
                      <div className="space-y-2 mb-3">
                        <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                          <Database className="w-3 h-3" />
                          manufacturing_data_2024.csv (15,234 rows)
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                          <Database className="w-3 h-3" />
                          quality_metrics.xlsx (8,912 rows)
                        </div>
                      </div>
                      <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                        <p className="text-xs text-gray-700 dark:text-gray-300 font-medium mb-2">
                          ⚠️ 불량률 높은 시간대
                        </p>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          1. 오전 6~8시: 4.2%<br />
                          2. 오후 2~4시: 3.8%<br />
                          3. 야간 10~12시: 5.1%
                        </p>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 px-2">14:32</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-6 py-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-end gap-3">
              <Button size="icon" variant="outline" className="h-11 w-11 flex-shrink-0">
                <Paperclip className="w-5 h-5" />
              </Button>
              <div className="flex-1">
                <Textarea
                  placeholder="메시지를 입력하세요..."
                  className="min-h-[44px] resize-none"
                  rows={1}
                />
              </div>
              <Button size="icon" className="h-11 w-11 flex-shrink-0 bg-blue-500">
                <Send className="w-5 h-5" />
              </Button>
            </div>
            <div className="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>AI 생성 콘텐츠는 부정확할 수 있습니다</span>
              <span>0 / 4000</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
