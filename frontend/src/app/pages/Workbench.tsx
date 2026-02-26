import React, { useState, useEffect, useRef, useCallback } from "react";
import { TimelineItem, TimelineItemStatus } from "../components/genui/TimelineItem";
import { ToolCallIndicator } from "../components/genui/ToolCallIndicator";
import { WorkbenchCommandBar } from "../components/genui/WorkbenchCommandBar";
import { Dropzone } from "../components/genui/Dropzone";
import { WorkbenchLayout } from "../components/genui/WorkbenchLayout";
import { StatusBadge, StatusType } from "../components/genui/StatusBadge";
import { DetailsPanel } from "../components/genui/DetailsPanel";
import { GateBar } from "../components/genui/GateBar";
import { AssistantReportMessage, type ReportSection } from "../components/genui/AssistantReportMessage";
import { RightPanelTabs, type RightTabId } from "../components/genui/RightPanelTabs";
import { CopilotPanel, type ToolCallEntry, type RunStatusData, type PipelineStep } from "../components/genui/CopilotPanel";
import { MCPPanel, RAW_LOGS_RUNNING, RAW_LOGS_ERROR } from "../components/genui/MCPPanel";
import { DecisionChips, type DecisionChip } from "../components/genui/DecisionChips";
import { EvidenceFooter, type EvidenceFooterProps } from "../components/genui/EvidenceFooter";
import { Sparkles, FileText, CheckCircle2 } from "lucide-react";
import { cn } from "../../lib/utils";
import { PipelineBar, type PipelineBarVariant } from "../components/genui/PipelineBar";

// --- INLINE COMPONENTS ---

const InlineUploadProgress = ({ progress }: { progress: number }) => {
  return (
    <div className="w-full max-w-2xl mx-auto p-4 bg-[var(--genui-surface)] rounded-xl border border-[var(--genui-border)] shadow-sm animate-in fade-in zoom-in-95 duration-300">
       <div className="flex items-center gap-4 mb-3">
          <div className="w-10 h-10 rounded-lg bg-[var(--genui-panel)] flex items-center justify-center border border-[var(--genui-border)]">
             <FileText className="w-5 h-5 text-[var(--genui-text)]" />
          </div>
          <div className="flex-1 space-y-1">
             <div className="flex justify-between text-sm font-medium text-[var(--genui-text)]">
                <span>sales_data_Q3.csv</span>
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

// --- REPORT CONTENT DATA ---

const RUNNING_SECTIONS: ReportSection[] = [
  { type: "paragraph", content: "I'm analyzing the Q3 sales dataset now. Generating a revenue breakdown by region and identifying preprocessing steps required before model training." },
  { type: "heading", content: "Steps in Progress" },
  { type: "numbered-list", items: ["Loaded dataset schema — 14,500 rows × 24 columns detected", "Scanning for missing values across all numeric columns…", "Planning preprocessing pipeline steps…"] },
];

const NEEDS_USER_SECTIONS: ReportSection[] = [
  { type: "paragraph", content: "I've found missing values that need your attention before I can proceed. Please review the proposed imputation strategy in the Details panel." },
  { type: "heading", content: "Finding" },
  { type: "numbered-list", items: ["142 rows in 'Region' column have null values (0.98% of dataset)", "Recommended strategy: mode imputation → 'West' (most frequent, 41% of non-null rows)", "Downstream steps 3–5 are blocked until this is resolved"] },
  { type: "heading", content: "Proposed Changes" },
  { type: "checklist", items: ["Impute 'Region' nulls with modal value ('West')", "Flag imputed rows with a new boolean column 'Region_imputed'"] },
];

const ERROR_SECTIONS: ReportSection[] = [
  { type: "paragraph", content: "Non-numeric characters found in 'Price' column (rows #142, #991, #3847). Parse error prevented step 2 of 5 from completing." },
];

// --- TOOL CALL DATA per state ---

const TOOL_CALLS_RUNNING: ToolCallEntry[] = [
  { id: "tc1", name: "load_dataset",   status: "completed", args: `{ "path": "sales_data_Q3.csv" }`,          result: "14,500 rows × 24 columns",          duration: "0.3s", startedAt: "10:00:01 AM" },
  { id: "tc2", name: "inspect_schema", status: "completed", args: `{ "target": "all_columns" }`,              result: "24 cols · 3 PII detected",           duration: "0.1s", startedAt: "10:00:02 AM" },
  { id: "tc3", name: "detect_missing", status: "running",   args: `{ "columns": ["Price", "Region", "Date_Sold"] }`,                                                             startedAt: "10:00:03 AM" },
];

const TOOL_CALLS_RUNNING_RAG: ToolCallEntry[] = [
  { id: "tc1", name: "load_dataset",   status: "completed", args: `{ "path": "sales_data_Q3.csv" }`,          result: "14,500 rows × 24 columns",          duration: "0.3s", startedAt: "10:00:01 AM" },
  { id: "tc2", name: "inspect_schema", status: "completed", args: `{ "target": "all_columns" }`,              result: "24 cols · 3 PII detected",           duration: "0.1s", startedAt: "10:00:02 AM" },
  { id: "tc3", name: "detect_missing", status: "completed", args: `{ "columns": ["Price", "Region", "Date_Sold"] }`, result: "142 nulls in 'Region'",          duration: "0.4s", startedAt: "10:00:03 AM" },
  { id: "tc4", name: "rag_retrieve",   status: "running",   args: `{ "query": "Q3 sales anomaly detection patterns", "top_k": 8 }`,                                              startedAt: "10:00:05 AM" },
];

const TOOL_CALLS_NEEDS_USER: ToolCallEntry[] = [
  { id: "tc1", name: "load_dataset",      status: "completed",  args: `{ "path": "sales_data_Q3.csv" }`,     result: "14,500 rows × 24 columns",          duration: "0.3s", startedAt: "10:00:01 AM" },
  { id: "tc2", name: "inspect_schema",    status: "completed",  args: `{ "target": "all_columns" }`,         result: "24 cols · 3 PII detected",           duration: "0.1s", startedAt: "10:00:02 AM" },
  { id: "tc3", name: "detect_missing",    status: "completed",  args: `{ "columns": ["Price", "Region"] }`,  result: "142 nulls in 'Region'",              duration: "0.4s", startedAt: "10:00:03 AM" },
  { id: "tc4", name: "propose_imputation",status: "needs-user", args: `{ "column": "Region", "strategy": "mode", "fill_value": "West" }`,                                       startedAt: "10:00:04 AM" },
];

const TOOL_CALLS_ERROR: ToolCallEntry[] = [
  { id: "tc1", name: "load_dataset",      status: "completed", args: `{ "path": "sales_data_Q3.csv" }`,     result: "14,500 rows × 24 columns",    duration: "0.3s", startedAt: "10:00:01 AM" },
  { id: "tc2", name: "inspect_schema",    status: "completed", args: `{ "target": "all_columns" }`,         result: "24 cols · 3 PII detected",     duration: "0.1s", startedAt: "10:00:02 AM" },
  { id: "tc3", name: "detect_missing",    status: "completed", args: `{ "columns": ["Price", "Region"] }`,  result: "142 nulls in 'Region'",        duration: "0.4s", startedAt: "10:00:03 AM" },
  { id: "tc4", name: "cast_dtype",        status: "failed",    args: `{ "column": "Price", "dtype": "float64" }`, result: "ParseError: non-numeric chars at rows #142, #991, #3847", duration: "0.2s", startedAt: "10:00:06 AM" },
];

function getToolCalls(state: StatusType, runningPhase?: "preprocessing" | "rag"): ToolCallEntry[] {
  if (state === "running")     return runningPhase === "rag" ? TOOL_CALLS_RUNNING_RAG : TOOL_CALLS_RUNNING;
  if (state === "needs-user")  return TOOL_CALLS_NEEDS_USER;
  if (state === "error")       return TOOL_CALLS_ERROR;
  return [];
}

function getRunStatus(state: StatusType, runningPhase?: "preprocessing" | "rag"): RunStatusData | undefined {
  if (state === "running")    return runningPhase === "rag"
    ? { phase: "RAG 분석", progress: 58, lastTool: "rag_retrieve", elapsedTime: "4.1s" }
    : { phase: "자동 전처리", progress: 42, lastTool: "detect_missing", elapsedTime: "3.2s" };
  if (state === "needs-user") return { phase: "Awaiting approval", progress: 60, lastTool: "propose_imputation", elapsedTime: "5.1s" };
  if (state === "error")      return { phase: "Failed — step 2/5", progress: 28, lastTool: "cast_dtype", elapsedTime: "6.3s" };
  return undefined;
}

// --- P1: PIPELINE STEPS per state ---

const PIPELINE_STEPS_RUNNING: PipelineStep[] = [
  { id: "intake",    label: "Intake",        status: "success",    toolCount: 2 },
  { id: "preprocess",label: "Preprocess",    status: "running",    sublabel: "자동 전처리 중…", toolCount: 1 },
  { id: "rag",       label: "RAG",           status: "queued" },
  { id: "viz",       label: "Visualization", status: "queued" },
  { id: "merge",     label: "Merge",         status: "queued" },
  { id: "report",    label: "Report",        status: "queued" },
];

const PIPELINE_STEPS_RUNNING_RAG: PipelineStep[] = [
  { id: "intake",    label: "Intake",        status: "success",    toolCount: 2 },
  { id: "preprocess",label: "Preprocess",    status: "success",    toolCount: 3 },
  { id: "rag",       label: "RAG",           status: "running",    sublabel: "RAG 분석 중…", toolCount: 1 },
  { id: "viz",       label: "Visualization", status: "queued" },
  { id: "merge",     label: "Merge",         status: "queued" },
  { id: "report",    label: "Report",        status: "queued" },
];

const PIPELINE_STEPS_NEEDS_USER: PipelineStep[] = [
  { id: "intake",    label: "Intake",        status: "success",    toolCount: 2 },
  { id: "preprocess",label: "Preprocess",    status: "needs-user", sublabel: "Awaiting approval — impute Region", toolCount: 2 },
  { id: "rag",       label: "RAG",           status: "queued" },
  { id: "viz",       label: "Visualization", status: "queued" },
  { id: "merge",     label: "Merge",         status: "queued" },
  { id: "report",    label: "Report",        status: "queued" },
];

const PIPELINE_STEPS_ERROR: PipelineStep[] = [
  { id: "intake",    label: "Intake",        status: "success", toolCount: 2 },
  { id: "preprocess",label: "Preprocess",    status: "success", toolCount: 3 },
  { id: "rag",       label: "RAG",           status: "success", toolCount: 1 },
  { id: "viz",       label: "Visualization", status: "failed",  sublabel: "Failed — ParseError in 'Price'", toolCount: 1 },
  { id: "merge",     label: "Merge",         status: "queued" },
  { id: "report",    label: "Report",        status: "queued" },
];

function getPipelineSteps(state: StatusType, runningPhase?: "preprocessing" | "rag"): PipelineStep[] | undefined {
  if (state === "running")    return runningPhase === "rag" ? PIPELINE_STEPS_RUNNING_RAG : PIPELINE_STEPS_RUNNING;
  if (state === "needs-user") return PIPELINE_STEPS_NEEDS_USER;
  if (state === "error")      return PIPELINE_STEPS_ERROR;
  return undefined;
}

// --- P2: DECISION CHIPS per state ---

const CHIPS_RUNNING: DecisionChip[] = [
  { stage: "Preprocess", value: "ON" },
  { stage: "RAG",        value: "ON" },
  { stage: "Viz",        value: "ON" },
  { stage: "Report",     value: "ON" },
  { stage: "Mode",       value: "Full" },
];

const CHIPS_NEEDS_USER: DecisionChip[] = [
  { stage: "Preprocess", value: "BLOCKED" },
  { stage: "RAG",        value: "ON" },
  { stage: "Viz",        value: "ON" },
  { stage: "Report",     value: "ON" },
  { stage: "Mode",       value: "Full" },
];

const CHIPS_ERROR: DecisionChip[] = [
  { stage: "Preprocess", value: "DONE" },
  { stage: "RAG",        value: "DONE" },
  { stage: "Viz",        value: "FAILED" },
  { stage: "Merge",      value: "QUEUED" },
  { stage: "Report",     value: "QUEUED" },
];

// --- P3: EVIDENCE FOOTER data per state ---

const EVIDENCE_RUNNING: EvidenceFooterProps = {
  data:    "sales_Q3.csv",
  scope:   "14,500×24",
  compute: "v3 · 00:03",
  rag:     "OFF",
};

const EVIDENCE_NEEDS_USER: EvidenceFooterProps = {
  data:    "sales_Q3.csv",
  scope:   "142 missing",
  compute: "v3 · 00:05",
  rag:     "OFF",
};

const EVIDENCE_ERROR: EvidenceFooterProps = {
  data:    "sales_Q3.csv",
  scope:   "col=Price",
  compute: "v3 · 00:06",
  rag:     "OFF",
};

// --- MAIN PAGE ---

interface HistoryItem {
  status: TimelineItemStatus;
  title: string;
  subtext?: string;
  timestamp: string;
  selected?: boolean;
}

export default function Workbench() {
  const [state, setState] = useState<StatusType>("empty");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [runningPhase, setRunningPhase] = useState<"preprocessing" | "rag">("preprocessing");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [highlightDetails, setHighlightDetails] = useState(false);
  const [rightTab, setRightTab] = useState<RightTabId>("details");
  const [copilotHasNew, setCopilotHasNew] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const detailsPanelRef = useRef<HTMLDivElement>(null);

  // ── Upload simulation ──
  useEffect(() => {
    let interval: any;
    if (state === "uploading") {
      setUploadProgress(0);
      interval = setInterval(() => {
        setUploadProgress(p => {
          if (p >= 100) { setState("running"); return 100; }
          return p + 2;
        });
      }, 50);
    }
    return () => clearInterval(interval);
  }, [state]);

  // ── Running phase: preprocessing → rag (after 2s) ──
  useEffect(() => {
    if (state === "running") {
      setRunningPhase("preprocessing");
      const timer = setTimeout(() => setRunningPhase("rag"), 2000);
      return () => clearTimeout(timer);
    }
  }, [state]);

  // ── Running → needs-user auto-transition ──
  useEffect(() => {
    let hitlTimer: any;
    if (state === "running" && history.length < 3) {
      hitlTimer = setTimeout(() => setState("needs-user"), 3500);
    }
    return () => clearTimeout(hitlTimer);
  }, [state, history.length]);

  // ── Show NEW dot on Agent tab when tool calls arrive and tab is not active ──
  useEffect(() => {
    if ((state === "running" || state === "needs-user" || state === "error") && rightTab !== "agent") {
      setCopilotHasNew(true);
    }
  }, [state, rightTab]);

  // ── Elapsed timer for running / needs-user ──
  useEffect(() => {
    let iv: ReturnType<typeof setInterval>;
    if (state === "running" || state === "needs-user") {
      iv = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    } else {
      setElapsedSeconds(0);
    }
    return () => clearInterval(iv);
  }, [state]);

  const formatElapsed = (s: number) => {
    const m   = Math.floor(s / 60).toString().padStart(2, "0");
    const sec = (s % 60).toString().padStart(2, "0");
    return `${m}:${sec}`;
  };

  const handleTabChange = (tab: RightTabId) => {
    setRightTab(tab);
    if (tab === "agent") setCopilotHasNew(false);
  };

  // ── Actions ──
  const handleStateChange = (newState: StatusType) => {
    setState(newState);
    if (newState === "uploading") setUploadProgress(0);
    if (newState === "running" || newState === "error" || newState === "needs-user") {
      if (rightTab !== "agent") setCopilotHasNew(true);
    }
  };

  const handleDetailsAction = (action: string) => {
    if (action === "try-sample") handleStateChange("uploading");
    if (action === "cancel-upload") handleStateChange("empty");
    if (action === "resolve-retry") handleStateChange("running");
  };

  const handleApprove = () => {
    setHistory(prev => [...prev, { status: "completed", title: "Approved Imputation", subtext: "User confirmed strategy", timestamp: "Now" }]);
    setState("running");
    setTimeout(() => setState("error"), 2500);
  };

  const handleReject = () => {
    setHistory(prev => [...prev, { status: "failed", title: "Rejected Changes", subtext: "User cancelled action", timestamp: "Now" }]);
    setState("running");
  };

  const handleEditInstruction = (text: string) => {
    setHistory(prev => [...prev, { status: "completed", title: "User Edit", subtext: text, timestamp: "Now" }]);
    setState("running");
    setTimeout(() => setState("success"), 2500);
  };

  const focusDetails = useCallback(() => {
    setHighlightDetails(true);
    setRightTab("details");
    detailsPanelRef.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
    setTimeout(() => setHighlightDetails(false), 1100);
  }, []);

  /* ── LEFT PANEL — P4 Milestone Log ──
     핵심 이벤트만 표시(스팸 금지), nav-only onClick (SSOT)
  ── */
  const milestones =
    state === "running" ? [
      { status: "completed" as TimelineItemStatus, title: "Upload complete", subtext: "schema detected · 24 columns", timestamp: "10:00 AM" },
      { status: "completed" as TimelineItemStatus, title: "Preprocess plan ready", subtext: "3 transforms identified", timestamp: "10:01 AM" },
      { status: "running"   as TimelineItemStatus, title: "Preprocess running", subtext: "detect_missing · scanning…", timestamp: "Now", selected: true },
    ] :
    state === "needs-user" ? [
      { status: "completed"  as TimelineItemStatus, title: "Upload complete", subtext: "schema detected · 24 columns", timestamp: "10:00 AM" },
      { status: "completed"  as TimelineItemStatus, title: "Missing values detected", subtext: "142 nulls in 'Region' (0.98%)", timestamp: "10:01 AM" },
      { status: "needs-user" as TimelineItemStatus, title: "Approval required", subtext: "propose_imputation · 142 rows", timestamp: "Now", selected: true },
    ] :
    state === "error" ? [
      { status: "completed" as TimelineItemStatus, title: "Upload complete", subtext: "schema detected · 24 columns", timestamp: "10:00 AM" },
      { status: "completed" as TimelineItemStatus, title: "Missing values detected", subtext: "142 nulls in 'Region'", timestamp: "10:01 AM" },
      { status: "completed" as TimelineItemStatus, title: "RAG retrieved", subtext: "12 chunks from knowledge base", timestamp: "10:02 AM" },
      { status: "failed"    as TimelineItemStatus, title: "Visualization failed", subtext: "ParseError in 'Price' column", timestamp: "10:03 AM", selected: true },
    ] :
    [];

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
            <TimelineItem status="running" title="Uploading dataset…" subtext="sales_data_Q3.csv" timestamp="Now" selected />
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
                /* nav-only: error/needs-user items navigate to Details panel */
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

  /* ── CENTER: Decision chips → centerSubHeader (not sticky/floating) ── */
  const decisionChips: DecisionChip[] =
    state === "running"    ? CHIPS_RUNNING    :
    state === "needs-user" ? CHIPS_NEEDS_USER :
    state === "error"      ? CHIPS_ERROR      :
    [];

  /* Tooltip text per chip — explains WHY this state in 1 line */
  const chipTooltips: Record<string, string> = {
    "Preprocess-BLOCKED": "Awaiting approval: Impute Missing Values (Region, 142 rows)",
    "Viz-FAILED":         "Visualization failed: ParseError in 'Price' column — see Details",
    "Preprocess-DONE":    "Preprocessing completed: 3 tools ran successfully",
    "RAG-DONE":           "RAG retrieval completed successfully",
  };

  const CenterSubHeader = decisionChips.length > 0 ? (
    <DecisionChips
      chips={decisionChips.map((c) => ({
        ...c,
        tooltip: chipTooltips[`${c.stage}-${c.value}`],
        onNavigate:
          c.value === "BLOCKED" || c.value === "FAILED"
            ? focusDetails
            : () => handleTabChange("agent"),
      }))}
    />
  ) : null;

  const MainContent = (
    <div className="max-w-3xl mx-auto w-full space-y-8 pb-32 pt-8 px-4">
      {/* Debug dots */}
      <div className="absolute top-0 right-0 p-2 opacity-0 hover:opacity-100 transition-opacity z-50 bg-[var(--genui-surface)]/80 backdrop-blur-sm border-b border-l border-[var(--genui-border)] rounded-bl-lg">
        <div className="flex gap-1">
          {(["empty", "uploading", "running", "needs-user", "error"] as StatusType[]).map(s => (
            <button key={s} onClick={() => handleStateChange(s)} className="w-3 h-3 rounded-full border border-[var(--genui-text)]" title={s} style={{ backgroundColor: state === s ? 'var(--genui-text)' : 'transparent' }} />
          ))}
        </div>
      </div>

      {state === "empty" && (
        <div className="flex flex-col items-center justify-center min-h-[50vh] animate-in fade-in zoom-in-95 duration-500">
          <Dropzone status="idle" onDrop={() => handleStateChange("uploading")} onTrySample={() => handleStateChange("uploading")} />
        </div>
      )}

      {state === "uploading" && (
        <div className="flex flex-col items-center justify-center min-h-[50vh]">
          <InlineUploadProgress progress={uploadProgress} />
        </div>
      )}

      {/* RUNNING */}
      {state === "running" && (
        <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
          <AssistantReportMessage
            variant="streaming"
            title="Analyzing Sales Data"
            subtitle="sales_data_Q3.csv · 14,500 rows"
            timestamp="Now"
            sections={RUNNING_SECTIONS}
            maxBodyHeight={300}
            evidence={{
              ...EVIDENCE_RUNNING,
              onDataNavigate:    focusDetails,
              onScopeNavigate:   focusDetails,
              onComputeNavigate: () => handleTabChange("agent"),
              onRagNavigate:     () => handleTabChange("agent"),
            }}
          />
          <div className="flex justify-center">
            <div className="inline-flex items-center gap-3 px-4 py-2 bg-[var(--genui-panel)] border border-[var(--genui-border)] rounded-full shadow-sm">
              {runningPhase === "rag"
                ? <ToolCallIndicator status="running" label="rag_retrieve" sublabel="RAG 분석 중…" />
                : <ToolCallIndicator status="running" label="detect_missing" sublabel="자동 전처리 중…" />
              }
            </div>
          </div>
        </div>
      )}

      {/* NEEDS-USER */}
      {state === "needs-user" && (
        <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
          <AssistantReportMessage
            variant="final"
            accentVariant="needs-user"
            title="Approval Required — Impute Missing Values"
            subtitle="Step 2 of 5 · Action needed"
            timestamp="Now"
            sections={NEEDS_USER_SECTIONS}
            maxBodyHeight={300}
            evidence={{
              ...EVIDENCE_NEEDS_USER,
              onDataNavigate:    focusDetails,
              onScopeNavigate:   focusDetails,
              onComputeNavigate: () => handleTabChange("agent"),
              onRagNavigate:     () => handleTabChange("agent"),
            }}
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
            sections={ERROR_SECTIONS}
            onReviewDetails={focusDetails}
            evidence={{
              ...EVIDENCE_ERROR,
              onDataNavigate:    focusDetails,
              onScopeNavigate:   focusDetails,
              onComputeNavigate: () => handleTabChange("agent"),
              onRagNavigate:     () => handleTabChange("agent"),
            }}
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
      onSend={(val) => alert(`Sent: ${val}`)}
      onStop={() => setState("needs-user")}
      onUploadDataset={() => handleStateChange("uploading")}
      onUseSample={() => handleStateChange("uploading")}
    />
  );

  /* ── GATE BAR ── */
  const GateBarComponent = state === "needs-user" ? (
    <GateBar onApprove={handleApprove} onReject={handleReject} onSubmitChange={handleEditInstruction} />
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
          <DetailsPanel state={state} onAction={handleDetailsAction} />
        </div>
      }
      toolsContent={
        <CopilotPanel
          runStatus={getRunStatus(state, runningPhase)}
          toolCalls={getToolCalls(state, runningPhase)}
          pipelineSteps={getPipelineSteps(state, runningPhase)}
          awaitingInfo={
            state === "needs-user"
              ? {
                  title: "Impute Missing Values",
                  description: "Region · 142 rows · mode → 'West'",
                  onViewDetails: focusDetails,
                }
              : undefined
          }
        />
      }
      mcpContent={<MCPPanel rawLogs={state === "running" ? RAW_LOGS_RUNNING : RAW_LOGS_ERROR} />}
    />
  );

  /* ── HEADER ── */
  const Header = (
    <div className="h-full flex items-center justify-between px-4 w-full">
      <div className="flex items-center gap-3">
        <span className="font-semibold text-[var(--genui-text)]">
          {state === "empty" ? "New Session" : "Q3 Sales Analysis"}
        </span>
        <StatusBadge status={state} />
      </div>
    </div>
  );

  /* ── PIPELINE BAR ── */
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
    : state === "running"    ? runningPhase === "rag" ? "RAG 분석 중…" : "자동 전처리 중…"
    : state === "needs-user" ? "Awaiting approval"
    : state === "error"      ? "Failed — ParseError in 'Price'"
    : undefined;

  const PipelineBarNode = (
    <PipelineBar
      variant={pipelineBarVariant}
      stage={
        state === "uploading"   ? "Ingest"     :
        state === "running"     ? (runningPhase === "rag" ? "RAG" : "Preprocess") :
        state === "needs-user"  ? "Preprocess" :
        state === "error"       ? "Preprocess" :
        undefined
      }
      message={pipelineMessage}
      stepFraction={
        state === "running" || state === "needs-user" ? "2/6" : undefined
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