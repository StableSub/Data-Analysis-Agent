import { NotebookLMNav } from '../layout/NotebookLMNav';
import { Moon, Paperclip, Send, BarChart3, FileEdit, Activity } from 'lucide-react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';

/**
 * NotebookLM 스타일 - 빈 상태
 * 피그마 디자인 참고용
 */
export function NotebookLMEmpty() {
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-[#1c1c1e]">
      {/* 좌측 네비게이션 */}
      <NotebookLMNav
        onNewChat={() => {}}
        sessions={[]}
        activeSessionId={null}
        onSessionSelect={() => {}}
        onSessionDelete={() => {}}
        onSessionRename={() => {}}
        files={[]}
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
                <button className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-gray-100 dark:bg-white/5 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-white/10 transition-all">
                  <BarChart3 className="w-4 h-4" />
                  <span>데이터 시각화</span>
                </button>
                <button className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-blue-600 dark:bg-[#0a84ff] text-white shadow-sm">
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

        {/* Empty State */}
        <div className="flex-1 overflow-auto p-6">
          <div className="h-full flex items-center justify-center">
            <div className="max-w-2xl mx-auto text-center space-y-8">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500 to-purple-600 text-white text-4xl shadow-lg">
                🤖
              </div>
              <div>
                <h2 className="text-3xl text-gray-900 dark:text-white mb-2">데이터 편집</h2>
                <p className="text-gray-600 dark:text-gray-400">
                  AI 기반 데이터 수정 및 보정
                </p>
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
