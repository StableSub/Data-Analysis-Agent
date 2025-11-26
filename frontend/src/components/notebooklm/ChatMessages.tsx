import { MutableRefObject } from 'react';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date | string;
};

interface ChatMessagesProps {
  messages: Message[];
  isGenerating: boolean;
  streamingContent: string;
  emptyTitle: string;
  emptySubtitle: string;
  endRef: MutableRefObject<HTMLDivElement | null>;
}

export function ChatMessages({
  messages,
  isGenerating,
  streamingContent,
  emptyTitle,
  emptySubtitle,
  endRef,
}: ChatMessagesProps) {
  const hasMessages = messages && messages.length > 0;

  return (
    <div className="flex-1 overflow-auto p-6">
      {!hasMessages ? (
        <div className="h-full flex items-center justify-center">
          <div className="max-w-2xl mx-auto text-center space-y-8">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500 to-purple-600 text-white text-4xl">
              🤖
            </div>
            <div>
              <h2 className="text-3xl text-gray-900 dark:text-white mb-2">{emptyTitle}</h2>
              <p className="text-gray-600 dark:text-gray-400">{emptySubtitle}</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[70%] ${msg.role === 'user' ? '' : 'flex items-start gap-3'}`}>
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white flex-shrink-0">
                    🤖
                  </div>
                )}
                <div>
                  <div
                    className={`px-4 py-3 rounded-2xl ${
                      msg.role === 'user'
                        ? 'bg-blue-500 dark:bg-[#0084ff] text-white'
                        : 'bg-gray-100 dark:bg-[#2f2f2f] text-gray-900 dark:text-white'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 px-2">
                    {new Date(msg.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            </div>
          ))}

          {isGenerating && streamingContent && (
            <div className="flex justify-start">
              <div className="max-w-[70%] flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white flex-shrink-0">
                  🤖
                </div>
                <div>
                  <div className="px-4 py-3 rounded-2xl bg-gray-100 dark:bg-[#2f2f2f] text-gray-900 dark:text-white">
                    <p className="text-sm whitespace-pre-wrap">
                      {streamingContent}
                      <span className="inline-block w-2 h-4 ml-0.5 bg-blue-500 dark:bg-blue-400 animate-pulse" />
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={endRef as any} />
        </div>
      )}
    </div>
  );
}

