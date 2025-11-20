import { FeatureNav } from '../layout/FeatureNav';
import { MessageSquare, Edit2, Trash2, Bot } from 'lucide-react';
import { Button } from '../ui/button';

/**
 * AI 챗봇 - 대화 진행 중
 * 피그마 디자인 참고용
 */
export function ChatWithMessages() {
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-[#1c1c1e]">
      {/* 좌측 네비게이션 */}
      <FeatureNav 
        activeFeature="chat"
        onFeatureChange={() => {}}
      />

      {/* SessionSidebar */}
      <div className="w-64 bg-white dark:bg-[#171717] border-r border-gray-200 dark:border-white/10 flex flex-col">
        <div className="p-3 border-b border-gray-200 dark:border-white/10">
          <Button className="w-full justify-start gap-3 h-11 bg-white dark:bg-white/5 hover:bg-gray-100 dark:hover:bg-white/10 border border-gray-200 dark:border-white/20 text-gray-900 dark:text-white shadow-none">
            <span className="text-lg">➕</span>
            새 대화
          </Button>
        </div>
        
        <div className="flex-1 p-2 space-y-1 overflow-auto">
          {/* 활성 대화 */}
          <div className="group relative flex items-center gap-2 px-3 py-2.5 rounded-lg bg-gray-100 dark:bg-white/5 cursor-pointer">
            <MessageSquare className="w-4 h-4 text-gray-900 dark:text-white flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-900 dark:text-white truncate">
                제조 데이터 분석
              </p>
            </div>
            <div className="absolute right-2 flex gap-1 items-center opacity-0 group-hover:opacity-100">
              <button className="h-7 w-7 rounded-md hover:bg-gray-200 dark:hover:bg-white/10 flex items-center justify-center">
                <Edit2 className="w-3.5 h-3.5" />
              </button>
              <button className="h-7 w-7 rounded-md hover:bg-red-100 dark:hover:bg-red-900/30 flex items-center justify-center text-red-600">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* 다른 대화들 */}
          <div className="group relative flex items-center gap-2 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-white/5 cursor-pointer">
            <MessageSquare className="w-4 h-4 text-gray-500 dark:text-gray-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700 dark:text-gray-300 truncate">
                이상 패턴 분석 요청
              </p>
            </div>
          </div>

          <div className="group relative flex items-center gap-2 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-white/5 cursor-pointer">
            <MessageSquare className="w-4 h-4 text-gray-500 dark:text-gray-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700 dark:text-gray-300 truncate">
                생산 라인 최적화
              </p>
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-gray-200 dark:border-white/10">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            <p>총 3개의 대화</p>
          </div>
        </div>
      </div>

      {/* 메인 영역 */}
      <div className="flex-1 flex flex-col bg-white dark:bg-[#1c1c1e]">
        {/* Header */}
        <div className="bg-white dark:bg-[#2c2c2e] border-b border-gray-200 dark:border-white/10 px-6 py-3 h-16">
          <div className="flex items-center justify-between h-10">
            <div className="flex items-center gap-3">
              <button className="h-10 w-10 rounded-md hover:bg-gray-100 dark:hover:bg-white/10 flex items-center justify-center">
                <span className="text-xl">✕</span>
              </button>
              <div>
                <h2 className="text-gray-900 dark:text-white">제조 데이터 분석</h2>
                <p className="text-xs text-gray-500 dark:text-[#98989d]">
                  Manufacturing AI Assistant
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* 모델 선택기 */}
              <div className="px-3 py-1.5 rounded-md border border-gray-200 dark:border-white/20 bg-white dark:bg-[#2c2c2e]">
                <span className="text-xs text-gray-900 dark:text-white">GPT-4 Turbo</span>
              </div>

              {/* 시계 */}
              <div className="hidden lg:flex items-center gap-2 px-3 rounded-md bg-gray-50 dark:bg-white/5 h-10">
                <span className="text-lg">🕐</span>
                <div>
                  <p className="text-sm text-gray-900 dark:text-white leading-tight">14:32:15</p>
                  <p className="text-xs text-gray-500 dark:text-[#98989d] leading-tight">2024.11.10</p>
                </div>
              </div>

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

        {/* Messages */}
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* User Message */}
            <div className="flex justify-end">
              <div className="max-w-[70%]">
                <div className="bg-blue-500 dark:bg-[#0a84ff] text-white rounded-2xl px-4 py-3">
                  <p className="text-sm">안녕하세요! 제조 데이터를 분석하고 싶습니다.</p>
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
                      <p className="text-sm text-gray-900 dark:text-white">
                        안녕하세요! 제조 데이터 분석을 도와드리겠습니다. 
                        어떤 데이터를 분석하고 싶으신가요? 
                        파일을 업로드하거나 분석 방법을 알려주세요.
                      </p>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">14:30</p>
                  </div>
                </div>
              </div>
            </div>

            {/* User Message */}
            <div className="flex justify-end">
              <div className="max-w-[70%]">
                <div className="bg-blue-500 dark:bg-[#0a84ff] text-white rounded-2xl px-4 py-3">
                  <p className="text-sm">생산 라인의 불량률 데이터가 있습니다. 패턴을 찾아주세요.</p>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right">14:31</p>
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
                      <p className="text-sm text-gray-900 dark:text-white">
                        네, 불량률 데이터 분석을 시작하겠습니다.
                      </p>
                      <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                        <p className="text-xs text-gray-700 dark:text-gray-300">
                          📊 데이터 분석 중...
                        </p>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                          • 데이터 로드 완료<br/>
                          • 이상 패턴 탐지 중<br/>
                          • 통계 분석 진행
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <p className="text-xs text-gray-500 dark:text-gray-400">14:32</p>
                      <button className="text-xs text-blue-600 dark:text-[#0a84ff] hover:underline">
                        재생성
                      </button>
                    </div>
                  </div>
                </div>
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
                  placeholder="메시지를 입력하세요..."
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
