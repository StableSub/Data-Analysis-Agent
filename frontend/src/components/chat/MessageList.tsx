import { useEffect, useRef } from 'react';
import { ChatMessage } from '../../types/chat';
import { MessageItem } from './MessageItem';
import { ModelSelector } from './ModelSelector';
import { ScrollArea } from '../ui/scroll-area';

interface MessageListProps {
  messages: ChatMessage[];
  onRegenerate?: () => void;
  selectedModelId?: string;
  onSelectModel?: (modelId: string) => void;
}

export function MessageList({
  messages,
  onRegenerate,
  selectedModelId,
  onSelectModel,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-6">
        <div className="w-full max-w-2xl mx-auto space-y-10">
          {/* Header */}
          <div className="text-center space-y-4">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500 to-purple-600 text-white text-4xl shadow-lg">
              🤖
            </div>
            <h1 className="text-4xl text-gray-900 dark:text-white">
              제조 데이터 분석 AI
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              데이터 분석, 이상 탐지, 리포트 생성 등 무엇이든 질문하세요
            </p>
          </div>

          {/* Model Selector */}
          <div className="space-y-4">
            <p className="text-sm text-center text-gray-600 dark:text-gray-400">
              사용할 AI 모델을 선택하세요
            </p>
            {onSelectModel && (
              <div className="flex justify-center">
                <ModelSelector
                  selectedModelId={selectedModelId}
                  onSelectModel={onSelectModel}
                  variant="default"
                />
              </div>
            )}
          </div>

          {/* Example Prompts */}
          <div className="space-y-4">
            <p className="text-sm text-center text-gray-600 dark:text-gray-400">
              예시 질문
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button className="group p-5 rounded-2xl border-2 border-gray-200 dark:border-white/20 hover:border-blue-500 dark:hover:border-[#0a84ff] hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-all text-left">
                <div className="text-3xl mb-3">📊</div>
                <p className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-[#0a84ff] transition-colors">
                  "업로드한 데이터를 분석해줘"
                </p>
              </button>
              <button className="group p-5 rounded-2xl border-2 border-gray-200 dark:border-white/20 hover:border-blue-500 dark:hover:border-[#0a84ff] hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-all text-left">
                <div className="text-3xl mb-3">⚠️</div>
                <p className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-[#0a84ff] transition-colors">
                  "이상 패턴을 찾아줘"
                </p>
              </button>
              <button className="group p-5 rounded-2xl border-2 border-gray-200 dark:border-white/20 hover:border-blue-500 dark:hover:border-[#0a84ff] hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-all text-left">
                <div className="text-3xl mb-3">📄</div>
                <p className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-[#0a84ff] transition-colors">
                  "분석 리포트를 생성해줘"
                </p>
              </button>
            </div>
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
    );
  }

  const lastAssistantIndex = messages.map((m, i) => ({ ...m, i }))
    .reverse()
    .find(m => m.role === 'assistant')?.i;

  // 메시지 그룹핑 로직 - 연속된 같은 발신자의 메시지 감지
  const getMessageGrouping = (index: number) => {
    const current = messages[index];
    if (!current) {
      return {
        isFirstInGroup: false,
        isLastInGroup: false,
        isSingleMessage: false,
      };
    }
    const previous = index > 0 ? messages[index - 1] : null;
    const next = index < messages.length - 1 ? messages[index + 1] : null;

    const isFirstInGroup = !previous || previous.role !== current.role;
    const isLastInGroup = !next || next.role !== current.role;

    return {
      isFirstInGroup,
      isLastInGroup,
      isSingleMessage: isFirstInGroup && isLastInGroup,
    };
  };

  return (
    <ScrollArea className="h-full w-full">
      <div className="py-4 pb-32">
        {messages.map((message, index) => {
          const grouping = getMessageGrouping(index);
          return (
            <MessageItem
              key={message.id}
              message={message}
              onRegenerate={onRegenerate}
              isLastAssistant={index === lastAssistantIndex}
              isFirstInGroup={grouping.isFirstInGroup}
              isLastInGroup={grouping.isLastInGroup}
            />
          );
        })}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
