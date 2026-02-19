import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiRequest } from '../lib/api';

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
  createSession: (feature: ChatSession['feature']) => string;
  deleteSession: (sessionId: string) => Promise<void>;
  setActiveSession: (sessionId: string | null) => void;
  setSessionBackendId: (sessionId: string, backendSessionId: number) => void;
  fetchMessages: (sessionId: string) => Promise<void>;
  addMessage: (sessionId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  addFile: (sessionId: string, file: Omit<UploadedFile, 'id' | 'uploadedAt' | 'selected'>) => boolean;
  removeFile: (sessionId: string, fileId: string) => void;
  toggleFileSelection: (sessionId: string, fileId: string) => void;
  updateSessionTitle: (sessionId: string, title: string) => void;

  uploadedFile: UploadedFile | null;
  setUploadedFile: (file: UploadedFile | null) => void;
}

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

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      uploadedFile: null,
      setUploadedFile: (file) => set({ uploadedFile: file }),

      sessions: [],
      activeSessionId: null,

      createSession: (feature) => {
        const sessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
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
        }));

        return sessionId;
      },

      deleteSession: async (sessionId) => {
        const session = get().sessions.find((s) => s.id === sessionId);
        const { backendSessionId } = session || {};

        // Optimistic update: remove session from UI immediately
        set((state) => ({
          sessions: state.sessions.filter((s) => s.id !== sessionId),
          activeSessionId: state.activeSessionId === sessionId ? null : state.activeSessionId,
        }));

        if (backendSessionId) {
          try {
            await apiRequest(`/chats/${backendSessionId}`, { method: 'DELETE' });
          } catch (error) {
            console.error('Failed to delete session from server:', error);
            // Optionally, we could revert the state here if we wanted to be strict,
            // but for deletion it's often better to just let it go or show a toast.
          }
        }
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
              s.id === sessionId ? { ...s, messages: newMessages } : s,
            ),
          }));
        } catch (error) {
          console.error('Failed to fetch messages:', error);
        }
      },

      addMessage: (sessionId, message) => {
        const fullMessage: ChatMessage = {
          ...message,
          id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`,
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
      },

      addFile: (sessionId, file) => {
        const session = get().sessions.find((s) => s.id === sessionId);

        if (session) {
          const duplicate = session.files.some(
            (existing) => existing.name === file.name && existing.size === file.size,
          );
          if (duplicate) return false;
        }

        const fullFile: UploadedFile = {
          ...file,
          id: `file-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`,
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
    }),
    {
      name: 'manufacturing-ai-storage',
      partialize: (state) => ({
        sessions: state.sessions,
        activeSessionId: state.activeSessionId,
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.sessions) {
          state.sessions = reviveDates(state.sessions);
        }
      },
    },
  ),
);
