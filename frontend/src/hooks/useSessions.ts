import { create } from 'zustand';
import { ChatSession, ChatMessage } from '../types/chat';

interface SessionState {
  sessions: ChatSession[];
  currentSessionId: string | null;
  
  createSession: (title?: string, modelId?: string) => string;
  deleteSession: (id: string) => void;
  setCurrentSession: (id: string) => void;
  renameSession: (id: string, title: string) => void;
  setSessionModel: (id: string, modelId: string) => void;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, content: string) => void;
  getCurrentSession: () => ChatSession | null;
  regenerateLastMessage: () => void;
}

export const useSessions = create<SessionState>((set, get) => ({
  sessions: [],
  currentSessionId: null,

  createSession: (title = '새 대화', modelId?: string) => {
    const newSession: ChatSession = {
      id: `session-${Date.now()}`,
      title,
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      modelId,
    };

    set((state) => ({
      sessions: [newSession, ...state.sessions],
      currentSessionId: newSession.id,
    }));

    return newSession.id;
  },

  deleteSession: (id: string) => {
    set((state) => {
      const newSessions = state.sessions.filter((s) => s.id !== id);
      const newCurrentId = state.currentSessionId === id
        ? (newSessions[0]?.id || null)
        : state.currentSessionId;

      return {
        sessions: newSessions,
        currentSessionId: newCurrentId,
      };
    });
  },

  setCurrentSession: (id: string) => {
    set({ currentSessionId: id });
  },

  renameSession: (id: string, title: string) => {
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === id
          ? { ...session, title, updatedAt: new Date().toISOString() }
          : session
      ),
    }));
  },

  setSessionModel: (id: string, modelId: string) => {
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === id
          ? { ...session, modelId, updatedAt: new Date().toISOString() }
          : session
      ),
    }));
  },

  addMessage: (message: ChatMessage) => {
    set((state) => {
      const sessions = state.sessions.map((session) => {
        if (session.id === state.currentSessionId) {
          return {
            ...session,
            messages: [...session.messages, message],
            updatedAt: new Date().toISOString(),
            title: session.messages.length === 0 
              ? message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '')
              : session.title,
          };
        }
        return session;
      });

      return { sessions };
    });
  },

  updateMessage: (id: string, content: string) => {
    set((state) => {
      const sessions = state.sessions.map((session) => {
        if (session.id === state.currentSessionId) {
          return {
            ...session,
            messages: session.messages.map((msg) =>
              msg.id === id ? { ...msg, content } : msg
            ),
            updatedAt: new Date().toISOString(),
          };
        }
        return session;
      });

      return { sessions };
    });
  },

  getCurrentSession: () => {
    const state = get();
    return state.sessions.find((s) => s.id === state.currentSessionId) || null;
  },

  regenerateLastMessage: () => {
    set((state) => {
      const sessions = state.sessions.map((session) => {
        if (session.id === state.currentSessionId) {
          // Remove last assistant message
          const messages = session.messages.filter(
            (msg, idx) => !(idx === session.messages.length - 1 && msg.role === 'assistant')
          );
          return {
            ...session,
            messages,
            updatedAt: new Date().toISOString(),
          };
        }
        return session;
      });

      return { sessions };
    });
  },
}));
