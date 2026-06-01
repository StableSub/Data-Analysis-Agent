import { useCallback, useEffect, useState } from "react";
import type { PipelineSessionContext } from "./useAnalysisPipeline";
import type { ChatSessionSummary } from "../../lib/api";

const STORAGE_KEY = "genui-workbench-sessions-v1";

export interface WorkbenchSessionItem {
  id: string;
  title: string;
  backendSessionId: number | null;
  updatedAt: string;
  activityAt: string | null;
  context: PipelineSessionContext;
}

interface SessionStorePayload {
  sessions: WorkbenchSessionItem[];
  activeSessionId: string | null;
}

interface SessionPatch {
  title?: string;
  backendSessionId?: number | null;
  context?: PipelineSessionContext;
}

interface MergeServerSessionsResult {
  sessions: WorkbenchSessionItem[];
  activeSessionId: string | null;
}

function createSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function createEmptyContext(): PipelineSessionContext {
  return {
    backendSessionId: null,
    runId: null,
    traceId: null,
    fileName: "",
    uploadedDatasets: [],
    selectedSourceId: null,
    uploadedGuidelines: [],
    selectedGuidelineSourceId: null,
    guidelinesScopedToSession: true,
    chatHistory: [],
    latestAssistantAnswer: null,
    latestVisualizationResult: null,
    pendingApproval: null,
    stateHint: "empty",
    errorMessage: null,
  };
}

function normalizeContext(value: unknown): PipelineSessionContext {
  if (!value || typeof value !== "object") {
    return createEmptyContext();
  }
  const context = value as Partial<PipelineSessionContext>;
  const keepSessionGuidelines = context.guidelinesScopedToSession === true;
  return {
    backendSessionId: typeof context.backendSessionId === "number" ? context.backendSessionId : null,
    runId: typeof context.runId === "string" ? context.runId : null,
    traceId: typeof context.traceId === "string" ? context.traceId : null,
    fileName: typeof context.fileName === "string" ? context.fileName : "",
    uploadedDatasets: Array.isArray(context.uploadedDatasets) ? context.uploadedDatasets : [],
    selectedSourceId: typeof context.selectedSourceId === "string" ? context.selectedSourceId : null,
    uploadedGuidelines:
      keepSessionGuidelines && Array.isArray(context.uploadedGuidelines) ? context.uploadedGuidelines : [],
    selectedGuidelineSourceId:
      keepSessionGuidelines && typeof context.selectedGuidelineSourceId === "string"
        ? context.selectedGuidelineSourceId
        : null,
    guidelinesScopedToSession: true,
    chatHistory: Array.isArray(context.chatHistory) ? context.chatHistory : [],
    latestAssistantAnswer:
      typeof context.latestAssistantAnswer === "string" ? context.latestAssistantAnswer : null,
    latestVisualizationResult: context.latestVisualizationResult ?? null,
    pendingApproval: context.pendingApproval ?? null,
    stateHint:
      context.stateHint === "needs-user" ||
      context.stateHint === "ready" ||
      context.stateHint === "success" ||
      context.stateHint === "error"
        ? context.stateHint
        : "empty",
    errorMessage: typeof context.errorMessage === "string" ? context.errorMessage : null,
  };
}

function normalizeSession(value: unknown): WorkbenchSessionItem | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const item = value as Partial<WorkbenchSessionItem>;
  if (typeof item.id !== "string" || !item.id) {
    return null;
  }
  return {
    id: item.id,
    title: typeof item.title === "string" && item.title.trim() ? item.title : "새 채팅",
    backendSessionId: typeof item.backendSessionId === "number" ? item.backendSessionId : null,
    updatedAt: typeof item.updatedAt === "string" && item.updatedAt ? item.updatedAt : new Date().toISOString(),
    activityAt:
      typeof item.activityAt === "string" && item.activityAt
        ? item.activityAt
        : typeof item.updatedAt === "string" && item.updatedAt
          ? item.updatedAt
          : null,
    context: normalizeContext(item.context),
  };
}

function loadSessionStore(): SessionStorePayload {
  if (typeof window === "undefined") {
    return { sessions: [], activeSessionId: null };
  }
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return { sessions: [], activeSessionId: null };
  }
  try {
    const parsed = JSON.parse(raw) as Partial<SessionStorePayload>;
    const sessions = Array.isArray(parsed.sessions)
      ? parsed.sessions
          .map((item) => normalizeSession(item))
          .filter((item): item is WorkbenchSessionItem => item !== null)
      : [];
    const activeSessionId =
      typeof parsed.activeSessionId === "string" && sessions.some((item) => item.id === parsed.activeSessionId)
        ? parsed.activeSessionId
        : sessions[0]?.id ?? null;
    return { sessions, activeSessionId };
  } catch {
    return { sessions: [], activeSessionId: null };
  }
}

function sortByRecent(items: WorkbenchSessionItem[]): WorkbenchSessionItem[] {
  return [...items].sort((a, b) => {
    const left = a.activityAt ?? "";
    const right = b.activityAt ?? "";
    if (left !== right) {
      return right.localeCompare(left);
    }
    return b.updatedAt.localeCompare(a.updatedAt);
  });
}

function createServerSessionItem(
  summary: ChatSessionSummary,
  baseContext: PipelineSessionContext,
): WorkbenchSessionItem {
  const updatedAt = summary.updated_at ?? new Date().toISOString();
  return {
    id: `server-${summary.id}`,
    title: summary.title || summary.last_message_preview || "새 채팅",
    backendSessionId: summary.id,
    updatedAt,
    activityAt: updatedAt,
    context: {
      ...baseContext,
      backendSessionId: summary.id,
      chatHistory: [],
      latestAssistantAnswer: null,
      uploadedGuidelines: [],
      selectedGuidelineSourceId: null,
      guidelinesScopedToSession: true,
      pendingApproval: null,
      stateHint: summary.message_count > 0 ? "success" : baseContext.stateHint,
      errorMessage: null,
    },
  };
}

export function useWorkbenchSessionStore() {
  const initial = loadSessionStore();
  const [sessions, setSessions] = useState<WorkbenchSessionItem[]>(initial.sessions);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(initial.activeSessionId);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const payload: SessionStorePayload = { sessions, activeSessionId };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  }, [sessions, activeSessionId]);

  const createSession = useCallback(() => {
    const now = new Date().toISOString();
    const next: WorkbenchSessionItem = {
      id: createSessionId(),
      title: "새 채팅",
      backendSessionId: null,
      updatedAt: now,
      activityAt: null,
      context: createEmptyContext(),
    };
    setSessions((prev) => [next, ...prev]);
    setActiveSessionId(next.id);
    return next;
  }, []);

  const selectSession = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId);
  }, []);

  const updateSession = useCallback((sessionId: string, patch: SessionPatch) => {
    setSessions((prev) => {
      return prev.map((item) => {
        if (item.id !== sessionId) {
          return item;
        }
        const nextContext = patch.context ?? item.context;
        const backendSessionId =
          patch.backendSessionId !== undefined
            ? patch.backendSessionId
            : nextContext.backendSessionId ?? item.backendSessionId;
        return {
          ...item,
          title: patch.title !== undefined ? patch.title : item.title,
          backendSessionId: backendSessionId ?? null,
          context: nextContext,
        };
      });
    });
  }, []);

  const markSessionActivity = useCallback((sessionId: string, patch?: SessionPatch) => {
    setSessions((prev) => {
      const now = new Date().toISOString();
      const next = prev.map((item) => {
        if (item.id !== sessionId) {
          return item;
        }

        const nextContext = patch?.context ?? item.context;
        const backendSessionId =
          patch?.backendSessionId !== undefined
            ? patch.backendSessionId
            : nextContext.backendSessionId ?? item.backendSessionId;

        return {
          ...item,
          title: patch?.title !== undefined ? patch.title : item.title,
          backendSessionId: backendSessionId ?? null,
          context: nextContext,
          updatedAt: now,
          activityAt: now,
        };
      });

      return sortByRecent(next);
    });
  }, []);

  const updateActiveSession = useCallback(
    (patch: SessionPatch) => {
      if (!activeSessionId) {
        return;
      }
      updateSession(activeSessionId, patch);
    },
    [activeSessionId, updateSession],
  );

  const markActiveSessionActivity = useCallback(
    (patch?: SessionPatch) => {
      if (!activeSessionId) {
        return;
      }
      markSessionActivity(activeSessionId, patch);
    },
    [activeSessionId, markSessionActivity],
  );

  const deleteSession = useCallback((sessionId: string) => {
    setSessions((prev) => prev.filter((item) => item.id !== sessionId));
    setActiveSessionId((prev) => (prev === sessionId ? null : prev));
  }, []);

  const mergeServerSessions = useCallback(
    (
      serverSessions: ChatSessionSummary[],
      baseContext: PipelineSessionContext,
    ): MergeServerSessionsResult => {
      const serverById = new Map(serverSessions.map((item) => [item.id, item]));
      const existingBackendIds = new Set<number>();
      const mergedExisting = sessions.map((item) => {
        if (item.backendSessionId === null) {
          return item;
        }
        const serverSession = serverById.get(item.backendSessionId);
        if (!serverSession) {
          return item;
        }
        existingBackendIds.add(item.backendSessionId);
        const updatedAt = serverSession.updated_at ?? item.updatedAt;
        return {
          ...item,
          title: serverSession.title || item.title,
          updatedAt,
          activityAt: updatedAt,
          context: {
            ...item.context,
            backendSessionId: serverSession.id,
            uploadedDatasets:
              item.context.uploadedDatasets.length > 0
                ? item.context.uploadedDatasets
                : baseContext.uploadedDatasets,
            selectedSourceId: item.context.selectedSourceId ?? baseContext.selectedSourceId,
            fileName: item.context.fileName || baseContext.fileName,
            stateHint:
              item.context.chatHistory.length > 0 || serverSession.message_count > 0
                ? "success"
                : item.context.stateHint,
          },
        };
      });
      const newServerSessions = serverSessions
        .filter((item) => !existingBackendIds.has(item.id))
        .map((item) => createServerSessionItem(item, baseContext));
      const nextSessions = sortByRecent([...mergedExisting, ...newServerSessions]);
      const nextActiveSessionId =
        activeSessionId && nextSessions.some((item) => item.id === activeSessionId)
          ? activeSessionId
          : nextSessions[0]?.id ?? null;

      setSessions(nextSessions);
      setActiveSessionId(nextActiveSessionId);
      return { sessions: nextSessions, activeSessionId: nextActiveSessionId };
    },
    [activeSessionId, sessions],
  );

  return {
    sessions,
    activeSessionId,
    createSession,
    selectSession,
    deleteSession,
    updateSession,
    updateActiveSession,
    markSessionActivity,
    markActiveSessionActivity,
    mergeServerSessions,
  };
}
