import { KeyboardEvent, RefObject, useEffect } from 'react';
import { ArrowUp, Paperclip, Square } from 'lucide-react';
import { AVAILABLE_MODELS } from '../../lib/models';

interface ChatInputBarProps {
  message: string;
  setMessage: (value: string) => void;
  isGenerating: boolean;
  onSend: () => void;
  onStop: () => void;
  onOpenUpload: () => void;
  selectedModelId: string;
  setSelectedModelId: (id: string) => void;
  textareaRef: RefObject<HTMLTextAreaElement>;
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
  useEffect(() => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = 'auto';
    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
  }, [message, textareaRef]);

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter' || event.shiftKey) return;
    if (event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229) return;
    event.preventDefault();
    if (!isGenerating && message.trim()) {
      onSend();
    }
  };

  return (
    <div className="px-4 py-3 border-t border-gray-200 dark:border-white/10 bg-white dark:bg-[#212121]">
      <div className="flex items-end gap-2 p-2 rounded-2xl border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-[#2f2f2f]">
        <button
          type="button"
          onClick={onOpenUpload}
          className="w-9 h-9 rounded-xl inline-flex items-center justify-center text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-[#3a3a3a]"
          aria-label="파일 첨부"
        >
          <Paperclip className="w-4 h-4" />
        </button>

        <textarea
          ref={textareaRef}
          rows={1}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isGenerating ? '응답 생성 중...' : '메시지를 입력하세요'}
          className="flex-1 resize-none bg-transparent outline-none text-sm text-gray-900 dark:text-white placeholder:text-gray-500 dark:placeholder:text-gray-400 max-h-[200px]"
        />

        {isGenerating ? (
          <button
            type="button"
            onClick={onStop}
            className="w-9 h-9 rounded-xl inline-flex items-center justify-center bg-red-500 text-white"
            aria-label="중지"
          >
            <Square className="w-4 h-4" />
          </button>
        ) : (
          <button
            type="button"
            onClick={onSend}
            disabled={!message.trim()}
            className="w-9 h-9 rounded-xl inline-flex items-center justify-center bg-blue-500 text-white disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="전송"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="mt-2 flex justify-end">
        <label className="text-xs text-gray-500 dark:text-gray-400 inline-flex items-center gap-2">
          모델
          <select
            value={selectedModelId}
            onChange={(event) => setSelectedModelId(event.target.value)}
            className="h-7 px-2 rounded-md border border-gray-200 dark:border-white/10 bg-white dark:bg-[#2f2f2f] text-xs text-gray-800 dark:text-white"
          >
            {AVAILABLE_MODELS.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}
