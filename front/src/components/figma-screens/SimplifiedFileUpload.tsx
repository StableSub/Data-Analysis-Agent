import { SimplifiedNav } from '../layout/SimplifiedNav';
import { Moon, Paperclip, Send, Upload, X } from 'lucide-react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Card } from '../ui/card';

/**
 * 단순화된 레이아웃 - 파일 업로드 모달
 * 피그마 디자인 참고용
 */
export function SimplifiedFileUpload() {
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-[#1c1c1e]">
      {/* 좌측 네비게이션 */}
      <SimplifiedNav 
        activeFeature="chat"
        onFeatureChange={() => {}}
        onNewChat={() => {}}
      />

      {/* 우측 대화 영역 */}
      <div className="flex-1 flex flex-col bg-white dark:bg-[#1c1c1e] relative">
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

        {/* Empty State Content (Dimmed) */}
        <div className="flex-1 overflow-auto p-6 opacity-50">
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
            </div>
          </div>
        </div>

        {/* File Upload Modal */}
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md mx-4 p-6 dark:bg-[#2c2c2e] dark:border-white/10">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">파일 업로드</h3>
              <Button size="icon" variant="ghost">
                <X className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="border-2 border-dashed border-gray-300 dark:border-white/20 rounded-xl p-8 text-center hover:border-blue-400 dark:hover:border-[#0a84ff] transition-all">
              <Upload className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-4" />
              <p className="text-gray-700 dark:text-white mb-2">
                파일을 드래그하여 업로드하거나
              </p>
              <label className="text-blue-600 dark:text-[#0a84ff] cursor-pointer hover:underline">
                파일 선택
              </label>
              <p className="text-sm text-gray-500 dark:text-[#98989d] mt-2">
                CSV, XLSX, XLS (최대 100MB)
              </p>
            </div>

            {/* Recent Files */}
            <div className="mt-6 space-y-2">
              <p className="text-sm font-medium text-gray-900 dark:text-white">최근 업로드</p>
              <div className="space-y-2">
                <button className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-white/5 transition-colors text-left">
                  <span className="text-sm text-gray-700 dark:text-white truncate">manufacturing_data_2024.csv</span>
                  <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">15,234 rows</span>
                </button>
                <button className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-white/5 transition-colors text-left">
                  <span className="text-sm text-gray-700 dark:text-white truncate">production_log.xlsx</span>
                  <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">8,912 rows</span>
                </button>
                <button className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-white/5 transition-colors text-left">
                  <span className="text-sm text-gray-700 dark:text-white truncate">quality_metrics.csv</span>
                  <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">12,456 rows</span>
                </button>
              </div>
            </div>
          </Card>
        </div>

        {/* Input Area (Dimmed) */}
        <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-6 py-4 opacity-50">
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
                  disabled
                />
              </div>

              {/* Send Button */}
              <Button size="icon" className="h-11 w-11 flex-shrink-0 bg-blue-500" disabled>
                <Send className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
