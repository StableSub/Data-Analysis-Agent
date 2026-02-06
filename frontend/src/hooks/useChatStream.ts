import { useState, useCallback, useRef } from 'react';
import { ChatMessage } from '../types/chat';
import { toast } from 'sonner';
import { DEFAULT_MODEL_ID } from '../lib/models';

export function useChatStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const send = useCallback(async (
    messages: ChatMessage[],
    onChunk: (delta: string, messageId: string) => void,
    onComplete: (messageId: string, usage?: any) => void,
    options?: { modelId?: string; sessionId?: string; data_source_id?: string; assistantMessageId?: string }
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
          numericSessionId = parseInt(lastPart);
        }
      }

      const body = {
        question: lastMessage.content,
        session_id: numericSessionId,
        model_id: options?.modelId || DEFAULT_MODEL_ID,
        data_source_id: options?.data_source_id,
      };

      console.log('Sending request to backend:', body);

      const response = await fetch('http://localhost:8000/chats/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error('Failed to fetch response');
      }

      const data = await response.json();
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
