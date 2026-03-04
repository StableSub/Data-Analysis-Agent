import React, { useState, useRef, useCallback, useEffect } from "react";
import { TimelineItem } from "../components/genui/TimelineItem";
import { ToolCallIndicator } from "../components/genui/ToolCallIndicator";
import { WorkbenchCommandBar } from "../components/genui/WorkbenchCommandBar";
import { Dropzone } from "../components/genui/Dropzone";
import { WorkbenchLayout } from "../components/genui/WorkbenchLayout";
import { StatusBadge, type StatusType } from "../components/genui/StatusBadge";
import { DetailsPanel } from "../components/genui/DetailsPanel";
import { GateBar } from "../components/genui/GateBar";
import { AssistantReportMessage } from "../components/genui/AssistantReportMessage";
import { RightPanelTabs, type RightTabId } from "../components/genui/RightPanelTabs";
import { CopilotPanel } from "../components/genui/CopilotPanel";
import { MCPPanel } from "../components/genui/MCPPanel";
import { DecisionChips } from "../components/genui/DecisionChips";
import { Sparkles, FileText, CheckCircle2 } from "lucide-react";
import { cn } from "../../lib/utils";
import { PipelineBar, type PipelineBarVariant } from "../components/genui/PipelineBar";
import { useAnalysisPipeline } from "../hooks/useAnalysisPipeline";

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
    hitlProposal,
    rawLogs,
    fileName,
  } = pipeline;

  // UI-only local state
  const [highlightDetails, setHighlightDetails] = useState(false);
  const [rightTab, setRightTab] = useState<RightTabId>("details");
  const [copilotHasNew, setCopilotHasNew] = useState(false);
  const detailsPanelRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Show NEW dot on Agent tab when tool calls arrive
  useEffect(() => {
    if ((state === "running" || state === "needs-user" || state === "error") && rightTab !== "agent") {
      setCopilotHasNew(true);
    }
  }, [state, rightTab]);

  const formatElapsed = (s: number) => {
    const m   = Math.floor(s / 60).toString().padStart(2, "0");
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

  // Current running tool call for inline indicator
  const currentRunningTool = toolCalls.filter((tc) => tc.status === "running");
  const lastRunningTool = currentRunningTool[currentRunningTool.length - 1];

  /* ── LEFT PANEL — Milestone Log ── */
  const LeftPanel = (
    <>
      {/* h-10 — aligns with Center Route bar and Right Details|Agent tab bar */}
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
                  item.status === "failed"     ? "Error"    :
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
  const CenterSubHeader = decisionChips.length > 0 ? (
    <DecisionChips
      chips={decisionChips.map((c) => ({
        ...c,
        onNavigate:
          c.value === "BLOCKED" || c.value === "FAILED"
            ? focusDetails
            : () => handleTabChange("agent"),
      }))}
    />
  ) : null;

  /* ── Evidence with nav callbacks ── */
  const evidenceWithNav = {
    ...evidence,
    onDataNavigate:    focusDetails,
    onScopeNavigate:   focusDetails,
    onComputeNavigate: () => handleTabChange("agent"),
    onRagNavigate:     () => handleTabChange("agent"),
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

      {/* RUNNING */}
      {state === "running" && (
        <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
          <AssistantReportMessage
            variant="streaming"
            title={`Analyzing ${fileName || "Dataset"}`}
            subtitle={fileName}
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
            title={`Approval Required${hitlProposal ? ` — Impute ${hitlProposal.column}` : ""}`}
            subtitle="Action needed"
            timestamp="Now"
            sections={reportSections}
            maxBodyHeight={300}
            evidence={evidenceWithNav}
          />
          <div className="flex justify-center">
            <div className="inline-flex items-center gap-3 px-4 py-2 bg-[var(--genui-panel)] border border-[var(--genui-needs-user)]/30 rounded-full shadow-sm">
              <ToolCallIndicator status="needs-user" label="propose_imputation" sublabel="Awaiting user decision" />
            </div>
          </div>
          <p className="text-center text-[11px] text-[var(--genui-muted)]">
            Use the decision bar below ↓ to approve, reject, or modify the proposed changes.
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
      {state === "success" && (
        <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
          <AssistantReportMessage
            variant="final"
            title="Analysis Complete"
            subtitle={fileName}
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
        state === "needs-user" ? "Agent is waiting for approval..." :
        state === "error" ? "Type to discuss the error..." :
        "Ask Gen-UI to analyze, visualize, or transform..."
      }
      onSend={(val) => pipeline.handleSend(val)}
      onStop={() => pipeline.handleCancel()}
      onUploadDataset={openFilePicker}
      onUseSample={() => pipeline.startWithSample()}
    />
  );

  /* ── GATE BAR ── */
  const GateBarComponent = state === "needs-user" ? (
    <GateBar
      onApprove={pipeline.handleApprove}
      onReject={pipeline.handleReject}
      onSubmitChange={pipeline.handleEditInstruction}
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
            state === "needs-user" && hitlProposal
              ? {
                  title: `Impute ${hitlProposal.column}`,
                  description: `${hitlProposal.column} · ${hitlProposal.missingCount} rows · ${hitlProposal.strategy}`,
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
          {state === "empty" ? "New Session" : fileName || "Analysis Session"}
        </span>
        <StatusBadge status={state as StatusType} />
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
    state === "uploading"   ? "ingest"      :
    state === "running"     ? "running"     :
    state === "needs-user"  ? "needs-user"  :
    state === "error"       ? "failed"      :
    state === "success"     ? "completed"   :
    "hidden";

  const pipelineMessage =
    state === "uploading"
      ? uploadProgress < 30 ? "Uploading file…"
        : uploadProgress < 70 ? "Parsing schema…"
        : "Validating dataset…"
    : state === "running"    ? `${subPhaseLabel[runningSubPhase] ?? runningSubPhase} 진행 중…`
    : state === "needs-user" ? "Awaiting approval"
    : state === "error"      ? "Failed — see details"
    : undefined;

  const completedToolCount = toolCalls.filter((tc) => tc.status === "completed").length;
  const totalStages = 6;

  const PipelineBarNode = (
    <PipelineBar
      variant={pipelineBarVariant}
      stage={
        state === "uploading"   ? "Ingest"     :
        state === "running"     ? (subPhaseLabel[runningSubPhase] ?? runningSubPhase) :
        state === "needs-user"  ? "Preprocess" :
        state === "error"       ? "Error"      :
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
        state === "running" || state === "needs-user"
          ? () => handleTabChange("agent")
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
