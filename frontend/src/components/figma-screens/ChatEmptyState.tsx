import { FeatureNav } from '../layout/FeatureNav';
import { Bot } from 'lucide-react';
import { Button } from '../ui/button';

/**
 * AI 챗봇 - 빈 상태 (메시지 없음)
 * 피그마 디자인 참고용
 */
export function ChatEmptyState() {
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-[#1c1c1e]">
      {/* 좌측 네비게이션 */}
      <FeatureNav 
        activeFeature="chat"
        onFeatureChange={() => {}}
      />

      {/* 중앙: SessionSidebar */}
      <div className="w-64 bg-white dark:bg-[#171717] border-r border-gray-200 dark:border-white/10 flex flex-col">
        <div className="p-3 border-b border-gray-200 dark:border-white/10">
          <Button className="w-full justify-start gap-3 h-11 bg-white dark:bg-white/5 hover:bg-gray-100 dark:hover:bg-white/10 border border-gray-200 dark:border-white/20 text-gray-900 dark:text-white shadow-none">
            <span className="text-lg">➕</span>
            새 대화
          </Button>
        </div>
        
        <div className="flex-1 flex items-center justify-center p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
            대화 기록이 없습니다
          </p>
        </div>

        <div className="p-4 border-t border-gray-200 dark:border-white/10">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            <p>총 0개의 대화</p>
          </div>
        </div>
      </div>

      {/* 메인 영역 */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white dark:bg-[#2c2c2e] border-b border-gray-200 dark:border-white/10 px-6 py-3 h-16">
          <div className="flex items-center justify-between h-10">
            <div className="flex items-center gap-3">
              <button className="h-10 w-10 rounded-md hover:bg-gray-100 dark:hover:bg-white/10 flex items-center justify-center">
                <span className="text-xl">☰</span>
              </button>
              <div>
                <h2 className="text-gray-900 dark:text-white">새 대화</h2>
                <p className="text-xs text-gray-500 dark:text-[#98989d]">
                  Manufacturing AI Assistant
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button className="h-10 w-10 rounded-md hover:bg-gray-100 dark:hover:bg-white/10 flex items-center justify-center">
                <span className="text-xl">🌙</span>
              </button>
              <button className="h-10 px-4 rounded-md border border-gray-200 dark:border-white/20 hover:bg-gray-100 dark:hover:bg-white/10 flex items-center gap-2">
                <Bot className="w-4 h-4" />
                <span className="text-sm">Agent</span>
              </button>
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs">
                U
              </div>
            </div>
          </div>
        </div>

        {/* Empty State Content */}
        <div className="flex-1 flex items-center justify-center p-6 overflow-auto">
          <div className="w-full max-w-2xl mx-auto space-y-10">
            {/* Header */}
            <div className="text-center space-y-4">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500 to-purple-600 text-white text-4xl shadow-lg">
                🤖
              </div>
              <h1 className="text-4xl text-gray-900 dark:text-white">
                제조 데이터 분석 AI
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                데이터 분석, 이상 탐지, 리포트 생성 등 무엇이든 질문하세요
              </p>
            </div>

            {/* Model Selector */}
            <div className="space-y-4">
              <p className="text-sm text-center text-gray-600 dark:text-gray-400">
                사용할 AI 모델을 선택하세요
              </p>
              <div className="flex justify-center">
                <button className="px-4 py-2 rounded-lg border-2 border-gray-200 dark:border-white/20 bg-white dark:bg-[#2c2c2e] hover:border-blue-500 dark:hover:border-[#0a84ff]">
                  <span className="text-sm text-gray-900 dark:text-white">GPT-4 Turbo</span>
                </button>
              </div>
            </div>

            {/* Example Prompts */}
            <div className="space-y-4">
              <p className="text-sm text-center text-gray-600 dark:text-gray-400">
                예시 질문
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button className="group p-5 rounded-2xl border-2 border-gray-200 dark:border-white/20 hover:border-blue-500 dark:hover:border-[#0a84ff] hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-all text-left">
                  <div className="text-3xl mb-3">📊</div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-[#0a84ff]">
                    "업로드한 데이터를 분석해줘"
                  </p>
                </button>
                <button className="group p-5 rounded-2xl border-2 border-gray-200 dark:border-white/20 hover:border-blue-500 dark:hover:border-[#0a84ff] hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-all text-left">
                  <div className="text-3xl mb-3">⚠️</div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-[#0a84ff]">
                    "이상 패턴을 찾아줘"
                  </p>
                </button>
                <button className="group p-5 rounded-2xl border-2 border-gray-200 dark:border-white/20 hover:border-blue-500 dark:hover:border-[#0a84ff] hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-all text-left">
                  <div className="text-3xl mb-3">📄</div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-[#0a84ff]">
                    "분석 리포트를 생성해줘"
                  </p>
                </button>
              </div>
            </div>

            {/* Features */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 pt-8 border-t border-gray-200 dark:border-white/10">
              <div className="text-center space-y-2">
                <div className="text-3xl">🔍</div>
                <p className="text-xs text-gray-600 dark:text-gray-400">실시간 분석</p>
              </div>
              <div className="text-center space-y-2">
                <div className="text-3xl">📈</div>
                <p className="text-xs text-gray-600 dark:text-gray-400">시각화</p>
              </div>
              <div className="text-center space-y-2">
                <div className="text-3xl">🔒</div>
                <p className="text-xs text-gray-600 dark:text-gray-400">보안 모니터링</p>
              </div>
              <div className="text-center space-y-2">
                <div className="text-3xl">⚡</div>
                <p className="text-xs text-gray-600 dark:text-gray-400">빠른 응답</p>
              </div>
            </div>
          </div>
        </div>

        {/* Chat Input */}
        <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-6 py-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-end gap-3">
              <button className="flex items-center justify-center h-10 w-10 rounded-md border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800">
                <span className="text-lg">📎</span>
              </button>
              
              <div className="flex-1 relative">
                <textarea
                  placeholder="메시지를 입력하세요... (Enter: 전송, Shift+Enter: 줄바꿈)"
                  className="w-full min-h-[44px] px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 resize-none"
                  rows={1}
                />
              </div>

              <button className="h-10 w-10 rounded-md bg-blue-500 hover:bg-blue-600 flex items-center justify-center text-white">
                <span className="text-lg">▶</span>
              </button>
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
