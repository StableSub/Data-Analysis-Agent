import { FeatureNav } from '../layout/FeatureNav';
import { MessageSquare, Bot, X, CheckCircle2, BarChart, FileSearch, Brain } from 'lucide-react';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';

/**
 * AI 챗봇 - Agent 위젯 열림
 * 피그마 디자인 참고용
 */
export function ChatWithAgent() {
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
        
        <div className="flex-1 p-2 space-y-1">
          <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-gray-100 dark:bg-white/5">
            <MessageSquare className="w-4 h-4 text-gray-900 dark:text-white" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-900 dark:text-white truncate">
                현재 분석 중
              </p>
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-gray-200 dark:border-white/10">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            <p>총 1개의 대화</p>
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
                <h2 className="text-gray-900 dark:text-white">현재 분석 중</h2>
                <p className="text-xs text-gray-500 dark:text-[#98989d]">
                  Manufacturing AI Assistant
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button className="h-10 w-10 rounded-md hover:bg-gray-100 dark:hover:bg-white/10 flex items-center justify-center">
                <span className="text-xl">🌙</span>
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
            <div className="flex justify-end">
              <div className="max-w-[70%]">
                <div className="bg-blue-500 dark:bg-[#0a84ff] text-white rounded-2xl px-4 py-3">
                  <p className="text-sm">데이터 분석을 시작해주세요</p>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right">14:40</p>
              </div>
            </div>

            <div className="flex justify-start">
              <div className="max-w-[70%]">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white flex-shrink-0">
                    🤖
                  </div>
                  <div className="flex-1">
                    <div className="bg-gray-100 dark:bg-[#2c2c2e] rounded-2xl px-4 py-3">
                      <p className="text-sm text-gray-900 dark:text-white">
                        네, 데이터 분석을 시작합니다. Agent가 작업을 처리하고 있습니다.
                        우측 Agent 패널에서 실시간 진행 상황을 확인하실 수 있습니다.
                      </p>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">14:40</p>
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

      {/* Agent Widget - 우측 */}
      <div className="w-80 h-screen bg-white dark:bg-[#2c2c2e] border-l border-gray-200 dark:border-white/10 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-white/10">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4 text-blue-600 dark:text-[#0a84ff]" />
              <h3 className="text-gray-900 dark:text-white">AI Agent</h3>
            </div>
            <button className="h-7 w-7 rounded-md hover:bg-gray-100 dark:hover:bg-white/10 flex items-center justify-center">
              <X className="w-4 h-4 text-gray-500 dark:text-[#98989d]" />
            </button>
          </div>
          <p className="text-xs text-gray-500 dark:text-[#98989d]">실시간 처리 상태</p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {/* Status Summary */}
          <Card className="p-4 dark:bg-[#3a3a3c] dark:border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600 dark:text-white">처리된 작업</span>
              <Badge variant="secondary">42</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-white">진행 중</span>
              <Badge variant="default">2</Badge>
            </div>
          </Card>

          {/* Agent Capabilities */}
          <Card className="p-4 dark:bg-[#3a3a3c] dark:border-white/10">
            <h4 className="text-sm text-gray-900 dark:text-white mb-3">활성 기능</h4>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-600 dark:bg-[#0a84ff] animate-pulse"></div>
                  <span className="text-gray-700 dark:text-white">데이터 분석</span>
                </div>
                <span className="text-xs text-blue-600 dark:text-[#0a84ff]">active</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-600"></div>
                  <span className="text-gray-700 dark:text-white">이상 탐지</span>
                </div>
                <span className="text-xs text-gray-500 dark:text-[#98989d]">inactive</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-600 dark:bg-[#0a84ff] animate-pulse"></div>
                  <span className="text-gray-700 dark:text-white">리포트 생성</span>
                </div>
                <span className="text-xs text-blue-600 dark:text-[#0a84ff]">active</span>
              </div>
            </div>
          </Card>

          {/* Recent Activities */}
          <Card className="p-4 dark:bg-[#3a3a3c] dark:border-white/10">
            <h4 className="text-sm text-gray-900 dark:text-white mb-3">최근 활동</h4>
            <div className="space-y-2.5">
              {/* Active Activity */}
              <div className="p-3 rounded-lg bg-blue-50 dark:bg-[#0a84ff]/10 border border-blue-200 dark:border-[#0a84ff]/30">
                <div className="flex items-start gap-2.5">
                  <div className="flex items-center justify-center w-6 h-6 rounded-md bg-blue-100 dark:bg-[#0a84ff]/20 flex-shrink-0">
                    <BarChart className="w-3.5 h-3.5 text-blue-600 dark:text-[#0a84ff]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-blue-700 dark:text-[#0a84ff]">
                        분석
                      </span>
                      <div className="flex items-center gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-blue-600 dark:bg-[#0a84ff] animate-pulse"></div>
                        <span className="text-xs text-blue-600 dark:text-[#0a84ff]">진행중</span>
                      </div>
                    </div>
                    <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                      제조 데이터 이상 패턴 분석 중입니다...
                    </p>
                    <p className="text-xs text-gray-400 dark:text-[#98989d] mt-1.5">
                      14:40
                    </p>
                  </div>
                </div>
              </div>

              {/* Completed Activity */}
              <div className="p-3 rounded-lg bg-gray-50 dark:bg-[#1c1c1e]">
                <div className="flex items-start gap-2.5">
                  <div className="flex items-center justify-center w-6 h-6 rounded-md bg-gray-200 dark:bg-[#2c2c2e] flex-shrink-0">
                    <FileSearch className="w-3.5 h-3.5 text-gray-500 dark:text-[#98989d]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-gray-600 dark:text-white">
                        검색
                      </span>
                      <CheckCircle2 className="w-3 h-3 text-green-600 dark:text-green-400" />
                    </div>
                    <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                      데이터베이스 쿼리 완료
                    </p>
                    <p className="text-xs text-gray-400 dark:text-[#98989d] mt-1.5">
                      14:39
                    </p>
                  </div>
                </div>
              </div>

              {/* Another Activity */}
              <div className="p-3 rounded-lg bg-gray-50 dark:bg-[#1c1c1e]">
                <div className="flex items-start gap-2.5">
                  <div className="flex items-center justify-center w-6 h-6 rounded-md bg-gray-200 dark:bg-[#2c2c2e] flex-shrink-0">
                    <Brain className="w-3.5 h-3.5 text-gray-500 dark:text-[#98989d]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-gray-600 dark:text-white">
                        사고
                      </span>
                      <CheckCircle2 className="w-3 h-3 text-green-600 dark:text-green-400" />
                    </div>
                    <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                      분석 전략 수립 완료
                    </p>
                    <p className="text-xs text-gray-400 dark:text-[#98989d] mt-1.5">
                      14:38
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
