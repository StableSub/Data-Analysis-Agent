import React, { useState, useRef, useCallback, useEffect } from "react";
import { ToolCallIndicator } from "../components/genui/ToolCallIndicator";
import { WorkbenchCommandBar } from "../components/genui/WorkbenchCommandBar";
import { Dropzone } from "../components/genui/Dropzone";
import { WorkbenchLayout } from "../components/genui/WorkbenchLayout";
import { StatusBadge } from "../components/genui/StatusBadge";
import { GateBar } from "../components/genui/GateBar";
import { AssistantReportMessage } from "../components/genui/AssistantReportMessage";
import { ApprovalCard } from "../components/genui/ApprovalCard";
import { CardBody, CardHeader, CardShell } from "../components/genui/CardShell";
import { PreEdaBoard } from "../components/genui/PreEdaBoard";
import { VisualizationResultView } from "../components/visualization/VisualizationResultView";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  FileText,
  MessageSquare,
  Plus,
  RefreshCw,
  Trash2,
  XCircle,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { PipelineBar, type PipelineBarVariant } from "../components/genui/PipelineBar";
import { useAnalysisPipeline, type PipelineSessionContext } from "../hooks/useAnalysisPipeline";
import { useWorkbenchSessionStore, type WorkbenchSessionItem } from "../hooks/useWorkbenchSessionStore";
import {
  deleteChatSession,
  type EdaRecommendedOperation,
  fetchPendingApproval,
  getChatHistory,
  isApiErrorStatus,
  listDatasets,
  type PendingApprovalPayload,
} from "../../lib/api";
import {
  hasVisualizationArtifact,
  hasVisualizationChartData,
} from "../../lib/visualization";
import { toast } from "sonner";
import {
  getRestoredFallbackStateHint,
  normalizeRestoredSessionContext,
} from "../lib/pipelineSessionContext";

// --- INLINE COMPONENTS ---

const InlineUploadProgress = ({ progress, fileName }: { progress: number; fileName: string }) => {
  return (
    <div className="w-full max-w-2xl mx-auto p-4 bg-[var(--genui-surface)] rounded-xl border border-[var(--genui-border)] shadow-sm animate-in fade-in zoom-in-95 duration-300">
      <div className="flex items-center gap-4 mb-3">
        <div className="w-10 h-10 rounded-lg bg-[var(--genui-panel)] flex items-center justify-center border border-[var(--genui-border)]">
          <FileText className="w-5 h-5 text-[var(--genui-text)]" />
        </div>
        <div className="flex-1 space-y-1">
          <div className="flex justify-between text-sm font-medium text-[var(--genui-text)]">
            <span>{fileName || "data.csv"}</span>
            <span>{progress}%</span>
          </div>
          <div className="h-1.5 w-full bg-[var(--genui-panel)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--genui-running)] transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs text-[var(--genui-muted)] px-1">
        <div className={cn("flex items-center gap-1", progress >= 30 ? "text-[var(--genui-success)]" : "text-[var(--genui-running)]")}>
          {progress >= 30 ? <CheckCircle2 className="w-3 h-3" /> : <div className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
          Uploading
        </div>
        <div className="w-4 h-px bg-[var(--genui-border)]" />
        <div className={cn("flex items-center gap-1", progress < 30 ? "opacity-50" : progress >= 70 ? "text-[var(--genui-success)]" : "text-[var(--genui-running)]")}>
          {progress >= 70 ? <CheckCircle2 className="w-3 h-3" /> : <div className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
          Parsing
        </div>
        <div className="w-4 h-px bg-[var(--genui-border)]" />
        <div className={cn("flex items-center gap-1", progress < 70 ? "opacity-50" : progress === 100 ? "text-[var(--genui-success)]" : "text-[var(--genui-running)]")}>
          {progress === 100 ? <CheckCircle2 className="w-3 h-3" /> : <div className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
          Validating
        </div>
      </div>
    </div>
  );
};

const formatPendingValue = (value: unknown): string => {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join(", ");
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean" || value === null) {
    return String(value);
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  return "";
};

const formatPendingOperation = (operation: Record<string, unknown>): string => {
  const op = typeof operation.op === "string" && operation.op.trim() ? operation.op : "operation";
  const details = Object.entries(operation)
    .filter(([key, value]) => key !== "op" && value !== undefined && value !== "")
    .map(([key, value]) => `${key}: ${formatPendingValue(value)}`)
    .filter((value) => value.trim());
  return details.length > 0 ? `${op} (${details.join(" · ")})` : op;
};

const buildPendingApprovalChanges = (
  pendingApproval: PendingApprovalPayload | null,
): string[] => {
  if (!pendingApproval) {
    return ["승인 대기 중인 작업이 있습니다."];
  }

  if (pendingApproval.stage === "report") {
    return [
      "분석 결과 초안을 검토한 뒤 승인 또는 수정 요청",
      typeof pendingApproval.review?.revision_count === "number"
        ? `현재 revision count: ${pendingApproval.review.revision_count}`
        : "분석 결과 수정 횟수 정보 없음",
      "승인 후 최종 Analysis 흐름을 마무리",
    ];
  }

  if (pendingApproval.stage === "visualization") {
    return [
      `chart_type: ${pendingApproval.plan.chart_type || "-"}`,
      `x: ${pendingApproval.plan.x_key || "-"} / y: ${pendingApproval.plan.y_key || "-"}`,
      pendingApproval.plan.reason || "시각화 계획 검토 필요",
    ];
  }

  const operationItems =
    pendingApproval.plan.operations.length > 0
      ? pendingApproval.plan.operations.map((operation) => formatPendingOperation(operation))
      : ["제안된 전처리 operation 없음"];

  return operationItems.slice(0, 4);
};

const ANALYSIS_FAILURE_MESSAGE = "응답을 생성하지 못했습니다.";

// --- MAIN PAGE ---

export default function Workbench() {
  const pipeline = useAnalysisPipeline();
  const {
    state,
    uploadProgress,
    runningSubPhase,
    elapsedSeconds,
    reportSections,
    toolCalls,
    evidence,
    pendingApproval,
    latestVisualizationResult,
    selectedPreEdaProfile,
    selectedPreEdaApplyError,
    selectedApplyingPreEdaOperationKey,
    isPreEdaApplying,
    selectedPreEdaDistributionLoadingColumn,
    selectedPreEdaDistributionError,
    chatHistory,
    fileName,
    uploadedDatasets,
    selectedSourceId,
    selectUploadedDataset,
    removeUploadedDataset,
    sessionId,
    handleSend,
    applyRecommendedOperation,
    loadSelectedPreEdaDistribution,
    captureSessionContext,
    restoreSessionContext,
    clearForNewDraft,
  } = pipeline;
  const {
    sessions,
    activeSessionId,
    createSession,
    selectSession,
    deleteSession: deleteSessionFromStore,
    updateSession,
    updateActiveSession,
    markSessionActivity,
  } = useWorkbenchSessionStore();

  const activeSession = sessions.find((item) => item.id === activeSessionId) ?? null;
  const hasDatasetContext = Boolean(selectedSourceId);
  const hasUploadedDatasets = uploadedDatasets.length > 0;
  const selectedDataset =
    uploadedDatasets.find((item) => item.sourceId === selectedSourceId) ?? null;
  const visualizationSummaryChart =
    latestVisualizationResult?.chart ?? latestVisualizationResult?.chart_data ?? null;
  const hasVisualizationPreview =
    hasVisualizationArtifact(latestVisualizationResult)
    || hasVisualizationChartData(latestVisualizationResult);
  const visualizationPreviewMeta =
    visualizationSummaryChart?.chart_type ?? "Chart";
  const preprocessApproveStartsAnalysis =
    pendingApproval?.stage === "preprocess" && state === "needs-user";
  const isDatasetSelectorLocked = preprocessApproveStartsAnalysis || isPreEdaApplying;

  // UI-only local state
  type CanvasView = "current" | "pre-eda" | "deep-eda" | "report";
  const [canvasView, setCanvasView] = useState<CanvasView>("current");
  const canvasScrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const initializedRef = useRef(false);
  const lastAutoOpenedPreEdaSourceRef = useRef<string | null>(null);
  const restoreRequestSeqRef = useRef(0);
  const expectedSessionIdRef = useRef<string | null>(activeSessionId);

  // Reset canvas view when pipeline state transitions forward
  useEffect(() => {
    if (state === "running" || state === "uploading") {
      setCanvasView("current");
    }
  }, [state]);

  useEffect(() => {
    if (!selectedSourceId || state !== "ready" || !selectedPreEdaProfile) {
      if (!selectedSourceId) {
        lastAutoOpenedPreEdaSourceRef.current = null;
      }
      return;
    }

    if (chatHistory.length > 0) {
      return;
    }

    if (lastAutoOpenedPreEdaSourceRef.current === selectedSourceId) {
      return;
    }

    lastAutoOpenedPreEdaSourceRef.current = selectedSourceId;
    setCanvasView("pre-eda");
  }, [selectedSourceId, selectedPreEdaProfile, state, chatHistory.length]);

  useEffect(() => {
    if (canvasView === "current") {
      return;
    }

    const frame = window.requestAnimationFrame(() => {
      canvasScrollRef.current?.scrollTo({ top: 0, behavior: "auto" });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [canvasView]);

  const handleApplyRecommendedOperation = useCallback(
    async (operation: EdaRecommendedOperation, index: number) => {
      const result = await applyRecommendedOperation(operation, index);
      if (result !== "applied") {
        return;
      }
      setCanvasView("pre-eda");
      toast.success("선택한 전처리 작업을 적용했습니다.");
    },
    [applyRecommendedOperation],
  );

  const handleRetryPreEda = useCallback(async () => {
    const result = await pipeline.retrySelectedPreEda();
    if (result === "ready") {
      toast.success("Pre-EDA 정보를 다시 불러왔습니다.");
      return;
    }
    if (result === "unavailable") {
      toast.error("Pre-EDA 정보를 다시 불러오지 못했습니다.");
    }
  }, [pipeline]);

  const formatElapsed = (s: number) => {
    const m = Math.floor(s / 60).toString().padStart(2, "0");
    const sec = (s % 60).toString().padStart(2, "0");
    return `${m}:${sec}`;
  };

  function getCurrentSession(items: WorkbenchSessionItem[]): WorkbenchSessionItem | null {
    const sessionsWithActivity = items.filter((item) => Boolean(item.activityAt));
    if (sessionsWithActivity.length === 0) {
      return activeSession ?? items[0] ?? null;
    }
    return sessionsWithActivity.reduce((latest, item) => {
      if (!latest) {
        return item;
      }
      return (item.activityAt ?? "") > (latest.activityAt ?? "") ? item : latest;
    }, sessionsWithActivity[0]);
  }

  const currentSession = getCurrentSession(sessions);

  const saveSessionSnapshot = useCallback(
    (targetSessionId: string | null) => {
      if (!targetSessionId) {
        return;
      }
      const snapshot = captureSessionContext();
      updateSession(targetSessionId, {
        backendSessionId: snapshot.backendSessionId,
        context: snapshot,
      });
    },
    [captureSessionContext, updateSession],
  );

  const markExpectedSession = useCallback((sessionId: string | null) => {
    expectedSessionIdRef.current = sessionId;
  }, []);

  const ensureActiveSessionForInteraction = useCallback((): WorkbenchSessionItem => {
    if (activeSessionId) {
      const currentSession = sessions.find((item) => item.id === activeSessionId);
      if (currentSession) {
        return currentSession;
      }
    }

    const fallbackSession = sessions[0] ?? null;
    if (fallbackSession) {
      markExpectedSession(fallbackSession.id);
      selectSession(fallbackSession.id);
      return fallbackSession;
    }

    const nextSession = createSession();
    markExpectedSession(nextSession.id);
    selectSession(nextSession.id);
    return nextSession;
  }, [activeSessionId, sessions, selectSession, createSession, markExpectedSession]);

  const reconcileSessionDatasets = useCallback(
    async (
      context: PipelineSessionContext,
    ): Promise<{ context: PipelineSessionContext; changed: boolean }> => {
      if (context.uploadedDatasets.length === 0) {
        return { context, changed: false };
      }

      const requestedSourceIds = new Set(
        context.uploadedDatasets
          .map((dataset) => dataset.sourceId)
          .filter((sourceId): sourceId is string => Boolean(sourceId)),
      );

      if (requestedSourceIds.size === 0) {
        return { context, changed: false };
      }

      const foundSourceIds = new Set<string>();
      const limit = Math.min(100, Math.max(requestedSourceIds.size, 20));
      let skip = 0;
      let total = 0;

      try {
        do {
          const response = await listDatasets(skip, limit);
          total = response.total;
          response.items.forEach((item) => {
            if (requestedSourceIds.has(item.source_id)) {
              foundSourceIds.add(item.source_id);
            }
          });
          skip += response.items.length;

          if (foundSourceIds.size === requestedSourceIds.size || response.items.length === 0) {
            break;
          }
        } while (skip < total);
      } catch {
        return { context, changed: false };
      }

      const nextUploadedDatasets = context.uploadedDatasets.filter((dataset) =>
        foundSourceIds.has(dataset.sourceId),
      );
      const nextSelectedSourceId =
        typeof context.selectedSourceId === "string"
        && nextUploadedDatasets.some((dataset) => dataset.sourceId === context.selectedSourceId)
          ? context.selectedSourceId
          : nextUploadedDatasets[0]?.sourceId ?? null;
      const nextSelectedDataset =
        nextUploadedDatasets.find((dataset) => dataset.sourceId === nextSelectedSourceId) ?? null;
      const hasConversation =
        context.chatHistory.length > 0 || Boolean(context.latestAssistantAnswer);
      const nextStateHint =
        nextUploadedDatasets.length > 0
          ? context.stateHint
          : hasConversation
            ? "success"
            : "empty";
      const nextFileName = nextSelectedDataset?.fileName ?? "";
      const changed =
        nextUploadedDatasets.length !== context.uploadedDatasets.length
        || nextSelectedSourceId !== context.selectedSourceId
        || nextStateHint !== context.stateHint
        || nextFileName !== context.fileName;

      if (!changed) {
        return { context, changed: false };
      }

      return {
        changed: true,
        context: {
          ...context,
          uploadedDatasets: nextUploadedDatasets,
          selectedSourceId: nextSelectedSourceId,
          stateHint: nextStateHint,
          fileName: nextFileName,
        },
      };
    },
    [],
  );

  const restoreSessionById = useCallback(
    async (targetSessionId: string) => {
      const targetSession = sessions.find((item) => item.id === targetSessionId);
      if (!targetSession) {
        return;
      }
      const requestId = ++restoreRequestSeqRef.current;
      const isStaleRestoreRequest = () =>
        restoreRequestSeqRef.current !== requestId || expectedSessionIdRef.current !== targetSessionId;

      let nextContext: PipelineSessionContext = targetSession.context;
      let shouldPersistContext = false;

      const reconciled = await reconcileSessionDatasets(nextContext);
      if (isStaleRestoreRequest()) {
        return;
      }
      nextContext = reconciled.context;
      shouldPersistContext = reconciled.changed;

      if (targetSession.backendSessionId !== null) {
        try {
          const history = await getChatHistory(targetSession.backendSessionId);
          if (isStaleRestoreRequest()) {
            return;
          }
          const msgs = history.messages ?? [];
          const latestAssistant = [...msgs]
            .reverse()
            .find((message) => message.role === "assistant");
          const latestAssistantAnswer = latestAssistant?.content ?? nextContext.latestAssistantAnswer;
          let restoredPendingApproval = nextContext.pendingApproval;
          let stateHint = nextContext.stateHint;

          if (nextContext.stateHint === "needs-user" && nextContext.runId) {
            try {
              const pending = await fetchPendingApproval(nextContext.runId);
              if (isStaleRestoreRequest()) {
                return;
              }
              restoredPendingApproval = pending.pending_approval;
              stateHint = "needs-user";
            } catch (error) {
              if (isStaleRestoreRequest()) {
                return;
              }
              if (isApiErrorStatus(error, 404)) {
                restoredPendingApproval = null;
                stateHint = getRestoredFallbackStateHint({
                  ...nextContext,
                  chatHistory: msgs,
                  latestAssistantAnswer,
                  pendingApproval: null,
                });
              } else {
                restoredPendingApproval = nextContext.pendingApproval;
                stateHint = "needs-user";
                toast.error("승인 대기 상태를 다시 확인하지 못했습니다. 현재 상태를 유지합니다.");
              }
            }
          } else if (msgs.length > 0) {
            stateHint = "success";
          }

          nextContext = {
            ...nextContext,
            backendSessionId: targetSession.backendSessionId,
            chatHistory: msgs,
            latestAssistantAnswer,
            pendingApproval: restoredPendingApproval,
            stateHint,
            errorMessage: nextContext.stateHint === "error" ? nextContext.errorMessage : null,
          };
          nextContext = normalizeRestoredSessionContext(nextContext);
          shouldPersistContext = true;
        } catch (error) {
          if (isStaleRestoreRequest()) {
            return;
          }
          if (isApiErrorStatus(error, 404)) {
            nextContext = normalizeRestoredSessionContext({
              ...nextContext,
              backendSessionId: null,
            });
            shouldPersistContext = true;
          } else {
            toast.error("세션 히스토리를 불러오지 못했습니다.");
          }
        }
      }

      const normalizedContext = normalizeRestoredSessionContext(nextContext);
      if (normalizedContext !== nextContext) {
        nextContext = normalizedContext;
        shouldPersistContext = true;
      }

      if (isStaleRestoreRequest()) {
        return;
      }
      if (shouldPersistContext) {
        updateSession(targetSessionId, {
          backendSessionId: nextContext.backendSessionId,
          context: nextContext,
        });
      }

      if (isStaleRestoreRequest()) {
        return;
      }
      restoreSessionContext(nextContext);
    },
    [sessions, reconcileSessionDatasets, updateSession, restoreSessionContext],
  );

  const handleNewChat = useCallback(() => {
    saveSessionSnapshot(activeSessionId);
    const nextSession = createSession();
    markExpectedSession(nextSession.id);
    clearForNewDraft();
  }, [activeSessionId, saveSessionSnapshot, createSession, clearForNewDraft, markExpectedSession]);

  const handleSessionSelect = useCallback(
    async (targetSessionId: string) => {
      if (targetSessionId === activeSessionId) {
        return;
      }
      saveSessionSnapshot(activeSessionId);
      markExpectedSession(targetSessionId);
      selectSession(targetSessionId);
      await restoreSessionById(targetSessionId);
    },
    [activeSessionId, saveSessionSnapshot, selectSession, restoreSessionById, markExpectedSession],
  );

  const handleSessionDelete = useCallback(
    async (targetSessionId: string) => {
      const targetSession = sessions.find((item) => item.id === targetSessionId);
      if (!targetSession) {
        return;
      }

      if (targetSession.backendSessionId !== null) {
        try {
          await deleteChatSession(targetSession.backendSessionId);
        } catch (error) {
          if (isApiErrorStatus(error, 404)) {
            updateSession(targetSessionId, {
              backendSessionId: null,
              context: {
                ...targetSession.context,
                backendSessionId: null,
              },
            });
          } else {
            toast.error("서버 세션 삭제에 실패했습니다.");
            return;
          }
        }
      }

      const wasActive = targetSessionId === activeSessionId;
      const remaining = sessions.filter((item) => item.id !== targetSessionId);
      deleteSessionFromStore(targetSessionId);

      if (!wasActive) {
        return;
      }

      if (remaining.length === 0) {
        markExpectedSession(null);
        clearForNewDraft();
        return;
      }

      const fallbackSession = remaining[0];
      markExpectedSession(fallbackSession.id);
      selectSession(fallbackSession.id);
      await restoreSessionById(fallbackSession.id);
    },
    [
      sessions,
      activeSessionId,
      deleteSessionFromStore,
      clearForNewDraft,
      selectSession,
      restoreSessionById,
      markExpectedSession,
    ],
  );

  const handleSendMessage = useCallback(
    (value: string) => {
      const question = value.trim();
      if (!question) {
        return;
      }

      const targetSession = ensureActiveSessionForInteraction();
      const nextTitle =
        targetSession.title === "새 채팅"
          ? question.length > 30 ? `${question.slice(0, 30)}...` : question
          : undefined;
      markSessionActivity(targetSession.id, nextTitle ? { title: nextTitle } : undefined);

      handleSend(value);
    },
    [ensureActiveSessionForInteraction, markSessionActivity, handleSend],
  );

  useEffect(() => {
    if (initializedRef.current) {
      return;
    }
    if (sessions.length === 0) {
      markExpectedSession(null);
      clearForNewDraft();
      initializedRef.current = true;
      return;
    }

    const initialSessionId = activeSessionId ?? sessions[0]?.id ?? null;
    if (!initialSessionId) {
      return;
    }
    markExpectedSession(initialSessionId);
    if (!activeSessionId) {
      selectSession(initialSessionId);
    }
    void restoreSessionById(initialSessionId);
    initializedRef.current = true;
  }, [sessions, activeSessionId, clearForNewDraft, selectSession, restoreSessionById, markExpectedSession]);

  useEffect(() => {
    if (!initializedRef.current || !activeSessionId) {
      return;
    }
    if (state === "running" || state === "uploading") {
      return;
    }
    const snapshot = captureSessionContext();
    updateActiveSession({
      backendSessionId: snapshot.backendSessionId,
      context: snapshot,
    });
  }, [activeSessionId, state, captureSessionContext, updateActiveSession]);

  useEffect(() => {
    if (!initializedRef.current || !activeSessionId || sessionId === null) {
      return;
    }
    const snapshot = captureSessionContext();
    updateActiveSession({
      backendSessionId: sessionId,
      context: {
        ...snapshot,
        backendSessionId: sessionId,
      },
    });
  }, [activeSessionId, sessionId, captureSessionContext, updateActiveSession]);

  /** Open file picker for real file selection */
  const openFilePicker = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileSelected = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        const targetSession = ensureActiveSessionForInteraction();
        markSessionActivity(targetSession.id);
        pipeline.startUpload(file);
      }
      // Reset so the same file can be re-selected
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [ensureActiveSessionForInteraction, markSessionActivity, pipeline],
  );

  /** Handle Dropzone onDrop — if FileList is empty (button click), open picker */
  const handleDrop = useCallback(
    (files: FileList) => {
      const file = files[0]; // noUncheckedIndexedAccess: may be undefined
      if (file) {
        const targetSession = ensureActiveSessionForInteraction();
        markSessionActivity(targetSession.id);
        pipeline.startUpload(file);
      } else {
        openFilePicker();
      }
    },
    [ensureActiveSessionForInteraction, markSessionActivity, pipeline, openFilePicker],
  );

  const formatSessionUpdatedAt = (value: string | null | undefined) => {
    if (!value) {
      return "활동 없음";
    }
    const date = new Date(value);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const formatPercent = (value: number) => `${(value * 100).toFixed(2).replace(/\.00$/, "")}%`;

  const formatUploadedAt = (value?: string) => {
    if (!value) {
      return "-";
    }
    return new Date(value).toLocaleString([], {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatChatMessageTime = (value?: string | null) => {
    if (!value) {
      return undefined;
    }

    let date = new Date(value);
    if (Number.isNaN(date.getTime()) && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(value)) {
      date = new Date(`${value}Z`);
    }

    if (Number.isNaN(date.getTime())) {
      return undefined;
    }

    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const handleDeleteSelectedDataset = useCallback(() => {
    if (!selectedSourceId || isPreEdaApplying) {
      return;
    }
    void removeUploadedDataset(selectedSourceId);
  }, [isPreEdaApplying, selectedSourceId, removeUploadedDataset]);

  // Current running tool call for inline indicator
  const currentRunningTool = toolCalls.filter((tc) => tc.status === "running");
  const lastRunningTool = currentRunningTool[currentRunningTool.length - 1];
  const currentDatasetLabel = selectedDataset?.fileName || fileName || "선택된 데이터셋 없음";
  const sessionDisplayTitle =
    activeSession?.title ||
    (hasDatasetContext
      ? currentDatasetLabel
      : state === "empty"
        ? "새 세션"
        : "Gen-UI Workbench");
  const hasCompletedEda = Boolean(hasDatasetContext && selectedPreEdaProfile);
  const latestAssistantMessage =
    [...chatHistory].reverse().find((message) => message.role === "assistant") ?? null;
  const latestAssistantContent = latestAssistantMessage?.content.trim() ?? "";
  const hasCompletedAnalysis =
    (latestAssistantContent.length > 0 && latestAssistantContent !== ANALYSIS_FAILURE_MESSAGE)
    || (chatHistory.length === 0 && state === "success" && reportSections.length > 0);
  const hasFailedAnalysis =
    latestAssistantContent === ANALYSIS_FAILURE_MESSAGE
    || (chatHistory.length === 0 && state === "error");
  const effectiveCurrentView: Exclude<CanvasView, "current"> | null =
    state === "empty" || state === "uploading" || state === "running"
      ? null
      : hasCompletedAnalysis
        ? "deep-eda"
        : hasCompletedEda
          ? "pre-eda"
          : null;
  const displayedCanvasView: Exclude<CanvasView, "current"> | null =
    canvasView === "current" ? effectiveCurrentView : canvasView;
  const statusSteps = hasUploadedDatasets
    ? [
        {
          key: "eda" as const,
          label: "EDA",
          completed: hasCompletedEda,
          onNavigate: hasCompletedEda
            ? () => {
              setCanvasView("pre-eda");
            }
            : undefined,
        },
        {
          key: "analysis" as const,
          label: "Analysis",
          completed: hasCompletedAnalysis,
          onNavigate: hasCompletedAnalysis
            ? () => {
              setCanvasView("deep-eda");
            }
            : undefined,
        },
      ]
    : [];

  const preEdaSummarySections = [
    {
      type: "paragraph" as const,
      content:
        selectedPreEdaProfile?.qualitySummary
          ?? (hasDatasetContext
            ? `${currentDatasetLabel}이(가) 현재 source로 선택되어 있습니다. 질문 전에 구조와 품질 맥락을 먼저 확인하고, 이후 질문이 들어오면 Analysis로 이어집니다.`
            : "데이터 업로드는 완료됐지만 아직 source가 선택되지 않았습니다. 상단에서 source를 고르면 해당 데이터 기준으로 질문을 이어갈 수 있습니다."),
    },
    {
      type: "checklist" as const,
      items:
        selectedPreEdaProfile?.summaryBullets ?? [
          "상위 3개 row 미리보기와 데이터 개요 요약을 먼저 확인합니다.",
          "컬럼 타입 분류와 결측치 분석을 먼저 확인합니다.",
          "질문 이후에는 Analysis 흐름으로 이어집니다.",
        ],
    },
  ];

  const chatThreadWidthClassName = "mx-auto w-full max-w-[1320px]";
  const assistantChatCardClassName = "mx-0 w-full max-w-[1120px]";

  const preEdaUnavailableCard = selectedDataset?.preEdaStatus === "unavailable" ? (
    <CardShell status="needs-user" className="max-w-none mx-0">
      <CardHeader
        title="Pre-EDA unavailable"
        meta="WARNING"
        statusLabel="Unavailable"
        statusVariant="needs-user"
      />
      <CardBody className="space-y-3">
        <div className="flex items-start gap-3 rounded-xl border border-[var(--genui-warning)]/30 bg-[var(--genui-warning)]/8 px-4 py-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--genui-warning)]" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-[var(--genui-text)]">
              EDA 또는 전처리 추천 정보를 아직 불러오지 못했습니다.
            </p>
            <p className="text-xs text-[var(--genui-muted)]">
              {selectedDataset.preEdaWarning ?? "잠시 후 다시 시도하면 최신 Pre-EDA 상태를 다시 조회합니다."}
            </p>
          </div>
        </div>
        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleRetryPreEda}
            className="inline-flex items-center gap-2 rounded-md border border-[var(--genui-border)] bg-[var(--genui-panel)] px-3 py-2 text-xs font-medium text-[var(--genui-text)] hover:bg-[var(--genui-surface)]"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry EDA
          </button>
        </div>
      </CardBody>
    </CardShell>
  ) : null;

  /* ── LEFT PANEL — Session only ── */
  const LeftPanel = (
    <>
      <div className="h-10 border-b border-[var(--genui-border)] flex items-center px-4 gap-2 flex-shrink-0">
        <MessageSquare className="w-3.5 h-3.5 text-[var(--genui-running)]" />
        <span className="font-semibold text-sm text-[var(--genui-text)]">Session</span>
      </div>
      <div className="flex-1 min-h-0 p-2 flex flex-col gap-2">
        <div className="rounded-md border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--genui-muted)]">
            Current
          </p>
          <p className="mt-1 text-[12px] font-medium text-[var(--genui-text)] truncate">
            {currentSession?.title || "새 채팅"}
          </p>
        </div>
        <button
          type="button"
          onClick={handleNewChat}
          className="w-full h-8 rounded-md border border-[var(--genui-border)] bg-[var(--genui-panel)] text-[12px] font-medium text-[var(--genui-text)] inline-flex items-center justify-center gap-1.5 hover:bg-[var(--genui-surface)] transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          새 채팅
        </button>
        <div className="flex-1 min-h-0 overflow-y-auto space-y-1 pr-1">
          {sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <button
                key={session.id}
                type="button"
                onClick={() => {
                  void handleSessionSelect(session.id);
                }}
                className={cn(
                  "w-full rounded-md border px-2 py-1.5 text-left transition-colors",
                  isActive
                    ? "border-[var(--genui-running)]/40 bg-[var(--genui-running)]/10"
                    : "border-[var(--genui-border)] bg-[var(--genui-panel)] hover:bg-[var(--genui-surface)]",
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-[12px] font-medium text-[var(--genui-text)] truncate">
                      {session.title}
                    </p>
                    <p className="mt-0.5 text-[10px] text-[var(--genui-muted)]">
                      {formatSessionUpdatedAt(session.activityAt ?? session.updatedAt)}
                    </p>
                  </div>
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(event) => {
                      event.stopPropagation();
                      void handleSessionDelete(session.id);
                    }}
                    className="w-6 h-6 rounded-md inline-flex items-center justify-center text-[var(--genui-muted)] hover:text-[var(--genui-error)] hover:bg-[var(--genui-surface)]"
                    aria-label="세션 삭제"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </span>
                </div>
              </button>
            );
          })}
          {sessions.length === 0 && (
            <div className="px-2 py-4 text-[11px] text-[var(--genui-muted)] text-center">
              세션이 없습니다.
            </div>
          )}
        </div>
      </div>
    </>
  );

  /* ── CENTER: Decision chips → centerSubHeader ── */
  const CenterSubHeader = (
    <div className="flex w-full min-w-0 items-center gap-3">
      <div className="flex min-w-0 flex-1 items-center gap-2 overflow-hidden">
        {hasUploadedDatasets ? (
          <>
            <span className="text-[11px] font-medium text-[var(--genui-muted)] whitespace-nowrap">데이터 소스</span>
            <div className="relative min-w-0 w-full max-w-[210px]">
              <select
                value={selectedSourceId ?? ""}
                onChange={(e) => selectUploadedDataset(e.target.value || null)}
                disabled={isDatasetSelectorLocked}
                className="h-7 w-full min-w-0 appearance-none rounded-md border border-[var(--genui-border)] bg-[var(--genui-surface)] pl-2 pr-8 text-xs text-[var(--genui-text)] focus:outline-none focus:ring-1 focus:ring-[var(--genui-focus-ring)] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="">선택 안 함 (일반 질문)</option>
                {uploadedDatasets.map((dataset) => (
                  <option key={dataset.sourceId} value={dataset.sourceId}>
                    {dataset.fileName}
                  </option>
                ))}
              </select>
              <span className="pointer-events-none absolute inset-y-0 right-2 inline-flex items-center text-[var(--genui-muted)]">
                <ChevronDown className="w-3.5 h-3.5" />
              </span>
            </div>
            <button
              type="button"
              onClick={handleDeleteSelectedDataset}
              disabled={!selectedSourceId || isPreEdaApplying}
              className="h-7 px-2 rounded-md border border-[var(--genui-border)] bg-[var(--genui-panel)] text-xs text-[var(--genui-text)] inline-flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--genui-surface)] whitespace-nowrap flex-shrink-0"
            >
              <Trash2 className="w-3.5 h-3.5" />
              삭제
            </button>
          </>
        ) : (
          <span className="text-xs text-[var(--genui-muted)] whitespace-nowrap">
            업로드가 완료되면 선택된 데이터 소스와 분석 상태가 여기에 표시됩니다.
          </span>
        )}
      </div>

      {statusSteps.length > 0 ? (
        <div className="ml-auto flex flex-shrink-0 items-center gap-2">
          {statusSteps.map((step) => (
            <button
              key={step.key}
              type="button"
              onClick={step.onNavigate}
              disabled={!step.onNavigate}
              className={cn(
                "inline-flex h-9 w-[148px] items-center justify-center gap-2 rounded-md border px-3 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors",
                step.completed
                  ? "border-[var(--genui-success)]/25 bg-[var(--genui-success)]/10 text-[var(--genui-success)]"
                  : "border-[var(--genui-error)]/25 bg-[var(--genui-error)]/10 text-[var(--genui-error)]",
                step.onNavigate
                  ? "cursor-pointer hover:opacity-85"
                  : "cursor-default",
              )}
              title={
                step.completed
                  ? `${step.label} 결과 보기`
                  : `${step.label}가 아직 완료되지 않았습니다.`
              }
            >
              {step.completed ? (
                <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
              ) : (
                <XCircle className="h-4 w-4 flex-shrink-0" />
              )}
              <span>{step.label}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );

  const MainContent = (
    <div
      className={cn(
        "mx-auto w-full space-y-4 pb-28 px-2 xl:px-3",
        canvasView === "current" ? "pt-4" : "pt-2",
        canvasView === "pre-eda"
          ? "max-w-[1680px] 2xl:max-w-[1820px]"
          : state === "empty" || state === "uploading"
            ? "max-w-4xl"
            : state === "ready"
              ? "max-w-[1680px] 2xl:max-w-[1820px]"
              : "max-w-[1420px] 2xl:max-w-[1560px]",
      )}
    >
      {/* Hidden file input for real file selection */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFileSelected}
      />

      {state === "empty" && (
        <div className="flex flex-col items-center justify-center min-h-[50vh] animate-in fade-in zoom-in-95 duration-500">
          <Dropzone status="idle" onDrop={handleDrop} />
        </div>
      )}

      {state === "uploading" && (
        <div className="flex flex-col items-center justify-center min-h-[50vh]">
          <InlineUploadProgress progress={uploadProgress} fileName={fileName} />
        </div>
      )}

      {/* ── CANVAS VIEW: explicit snapshot or effective current snapshot ── */}
      {displayedCanvasView !== null && (
        <div className="animate-in fade-in duration-300">
          {displayedCanvasView === "pre-eda" && (
            <div className="space-y-6">
              <div className="flex items-center gap-2 mb-2">
                <StatusBadge status="success" />
                <span className="text-xs font-semibold text-[var(--genui-text)]">Pre-EDA</span>
                <span className="text-sm text-[var(--genui-muted)]">업로드 직후 데이터 프로파일 스냅샷</span>
              </div>
              {selectedPreEdaProfile ? (
                <PreEdaBoard
                  profile={selectedPreEdaProfile}
                  summarySections={preEdaSummarySections}
                  recommendationMode={selectedDataset?.recommendationMode ?? null}
                  recommendationWarning={selectedDataset?.preEdaWarning ?? null}
                  applyError={selectedPreEdaApplyError}
                  applyingOperationKey={selectedApplyingPreEdaOperationKey}
                  onApplyOperation={handleApplyRecommendedOperation}
                  onSelectDistributionColumn={loadSelectedPreEdaDistribution}
                  distributionLoadingColumn={selectedPreEdaDistributionLoadingColumn}
                  distributionError={selectedPreEdaDistributionError}
                />
              ) : preEdaUnavailableCard ? (
                preEdaUnavailableCard
              ) : (
                <AssistantReportMessage
                  title="Pre-EDA"
                  subtitle="프로파일 데이터가 없습니다."
                  sections={[{ type: "paragraph", content: "데이터셋을 업로드하면 Pre-EDA 프로파일이 생성됩니다." }]}
                />
              )}
            </div>
          )}

          {displayedCanvasView === "deep-eda" && (
            <div className="space-y-4">
              {chatHistory.length > 0 ? (
                <div className={cn("space-y-5 animate-in fade-in duration-500", chatThreadWidthClassName)}>
                  {chatHistory.map((msg) => {
                    const messageTime = formatChatMessageTime(msg.created_at);

                    if (msg.role === "user") {
                      return (
                        <div key={msg.id} className="flex w-full justify-end">
                          <div className="w-full max-w-[58rem] space-y-1">
                            <div className="flex items-center justify-end gap-2 px-1">
                              {messageTime ? (
                                <span className="text-[10px] font-medium text-[var(--genui-muted)]">
                                  {messageTime}
                                </span>
                              ) : null}
                              <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--genui-running)]">You</span>
                            </div>
                            <div className="ml-auto w-fit max-w-full rounded-2xl rounded-tr-md border border-[var(--genui-running)]/25 bg-[var(--genui-running)]/10 px-4 py-3 text-[14px] leading-relaxed text-[var(--genui-text)] shadow-sm">
                              {msg.content}
                            </div>
                          </div>
                        </div>
                      );
                    }

                    if (msg.role !== "assistant") {
                      return null;
                    }

                    const isFailedMessage = msg.content.trim() === ANALYSIS_FAILURE_MESSAGE;

                    return (
                      <div key={msg.id} className="flex w-full justify-start">
                        <AssistantReportMessage
                          className={assistantChatCardClassName}
                          variant={isFailedMessage ? "error" : "final"}
                          title="AI 답변"
                          timestamp={messageTime}
                          sections={[{ type: "paragraph", content: msg.content }]}
                          maxBodyHeight={400}
                        />
                      </div>
                    );
                  })}
                </div>
              ) : reportSections.length > 0 ? (
                <AssistantReportMessage
                  variant={hasFailedAnalysis ? "error" : "final"}
                  title={hasFailedAnalysis ? "Analysis Failed" : "Analysis 결과"}
                  subtitle={hasDatasetContext ? currentDatasetLabel : undefined}
                  sections={reportSections}
                  maxBodyHeight={600}
                  evidence={evidence}
                />
              ) : (
                <AssistantReportMessage
                  title="Analysis"
                  subtitle="아직 분석 결과가 없습니다."
                  sections={[{ type: "paragraph", content: "질문을 전송하면 Analysis 결과가 여기에 표시됩니다." }]}
                />
              )}
              {hasVisualizationPreview && latestVisualizationResult && (
                <CardShell>
                  <CardHeader title="시각화 결과" meta={visualizationPreviewMeta} />
                  <CardBody>
                    <VisualizationResultView visualization={latestVisualizationResult} showCaption={false} />
                  </CardBody>
                </CardShell>
              )}
            </div>
          )}

          {displayedCanvasView === "report" && (
            <div className="space-y-6">
              <div className="flex items-center gap-2 mb-2">
                <StatusBadge
                  status={state === "success" ? "success" : "ready"}
                />
                <span className="text-xs font-semibold text-[var(--genui-text)]">Analysis</span>
                <span className="text-sm text-[var(--genui-muted)]">최종 분석 결과 스냅샷</span>
              </div>
              {state === "success" && reportSections.length > 0 ? (
                <AssistantReportMessage
                  variant="final"
                  title="Analysis 결과"
                  subtitle={hasDatasetContext ? currentDatasetLabel : undefined}
                  sections={reportSections}
                  maxBodyHeight={600}
                  evidence={evidence}
                />
              ) : (
                <AssistantReportMessage
                  title="Analysis"
                  subtitle="아직 분석 결과가 생성되지 않았습니다."
                  sections={[{ type: "paragraph", content: "Analysis 완료 후 최종 분석 결과가 여기에 표시됩니다." }]}
                />
              )}
            </div>
          )}
        </div>
      )}

      {/* ── CURRENT VIEW: 기존 상태 기반 렌더링 ── */}
      {canvasView === "current" && displayedCanvasView === null && (
        <>
          {state === "ready" && (
            <div className="space-y-6 animate-in fade-in zoom-in-95 duration-300">
              {selectedPreEdaProfile ? (
                <PreEdaBoard
                  profile={selectedPreEdaProfile}
                  summarySections={preEdaSummarySections}
                  recommendationMode={selectedDataset?.recommendationMode ?? null}
                  recommendationWarning={selectedDataset?.preEdaWarning ?? null}
                  applyError={selectedPreEdaApplyError}
                  applyingOperationKey={selectedApplyingPreEdaOperationKey}
                  onApplyOperation={handleApplyRecommendedOperation}
                  onSelectDistributionColumn={loadSelectedPreEdaDistribution}
                  distributionLoadingColumn={selectedPreEdaDistributionLoadingColumn}
                  distributionError={selectedPreEdaDistributionError}
                />
              ) : preEdaUnavailableCard ? (
                preEdaUnavailableCard
              ) : (
                <AssistantReportMessage
                  className="max-w-none mx-0"
                  title="Pre-EDA Summary"
                  subtitle={hasDatasetContext ? currentDatasetLabel : "Select source"}
                  sections={preEdaSummarySections}
                  maxBodyHeight={420}
                />
              )}
            </div>
          )}

          {/* RUNNING */}
          {state === "running" && (
            <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
              <AssistantReportMessage
                variant="streaming"
                title={hasDatasetContext ? `Analyzing ${selectedDataset?.fileName || fileName || "Dataset"}` : "질문 처리 중"}
                subtitle={hasDatasetContext ? selectedDataset?.fileName || fileName : "AI가 답변을 생성하고 있습니다."}
                timestamp="Now"
                sections={reportSections}
                maxBodyHeight={300}
                evidence={evidence}
              />
              {lastRunningTool && (
                <div className="rounded-xl border border-[var(--genui-border)] bg-[var(--genui-panel)] px-4 py-3 shadow-sm">
                  <ToolCallIndicator status="running" label={lastRunningTool.name} sublabel="현재 질문 범위를 기준으로 계산 중입니다." />
                </div>
              )}
            </div>
          )}

          {/* NEEDS-USER */}
          {state === "needs-user" && (
            <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
              {pendingApproval && (
                <ApprovalCard
                  title={pendingApproval.title}
                  description={pendingApproval.summary}
                  changes={buildPendingApprovalChanges(pendingApproval)}
                  hideActions
                />
              )}

              <AssistantReportMessage
                variant="final"
                accentVariant="needs-user"
                title={pendingApproval?.title ?? "Plan review"}
                subtitle={
                  pendingApproval?.stage === "report"
                    ? "Waiting for analysis review"
                    : "Waiting for approval"
                }
                timestamp="Now"
                sections={reportSections}
                maxBodyHeight={300}
                evidence={evidence}
              />
            </div>
          )}

          {/* ERROR */}
          {state === "error" && (
            <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
              <AssistantReportMessage
                variant="error"
                title="Analysis Failed"
                sections={reportSections}
                evidence={evidence}
              />
            </div>
          )}

          {/* SUCCESS */}
          {state === "success" && chatHistory.length === 0 && (
            <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
              <AssistantReportMessage
                title="Analysis 결과"
                subtitle={hasDatasetContext ? currentDatasetLabel : undefined}
                sections={reportSections}
                maxBodyHeight={400}
                evidence={evidence}
              />
            </div>
          )}
        </>
      )}
    </div>
  );

  /* ── BOTTOM BAR ── */
  const BottomBar = (
    <WorkbenchCommandBar
      status={
        state === "empty"
          ? "empty"
          : state === "running"
            ? "streaming"
            : isPreEdaApplying
              ? "disabled"
              : "idle"
      }
      placeholder={
        state === "empty" ? "Upload a dataset or ask a question..." :
          isPreEdaApplying ? "선택한 전처리 작업을 적용하는 중입니다..." :
          state === "ready" ? "Pre-EDA를 확인한 뒤 질문을 이어서 입력하세요..." :
            state === "needs-user"
              ? pendingApproval?.stage === "report"
                ? "분석 결과 초안을 검토하고 승인 또는 수정 의견을 입력하세요..."
                : pendingApproval?.stage === "visualization"
                  ? "시각화 계획을 검토하고 승인 또는 수정 지시를 입력하세요..."
                  : "전처리 계획을 검토하거나 수정 지시를 입력하세요..."
              :
              state === "error" ? "Type to discuss the error..." :
                "Gen-UI에게 분석, 시각화, 변환 등을 요청하세요."
      }
      onSend={handleSendMessage}
      onStop={() => pipeline.handleCancel()}
      onUploadDataset={openFilePicker}
    />
  );

  /* ── GATE BAR ── */
  const GateBarComponent = state === "needs-user" ? (
    <GateBar
      onApprove={pipeline.handleApprove}
      onCancel={pipeline.handleReject}
      onSubmitChange={pipeline.handleEditInstruction}
      approveLabel={pendingApproval?.stage === "report" ? "Approve Analysis" : undefined}
      cancelLabel={pendingApproval?.stage === "report" ? "Cancel Analysis" : undefined}
      changeLabel={pendingApproval?.stage === "report" ? "Request Analysis Revision..." : undefined}
      changePlaceholder={
        pendingApproval?.stage === "report"
          ? "What should change in the analysis draft?"
          : pendingApproval?.stage === "visualization"
          ? "What should change? (e.g., 'Use bar chart by region')"
          : "What should change? (e.g., 'Use median imputation')"
      }
    />
  ) : null;

  /* ── HEADER ── */
  const Header = (
    <div className="h-full flex items-center justify-between gap-4 px-4 w-full min-w-0">
      <div className="min-w-0">
        <div className="flex items-center gap-3 min-w-0">
          <span className="truncate text-[15px] font-semibold tracking-tight text-[var(--genui-text)]">
            {sessionDisplayTitle}
          </span>
          <StatusBadge
            status={state}
            labelOverride={state === "success" ? "Complete" : undefined}
            className="shrink-0"
          />
        </div>
      </div>
    </div>
  );

  /* ── PIPELINE BAR ── */
  const subPhaseLabel: Record<string, string> = {
    intake: "질문 확인",
    preprocessing: "데이터 준비",
    rag: "참고 정보 확인",
    visualization: "시각화",
    report: "분석 결과",
  };

  const pipelineBarVariant: PipelineBarVariant =
    !hasDatasetContext ? "hidden" :
      state === "uploading" ? "ingest" :
        state === "running" ? "running" :
          state === "needs-user" ? "needs-user" :
            state === "error" ? "failed" :
              state === "success" ? "completed" :
                "hidden";

  const pipelineMessage =
    state === "uploading"
      ? uploadProgress < 30 ? "Uploading file…"
        : uploadProgress < 70 ? "Parsing schema…"
          : "Validating dataset…"
      : state === "running" ? `${subPhaseLabel[runningSubPhase] ?? runningSubPhase} 진행 중…`
        : state === "needs-user"
          ? pendingApproval?.stage === "report"
            ? "Analysis draft review"
            : pendingApproval?.stage === "visualization"
            ? "Visualization plan review"
            : "Preprocess plan review"
          : state === "error" ? "Failed — see details"
            : undefined;

  const completedToolCount = toolCalls.filter((tc) => tc.status === "completed").length;
  const totalStages = 6;

  const PipelineBarNode = (
    <PipelineBar
      variant={pipelineBarVariant}
      stage={
        state === "uploading" ? "Ingest" :
          state === "running" ? (subPhaseLabel[runningSubPhase] ?? runningSubPhase) :
            state === "needs-user"
              ? pendingApproval?.stage === "report"
                ? "Analysis"
                : pendingApproval?.stage === "visualization"
                ? "Visualization"
                : "Preprocess"
            :
              state === "error" ? "Error" :
                undefined
      }
      message={pipelineMessage}
      stepFraction={
        state === "running" || state === "needs-user"
          ? `${completedToolCount}/${totalStages}`
          : undefined
      }
      elapsed={
        (state === "running" || state === "needs-user")
          ? formatElapsed(elapsedSeconds)
          : undefined
      }
      percent={state === "uploading" ? uploadProgress : undefined}
    />
  );

  return (
    <WorkbenchLayout
      header={Header}
      leftPanel={LeftPanel}
      mainContent={MainContent}
      contentScrollRef={canvasScrollRef}
      centerSubHeader={CenterSubHeader}
      bottomBar={BottomBar}
      gateBar={GateBarComponent}
      pipelineBar={PipelineBarNode}
    />
  );
}
