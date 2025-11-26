import { ChatMessage } from '../../types/chat';
import { MarkdownRenderer } from './MarkdownRenderer';
import { TypingDots } from './TypingDots';
import { Button } from '../ui/button';
import { Copy, RotateCcw, User, Bot } from 'lucide-react';
import { toast } from 'sonner@2.0.3';
import { Avatar, AvatarFallback } from '../ui/avatar';

interface MessageItemProps {
  message: ChatMessage;
  onRegenerate?: () => void;
  isLastAssistant?: boolean;
  isFirstInGroup?: boolean;
  isLastInGroup?: boolean;
}

export function MessageItem({ 
  message, 
  onRegenerate, 
  isLastAssistant,
  isFirstInGroup = true,
  isLastInGroup = true,
}: MessageItemProps) {
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      toast.success('메시지가 복사되었습니다');
    } catch (err) {
      toast.error('복사에 실패했습니다');
    }
  };

  const timeString = new Date(message.createdAt).toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
  });

  if (isUser) {
    // User message - Right aligned (카카오톡 스타일)
    return (
      <div className={`flex justify-end items-end gap-2 px-6 group ${isFirstInGroup ? 'mt-4' : 'mt-0.5'}`}>
        {isLastInGroup && (
          <span className="text-[11px] text-gray-400 dark:text-gray-500 mb-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {timeString}
          </span>
        )}
        <div className="flex flex-col items-end max-w-[70%]">
          <div className={`bg-blue-600 dark:bg-[#0a84ff] text-white px-4 py-2.5 shadow-sm ${
            isFirstInGroup && isLastInGroup 
              ? 'rounded-2xl rounded-tr-sm' 
              : isFirstInGroup 
              ? 'rounded-t-2xl rounded-tr-sm rounded-b-2xl' 
              : isLastInGroup
              ? 'rounded-2xl rounded-tr-sm'
              : 'rounded-2xl'
          }`}>
            <div className="prose prose-sm prose-invert max-w-none [&>p]:leading-relaxed [&>p]:my-0">
              {message.content}
            </div>
          </div>
        </div>
        {isLastInGroup ? (
          <Avatar className="w-7 h-7 flex-shrink-0">
            <AvatarFallback className="bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
              <User className="w-3.5 h-3.5" />
            </AvatarFallback>
          </Avatar>
        ) : (
          <div className="w-7 h-7 flex-shrink-0" />
        )}
      </div>
    );
  }

  // AI message - Left aligned (인스타그램 DM 스타일)
  return (
    <div className={`flex justify-start items-start gap-2 px-6 group ${isFirstInGroup ? 'mt-4' : 'mt-0.5'}`}>
      {isLastInGroup ? (
        <Avatar className="w-7 h-7 flex-shrink-0 mt-1">
          <AvatarFallback className="bg-purple-100 dark:bg-purple-950 text-purple-600 dark:text-purple-400">
            <Bot className="w-3.5 h-3.5" />
          </AvatarFallback>
        </Avatar>
      ) : (
        <div className="w-7 h-7 flex-shrink-0" />
      )}
      <div className="flex flex-col items-start max-w-[70%]">
        {isFirstInGroup && (
          <span className="text-[11px] text-gray-500 dark:text-gray-400 mb-1 ml-1">
            AI 어시스턴트
          </span>
        )}
        <div className={`bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-4 py-2.5 shadow-sm ${
          isFirstInGroup && isLastInGroup 
            ? 'rounded-2xl rounded-tl-sm' 
            : isFirstInGroup 
            ? 'rounded-t-2xl rounded-tl-sm rounded-b-2xl' 
            : isLastInGroup
            ? 'rounded-2xl rounded-tl-sm'
            : 'rounded-2xl'
        }`}>
          {message.isStreaming && !message.content ? (
            <TypingDots />
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none [&>p]:leading-relaxed [&>p]:my-1 [&>pre]:my-2 [&>ul]:my-1 [&>ol]:my-1">
              <MarkdownRenderer content={message.content} />
            </div>
          )}
        </div>
        {!message.isStreaming && isLastInGroup && (
          <div className="flex items-center gap-1 mt-1.5 ml-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-[11px] text-gray-400 dark:text-gray-500">
              {timeString}
            </span>
            <span className="text-gray-300 dark:text-gray-600 mx-1">·</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-6 px-2 text-[11px] text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            >
              <Copy className="w-3 h-3 mr-1" />
              복사
            </Button>
            {isLastAssistant && onRegenerate && (
              <>
                <span className="text-gray-300 dark:text-gray-600">·</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onRegenerate}
                  className="h-6 px-2 text-[11px] text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                >
                  <RotateCcw className="w-3 h-3 mr-1" />
                  재생성
                </Button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
