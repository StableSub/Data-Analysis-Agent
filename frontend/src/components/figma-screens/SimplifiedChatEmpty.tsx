import { SimplifiedNav } from '../layout/SimplifiedNav';
import { Moon, Paperclip, Send, Sun } from 'lucide-react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';

/**
 * 단순화된 레이아웃 - AI 챗봇 빈 상태
 * 피그마 디자인 참고용
 */
export function SimplifiedChatEmpty() {
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-[#1c1c1e]">
      {/* 좌측 네비게이션 */}
      <SimplifiedNav 
        activeFeature="chat"
        onFeatureChange={() => {}}
        onNewChat={() => {}}
      />

      {/* 우측 대화 영역 */}
      <div className="flex-1 flex flex-col bg-white dark:bg-[#1c1c1e]">
        {/* Header */}
        <div className="bg-white dark:bg-[#2c2c2e] border-b border-gray-200 dark:border-white/10 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl text-gray-900 dark:text-white">AI 챗봇</h1>
              <p className="text-sm text-gray-500 dark:text-[#98989d]">
                제조 데이터 분석 AI 어시스턴트
              </p>
            </div>

            <div className="flex items-center gap-3">
              {/* Model Selector */}
              <div className="px-4 py-2 rounded-lg border border-gray-200 dark:border-white/20 bg-white dark:bg-[#2c2c2e]">
                <span className="text-sm text-gray-900 dark:text-white">GPT-4 Turbo</span>
              </div>

              {/* Theme Toggle */}
              <Button size="icon" variant="ghost" className="h-10 w-10">
                <Moon className="w-5 h-5" />
              </Button>

              {/* Avatar */}
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm">
                U
              </div>
            </div>
          </div>
        </div>

        {/* Empty State Content */}
        <div className="flex-1 overflow-auto p-6">
          <div className="h-full flex items-center justify-center">
            <div className="max-w-2xl mx-auto text-center space-y-8">
              {/* Icon */}
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500 to-purple-600 text-white text-4xl shadow-lg">
                🤖
              </div>

              {/* Title */}
              <div>
                <h2 className="text-3xl text-gray-900 dark:text-white mb-2">
                  AI 챗봇
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                  제조 데이터 분석 AI 어시스턴트
                </p>
              </div>

              {/* Example Prompts */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button className="group p-5 rounded-2xl border-2 border-gray-200 dark:border-white/20 hover:border-blue-500 dark:hover:border-[#0a84ff] hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-all text-left">
                  <div className="text-3xl mb-3">📊</div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-[#0a84ff]">
                    "데이터 분석 시작"
                  </p>
                </button>
                <button className="group p-5 rounded-2xl border-2 border-gray-200 dark:border-white/20 hover:border-blue-500 dark:hover:border-[#0a84ff] hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-all text-left">
                  <div className="text-3xl mb-3">📁</div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-[#0a84ff]">
                    "파일 업로드"
                  </p>
                </button>
                <button className="group p-5 rounded-2xl border-2 border-gray-200 dark:border-white/20 hover:border-blue-500 dark:hover:border-[#0a84ff] hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-all text-left">
                  <div className="text-3xl mb-3">💡</div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-[#0a84ff]">
                    "도움말 보기"
                  </p>
                </button>
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
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-6 py-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-end gap-3">
              {/* File Upload Button */}
              <Button size="icon" variant="outline" className="h-11 w-11 flex-shrink-0">
                <Paperclip className="w-5 h-5" />
              </Button>

              {/* Input */}
              <div className="flex-1">
                <Textarea
                  placeholder="메시지를 입력하세요... (Enter: 전송, Shift+Enter: 줄바꿈)"
                  className="min-h-[44px] resize-none"
                  rows={1}
                />
              </div>

              {/* Send Button */}
              <Button size="icon" className="h-11 w-11 flex-shrink-0 bg-blue-500 hover:bg-blue-600">
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
