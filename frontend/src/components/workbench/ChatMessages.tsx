import { MutableRefObject, useEffect, useState } from 'react';
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  pipelineSteps?: Array<{
    phase: string;
    message: string;
    status?: 'active' | 'completed' | 'failed';
  }>;
  visualizationResult?: {
    status?: string;
    source_id?: string;
    summary?: string;
    chart?: {
      chart_type?: string;
      x_key?: string;
      y_key?: string;
      points?: Array<{ x: number; y: number }>;
    };
  };
  timestamp: Date | string;
};

interface ChatMessagesProps {
  messages: Message[];
  isGenerating: boolean;
  streamingContent: string;
  thinkingSteps?: Array<{
    phase: string;
    message: string;
    status?: 'active' | 'completed' | 'failed';
  }>;
  emptyTitle: string;
  emptySubtitle: string;
  endRef: MutableRefObject<HTMLDivElement | null>;
}

export function ChatMessages({
  messages,
  isGenerating,
  streamingContent,
  thinkingSteps = [],
  emptyTitle,
  emptySubtitle,
  endRef,
}: ChatMessagesProps) {
  const hasMessages = messages && messages.length > 0;
  const [thinkingDots, setThinkingDots] = useState('...');

  useEffect(() => {
    if (!isGenerating || Boolean(streamingContent)) {
      setThinkingDots('...');
      return;
    }
    let dotCount = 0;
    const timerId = window.setInterval(() => {
      dotCount = (dotCount % 3) + 1;
      setThinkingDots('.'.repeat(dotCount));
    }, 350);
    return () => window.clearInterval(timerId);
  }, [isGenerating, streamingContent]);

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
                    {msg.role === 'assistant' && Array.isArray(msg.pipelineSteps) && msg.pipelineSteps.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-200 dark:border-white/10 space-y-1">
                        {msg.pipelineSteps.map((step, index) => (
                          <p
                            key={`${step.phase}-${index}-${step.message}`}
                            className="text-xs text-gray-600 dark:text-gray-300 whitespace-pre-wrap"
                          >
                            {index + 1}. {step.message}
                          </p>
                        ))}
                      </div>
                    )}
                    {msg.role === 'assistant' &&
                      msg.visualizationResult?.status === 'generated' &&
                      msg.visualizationResult.chart?.chart_type === 'scatter' &&
                      Array.isArray(msg.visualizationResult.chart.points) &&
                      msg.visualizationResult.chart.points.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-white/10">
                          <p className="text-xs text-gray-600 dark:text-gray-300 mb-2">
                            시각화: {msg.visualizationResult.chart.x_key || 'x'} vs {msg.visualizationResult.chart.y_key || 'y'}
                          </p>
                          <div className="w-full h-56 bg-white dark:bg-[#212121] rounded-lg p-2">
                            <ResponsiveContainer width="100%" height="100%">
                              <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis
                                  type="number"
                                  dataKey="x"
                                  name={msg.visualizationResult.chart.x_key || 'x'}
                                />
                                <YAxis
                                  type="number"
                                  dataKey="y"
                                  name={msg.visualizationResult.chart.y_key || 'y'}
                                />
                                <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                                <Scatter data={msg.visualizationResult.chart.points} fill="#3b82f6" />
                              </ScatterChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      )}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 px-2">
                    {new Date(msg.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            </div>
          ))}

          {isGenerating && (streamingContent || thinkingSteps.length > 0) && (
            <div className="flex justify-start">
              <div className="max-w-[70%] flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white flex-shrink-0">
                  🤖
                </div>
                <div>
                  <div className="px-4 py-3 rounded-2xl bg-gray-100 dark:bg-[#2f2f2f] text-gray-900 dark:text-white">
                    <p className="text-sm whitespace-pre-wrap">
                      {streamingContent || `AI가 생각 중 입니다${thinkingDots}`}
                      {streamingContent && (
                        <span className="inline-block w-2 h-4 ml-0.5 bg-gray-400 dark:bg-gray-500 animate-pulse" />
                      )}
                    </p>
                    {thinkingSteps.length > 0 && (
                      <div className="mt-3 pt-2 border-t border-gray-200 dark:border-white/10 space-y-1">
                        {thinkingSteps.map((step, index) => (
                          <p
                            key={`${step.phase}-${index}-${step.message}`}
                            className="text-xs text-gray-600 dark:text-gray-300 whitespace-pre-wrap"
                          >
                            {index + 1}. {step.message}
                          </p>
                        ))}
                      </div>
                    )}
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
