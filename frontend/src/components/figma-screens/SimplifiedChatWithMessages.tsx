import { SimplifiedNav } from '../layout/SimplifiedNav';
import { Moon, Paperclip, Send, X } from 'lucide-react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';

/**
 * 단순화된 레이아웃 - AI 챗봇 대화 중
 * 피그마 디자인 참고용
 */
export function SimplifiedChatWithMessages() {
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

        {/* Uploaded Files Bar */}
        <div className="bg-blue-50 dark:bg-blue-900/10 border-b border-blue-200 dark:border-blue-900/30 px-6 py-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-blue-700 dark:text-blue-300">업로드된 파일:</span>
            <Badge variant="secondary" className="gap-2">
              manufacturing_data_2024.csv
              <button className="hover:text-red-600">
                <X className="w-3 h-3" />
              </button>
            </Badge>
            <Badge variant="secondary" className="gap-2">
              quality_metrics.xlsx
              <button className="hover:text-red-600">
                <X className="w-3 h-3" />
              </button>
            </Badge>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* User Message */}
            <div className="flex justify-end">
              <div className="max-w-[70%]">
                <div className="bg-blue-500 dark:bg-[#0a84ff] text-white rounded-2xl px-4 py-3">
                  <p className="text-sm">업로드한 데이터를 분석해주세요</p>
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
                        네, 업로드하신 manufacturing_data_2024.csv 파일을 분석하겠습니다.
                      </p>
                      <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                        <p className="text-xs text-gray-700 dark:text-gray-300 font-medium mb-2">
                          📊 데이터 요약
                        </p>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          • 총 15,234개 행<br/>
                          • 12개 컬럼<br/>
                          • 기간: 2024.01.01 ~ 2024.10.31<br/>
                          • 결측치: 0.3%
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <p className="text-xs text-gray-500 dark:text-gray-400">14:30</p>
                      <button className="text-xs text-blue-600 dark:text-[#0a84ff] hover:underline">
                        재생성
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* User Message */}
            <div className="flex justify-end">
              <div className="max-w-[70%]">
                <div className="bg-blue-500 dark:bg-[#0a84ff] text-white rounded-2xl px-4 py-3">
                  <p className="text-sm">불량률이 높은 시간대를 찾아주세요</p>
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
                        불량률 분석 결과입니다:
                      </p>
                      <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                        <p className="text-xs text-gray-700 dark:text-gray-300 font-medium mb-2">
                          ⚠️ 불량률 높은 시간대
                        </p>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          1. 오전 6~8시: 4.2%<br/>
                          2. 오후 2~4시: 3.8%<br/>
                          3. 야간 10~12시: 5.1%
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
                  placeholder="메시지를 입력하세요..."
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
