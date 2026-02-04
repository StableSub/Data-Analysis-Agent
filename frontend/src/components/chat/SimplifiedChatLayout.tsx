import { useState } from 'react';
import { Bot, Moon, Sun, Upload, Paperclip, Send, X } from 'lucide-react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { FeatureType } from '../layout/SimplifiedNav';

interface SimplifiedChatLayoutProps {
  feature: FeatureType;
}

const featureTitles = {
  chat: 'AI 챗봇',
  visualization: '데이터 시각화',
  edit: '데이터 편집',
  simulation: '시뮬레이션',
  audit: '감사 로그',
};

const featureDescriptions = {
  chat: '제조 데이터 분석 AI 어시스턴트',
  visualization: '데이터를 차트와 그래프로 시각화',
  edit: 'AI 기반 데이터 수정 및 보정',
  simulation: '제조 공정 시뮬레이션 및 예측',
  audit: '사용자 활동 추적 및 보안 모니터링',
};

export function SimplifiedChatLayout({ feature }: SimplifiedChatLayoutProps) {
  const [isDark, setIsDark] = useState(false);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; size: number }>>([]);
  const [showUpload, setShowUpload] = useState(false);

  const handleSend = () => {
    if (!message.trim()) return;

    setMessages([...messages, { role: 'user', content: message }]);
    setMessage('');

    // Generate AI response simulation
    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `${featureTitles[feature]} 기능으로 "${message}" 요청을 처리하고 있습니다.`
      }]);
    }, 1000);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      const newFiles = Array.from(files).map(f => ({
        name: f.name,
        size: f.size,
      }));
      setUploadedFiles([...uploadedFiles, ...newFiles]);
      setShowUpload(false);
    }
  };

  return (
    <div className={isDark ? 'dark' : ''}>
      <div className="flex flex-col h-screen bg-white dark:bg-[#1c1c1e]">
        {/* Header */}
        <div className="bg-white dark:bg-[#2c2c2e] border-b border-gray-200 dark:border-white/10 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl text-gray-900 dark:text-white">{featureTitles[feature]}</h1>
              <p className="text-sm text-gray-500 dark:text-[#98989d]">
                {featureDescriptions[feature]}
              </p>
            </div>

            <div className="flex items-center gap-3">
              {/* Model Selector */}
              <div className="px-4 py-2 rounded-lg border border-gray-200 dark:border-white/20 bg-white dark:bg-[#2c2c2e]">
                <span className="text-sm text-gray-900 dark:text-white">GPT-4 Turbo</span>
              </div>

              {/* Theme Toggle */}
              <Button
                size="icon"
                variant="ghost"
                onClick={() => setIsDark(!isDark)}
                className="h-10 w-10"
              >
                {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </Button>

              {/* Avatar */}
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm">
                U
              </div>
            </div>
          </div>
        </div>

        {/* Uploaded Files Bar */}
        {uploadedFiles.length > 0 && (
          <div className="bg-blue-50 dark:bg-blue-900/10 border-b border-blue-200 dark:border-blue-900/30 px-6 py-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm text-blue-700 dark:text-blue-300">업로드된 파일:</span>
              {uploadedFiles.map((file, idx) => (
                <Badge key={idx} variant="secondary" className="gap-2">
                  {file.name}
                  <button
                    onClick={() => setUploadedFiles(uploadedFiles.filter((_, i) => i !== idx))}
                    className="hover:text-red-600"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Messages Area */}
        <div className="flex-1 overflow-auto p-6">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="max-w-2xl mx-auto text-center space-y-8">
                <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500 to-purple-600 text-white text-4xl">
                  🤖
                </div>
                <div>
                  <h2 className="text-3xl text-gray-900 dark:text-white mb-2">
                    {featureTitles[feature]}
                  </h2>
                  <p className="text-gray-600 dark:text-gray-400">
                    {featureDescriptions[feature]}
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
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[70%] ${msg.role === 'user' ? '' : 'flex items-start gap-3'}`}>
                    {msg.role === 'assistant' && (
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white flex-shrink-0">
                        🤖
                      </div>
                    )}
                    <div>
                      <div className={`px-4 py-3 rounded-2xl ${msg.role === 'user'
                          ? 'bg-blue-500 dark:bg-[#0a84ff] text-white'
                          : 'bg-gray-100 dark:bg-[#2c2c2e] text-gray-900 dark:text-white'
                        }`}>
                        <p className="text-sm">{msg.content}</p>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 px-2">
                        {new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* File Upload Modal */}
        {showUpload && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-50">
            <Card className="w-full max-w-md mx-4 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">파일 업로드</h3>
                <Button size="icon" variant="ghost" onClick={() => setShowUpload(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </div>

              <div className="border-2 border-dashed border-gray-300 dark:border-white/20 rounded-xl p-8 text-center">
                <Upload className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-4" />
                <p className="text-gray-700 dark:text-white mb-2">
                  파일을 드래그하여 업로드하거나
                </p>
                <label className="text-blue-600 dark:text-[#0a84ff] cursor-pointer hover:underline">
                  파일 선택
                  <input
                    type="file"
                    multiple
                    className="hidden"
                    onChange={handleFileUpload}
                    accept=".csv,.xlsx,.xls"
                  />
                </label>
                <p className="text-sm text-gray-500 dark:text-[#98989d] mt-2">
                  CSV, XLSX, XLS (최대 100MB)
                </p>
              </div>
            </Card>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-6 py-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-end gap-3">
              {/* File Upload Button */}
              <Button
                size="icon"
                variant="outline"
                onClick={() => setShowUpload(true)}
                className="h-11 w-11 flex-shrink-0"
              >
                <Paperclip className="w-5 h-5" />
              </Button>

              {/* Input */}
              <div className="flex-1">
                <Textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="메시지를 입력하세요... (Enter: 전송, Shift+Enter: 줄바꿈)"
                  className="min-h-[44px] max-h-32 resize-none"
                  rows={1}
                />
              </div>

              {/* Send Button */}
              <Button
                size="icon"
                onClick={handleSend}
                disabled={!message.trim()}
                className="h-11 w-11 flex-shrink-0 bg-blue-500 hover:bg-blue-600"
              >
                <Send className="w-5 h-5" />
              </Button>
            </div>

            <div className="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>AI 생성 콘텐츠는 부정확할 수 있습니다</span>
              <span>{message.length} / 4000</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
