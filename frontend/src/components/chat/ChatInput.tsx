import { useState, useRef, KeyboardEvent } from 'react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Card } from '../ui/card';
import { Send, Square, Paperclip, X, File } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../ui/dialog';
import { FileUpload } from './FileUpload';

interface ChatInputProps {
  onSend: (message: string, files?: File[]) => void;
  onStop?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  attachedFiles?: File[];
  onFilesChange?: (files: File[]) => void;
}

export function ChatInput({
  onSend,
  onStop,
  isStreaming,
  disabled,
  attachedFiles = [],
  onFilesChange,
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const [showFileDialog, setShowFileDialog] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!input.trim() || disabled) return;
    
    onSend(input.trim(), attachedFiles.length > 0 ? attachedFiles : undefined);
    setInput('');
    if (onFilesChange) onFilesChange([]);
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to send, Shift+Enter for newline
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    
    // 4000자 제한 - 초과 시 입력 차단
    if (value.length > 4000) {
      return;
    }
    
    setInput(value);
    
    // Auto-resize textarea
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
  };

  const removeFile = (index: number) => {
    if (onFilesChange) {
      onFilesChange(attachedFiles.filter((_, i) => i !== index));
    }
  };

  return (
    <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 sm:px-6 py-4 transition-colors">
      <div className="max-w-4xl mx-auto">
        {/* Attached Files Preview */}
        {attachedFiles.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {attachedFiles.map((file, index) => (
              <Card
                key={index}
                className="px-3 py-2 flex items-center gap-2 bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700"
              >
                <File className="w-3 h-3 text-gray-500" />
                <span className="text-xs text-gray-700 dark:text-gray-300">
                  {file.name}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5"
                  onClick={() => removeFile(index)}
                >
                  <X className="w-3 h-3" />
                </Button>
              </Card>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2 sm:gap-3">
          <Dialog open={showFileDialog} onOpenChange={setShowFileDialog}>
            <DialogTrigger asChild>
              <button
                className="flex items-center justify-center h-10 w-10 rounded-md border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={disabled}
              >
                <Paperclip className="w-4 h-4" />
              </button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]" aria-describedby="file-upload-description">
              <DialogHeader>
                <DialogTitle>파일 업로드</DialogTitle>
              </DialogHeader>
              <div id="file-upload-description" className="sr-only">
                분석할 파일을 선택하거나 드래그하여 업로드하세요
              </div>
              <FileUpload
                onFilesSelect={(files) => {
                  if (onFilesChange) {
                    onFilesChange([...attachedFiles, ...files]);
                  }
                  setShowFileDialog(false);
                }}
              />
            </DialogContent>
          </Dialog>

          <div className="flex-1 relative">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="메시지를 입력하세요... (Enter: 전송, Shift+Enter: 줄바꿈)"
              className="min-h-[44px] max-h-[200px] resize-none pr-12 dark:bg-gray-800 dark:border-gray-700"
              disabled={disabled}
              aria-label="메시지 입력"
              rows={1}
              maxLength={4000}
            />
          </div>

          {isStreaming ? (
            <Button
              onClick={onStop}
              variant="destructive"
              size="icon"
              className="flex-shrink-0"
            >
              <Square className="w-4 h-4" />
            </Button>
          ) : (
            <Button
              onClick={handleSend}
              disabled={!input.trim() || disabled}
              size="icon"
              className="flex-shrink-0"
            >
              <Send className="w-4 h-4" />
            </Button>
          )}
        </div>
        
        <div className="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>AI 생성 콘텐츠는 부정확할 수 있습니다</span>
          <div className="flex items-center gap-3">
            {attachedFiles.length > 0 && (
              <span>{attachedFiles.length}개 파일 첨부</span>
            )}
            <span className={input.length >= 4000 ? 'text-red-500 dark:text-red-400' : ''}>
              {input.length} / 4000
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}