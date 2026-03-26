import React, { useState, useRef, useCallback, useEffect } from "react";
import { ToolCallIndicator } from "../components/genui/ToolCallIndicator";
import { WorkbenchCommandBar } from "../components/genui/WorkbenchCommandBar";
import { Dropzone } from "../components/genui/Dropzone";
import { WorkbenchLayout } from "../components/genui/WorkbenchLayout";
import { StatusBadge } from "../components/genui/StatusBadge";
import { GateBar } from "../components/genui/GateBar";
import { AssistantReportMessage } from "../components/genui/AssistantReportMessage";
import { RightPanelTabs, type RightTabId } from "../components/genui/RightPanelTabs";
import { CopilotPanel } from "../components/genui/CopilotPanel";
import { MCPPanel } from "../components/genui/MCPPanel";
import { DecisionChips } from "../components/genui/DecisionChips";
import { ApprovalCard } from "../components/genui/ApprovalCard";
import { CardShell, CardHeader, CardBody } from "../components/genui/CardShell";
import { PreEdaBoard } from "../components/genui/PreEdaBoard";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  MessageSquare,
  Plus,
  Trash2,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { PipelineBar, type PipelineBarVariant } from "../components/genui/PipelineBar";
import { useAnalysisPipeline, type PipelineSessionContext } from "../hooks/useAnalysisPipeline";
import { useWorkbenchSessionStore } from "../hooks/useWorkbenchSessionStore";
import {
  deleteChatSession,
  fetchPendingApproval,
  getChatHistory,
  isApiErrorStatus,
  type PendingApprovalPayload,
} from "../../lib/api";
import { toast } from "sonner";

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
      "리포트 초안을 검토한 뒤 승인 또는 수정 요청",
      typeof pendingApproval.review?.revision_count === "number"
        ? `현재 revision count: ${pendingApproval.review.revision_count}`
        : "리포트 수정 횟수 정보 없음",
      "승인 후 최종 report 흐름을 마무리",
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
    runStatus,
    pipelineSteps,
    decisionChips,
    evidence,
    pendingApproval,
    rawLogs,
    latestVisualizationResult,
    selectedPreEdaProfile,
    chatHistory,
    fileName,
    uploadedDatasets,
    selectedSourceId,
    selectUploadedDataset,
    removeUploadedDataset,
    sessionId,
    handleSend,
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
  } = useWorkbenchSessionStore();

  const activeSession = sessions.find((item) => item.id === activeSessionId) ?? null;
  const hasDatasetContext = Boolean(selectedSourceId);
  const hasUploadedDatasets = uploadedDatasets.length > 0;
  const selectedDataset =
    uploadedDatasets.find((item) => item.sourceId === selectedSourceId) ?? null;

  // UI-only local state
  const [highlightDetails, setHighlightDetails] = useState(false);
  const [rightTab, setRightTab] = useState<RightTabId>("details");
  const [copilotHasNew, setCopilotHasNew] = useState(false);
  const detailsPanelRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const initializedRef = useRef(false);

  // Show NEW dot on Agent tab when tool calls arrive
  useEffect(() => {
    if ((state === "running" || state === "needs-user" || state === "error") && rightTab !== "agent") {
      setCopilotHasNew(true);
    }
  }, [state, rightTab]);

  const formatElapsed = (s: number) => {
    const m = Math.floor(s / 60).toString().padStart(2, "0");
    const sec = (s % 60).toString().padStart(2, "0");
    return `${m}:${sec}`;
  };

  const handleTabChange = (tab: RightTabId) => {
    setRightTab(tab);
    if (tab === "agent") setCopilotHasNew(false);
  };

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

  const restoreSessionById = useCallback(
    async (targetSessionId: string) => {
      const targetSession = sessions.find((item) => item.id === targetSessionId);
      if (!targetSession) {
        return;
      }

      let nextContext: PipelineSessionContext = targetSession.context;

      if (targetSession.backendSessionId !== null) {
        try {
          const history = await getChatHistory(targetSession.backendSessionId);
          const msgs = history.messages ?? [];
          const latestAssistant = [...msgs]
            .reverse()
            .find((message) => message.role === "assistant");
          let restoredPendingApproval = nextContext.pendingApproval;
          let stateHint = nextContext.stateHint;

          if (nextContext.stateHint === "needs-user" && nextContext.runId) {
            try {
              const pending = await fetchPendingApproval(
                targetSession.backendSessionId,
                nextContext.runId,
              );
              restoredPendingApproval = pending.pending_approval;
              stateHint = "needs-user";
            } catch {
              restoredPendingApproval = null;
              stateHint = msgs.length > 0
                ? "success"
                : nextContext.uploadedDatasets.length > 0
                  ? "ready"
                  : "empty";
            }
          } else if (msgs.length > 0) {
            stateHint = "success";
          }

          nextContext = {
            ...nextContext,
            backendSessionId: targetSession.backendSessionId,
            chatHistory: msgs,
            latestAssistantAnswer: latestAssistant?.content ?? nextContext.latestAssistantAnswer,
            pendingApproval: restoredPendingApproval,
            stateHint,
            errorMessage: nextContext.stateHint === "error" ? nextContext.errorMessage : null,
          };

          updateSession(targetSessionId, {
            backendSessionId: targetSession.backendSessionId,
            context: nextContext,
          });
        } catch (error) {
          if (isApiErrorStatus(error, 404)) {
            nextContext = {
              ...nextContext,
              backendSessionId: null,
            };
            updateSession(targetSessionId, {
              backendSessionId: null,
              context: nextContext,
            });
          } else {
            toast.error("세션 히스토리를 불러오지 못했습니다.");
          }
        }
      }

      restoreSessionContext(nextContext);
    },
    [sessions, updateSession, restoreSessionContext],
  );

  const handleNewChat = useCallback(() => {
    saveSessionSnapshot(activeSessionId);
    createSession();
    clearForNewDraft();
  }, [activeSessionId, saveSessionSnapshot, createSession, clearForNewDraft]);

  const handleSessionSelect = useCallback(
    async (targetSessionId: string) => {
      if (targetSessionId === activeSessionId) {
        return;
      }
      saveSessionSnapshot(activeSessionId);
      selectSession(targetSessionId);
      await restoreSessionById(targetSessionId);
    },
    [activeSessionId, saveSessionSnapshot, selectSession, restoreSessionById],
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
        clearForNewDraft();
        return;
      }

      const fallbackSession = remaining[0];
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
    ],
  );

  const handleSendMessage = useCallback(
    (value: string) => {
      const question = value.trim();
      if (!question) {
        return;
      }

      if (activeSessionId) {
        const currentSession = sessions.find((item) => item.id === activeSessionId);
        if (currentSession && currentSession.title === "새 채팅") {
          const title = question.length > 30 ? `${question.slice(0, 30)}...` : question;
          updateSession(activeSessionId, { title });
        }
      }

      handleSend(value);
    },
    [activeSessionId, sessions, updateSession, handleSend],
  );

  useEffect(() => {
    if (initializedRef.current) {
      return;
    }
    if (sessions.length === 0) {
      clearForNewDraft();
      initializedRef.current = true;
      return;
    }

    const initialSessionId = activeSessionId ?? sessions[0]?.id ?? null;
    if (!initialSessionId) {
      return;
    }
    if (!activeSessionId) {
      selectSession(initialSessionId);
    }
    void restoreSessionById(initialSessionId);
    initializedRef.current = true;
  }, [sessions, activeSessionId, clearForNewDraft, selectSession, restoreSessionById]);

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

  const focusDetails = useCallback(() => {
    setHighlightDetails(true);
    setRightTab("details");
    detailsPanelRef.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
    setTimeout(() => setHighlightDetails(false), 1100);
  }, []);

  /** Open file picker for real file selection */
  const openFilePicker = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileSelected = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) pipeline.startUpload(file);
      // Reset so the same file can be re-selected
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [pipeline],
  );

  /** Handle Dropzone onDrop — if FileList is empty (button click), open picker */
  const handleDrop = useCallback(
    (files: FileList) => {
      const file = files[0]; // noUncheckedIndexedAccess: may be undefined
      if (file) {
        pipeline.startUpload(file);
      } else {
        openFilePicker();
      }
    },
    [pipeline, openFilePicker],
  );

  const formatSessionUpdatedAt = (value: string) => {
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

  const handleDeleteSelectedDataset = useCallback(() => {
    if (!selectedSourceId) {
      return;
    }
    void removeUploadedDataset(selectedSourceId);
  }, [selectedSourceId, removeUploadedDataset]);

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

  const derivedRouteChips = hasUploadedDatasets
    ? [
        {
          stage: "Pre-EDA",
          value: "DONE" as const,
          tooltip: "업로드 직후 데이터 미리보기와 구조/품질 요약을 먼저 확인합니다.",
        },
        {
          stage: "Deep EDA",
          value:
            state === "ready"
              ? "QUEUED" as const
              : state === "running"
                ? runningSubPhase === "report"
                  ? "DONE" as const
                  : "RUNNING" as const
                : state === "needs-user"
                  ? "BLOCKED" as const
                  : state === "error"
                    ? "FAILED" as const
                    : state === "success"
                      ? "DONE" as const
                      : "QUEUED" as const,
          tooltip: "사용자 질문 이후 분포, 상관관계, 이상치 탐지로 확장됩니다.",
        },
        {
          stage: "Report",
          value:
            state === "success"
              ? "DONE" as const
              : state === "running" && runningSubPhase === "report"
                ? "RUNNING" as const
                : state === "error" && runningSubPhase === "report"
                  ? "FAILED" as const
                  : "QUEUED" as const,
          tooltip: "Deep EDA가 끝나면 최종 요약과 후속 리포트 흐름을 남깁니다.",
        },
      ]
    : [];

  const preEdaSummarySections = [
    { type: "heading" as const, content: "AI 분석 요약" },
    {
      type: "paragraph" as const,
      content:
        selectedPreEdaProfile?.qualitySummary
          ?? (hasDatasetContext
            ? `${currentDatasetLabel}이(가) 현재 source로 선택되어 있습니다. 질문 전에 구조와 품질 맥락을 먼저 확인하고, 이후 질문이 들어오면 Deep EDA와 report로 이어집니다.`
            : "데이터 업로드는 완료됐지만 아직 source가 선택되지 않았습니다. 상단에서 source를 고르면 해당 데이터 기준으로 질문을 이어갈 수 있습니다."),
    },
    {
      type: "checklist" as const,
      items:
        selectedPreEdaProfile?.summaryBullets ?? [
          "상위 5개 row 미리보기와 데이터 개요 요약을 먼저 확인합니다.",
          "컬럼 타입 분류와 결측치 분석은 Details 패널에서 drill-down 됩니다.",
          "질문 이후에는 Deep EDA와 report 흐름으로 이어집니다.",
        ],
    },
  ];

  const headerSubtitle =
    state === "empty"
      ? "데이터 업로드 또는 일반 질문으로 새 세션을 시작할 수 있습니다."
      : state === "uploading"
        ? `${fileName || "dataset"} 업로드와 검증이 진행 중입니다.`
        : state === "ready"
          ? hasDatasetContext
            ? `${currentDatasetLabel} 기준 Pre-EDA 레이아웃이 준비되었습니다.`
            : "업로드는 완료됐지만 아직 source가 선택되지 않았습니다."
          : state === "running"
            ? `${currentDatasetLabel} 질문을 바탕으로 Deep EDA를 진행 중입니다.`
            : state === "needs-user"
              ? "전처리 필요성이 감지되어 HITL 승인 대기 상태입니다."
              : state === "error"
                ? "실패 원인과 복구 맥락을 우측 패널과 중앙 카드에서 함께 확인합니다."
                : hasDatasetContext
                  ? `${currentDatasetLabel} 기준 Deep EDA 결과와 report가 누적되고 있습니다.`
                  : "일반 질문 결과가 준비되었습니다.";

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
            {activeSession?.title || "새 채팅"}
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
                      {formatSessionUpdatedAt(session.updatedAt)}
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
      <div className="border-t border-[var(--genui-border)] px-3 py-3 bg-[var(--genui-surface)]">
        <p className="text-[10px] leading-relaxed text-[var(--genui-muted)]">
          세션 전환과 삭제는 여기서만 처리하고, 실제 분석 흐름과 승인 결정은 중앙 캔버스에서 진행합니다.
        </p>
      </div>
    </>
  );

  /* ── CENTER: Decision chips → centerSubHeader ── */
  const CenterSubHeader = (
    <div className="grid w-full min-w-0 items-center gap-3 xl:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
      {hasUploadedDatasets ? (
        <div className="flex min-w-0 items-center gap-2 overflow-hidden">
          <span className="text-[11px] font-medium text-[var(--genui-muted)] whitespace-nowrap">데이터 소스</span>
          <select
            value={selectedSourceId ?? ""}
            onChange={(e) => selectUploadedDataset(e.target.value || null)}
            className="h-7 w-[220px] max-w-full flex-shrink-0 rounded-md border border-[var(--genui-border)] bg-[var(--genui-surface)] px-2 text-xs text-[var(--genui-text)] focus:outline-none focus:ring-1 focus:ring-[var(--genui-focus-ring)] truncate"
          >
            <option value="">선택 안 함 (일반 질문)</option>
            {uploadedDatasets.map((dataset) => (
              <option key={dataset.sourceId} value={dataset.sourceId}>
                {dataset.fileName}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleDeleteSelectedDataset}
            disabled={!selectedSourceId}
            className="h-7 px-2 rounded-md border border-[var(--genui-border)] bg-[var(--genui-panel)] text-xs text-[var(--genui-text)] inline-flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--genui-surface)] whitespace-nowrap flex-shrink-0"
          >
            <Trash2 className="w-3.5 h-3.5" />
            삭제
          </button>
        </div>
      ) : (
        <span className="text-xs text-[var(--genui-muted)] whitespace-nowrap">
          업로드가 완료되면 선택된 source와 route 상태가 여기에 표시됩니다.
        </span>
      )}

      {derivedRouteChips.length > 0 ? (
        <div className="justify-self-start xl:justify-self-center">
          <DecisionChips
            className="flex-wrap"
            chips={derivedRouteChips.map((c) => ({
              ...c,
              onNavigate:
                c.value === "BLOCKED" || c.value === "FAILED"
                  ? focusDetails
                  : c.stage === "Mode"
                    ? undefined
                    : () => handleTabChange("agent"),
            }))}
          />
        </div>
      ) : (
        <div />
      )}

      <div className="hidden xl:block" />
    </div>
  );

  /* ── Evidence with nav callbacks ── */
  const evidenceWithNav = {
    ...evidence,
    onDataNavigate: focusDetails,
    onScopeNavigate: focusDetails,
    onComputeNavigate: () => handleTabChange("agent"),
    onRagNavigate: () => handleTabChange("agent"),
  };

  const MainContent = (
    <div
      className={cn(
        "mx-auto w-full space-y-4 pb-28 pt-4 px-2 xl:px-3",
        state === "empty" || state === "uploading"
          ? "max-w-3xl"
          : state === "ready"
            ? "max-w-[1360px] 2xl:max-w-[1460px]"
            : "max-w-[1120px]",
      )}
    >
      {/* Hidden file input for real file selection */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.json,.xlsx,.xls"
        className="hidden"
        onChange={handleFileSelected}
      />

      {state !== "empty" && state !== "uploading" && (
        <div className="flex justify-center">
          <div className="max-w-[480px] truncate rounded-full border border-[var(--genui-border)] bg-[var(--genui-panel)] px-6 py-3 text-sm font-semibold text-[var(--genui-text)] shadow-[0_10px_30px_rgba(15,23,42,0.12)]">
            {sessionDisplayTitle}
          </div>
        </div>
      )}

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

      {/* ── CHAT HISTORY (Past Turns) ── */}
      {chatHistory.length > 0 && (
        <div className="space-y-6 mb-8 w-full max-w-3xl animate-in fade-in duration-500">
          {chatHistory.map((msg) => {
            if (msg.role === "user") {
              return (
                <div key={msg.id} className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl bg-[var(--genui-surface)] text-[var(--genui-text)] px-4 py-2.5 text-[13px] leading-relaxed border border-[var(--genui-border)] shadow-[0_2px_12px_rgba(0,0,0,0.06)] dark:shadow-[0_2px_12px_rgba(0,0,0,0.4)] relative">
                    {msg.content}
                    <div className="absolute top-1/2 -right-1.5 -translate-y-1/2 w-3 h-3 bg-[var(--genui-surface)] border-r border-b border-[var(--genui-border)] transform rotate-45 rounded-sm z-[-1]" />
                  </div>
                </div>
              );
            }
            return (
              <div key={msg.id} className="flex justify-start">
                <AssistantReportMessage
                  variant="final"
                  title="AI 답변"
                  timestamp={
                    msg.created_at
                      ? new Date(msg.created_at + "Z").toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                      : undefined
                  }
                  sections={[{ type: "paragraph", content: msg.content }]}
                  maxBodyHeight={400}
                />
              </div>
            );
          })}
        </div>
      )}

      {state === "ready" && (
        <div className="space-y-6 animate-in fade-in zoom-in-95 duration-300">
          {selectedPreEdaProfile ? (
            <PreEdaBoard
              profile={selectedPreEdaProfile}
              summarySections={preEdaSummarySections}
            />
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
            evidence={evidenceWithNav}
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
                ? "Waiting for report review"
                : "Waiting for approval"
            }
            timestamp="Now"
            sections={reportSections}
            maxBodyHeight={300}
            evidence={evidenceWithNav}
          />

          <div className="rounded-xl border border-[var(--genui-needs-user)]/30 bg-[var(--genui-needs-user)]/5 px-4 py-3">
            <ToolCallIndicator
              status="needs-user"
              label={
                pendingApproval?.stage === "report"
                  ? "report review"
                  : pendingApproval?.stage === "visualization"
                    ? "visualization review"
                    : "preprocess approval"
              }
              sublabel="결정은 중앙 승인 카드와 하단 GateBar에서만 처리됩니다."
            />
          </div>
        </div>
      )}

      {/* ERROR */}
      {state === "error" && (
        <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
          <AssistantReportMessage
            variant="error"
            title="Analysis Failed"
            sections={reportSections}
            onReviewDetails={focusDetails}
            evidence={evidenceWithNav}
          />
        </div>
      )}

      {/* SUCCESS */}
      {state === "success" && chatHistory.length === 0 && (
        <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
          <AssistantReportMessage
            title="AI 답변"
            subtitle={hasDatasetContext ? currentDatasetLabel : undefined}
            sections={reportSections}
            maxBodyHeight={400}
            evidence={evidenceWithNav}
          />
        </div>
      )}
    </div>
  );

  /* ── BOTTOM BAR ── */
  const BottomBar = (
    <WorkbenchCommandBar
      status={state === "empty" ? "empty" : state === "running" ? "streaming" : "idle"}
      placeholder={
        state === "empty" ? "Upload a dataset or ask a question..." :
          state === "ready" ? "Pre-EDA를 확인한 뒤 질문을 이어서 입력하세요..." :
            state === "needs-user"
              ? pendingApproval?.stage === "report"
                ? "리포트 초안을 검토하고 승인 또는 수정 의견을 입력하세요..."
                : pendingApproval?.stage === "visualization"
                  ? "시각화 계획을 검토하고 승인 또는 수정 지시를 입력하세요..."
                  : "전처리 계획을 검토하거나 수정 지시를 입력하세요..."
              :
              state === "error" ? "Type to discuss the error..." :
                "Ask Gen-UI to analyze, visualize, or transform..."
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
      approveLabel={pendingApproval?.stage === "report" ? "Approve Report" : undefined}
      cancelLabel={pendingApproval?.stage === "report" ? "Cancel Report" : undefined}
      changeLabel={pendingApproval?.stage === "report" ? "Request Report Revision..." : undefined}
      changePlaceholder={
        pendingApproval?.stage === "report"
          ? "What should change in the report draft?"
          : pendingApproval?.stage === "visualization"
          ? "What should change? (e.g., 'Use bar chart by region')"
          : "What should change? (e.g., 'Use median imputation')"
      }
    />
  ) : null;

  /* ── RIGHT PANEL with TABS ── */
  const RightPanel = (
    <RightPanelTabs
      activeTab={rightTab}
      onTabChange={handleTabChange}
      agentHasNew={copilotHasNew}
      detailsContent={
        <div ref={detailsPanelRef} className="h-full overflow-y-auto p-4 space-y-4">
          {highlightDetails && (
            <div className="mx-4 mt-3 mb-0 px-3 py-2 rounded-lg border border-[var(--genui-error)]/40 bg-[var(--genui-error)]/5 flex items-center gap-2 animate-in fade-in duration-200">
              <span className="text-[10px] font-semibold text-[var(--genui-error)] animate-pulse">
                ↓ Resolution Required
              </span>
            </div>
          )}
          {state === "empty" && (
            <>
              <CardShell>
                <CardHeader title="업로드 규칙" meta="Details" statusLabel="CSV · JSON · XLSX" statusVariant="neutral" />
                <CardBody className="space-y-2 text-sm text-[var(--genui-text)]">
                  <p>파일당 최대 200MB까지 업로드할 수 있습니다.</p>
                  <p>업로드 후에는 선택된 source와 Pre-EDA 맥락이 중앙과 이 패널에 함께 표시됩니다.</p>
                </CardBody>
              </CardShell>
              <CardShell>
                <CardHeader title="질문 흐름" meta="Before dataset" statusLabel="Optional" statusVariant="neutral" />
                <CardBody className="space-y-2 text-sm text-[var(--genui-text)]">
                  <p>데이터 없이도 일반 질문은 가능하지만, Pre-EDA와 Deep EDA 흐름은 업로드 후에만 활성화됩니다.</p>
                </CardBody>
              </CardShell>
            </>
          )}

          {state === "ready" && (
            <>
              <CardShell>
                <CardHeader
                  title="컬럼 타입 분해"
                  meta="DETAILS"
                  statusLabel={`${selectedPreEdaProfile?.columnCount ?? 0} Columns`}
                  statusVariant="neutral"
                />
                <CardBody className="space-y-3">
                  {selectedPreEdaProfile ? (
                    <>
                      {[
                        {
                          label: `numeric ${selectedPreEdaProfile.numericColumns.length}개`,
                          detail: "기본 통계 / 상관관계 / 이상치 대상",
                        },
                        {
                          label: `categorical ${selectedPreEdaProfile.categoricalColumns.length}개`,
                          detail: "빈도 분석 / bar chart 대상",
                        },
                        {
                          label: `boolean ${selectedPreEdaProfile.booleanColumns.length}개`,
                          detail: "categorical로 간주하여 빈도 분석 포함",
                        },
                        {
                          label: `datetime ${selectedPreEdaProfile.datetimeColumns.length}개`,
                          detail: "시계열 흐름 / key 후보",
                        },
                        {
                          label: `group key ${selectedPreEdaProfile.groupKeyColumns.length}개`,
                          detail: "그룹별 비교 기준 컬럼",
                        },
                        {
                          label: `identifier ${selectedPreEdaProfile.identifierColumns.length}개`,
                          detail: "미리보기 전용 / 통계·상관관계 제외",
                        },
                      ].map((item) => (
                        <div key={item.label} className="rounded-xl border border-[var(--genui-border)] bg-[var(--genui-surface)] px-4 py-3">
                          <p className="text-sm font-medium text-[var(--genui-text)]">{item.label}</p>
                          <p className="mt-1 text-xs text-[var(--genui-muted)]">{item.detail}</p>
                        </div>
                      ))}
                    </>
                  ) : (
                    <p className="text-sm text-[var(--genui-text)]">선택된 source의 Pre-EDA 정보가 아직 없습니다.</p>
                  )}
                </CardBody>
              </CardShell>

              <CardShell>
                <CardHeader
                  title="선택 source 메타데이터"
                  meta="SOURCE"
                  statusLabel={selectedDataset?.sourceId ?? "-"}
                  statusVariant="neutral"
                />
                <CardBody className="space-y-3 text-sm text-[var(--genui-text)]">
                  <div className="space-y-2">
                    <p>업로드 시각: {formatUploadedAt(selectedDataset?.uploadedAt)}</p>
                    <p>source_id: {selectedDataset?.sourceId ?? "-"}</p>
                    <p>
                      group key 후보: {selectedPreEdaProfile?.groupKeyColumns.length
                        ? selectedPreEdaProfile.groupKeyColumns.join(", ")
                        : "없음"}
                    </p>
                  </div>
                </CardBody>
              </CardShell>
            </>
          )}

          {state === "running" && (
            <>
              <CardShell>
                <CardHeader title="현재 질문 범위" meta="Details" statusLabel="Running" statusVariant="running" />
                <CardBody className="space-y-2 text-sm text-[var(--genui-text)]">
                  <p>{selectedDataset ? `${selectedDataset.fileName} 기준으로 질문이 실행 중입니다.` : "선택된 데이터 source 기준으로 질문이 실행 중입니다."}</p>
                  <p className="text-xs text-[var(--genui-muted)]">현재 단계: {runningSubPhase === "report" ? "report" : "Deep EDA"}</p>
                </CardBody>
              </CardShell>
              <CardShell>
                <CardHeader title="도착 예정 결과" meta="Artifacts" statusLabel="Pending" statusVariant="neutral" />
                <CardBody className="space-y-2 text-sm text-[var(--genui-text)]">
                  <p>분포 시각화, 상관관계, 이상치 결과와 최종 report가 질문 맥락에 맞춰 순차적으로 도착합니다.</p>
                </CardBody>
              </CardShell>
            </>
          )}

          {state === "needs-user" && (
            <>
              <CardShell>
                <CardHeader title="왜 멈췄나" meta="Before / After" statusLabel="Needs Approval" statusVariant="needs-user" />
                <CardBody className="space-y-2 text-sm text-[var(--genui-text)]">
                  <p>
                    {pendingApproval?.stage === "report"
                      ? "리포트 초안 검토와 승인 여부 확인이 필요해 현재 단계에서 멈췄습니다."
                      : pendingApproval?.stage === "visualization"
                        ? "시각화 계획 검토와 승인 여부 확인이 필요해 현재 단계에서 멈췄습니다."
                        : "전처리 계획에 대한 사용자 확인이 필요해 현재 단계에서 멈췄습니다."}
                  </p>
                  <p className="text-xs text-[var(--genui-muted)]">승인/거절/수정은 중앙 승인 카드와 GateBar에서만 처리합니다.</p>
                </CardBody>
              </CardShell>
            </>
          )}

          {state === "success" && (
            <>
              <CardShell>
                <CardHeader title="최종 결과 보강" meta="Details" statusLabel="Complete" statusVariant="success" />
                <CardBody className="space-y-2 text-sm text-[var(--genui-text)]">
                  <p>질문 결과와 함께 생성된 Deep EDA 결과와 report 아티팩트는 이후 후속 질문에서도 계속 누적됩니다.</p>
                  {latestVisualizationResult?.summary ? (
                    <p className="text-xs text-[var(--genui-muted)]">{latestVisualizationResult.summary}</p>
                  ) : null}
                </CardBody>
              </CardShell>
            </>
          )}

          {state === "error" && (
            <>
              <CardShell status="error">
                <CardHeader title="실패 요약" meta="Details" statusLabel="Error" statusVariant="error" />
                <CardBody className="space-y-2 text-sm text-[var(--genui-text)]">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-[var(--genui-error)] mt-0.5" />
                    <p>실패한 툴과 원인 요약을 먼저 확인한 뒤, 우측 Agent 또는 중앙 입력창에서 다음 복구 질문을 이어갈 수 있습니다.</p>
                  </div>
                </CardBody>
              </CardShell>
            </>
          )}
        </div>
      }
      toolsContent={
        <CopilotPanel
          runStatus={runStatus}
          toolCalls={toolCalls}
          pipelineSteps={pipelineSteps}
          awaitingInfo={
            state === "needs-user" && pendingApproval
              ? {
                title: pendingApproval.title,
                description: pendingApproval.summary,
                onViewDetails: focusDetails,
              }
              : undefined
          }
        />
      }
      mcpContent={<MCPPanel rawLogs={rawLogs.length > 0 ? rawLogs : undefined} />}
    />
  );

  /* ── HEADER ── */
  const Header = (
    <div className="h-full flex items-center justify-between gap-4 px-4 w-full min-w-0">
      <div className="min-w-0">
        <div className="flex items-center gap-3 min-w-0">
          <span className="truncate text-[15px] font-semibold tracking-tight text-[var(--genui-text)]">
            {sessionDisplayTitle}
          </span>
          <StatusBadge status={state} className="shrink-0" />
        </div>
        <p className="mt-0.5 truncate text-[11px] text-[var(--genui-muted)]">
          {headerSubtitle}
        </p>
      </div>
      {hasDatasetContext && (
        <div className="hidden xl:flex items-center gap-2 rounded-full border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3 py-1.5 text-[11px] text-[var(--genui-muted)]">
          <span className="font-medium text-[var(--genui-text)] truncate max-w-[220px]">{currentDatasetLabel}</span>
        </div>
      )}
    </div>
  );

  /* ── PIPELINE BAR ── */
  const subPhaseLabel: Record<string, string> = {
    intake: "Intake",
    preprocessing: "Preprocess",
    rag: "RAG",
    visualization: "Visualization",
    report: "Report",
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
            ? "Report draft review"
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
                ? "Report"
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
      onViewDetails={
        state === "running"
          ? () => handleTabChange("agent")
          : state === "needs-user"
            ? focusDetails
          : state === "error"
            ? focusDetails
            : undefined
      }
    />
  );

  return (
    <WorkbenchLayout
      header={Header}
      leftPanel={LeftPanel}
      mainContent={MainContent}
      rightPanel={RightPanel}
      centerSubHeader={CenterSubHeader}
      bottomBar={BottomBar}
      gateBar={GateBarComponent}
      pipelineBar={PipelineBarNode}
    />
  );
}
