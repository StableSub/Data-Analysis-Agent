import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, Role, Permission, ROLE_DEFINITIONS, AuditLogEntry } from '../types/rbac';
import { apiRequest } from '../lib/api';

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: 'dataset' | 'document'; // 데이터셋 vs 문서
  sourceId?: string; // Backend source ID
  uploadedAt: Date;
  columns?: string[];
  rowCount?: number;
  preview?: any[];
  selected?: boolean; // 분석에 사용할지 여부
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

interface AnalysisResult {
  eda: {
    summary: any;
    distributions: any[];
    correlations: any[];
  };
  anomalies: {
    detected: number;
    items: any[];
  };
}

interface TraceEvent {
  timestamp: string;
  type: 'exec' | 'open' | 'tcp_connect';
  process: string;
  details: string;
  suspicious: boolean;
}

interface AppState {
  // Auth
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string, role?: Role) => Promise<boolean>;
  logout: () => void;

  // Chat Sessions
  sessions: ChatSession[];
  activeSessionId: string | null;
  createSession: (feature: ChatSession['feature']) => string;
  deleteSession: (sessionId: string) => void;
  setActiveSession: (sessionId: string | null) => void;
  setSessionBackendId: (sessionId: string, backendSessionId: number) => void;
  fetchMessages: (sessionId: string) => Promise<void>;
  addMessage: (sessionId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  addFile: (sessionId: string, file: Omit<UploadedFile, 'id' | 'uploadedAt' | 'selected'>) => boolean;
  removeFile: (sessionId: string, fileId: string) => void;
  toggleFileSelection: (sessionId: string, fileId: string) => void;
  updateSessionTitle: (sessionId: string, title: string) => void;

  // Upload (legacy - keeping for backward compatibility)
  uploadedFile: UploadedFile | null;
  setUploadedFile: (file: UploadedFile | null) => void;

  // Analysis
  analysisResult: AnalysisResult | null;
  setAnalysisResult: (result: AnalysisResult | null) => void;
  isAnalyzing: boolean;
  setIsAnalyzing: (status: boolean) => void;

  // Report
  report: string | null;
  setReport: (report: string | null) => void;

  // Trace
  traceEvents: TraceEvent[];
  setTraceEvents: (events: TraceEvent[]) => void;
  addTraceEvent: (event: TraceEvent) => void;

  // Audit Log
  auditLogs: AuditLogEntry[];
  addAuditLog: (entry: Omit<AuditLogEntry, 'id' | 'timestamp'>) => void;
}

// Helper function to revive dates from localStorage
const reviveDates = (sessions: ChatSession[]): ChatSession[] => {
  return sessions.map(session => ({
    ...session,
    createdAt: typeof session.createdAt === 'string' ? new Date(session.createdAt) : session.createdAt,
    updatedAt: typeof session.updatedAt === 'string' ? new Date(session.updatedAt) : session.updatedAt,
    messages: session.messages.map(msg => ({
      ...msg,
      timestamp: typeof msg.timestamp === 'string' ? new Date(msg.timestamp) : msg.timestamp,
    })),
    files: session.files.map(file => ({
      ...file,
      uploadedAt: typeof file.uploadedAt === 'string' ? new Date(file.uploadedAt) : file.uploadedAt,
    })),
  }));
};

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Auth
      user: null,
      isAuthenticated: false,
      login: async (email: string, password: string, role: Role = 'ADMIN') => {
        // Mock authentication - in production, this would call a real API
        return new Promise((resolve) => {
          setTimeout(() => {
            // Demo accounts
            const accounts = {
              'admin@manufacturing.ai': { password: 'admin123', role: 'ADMIN' as Role, name: '이승현 (관리자)' },
              'analyst@manufacturing.ai': { password: 'analyst123', role: 'ANALYST' as Role, name: '김분석 (분석가)' },
              'user@manufacturing.ai': { password: 'user123', role: 'USER' as Role, name: '박사용 (사용자)' },
            };

            const account = accounts[email as keyof typeof accounts];

            if (account && password === account.password) {
              const userRole = account.role;
              const permissions = ROLE_DEFINITIONS[userRole].permissions;

              const user: User = {
                id: `user-${Date.now()}`,
                name: account.name,
                email,
                role: userRole,
                permissions,
                createdAt: new Date().toISOString(),
              };

              set({
                user,
                isAuthenticated: true,
              });

              // Add audit log
              get().addAuditLog({
                user: email,
                action: 'LOGIN',
                result: 'success',
              });

              resolve(true);
            } else {
              resolve(false);
            }
          }, 1000);
        });
      },
      logout: () => {
        const state = get();
        if (state.user) {
          state.addAuditLog({
            user: state.user.email,
            action: 'LOGOUT',
            result: 'success',
          });
        }
        set({ user: null, isAuthenticated: false });
      },

      // Upload
      uploadedFile: null,
      setUploadedFile: (file) => set({ uploadedFile: file }),

      // Analysis
      analysisResult: null,
      setAnalysisResult: (result) => set({ analysisResult: result }),
      isAnalyzing: false,
      setIsAnalyzing: (status) => set({ isAnalyzing: status }),

      // Report
      report: null,
      setReport: (report) => set({ report: report }),

      // Trace
      traceEvents: [],
      setTraceEvents: (events) => set({ traceEvents: events }),
      addTraceEvent: (event) => set((state) => ({
        traceEvents: [event, ...state.traceEvents].slice(0, 100)
      })),

      // Audit Log
      auditLogs: [],
      addAuditLog: (entry) => {
        const fullEntry: AuditLogEntry = {
          ...entry,
          id: `audit-${Date.now()}-${Math.random()}`,
          timestamp: new Date().toISOString(),
        };

        set((state) => ({
          auditLogs: [fullEntry, ...state.auditLogs].slice(0, 500),
        }));
      },

      // Chat Sessions
      sessions: [],
      activeSessionId: null,

      createSession: (feature) => {
        const sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
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
        const session = get().sessions.find(s => s.id === sessionId);

        // Backend delete attempt
        if (session && session.backendSessionId) {
          try {
            await apiRequest(`/chats/${session.backendSessionId}`, { method: 'DELETE' });
          } catch (error) {
            console.error('Failed to delete session from server:', error);
            // Continue with local deletion
          }
        }

        set((state) => ({
          sessions: state.sessions.filter(s => s.id !== sessionId),
          activeSessionId: state.activeSessionId === sessionId ? null : state.activeSessionId,
        }));
      },

      setActiveSession: (sessionId) => {
        set({ activeSessionId: sessionId });
      },

      setSessionBackendId: (sessionId, backendSessionId) => {
        set((state) => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId
              ? { ...session, backendSessionId }
              : session
          ),
        }));
      },

      fetchMessages: async (sessionId) => {
        const state = get();
        const session = state.sessions.find(s => s.id === sessionId);

        if (!session || !session.backendSessionId) return;

        try {
          // Import needed interface locally or assume backend structure
          interface ChatHistoryResponse {
            session_id: number;
            messages: {
              id: number;
              role: string;
              content: string;
              created_at?: string;
            }[];
          }

          const history = await apiRequest<ChatHistoryResponse>(`/chats/${session.backendSessionId}/history`);

          const newMessages: ChatMessage[] = history.messages.map(msg => ({
            id: `msg-${msg.id}`,
            role: msg.role as 'user' | 'assistant',
            content: msg.content,
            timestamp: msg.created_at ? new Date(msg.created_at) : new Date(),
          }));

          set((state) => ({
            sessions: state.sessions.map(s =>
              s.id === sessionId
                ? { ...s, messages: newMessages }
                : s
            ),
          }));
        } catch (error) {
          console.error('Failed to fetch messages:', error);
        }
      },

      addMessage: (sessionId, message) => {
        const fullMessage: ChatMessage = {
          ...message,
          id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
        };

        set((state) => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId
              ? {
                ...session,
                messages: [...session.messages, fullMessage],
                updatedAt: new Date(),
                // Auto-update title from first message
                title: session.messages.length === 0 && message.role === 'user'
                  ? message.content.slice(0, 30) + (message.content.length > 30 ? '...' : '')
                  : session.title
              }
              : session
          ),
        }));
      },

      addFile: (sessionId, file) => {
        const state = get();
        const session = state.sessions.find(s => s.id === sessionId);

        // 중복 파일 체크 (파일명과 크기가 동일한 경우)
        if (session) {
          const isDuplicate = session.files.some(
            existingFile => existingFile.name === file.name && existingFile.size === file.size
          );

          if (isDuplicate) {
            // 중복 파일인 경우 추가하지 않음
            return false;
          }
        }

        const fullFile: UploadedFile = {
          ...file,
          id: `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          uploadedAt: new Date(),
          selected: true, // 기본적으로 선택됨
        };

        set((state) => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId
              ? {
                ...session,
                files: [...session.files, fullFile],
                updatedAt: new Date(),
              }
              : session
          ),
        }));

        return true;
      },

      removeFile: (sessionId, fileId) => {
        set((state) => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId
              ? {
                ...session,
                files: session.files.filter(f => f.id !== fileId),
                updatedAt: new Date(),
              }
              : session
          ),
        }));
      },

      toggleFileSelection: (sessionId, fileId) => {
        set((state) => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId
              ? {
                ...session,
                files: session.files.map(file =>
                  file.id === fileId
                    ? { ...file, selected: !file.selected }
                    : file
                ),
                updatedAt: new Date(),
              }
              : session
          ),
        }));
      },

      updateSessionTitle: (sessionId, title) => {
        set((state) => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId
              ? { ...session, title, updatedAt: new Date() }
              : session
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
        // LocalStorage에서 로드된 후 Date 문자열을 Date 객체로 변환
        if (state && state.sessions) {
          state.sessions = reviveDates(state.sessions);
        }
      },
    }
  )
);
