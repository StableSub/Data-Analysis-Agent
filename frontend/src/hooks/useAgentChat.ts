import { useCallback, useEffect, useMemo, useRef } from 'react';

import type { Message } from '@ag-ui/core';
import { useCoAgent, useCoAgentStateRender } from '@copilotkit/react-core';
import { useAgent } from '@copilotkitnext/react';

import type { WorkbenchCardProps } from '../components/gen-ui';
import { useStore } from '../store/useStore';
import {
  COAGENT_NAME,
  DEFAULT_STREAMING_STATE,
  type AgentState,
  type SessionArtifact,
  type StreamingState,
  type ToolCallState,
} from '../types/agent-state';

interface FileRef {
  id: string;
  type: 'dataset' | 'document';
  sourceId?: string;
  selected?: boolean;
}

interface SendMessageOptions {
  addUserMessage?: boolean;
}

interface UseAgentChatOptions {
  activeSessionId: string | null;
  files: FileRef[];
}

const COPILOTKIT_ENABLED = import.meta.env.VITE_USE_COPILOTKIT !== 'false';

function mapToolCall(item: AgentState['tool_calls'][number]): ToolCallState {
  return {
    id: item.id,
    name: item.name,
    status: item.status,
    error: item.error,
    updatedAt: new Date().toISOString(),
  };
}

function cardToArtifact(card: WorkbenchCardProps): SessionArtifact {
  return {
    id: `artifact-${card.cardId}`,
    createdAt: card.createdAt ?? new Date().toISOString(),
    type: 'card',
    card,
  };
}

function normalizePhase(phase: AgentState['phase']): StreamingState['phase'] {
  if (!phase) return 'idle';
  if (
    phase === 'idle' ||
    phase === 'thinking' ||
    phase === 'analyzing' ||
    phase === 'preprocessing' ||
    phase === 'visualizing' ||
    phase === 'searching' ||
    phase === 'reporting'
  ) {
    return phase;
  }
  return 'thinking';
}

export function useAgentChat({ activeSessionId, files }: UseAgentChatOptions) {
  const selectedSourceId = useMemo(
    () => files.find((file) => file.selected && file.type === 'dataset')?.sourceId,
    [files],
  );

  const {
    addMessage,
    updateMessageContent,
    setSessionArtifacts,
    setStreamingState,
    setPhaseProgress,
    markStreamStale,
    setToolCalls,
    upsertToolCall,
    clearToolCalls,
  } = useStore((state) => ({
    addMessage: state.addMessage,
    updateMessageContent: state.updateMessageContent,
    setSessionArtifacts: state.setSessionArtifacts,
    setStreamingState: state.setStreamingState,
    setPhaseProgress: state.setPhaseProgress,
    markStreamStale: state.markStreamStale,
    setToolCalls: state.setToolCalls,
    upsertToolCall: state.upsertToolCall,
    clearToolCalls: state.clearToolCalls,
  }));

  const streamingState = useStore((state) =>
    activeSessionId ? state.streamingStateBySession[activeSessionId] ?? DEFAULT_STREAMING_STATE : DEFAULT_STREAMING_STATE,
  );
  const toolCalls = useStore((state) =>
    activeSessionId ? state.toolCallsBySession[activeSessionId] ?? [] : [],
  );

  const { agent } = useAgent({ agentId: COAGENT_NAME });
  const coAgent = useCoAgent<AgentState>({
    name: COAGENT_NAME,
    initialState: {
      cards: [],
      phase: 'idle',
      progress: 0,
    },
    config: {
      configurable: {
        thread_id: activeSessionId ?? undefined,
        session_id: activeSessionId ?? undefined,
        data_source_id: selectedSourceId ?? undefined,
      },
    },
  });

  const placeholderBySessionRef = useRef<Record<string, string>>({});

  const applyAgentState = useCallback(
    (state: AgentState) => {
      if (!activeSessionId) return;

      if (Array.isArray(state.cards)) {
        setSessionArtifacts(activeSessionId, state.cards.map((card) => cardToArtifact(card as WorkbenchCardProps)));
      }

      if (Array.isArray(state.tool_calls)) {
        setToolCalls(activeSessionId, state.tool_calls.map(mapToolCall));
      }

      const phase = normalizePhase(state.phase);
      const progress = typeof state.progress === 'number' ? state.progress : 0;
      setPhaseProgress(activeSessionId, phase, progress, state.last_tool);
    },
    [activeSessionId, setPhaseProgress, setSessionArtifacts, setToolCalls],
  );

  useCoAgentStateRender<AgentState>(
    {
      name: COAGENT_NAME,
      handler: ({ state }) => {
        applyAgentState(state);
      },
    },
    [applyAgentState],
  );

  useEffect(() => {
    if (!agent || !activeSessionId || !COPILOTKIT_ENABLED) return;

    const subscription = agent.subscribe({
      onTextMessageContentEvent: ({ textMessageBuffer }) => {
        const placeholderId = placeholderBySessionRef.current[activeSessionId];
        if (!placeholderId) return;
        updateMessageContent(activeSessionId, placeholderId, textMessageBuffer);
      },
      onToolCallStartEvent: ({ event }) => {
        upsertToolCall(activeSessionId, {
          id: event.toolCallId,
          name: event.toolCallName,
          status: 'running',
          updatedAt: new Date().toISOString(),
        });
      },
      onToolCallEndEvent: ({ event, toolCallName }) => {
        upsertToolCall(activeSessionId, {
          id: event.toolCallId,
          name: toolCallName,
          status: 'completed',
          updatedAt: new Date().toISOString(),
        });
      },
      onRunErrorEvent: ({ event }) => {
        const placeholderId = placeholderBySessionRef.current[activeSessionId];
        if (placeholderId) {
          updateMessageContent(activeSessionId, placeholderId, `오류가 발생했습니다: ${event.message}`);
          delete placeholderBySessionRef.current[activeSessionId];
        }

        setStreamingState(activeSessionId, {
          isStreaming: false,
          phase: 'idle',
          progress: 0,
          lastError: event.message,
        });
      },
      onRunFinalized: () => {
        const placeholderId = placeholderBySessionRef.current[activeSessionId];
        if (placeholderId) {
          delete placeholderBySessionRef.current[activeSessionId];
        }

        setStreamingState(activeSessionId, {
          isStreaming: false,
          phase: 'idle',
          progress: 1,
        });
      },
      onStateChanged: ({ state }) => {
        applyAgentState(state as AgentState);
      },
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [activeSessionId, agent, applyAgentState, setStreamingState, updateMessageContent, upsertToolCall]);

  const sendMessage = useCallback(
    async (content: string, options: SendMessageOptions = {}) => {
      if (!activeSessionId) return false;

      const trimmed = content.trim();
      if (!trimmed) return false;

      if (streamingState.isStreaming) return false;

      if (options.addUserMessage !== false) {
        addMessage(activeSessionId, {
          role: 'user',
          content: trimmed,
        });
      }

      const placeholderId = addMessage(activeSessionId, {
        role: 'assistant',
        content: '',
      });
      placeholderBySessionRef.current[activeSessionId] = placeholderId;

      setStreamingState(activeSessionId, {
        isStreaming: true,
        phase: 'thinking',
        progress: 0.05,
        staleStream: false,
        lastError: undefined,
      });
      clearToolCalls(activeSessionId);

      if (!COPILOTKIT_ENABLED) {
        window.setTimeout(() => {
          updateMessageContent(
            activeSessionId,
            placeholderId,
            'CopilotKit 비활성화 모드입니다. `VITE_USE_COPILOTKIT=true`로 전환하면 실시간 스트리밍을 사용할 수 있습니다.',
          );
          setStreamingState(activeSessionId, {
            isStreaming: false,
            phase: 'idle',
            progress: 1,
          });
          delete placeholderBySessionRef.current[activeSessionId];
        }, 300);
        return true;
      }

      if (!agent) {
        updateMessageContent(activeSessionId, placeholderId, '에이전트 연결이 아직 준비되지 않았습니다.');
        setStreamingState(activeSessionId, {
          isStreaming: false,
          phase: 'idle',
          progress: 0,
          lastError: 'agent_not_ready',
        });
        delete placeholderBySessionRef.current[activeSessionId];
        return false;
      }

      try {
        const userMessage: Message = {
          id: `user-${crypto.randomUUID()}`,
          role: 'user',
          content: trimmed,
        };
        agent.addMessage(userMessage);
        await agent.runAgent();
        return true;
      } catch (error) {
        const message = error instanceof Error ? error.message : 'run_failed';
        updateMessageContent(activeSessionId, placeholderId, `요청 처리 중 오류가 발생했습니다: ${message}`);
        setStreamingState(activeSessionId, {
          isStreaming: false,
          phase: 'idle',
          progress: 0,
          lastError: message,
        });
        delete placeholderBySessionRef.current[activeSessionId];
        return false;
      }
    },
    [
      activeSessionId,
      addMessage,
      agent,
      clearToolCalls,
      setStreamingState,
      streamingState.isStreaming,
      updateMessageContent,
    ],
  );

  const stop = useCallback(() => {
    if (!activeSessionId) return;

    if (agent) {
      agent.abortRun();
    }

    setStreamingState(activeSessionId, {
      isStreaming: false,
      phase: 'idle',
      progress: 0,
      lastError: 'stopped_by_user',
    });
    markStreamStale(activeSessionId);

    const placeholderId = placeholderBySessionRef.current[activeSessionId];
    if (placeholderId) {
      updateMessageContent(activeSessionId, placeholderId, '생성이 중지되었습니다.');
      delete placeholderBySessionRef.current[activeSessionId];
    }
  }, [activeSessionId, agent, markStreamStale, setStreamingState, updateMessageContent]);

  const retryTool = useCallback(
    async (toolName: string) => {
      return sendMessage(`이전 실패 단계인 ${toolName} 도구를 다시 실행해줘.`);
    },
    [sendMessage],
  );

  return {
    isCopilotEnabled: COPILOTKIT_ENABLED,
    sendMessage,
    stop,
    retryTool,
    isStreaming: streamingState.isStreaming,
    phase: streamingState.phase,
    progress: streamingState.progress,
    lastTool: streamingState.lastTool,
    lastError: streamingState.lastError,
    staleStream: streamingState.staleStream,
    toolCalls,
    coAgent,
  };
}
