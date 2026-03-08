import React, { useState, useRef, useCallback, useEffect } from "react";
import { TimelineItem } from "../components/genui/TimelineItem";
import { ToolCallIndicator } from "../components/genui/ToolCallIndicator";
import { WorkbenchCommandBar } from "../components/genui/WorkbenchCommandBar";
import { Dropzone } from "../components/genui/Dropzone";
import { WorkbenchLayout } from "../components/genui/WorkbenchLayout";
import { StatusBadge } from "../components/genui/StatusBadge";
import { DetailsPanel } from "../components/genui/DetailsPanel";
import { GateBar } from "../components/genui/GateBar";
import { AssistantReportMessage } from "../components/genui/AssistantReportMessage";
import { RightPanelTabs, type RightTabId } from "../components/genui/RightPanelTabs";
import { CopilotPanel } from "../components/genui/CopilotPanel";
import { MCPPanel } from "../components/genui/MCPPanel";
import { DecisionChips } from "../components/genui/DecisionChips";
import { Sparkles, FileText, CheckCircle2, Plus, Trash2, MessageSquare } from "lucide-react";
import { cn } from "../../lib/utils";
import { PipelineBar, type PipelineBarVariant } from "../components/genui/PipelineBar";
import { useAnalysisPipeline, type PipelineSessionContext } from "../hooks/useAnalysisPipeline";
import { useWorkbenchSessionStore } from "../hooks/useWorkbenchSessionStore";
import { deleteChatSession, fetchPendingApproval, getChatHistory } from "../../lib/api";
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
    milestones,
    history,
    pendingApproval,
    rawLogs,
    latestVisualizationResult,
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

  const handleDetailsAction = (action: string) => {
    if (action === "try-sample") pipeline.startWithSample();
    if (action === "cancel-upload") pipeline.handleCancel();
    if (action === "resolve-retry") pipeline.handleRetry();
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
        } catch {
          toast.error("세션 히스토리를 불러오지 못했습니다.");
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
        } catch {
          toast.error("서버 세션 삭제에 실패했습니다.");
          return;
        }
      }

      const wasActive = targetSessionId === activeSessionId;
      const remaining = sessions.filter((item) => item.id !== targetSessionId);
      deleteSessionFromStore(targetSessionId);

      if (!wasActive) {
        return;
      }

      if (remaining.length === 0) {
        createSession();
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
      createSession,
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
      createSession();
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
  }, [sessions, activeSessionId, createSession, clearForNewDraft, selectSession, restoreSessionById]);

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

  const handleDeleteSelectedDataset = useCallback(() => {
    if (!selectedSourceId) {
      return;
    }
    void removeUploadedDataset(selectedSourceId);
  }, [selectedSourceId, removeUploadedDataset]);

  // Current running tool call for inline indicator
  const currentRunningTool = toolCalls.filter((tc) => tc.status === "running");
  const lastRunningTool = currentRunningTool[currentRunningTool.length - 1];

  /* ── LEFT PANEL — Session + History ── */
  const LeftPanel = (
    <>
      <div className="h-10 border-b border-[var(--genui-border)] flex items-center px-4 gap-2 flex-shrink-0">
        <MessageSquare className="w-3.5 h-3.5 text-[var(--genui-running)]" />
        <span className="font-semibold text-sm text-[var(--genui-text)]">Session</span>
      </div>
      <div className="p-2 border-b border-[var(--genui-border)] space-y-2">
        <button
          type="button"
          onClick={handleNewChat}
          className="w-full h-8 rounded-md border border-[var(--genui-border)] bg-[var(--genui-panel)] text-[12px] font-medium text-[var(--genui-text)] inline-flex items-center justify-center gap-1.5 hover:bg-[var(--genui-surface)] transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          새 채팅
        </button>
        <div className="max-h-44 overflow-y-auto space-y-1">
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
      <div className="h-10 border-b border-[var(--genui-border)] flex items-center px-4 gap-2 flex-shrink-0">
        <Sparkles className="w-3.5 h-3.5 text-[var(--genui-running)]" />
        <span className="font-semibold text-sm text-[var(--genui-text)]">History</span>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {state === "empty" && (
          <div className="px-4 py-8 text-center opacity-50">
            <div className="w-full h-2 bg-[var(--genui-surface)] rounded mb-2" />
            <div className="w-2/3 h-2 bg-[var(--genui-surface)] rounded mx-auto" />
          </div>
        )}
        {state === "uploading" && (
          <>
            <div className="px-2 py-2 text-[10px] font-semibold text-[var(--genui-muted)] uppercase tracking-wider">Today</div>
            <TimelineItem status="running" title="Uploading dataset…" subtext={fileName} timestamp="Now" selected />
          </>
        )}
        {milestones.length > 0 && (
          <>
            <div className="px-2 py-2 text-[10px] font-semibold text-[var(--genui-muted)] uppercase tracking-wider">Today</div>
            {milestones.map((item, idx) => (
              <TimelineItem
                key={idx}
                status={item.status}
                title={item.title}
                subtext={item.subtext}
                timestamp={item.timestamp}
                selected={item.selected}
                onClick={
                  (item.status === "failed" || item.status === "needs-user")
                    ? focusDetails
                    : undefined
                }
                statusBadge={
                  item.status === "needs-user" ? "Awaiting" :
                    item.status === "failed" ? "Error" :
                      undefined
                }
              />
            ))}
            {history.map((item, idx) => <TimelineItem key={`h-${idx}`} {...item} />)}
          </>
        )}
      </div>
    </>
  );

  /* ── CENTER: Decision chips → centerSubHeader ── */
  const CenterSubHeader = (
    <div className="w-full flex flex-wrap items-center justify-between gap-3 min-w-0">
      {hasUploadedDatasets ? (
        <div className="flex items-center gap-2 min-w-0 flex-shrink-0">
          <span className="text-[11px] font-medium text-[var(--genui-muted)] whitespace-nowrap">데이터 소스</span>
          <select
            value={selectedSourceId ?? ""}
            onChange={(e) => selectUploadedDataset(e.target.value || null)}
            className="h-7 w-[200px] flex-shrink-0 max-w-[320px] rounded-md border border-[var(--genui-border)] bg-[var(--genui-surface)] px-2 text-xs text-[var(--genui-text)] focus:outline-none focus:ring-1 focus:ring-[var(--genui-focus-ring)] truncate"
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
        <span className="text-xs text-[var(--genui-muted)] whitespace-nowrap flex-shrink-0">
          업로드 없이도 질문을 바로 보낼 수 있습니다.
        </span>
      )}

      {decisionChips.length > 0 ? (
        <DecisionChips
          className="flex-shrink flex-wrap justify-end min-w-0"
          chips={decisionChips.map((c) => ({
            ...c,
            onNavigate:
              c.value === "BLOCKED" || c.value === "FAILED"
                ? focusDetails
                : () => handleTabChange("agent"),
          }))}
        />
      ) : null}
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
    <div className="max-w-3xl mx-auto w-full space-y-8 pb-32 pt-8 px-4">
      {/* Hidden file input for real file selection */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.json,.xlsx,.xls"
        className="hidden"
        onChange={handleFileSelected}
      />

      {state === "empty" && (
        <div className="flex flex-col items-center justify-center min-h-[50vh] animate-in fade-in zoom-in-95 duration-500">
          <Dropzone status="idle" onDrop={handleDrop} onTrySample={() => pipeline.startWithSample()} />
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
        <div className="flex flex-col items-center justify-center min-h-[50vh] animate-in fade-in zoom-in-95 duration-300">
          <div className="w-full max-w-2xl rounded-xl border border-[var(--genui-border)] bg-[var(--genui-panel)] p-6 space-y-2">
            <h2 className="text-lg font-semibold text-[var(--genui-text)]">
              업로드 완료, 질문 대기 중
            </h2>
            <p className="text-sm text-[var(--genui-muted)] leading-relaxed">
              {selectedDataset
                ? `${selectedDataset.fileName}이(가) 선택되었습니다. 질문을 보내면 LangGraph가 라우팅합니다.`
                : "상단에서 파일을 선택하면 해당 source로 질문이 전송됩니다. 선택 없이 질문하면 일반 질의로 처리됩니다."}
            </p>
          </div>
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
            <div className="flex justify-center">
              <div className="inline-flex items-center gap-3 px-4 py-2 bg-[var(--genui-panel)] border border-[var(--genui-border)] rounded-full shadow-sm">
                <ToolCallIndicator status="running" label={lastRunningTool.name} sublabel="Processing..." />
              </div>
            </div>
          )}
        </div>
      )}

      {/* NEEDS-USER */}
      {state === "needs-user" && (
        <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
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
          <div className="flex justify-center">
            <div className="inline-flex items-center gap-3 px-4 py-2 bg-[var(--genui-panel)] border border-[var(--genui-needs-user)]/30 rounded-full shadow-sm">
              <ToolCallIndicator
                status="needs-user"
                label={
                  pendingApproval?.stage === "report"
                    ? "report_draft_review"
                    : pendingApproval?.stage === "visualization"
                      ? "visualization_plan_review"
                      : "preprocess_plan_review"
                }
                sublabel={pendingApproval?.summary ?? "Awaiting user decision"}
              />
            </div>
          </div>
          <p className="text-center text-[11px] text-[var(--genui-muted)]">
            Review the current plan below and approve, request changes, or cancel the run.
          </p>
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
            variant="final"
            title={hasDatasetContext ? "Analysis Complete" : "AI 답변"}
            subtitle={hasDatasetContext ? selectedDataset?.fileName || fileName : undefined}
            timestamp="Now"
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
          state === "ready" ? "파일을 선택하거나, 바로 질문을 입력하세요..." :
            state === "needs-user"
              ? pendingApproval?.stage === "report"
                ? "Review the report draft below to continue..."
                : "Review the current plan below to continue..."
              :
              state === "error" ? "Type to discuss the error..." :
                "Ask Gen-UI to analyze, visualize, or transform..."
      }
      onSend={handleSendMessage}
      onStop={() => pipeline.handleCancel()}
      onUploadDataset={openFilePicker}
      onUseSample={() => pipeline.startWithSample()}
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
        <div ref={detailsPanelRef}>
          {highlightDetails && (
            <div className="mx-4 mt-3 mb-0 px-3 py-2 rounded-lg border border-[var(--genui-error)]/40 bg-[var(--genui-error)]/5 flex items-center gap-2 animate-in fade-in duration-200">
              <span className="text-[10px] font-semibold text-[var(--genui-error)] animate-pulse">
                ↓ Resolution Required
              </span>
            </div>
          )}
          <DetailsPanel
            state={state === "running" || state === "success" ? "streaming" : state}
            selectedItem={{ visualization: latestVisualizationResult, hasDatasetContext, pendingApproval }}
            onAction={handleDetailsAction}
          />
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
    <div className="h-full flex items-center justify-between px-4 w-full">
      <div className="flex items-center gap-3">
        <span className="font-semibold text-[var(--genui-text)]">
          {activeSession?.title || (state === "empty" ? "새 세션" : selectedDataset?.fileName || fileName || "채팅 세션")}
        </span>
        <StatusBadge status={state} />
      </div>
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
