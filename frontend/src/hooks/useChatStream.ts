import { useState, useCallback, useRef } from 'react';
import { ChatMessage } from '../types/chat';
import { toast } from 'sonner';

export function useChatStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const send = useCallback(async (
    messages: ChatMessage[],
    onChunk: (delta: string, messageId: string) => void,
    onComplete: (messageId: string, usage?: any) => void
  ) => {
    try {
      setIsStreaming(true);
      abortControllerRef.current = new AbortController();

      // Simulate streaming - in production, this would call /api/chat/stream
      const messageId = `msg-${Date.now()}`;

      // Simulate streaming with responses
      const responses = [
        "분석을 시작하겠습니다. ",
        "업로드하신 데이터를 확인했습니다.\n\n",
        "## 주요 발견사항\n\n",
        "1. **온도 데이터**: 평균 73.5°C로 정상 범위입니다.\n",
        "2. **이상 탐지**: 총 23건의 이상 패턴이 감지되었습니다.\n",
        "3. **권장사항**: M001 설비의 냉각 시스템 점검이 필요합니다.\n\n",
        "추가로 궁금한 사항이 있으시면 말씀해 주세요!"
      ];

      for (let i = 0; i < responses.length; i++) {
        if (abortControllerRef.current?.signal.aborted) {
          break;
        }

        await new Promise(resolve => setTimeout(resolve, 200 + Math.random() * 300));
        onChunk(responses[i]!, messageId);
      }

      if (!abortControllerRef.current?.signal.aborted) {
        onComplete(messageId, {
          promptTokens: 512,
          completionTokens: 256
        });
      }
    } catch (error) {
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
