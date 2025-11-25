import { FeatureNav } from '../layout/FeatureNav';
import { MessageSquare, Bot } from 'lucide-react';
import { Button } from '../ui/button';

/**
 * AI 챗봇 - 스트리밍 중
 * 피그마 디자인 참고용
 */
export function ChatStreaming() {
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
          <div className="group relative flex items-center gap-2 px-3 py-2.5 rounded-lg bg-gray-100 dark:bg-white/5">
            <MessageSquare className="w-4 h-4 text-gray-900 dark:text-white" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-900 dark:text-white truncate">
                데이터 분석 요청
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-white/5">
            <MessageSquare className="w-4 h-4 text-gray-500 dark:text-gray-400" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700 dark:text-gray-300 truncate">
                이전 대화
              </p>
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-gray-200 dark:border-white/10">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            <p>총 2개의 대화</p>
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
                <h2 className="text-gray-900 dark:text-white">데이터 분석 요청</h2>
                <p className="text-xs text-gray-500 dark:text-[#98989d]">
                  Manufacturing AI Assistant
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="px-3 py-1.5 rounded-md border border-gray-200 dark:border-white/20">
                <span className="text-xs text-gray-900 dark:text-white">GPT-4 Turbo</span>
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

        {/* Messages with Streaming */}
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* User Message */}
            <div className="flex justify-end">
              <div className="max-w-[70%]">
                <div className="bg-blue-500 dark:bg-[#0a84ff] text-white rounded-2xl px-4 py-3">
                  <p className="text-sm">
                    지난 6개월간의 생산 라인 데이터를 분석하여 불량률이 높은 시간대와 원인을 찾아주세요.
                  </p>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right">14:35</p>
              </div>
            </div>

            {/* Assistant Message - Streaming */}
            <div className="flex justify-start">
              <div className="max-w-[70%]">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white flex-shrink-0 animate-pulse">
                    🤖
                  </div>
                  <div className="flex-1">
                    <div className="bg-gray-100 dark:bg-[#2c2c2e] rounded-2xl px-4 py-3">
                      <p className="text-sm text-gray-900 dark:text-white">
                        네, 지난 6개월간의 생산 라인 데이터를 분석하겠습니다.
                        <br/><br/>
                        <strong>📊 분석 결과:</strong>
                        <br/><br/>
                        1. <strong>불량률이 높은 시간대</strong>
                        <br/>
                        - 오전 6시~8시: 평균 불량률 4.2%
                        <br/>
                        - 오후 2시~4시: 평균 불량률 3.8%
                        <br/>
                        - 야간 10시~12시: 평균 불량률 5.1%
                        <br/><br/>
                        2. <strong>주요 원인 분석</strong>
                        <br/>
                        - 교대 시간 전후 집중도 저하
                        <br/>
                        - 점심시간 이후 피로도 증가
                        <br/>
                        - 야간 근무 시 조명 및 환경 요인
                        <br/><br/>
                        3. <strong>개선 제안</strong>
                        <br/>
                        - 교대 시간 30분 전 품질 체크 강화
                        <br/>
                        - 오후 시간대 추가 휴식 시간 배정
                        <br/>
                        - 야간 작<span className="animate-pulse">▋</span>
                      </p>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-blue-600 dark:bg-[#0a84ff] animate-pulse"></div>
                        <p className="text-xs text-blue-600 dark:text-[#0a84ff]">응답 생성 중...</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Chat Input - With Stop Button */}
        <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-6 py-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-end gap-3">
              <button className="flex items-center justify-center h-10 w-10 rounded-md border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 opacity-50 cursor-not-allowed">
                <span className="text-lg">📎</span>
              </button>
              
              <div className="flex-1 relative">
                <textarea
                  placeholder="메시지를 입력하세요..."
                  className="w-full min-h-[44px] px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 resize-none opacity-50 cursor-not-allowed"
                  rows={1}
                  disabled
                />
              </div>

              {/* Stop Button */}
              <button className="h-10 w-10 rounded-md bg-red-600 hover:bg-red-700 flex items-center justify-center text-white">
                <span className="text-lg">⬛</span>
              </button>
            </div>
            
            <div className="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-600 dark:bg-[#0a84ff] animate-pulse"></div>
                AI가 응답을 생성하고 있습니다...
              </span>
              <span>0 / 4000</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
