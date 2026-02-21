import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import type { WorkbenchCardProps } from '../components/gen-ui';
import { apiRequest } from '../lib/api';
import {
  DEFAULT_STREAMING_STATE,
  type AgentPhase,
  type SessionArtifact,
  type StreamingState,
  type ToolCallState,
} from '../types/agent-state';

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: 'dataset' | 'document';
  sourceId?: string;
  uploadedAt: Date;
  columns?: string[];
  rowCount?: number;
  preview?: unknown[];
  selected?: boolean;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatSession {
  id: string;
  backendSessionId?: number | null;
  title: string;
  feature: 'chat' | 'visualization' | 'edit' | 'simulation';
  messages: ChatMessage[];
  files: UploadedFile[];
  createdAt: Date;
  updatedAt: Date;
}

interface AppState {
  sessions: ChatSession[];
  activeSessionId: string | null;
  sessionArtifacts: Record<string, SessionArtifact[]>;
  streamingStateBySession: Record<string, StreamingState>;
  toolCallsBySession: Record<string, ToolCallState[]>;

  createSession: (feature: ChatSession['feature']) => string;
  deleteSession: (sessionId: string) => Promise<void>;
  setActiveSession: (sessionId: string | null) => void;
  setSessionBackendId: (sessionId: string, backendSessionId: number) => void;
  fetchMessages: (sessionId: string) => Promise<void>;
  addMessage: (sessionId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>) => string;
  updateMessageContent: (sessionId: string, messageId: string, content: string) => void;
  updateLastAssistantMessage: (sessionId: string, content: string) => void;
  addFile: (sessionId: string, file: Omit<UploadedFile, 'id' | 'uploadedAt' | 'selected'>) => boolean;
  removeFile: (sessionId: string, fileId: string) => void;
  toggleFileSelection: (sessionId: string, fileId: string) => void;
  updateSessionTitle: (sessionId: string, title: string) => void;

  setSessionArtifacts: (sessionId: string, artifacts: SessionArtifact[]) => void;
  appendArtifact: (sessionId: string, artifact: SessionArtifact) => void;
  upsertCardArtifact: (sessionId: string, card: WorkbenchCardProps) => void;
  removeCardArtifact: (sessionId: string, cardId: string) => void;
  updateCardArtifact: (
    sessionId: string,
    cardId: string,
    updater: (card: WorkbenchCardProps) => WorkbenchCardProps,
  ) => void;

  setStreamingState: (sessionId: string, patch: Partial<StreamingState>) => void;
  setPhaseProgress: (
    sessionId: string,
    phase: AgentPhase,
    progress: number,
    lastTool?: string,
  ) => void;
  markStreamStale: (sessionId: string) => void;

  setToolCalls: (sessionId: string, toolCalls: ToolCallState[]) => void;
  upsertToolCall: (sessionId: string, toolCall: ToolCallState) => void;
  clearToolCalls: (sessionId: string) => void;

  uploadedFile: UploadedFile | null;
  setUploadedFile: (file: UploadedFile | null) => void;
}

const nowIso = () => new Date().toISOString();

const makeId = (prefix: string): string => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;

const reviveDates = (sessions: ChatSession[]): ChatSession[] => {
  return sessions.map((session) => ({
    ...session,
    createdAt: typeof session.createdAt === 'string' ? new Date(session.createdAt) : session.createdAt,
    updatedAt: typeof session.updatedAt === 'string' ? new Date(session.updatedAt) : session.updatedAt,
    messages: session.messages.map((msg) => ({
      ...msg,
      timestamp: typeof msg.timestamp === 'string' ? new Date(msg.timestamp) : msg.timestamp,
    })),
    files: session.files.map((file) => ({
      ...file,
      uploadedAt: typeof file.uploadedAt === 'string' ? new Date(file.uploadedAt) : file.uploadedAt,
    })),
  }));
};

function clampProgress(progress: number): number {
  if (!Number.isFinite(progress)) return 0;
  return Math.max(0, Math.min(1, progress));
}

function normalizeStreamingState(state: StreamingState): StreamingState {
  return {
    ...DEFAULT_STREAMING_STATE,
    ...state,
    progress: clampProgress(state.progress),
  };
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      uploadedFile: null,
      setUploadedFile: (file) => set({ uploadedFile: file }),

      sessions: [],
      activeSessionId: null,
      sessionArtifacts: {},
      streamingStateBySession: {},
      toolCallsBySession: {},

      createSession: (feature) => {
        const sessionId = makeId('session');
        const newSession: ChatSession = {
          id: sessionId,
          backendSessionId: null,
          title: '새 대화',
          feature,
          messages: [],
          files: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        };

        set((state) => ({
          sessions: [newSession, ...state.sessions],
          activeSessionId: sessionId,
          sessionArtifacts: {
            ...state.sessionArtifacts,
            [sessionId]: [],
          },
          streamingStateBySession: {
            ...state.streamingStateBySession,
            [sessionId]: { ...DEFAULT_STREAMING_STATE },
          },
          toolCallsBySession: {
            ...state.toolCallsBySession,
            [sessionId]: [],
          },
        }));

        return sessionId;
      },

      deleteSession: async (sessionId) => {
        const session = get().sessions.find((s) => s.id === sessionId);

        if (session?.backendSessionId) {
          try {
            await apiRequest(`/chats/${session.backendSessionId}`, { method: 'DELETE' });
          } catch (error) {
            console.error('Failed to delete session from server:', error);
          }
        }

        set((state) => {
          const { [sessionId]: _removedArtifacts, ...nextArtifacts } = state.sessionArtifacts;
          const { [sessionId]: _removedStreaming, ...nextStreaming } = state.streamingStateBySession;
          const { [sessionId]: _removedToolCalls, ...nextToolCalls } = state.toolCallsBySession;

          return {
            sessions: state.sessions.filter((s) => s.id !== sessionId),
            activeSessionId: state.activeSessionId === sessionId ? null : state.activeSessionId,
            sessionArtifacts: nextArtifacts,
            streamingStateBySession: nextStreaming,
            toolCallsBySession: nextToolCalls,
          };
        });
      },

      setActiveSession: (sessionId) => {
        set({ activeSessionId: sessionId });
      },

      setSessionBackendId: (sessionId, backendSessionId) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId ? { ...session, backendSessionId } : session,
          ),
        }));
      },

      fetchMessages: async (sessionId) => {
        const session = get().sessions.find((s) => s.id === sessionId);
        if (!session?.backendSessionId) return;

        interface ChatHistoryResponse {
          session_id: number;
          messages: {
            id: number;
            role: string;
            content: string;
            created_at: string;
          }[];
        }

        try {
          const history = await apiRequest<ChatHistoryResponse>(`/chats/${session.backendSessionId}/history`);
          const newMessages: ChatMessage[] = history.messages.map((msg) => ({
            id: `msg-${msg.id}`,
            role: msg.role === 'user' ? 'user' : 'assistant',
            content: msg.content,
            timestamp: new Date(msg.created_at),
          }));

          set((state) => ({
            sessions: state.sessions.map((s) =>
              s.id === sessionId ? { ...s, messages: newMessages, updatedAt: new Date() } : s,
            ),
          }));
        } catch (error) {
          console.error('Failed to fetch messages:', error);
        }
      },

      addMessage: (sessionId, message) => {
        const fullMessage: ChatMessage = {
          ...message,
          id: makeId('msg'),
          timestamp: new Date(),
        };

        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: [...session.messages, fullMessage],
                  updatedAt: new Date(),
                  title:
                    session.messages.length === 0 && message.role === 'user'
                      ? `${message.content.slice(0, 30)}${message.content.length > 30 ? '...' : ''}`
                      : session.title,
                }
              : session,
          ),
        }));

        return fullMessage.id;
      },

      updateMessageContent: (sessionId, messageId, content) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: session.messages.map((message) =>
                    message.id === messageId ? { ...message, content, timestamp: new Date() } : message,
                  ),
                  updatedAt: new Date(),
                }
              : session,
          ),
        }));
      },

      updateLastAssistantMessage: (sessionId, content) => {
        set((state) => ({
          sessions: state.sessions.map((session) => {
            if (session.id !== sessionId) return session;

            const messages = [...session.messages];
            for (let i = messages.length - 1; i >= 0; i -= 1) {
              if (messages[i]?.role === 'assistant') {
                messages[i] = { ...messages[i], content, timestamp: new Date() };
                return {
                  ...session,
                  messages,
                  updatedAt: new Date(),
                };
              }
            }

            const fallback: ChatMessage = {
              id: makeId('msg'),
              role: 'assistant',
              content,
              timestamp: new Date(),
            };
            messages.push(fallback);
            return {
              ...session,
              messages,
              updatedAt: new Date(),
            };
          }),
        }));
      },

      addFile: (sessionId, file) => {
        const session = get().sessions.find((s) => s.id === sessionId);

        if (session) {
          const duplicate = session.files.some(
            (existing) =>
              (file.sourceId && existing.sourceId && existing.sourceId === file.sourceId) ||
              (existing.name === file.name && existing.size === file.size),
          );
          if (duplicate) return false;
        }

        const fullFile: UploadedFile = {
          ...file,
          id: makeId('file'),
          uploadedAt: new Date(),
          selected: true,
        };

        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  files: [...session.files, fullFile],
                  updatedAt: new Date(),
                }
              : session,
          ),
        }));

        return true;
      },

      removeFile: (sessionId, fileId) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  files: session.files.filter((f) => f.id !== fileId),
                  updatedAt: new Date(),
                }
              : session,
          ),
        }));
      },

      toggleFileSelection: (sessionId, fileId) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? {
                  ...session,
                  files: session.files.map((file) =>
                    file.id === fileId ? { ...file, selected: !file.selected } : file,
                  ),
                  updatedAt: new Date(),
                }
              : session,
          ),
        }));
      },

      updateSessionTitle: (sessionId, title) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId ? { ...session, title, updatedAt: new Date() } : session,
          ),
        }));
      },

      setSessionArtifacts: (sessionId, artifacts) => {
        set((state) => ({
          sessionArtifacts: {
            ...state.sessionArtifacts,
            [sessionId]: artifacts,
          },
        }));
      },

      appendArtifact: (sessionId, artifact) => {
        set((state) => ({
          sessionArtifacts: {
            ...state.sessionArtifacts,
            [sessionId]: [...(state.sessionArtifacts[sessionId] ?? []), artifact],
          },
        }));
      },

      upsertCardArtifact: (sessionId, card) => {
        set((state) => {
          const artifacts = state.sessionArtifacts[sessionId] ?? [];
          const index = artifacts.findIndex((artifact) => artifact.type === 'card' && artifact.card.cardId === card.cardId);
          const nextArtifact: SessionArtifact = {
            id: `artifact-${card.cardId}`,
            createdAt: card.createdAt ?? nowIso(),
            type: 'card',
            card,
          };

          if (index === -1) {
            return {
              sessionArtifacts: {
                ...state.sessionArtifacts,
                [sessionId]: [...artifacts, nextArtifact],
              },
            };
          }

          return {
            sessionArtifacts: {
              ...state.sessionArtifacts,
              [sessionId]: artifacts.map((artifact, i) => (i === index ? { ...artifact, card } : artifact)),
            },
          };
        });
      },

      removeCardArtifact: (sessionId, cardId) => {
        set((state) => ({
          sessionArtifacts: {
            ...state.sessionArtifacts,
            [sessionId]: (state.sessionArtifacts[sessionId] ?? []).filter(
              (artifact) => artifact.type !== 'card' || artifact.card.cardId !== cardId,
            ),
          },
        }));
      },

      updateCardArtifact: (sessionId, cardId, updater) => {
        set((state) => ({
          sessionArtifacts: {
            ...state.sessionArtifacts,
            [sessionId]: (state.sessionArtifacts[sessionId] ?? []).map((artifact) => {
              if (artifact.type !== 'card' || artifact.card.cardId !== cardId) return artifact;
              return {
                ...artifact,
                card: updater(artifact.card),
              };
            }),
          },
        }));
      },

      setStreamingState: (sessionId, patch) => {
        set((state) => {
          const current = state.streamingStateBySession[sessionId] ?? { ...DEFAULT_STREAMING_STATE };
          return {
            streamingStateBySession: {
              ...state.streamingStateBySession,
              [sessionId]: normalizeStreamingState({ ...current, ...patch }),
            },
          };
        });
      },

      setPhaseProgress: (sessionId, phase, progress, lastTool) => {
        set((state) => {
          const current = state.streamingStateBySession[sessionId] ?? { ...DEFAULT_STREAMING_STATE };
          return {
            streamingStateBySession: {
              ...state.streamingStateBySession,
              [sessionId]: normalizeStreamingState({
                ...current,
                phase,
                progress,
                lastTool,
              }),
            },
          };
        });
      },

      markStreamStale: (sessionId) => {
        set((state) => {
          const current = state.streamingStateBySession[sessionId] ?? { ...DEFAULT_STREAMING_STATE };
          return {
            streamingStateBySession: {
              ...state.streamingStateBySession,
              [sessionId]: {
                ...normalizeStreamingState(current),
                isStreaming: false,
                staleStream: true,
              },
            },
          };
        });
      },

      setToolCalls: (sessionId, toolCalls) => {
        set((state) => ({
          toolCallsBySession: {
            ...state.toolCallsBySession,
            [sessionId]: toolCalls,
          },
        }));
      },

      upsertToolCall: (sessionId, toolCall) => {
        set((state) => {
          const current = state.toolCallsBySession[sessionId] ?? [];
          const index = current.findIndex((item) => item.id === toolCall.id);
          if (index === -1) {
            return {
              toolCallsBySession: {
                ...state.toolCallsBySession,
                [sessionId]: [...current, toolCall],
              },
            };
          }

          return {
            toolCallsBySession: {
              ...state.toolCallsBySession,
              [sessionId]: current.map((item, i) => (i === index ? toolCall : item)),
            },
          };
        });
      },

      clearToolCalls: (sessionId) => {
        set((state) => ({
          toolCallsBySession: {
            ...state.toolCallsBySession,
            [sessionId]: [],
          },
        }));
      },
    }),
    {
      name: 'manufacturing-ai-storage',
      partialize: (state) => ({
        sessions: state.sessions,
        activeSessionId: state.activeSessionId,
        sessionArtifacts: state.sessionArtifacts,
        streamingStateBySession: state.streamingStateBySession,
        toolCallsBySession: state.toolCallsBySession,
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) return;

        if (state.sessions) {
          state.sessions = reviveDates(state.sessions);
        }

        if (state.streamingStateBySession) {
          const next: Record<string, StreamingState> = {};
          for (const [sessionId, streaming] of Object.entries(state.streamingStateBySession)) {
            const normalized = normalizeStreamingState({
              ...DEFAULT_STREAMING_STATE,
              ...streaming,
              isStreaming: false,
            });
            if (streaming?.isStreaming) {
              normalized.staleStream = true;
            }
            next[sessionId] = normalized;
          }
          state.streamingStateBySession = next;
        }
      },
    },
  ),
);
