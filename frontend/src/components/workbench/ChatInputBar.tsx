import { RefObject } from 'react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Paperclip, Send, ChevronDown, Square } from 'lucide-react';
import { AI_MODELS, getModelById } from '../../lib/models';

interface ChatInputBarProps {
  message: string;
  setMessage: (v: string) => void;
  isGenerating: boolean;
  onSend: () => void;
  onStop: () => void;
  onOpenUpload: () => void;
  selectedModelId: string;
  setSelectedModelId: (id: string) => void;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
}

export function ChatInputBar({
  message,
  setMessage,
  isGenerating,
  onSend,
  onStop,
  onOpenUpload,
  selectedModelId,
  setSelectedModelId,
  textareaRef,
}: ChatInputBarProps) {
  return (
    <div className="border-t border-gray-200 dark:border-white/10 bg-white dark:bg-[#212121] px-6 py-4">
      <div className="max-w-4xl mx-auto">
        {/* Model selector */}
        <div className="mb-2 flex items-center gap-2">
          <Popover>
            <PopoverTrigger asChild>
              <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-gray-100 dark:bg-white/5 hover:bg-gray-200 dark:hover:bg-white/10 text-gray-700 dark:text-gray-300 transition-colors border border-gray-200 dark:border-white/10">
                <span className="text-base">{getModelById(selectedModelId)?.icon}</span>
                <span>{getModelById(selectedModelId)?.name}</span>
                <ChevronDown className="w-4 h-4" />
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-80 p-2 bg-white dark:bg-[#2f2f2f] border border-gray-200 dark:border-white/10" align="start">
              <div className="space-y-1">
                {AI_MODELS.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => setSelectedModelId(model.id)}
                    className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                      selectedModelId === model.id
                        ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700/50'
                        : 'hover:bg-gray-100 dark:hover:bg-white/5'
                    }`}
                  >
                    <span className="text-xl flex-shrink-0">{model.icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className={`text-sm ${selectedModelId === model.id ? 'text-blue-700 dark:text-blue-300' : 'text-gray-900 dark:text-white'}`}>{model.name}</span>
                        {selectedModelId === model.id && (
                          <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{model.provider}</p>
                      <p className="text-xs text-gray-600 dark:text-gray-300">{model.description}</p>
                    </div>
                  </button>
                ))}
              </div>
            </PopoverContent>
          </Popover>
        </div>

        <div className="flex items-end gap-2">
          <Button size="icon" variant="outline" onClick={onOpenUpload} disabled={isGenerating} className="h-11 w-11 flex-shrink-0">
            <Paperclip className="w-5 h-5" />
          </Button>

          <div className="flex-1">
            <Textarea
              ref={textareaRef}
              value={message}
              disabled={isGenerating}
              onChange={(e) => {
                const newValue = e.target.value;
                if (newValue.length <= 4000) {
                  setMessage(newValue);
                  e.target.style.height = 'auto';
                  e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px';
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !isGenerating) {
                  e.preventDefault();
                  onSend();
                }
              }}
              placeholder={isGenerating ? 'AI가 답변 중입니다...' : '메시지를 입력하세요... (Enter: 전송, Shift+Enter: 줄바꿈)'}
              className="min-h-[44px] max-h-32 resize-none dark:bg-[#2f2f2f] dark:border-white/10 overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed"
              rows={1}
            />
          </div>

          {isGenerating ? (
            <Button size="icon" onClick={onStop} className="h-11 w-11 flex-shrink-0 bg-gray-200 hover:bg-gray-300 dark:bg-[#3a3a3a] dark:hover:bg-[#4a4a4a] text-gray-900 dark:text-white">
              <Square className="w-4 h-4 fill-current" />
            </Button>
          ) : (
            <Button size="icon" onClick={onSend} disabled={!message.trim()} className="h-11 w-11 flex-shrink-0 bg-blue-500 hover:bg-blue-600 dark:bg-[#0084ff] dark:hover:bg-[#0077ed] disabled:opacity-50 disabled:cursor-not-allowed">
              <Send className="w-5 h-5" />
            </Button>
          )}
        </div>

        <div className="mt-1.5 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 px-1">
          <span>AI 생성 콘텐츠는 부정확할 수 있습니다</span>
          <span>{message.length} / 4000</span>
        </div>
      </div>
    </div>
  );
}
