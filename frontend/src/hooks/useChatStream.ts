import { useState, useCallback, useRef } from 'react';
import { ChatMessage } from '../types/chat';
import { toast } from 'sonner';
import { apiRequest } from '../lib/api';

export function useChatStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const send = useCallback(async (
    messages: ChatMessage[],
    onChunk: (delta: string, messageId: string) => void,
    onComplete: (messageId: string, usage?: any) => void,
    options?: { modelId?: string; sessionId?: string; sourceId?: string; assistantMessageId?: string }
  ) => {
    try {
      setIsStreaming(true);
      abortControllerRef.current = new AbortController();

      const lastMessage = messages[messages.length - 1];
      if (!lastMessage) return;

      // Extract numeric ID from string like "session-1738679469212"
      let numericSessionId: number | undefined = undefined;
      if (options?.sessionId) {
        const parts = options.sessionId.split('-');
        const lastPart = parts[parts.length - 1];
        if (lastPart) {
          const parsed = parseInt(lastPart, 10);
          if (!Number.isNaN(parsed)) {
            numericSessionId = parsed;
          }
        }
      }

      const body: { question: string; session_id?: number; model_id?: string; source_id?: string } = {
        question: lastMessage.content,
      };
      if (numericSessionId !== undefined) {
        body.session_id = numericSessionId;
      }
      if (options?.modelId) {
        body.model_id = options.modelId;
      }
      if (options?.sourceId) {
        body.source_id = options.sourceId;
      }

      const data = await apiRequest<{ answer: string }>('/chats', {
        method: 'POST',
        body: JSON.stringify(body),
        signal: abortControllerRef.current.signal,
      });
      const messageId = options?.assistantMessageId || `assistant-${Date.now()}`;

      // Since backend doesn't support streaming yet, we return the whole answer as one chunk
      onChunk(data.answer, messageId);
      onComplete(messageId);

    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }
      toast.error('응답 생성 중 오류가 발생했습니다');
      console.error('Stream error:', error);
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  }, []);

  const stop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
      toast.info('응답 생성이 중단되었습니다');
    }
  }, []);

  return { isStreaming, send, stop };
}
