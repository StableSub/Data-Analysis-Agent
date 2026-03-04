import { useState, useEffect, useRef, useCallback } from "react";
import {
  uploadFile,
  fetchSample,
  sendChat,
  queryRag,
  applyPreprocess,
  createReport,
  type DatasetResponse,
  type SampleResponse,
  type ChatResponse,
  type RagResponse,
  type ReportResponse,
} from "../../lib/api";
import type { ReportSection } from "../components/genui/AssistantReportMessage";
import type {
  ToolCallEntry,
  RunStatusData,
  PipelineStep,
} from "../components/genui/CopilotPanel";
import type { DecisionChip, ChipValue } from "../components/genui/DecisionChips";
import type { EvidenceFooterProps } from "../components/genui/EvidenceFooter";
import type { RawLogEntry } from "../components/genui/MCPPanel";
import type { TimelineItemStatus } from "../components/genui/TimelineItem";
import type { PipelineStepStatus } from "../components/genui/PipelineTracker";

/* ─────────────────────────────────────────────
   Types
───────────────────────────────────────────── */

export type PipelineState =
  | "empty"
  | "uploading"
  | "running"
  | "needs-user"
  | "error"
  | "success";

export type RunningSubPhase =
  | "intake"
  | "preprocessing"
  | "rag"
  | "visualization"
  | "report";

export interface HistoryItem {
  status: TimelineItemStatus;
  title: string;
  subtext?: string;
  timestamp: string;
  selected?: boolean;
}

export interface HitlProposal {
  column: string;
  strategy: string;
  fillValue: string;
  missingCount: number;
  missingPercent: number;
}

export interface UseAnalysisPipelineReturn {
  // State
  state: PipelineState;
  runningSubPhase: RunningSubPhase;
  uploadProgress: number;
  elapsedSeconds: number;

  // GenUI-mapped data
  reportSections: ReportSection[];
  toolCalls: ToolCallEntry[];
  runStatus: RunStatusData | undefined;
  pipelineSteps: PipelineStep[] | undefined;
  decisionChips: DecisionChip[];
  evidence: EvidenceFooterProps;
  milestones: HistoryItem[];
  history: HistoryItem[];
  hitlProposal: HitlProposal | null;
  rawLogs: RawLogEntry[];

  // Actions
  startUpload: (file: File) => void;
  startWithSample: () => void;
  handleApprove: () => void;
  handleReject: () => void;
  handleEditInstruction: (text: string) => void;
  handleRetry: () => void;
  handleSend: (message: string) => void;
  handleCancel: () => void;
  reset: () => void;

  // Meta
  fileName: string;
  sourceId: string | null;
  sessionId: number | null;
}

/* ─────────────────────────────────────────────
   Helpers
───────────────────────────────────────────── */

const STAGES = ["intake", "preprocess", "rag", "viz", "merge", "report"] as const;
const STAGE_LABELS: Record<string, string> = {
  intake: "Intake",
  preprocess: "Preprocess",
  rag: "RAG",
  viz: "Visualization",
  merge: "Merge",
  report: "Report",
};

/** Map RunningSubPhase to STAGES index key */
function subPhaseToStageKey(phase: RunningSubPhase): string {
  if (phase === "preprocessing") return "preprocess";
  if (phase === "visualization") return "viz";
  return phase;
}

function now(): string {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatElapsed(s: number): string {
  const m = Math.floor(s / 60).toString().padStart(2, "0");
  const sec = (s % 60).toString().padStart(2, "0");
  return `${m}:${sec}`;
}

function makeToolCall(name: string, args: Record<string, unknown>): ToolCallEntry {
  return {
    id: crypto.randomUUID(),
    name,
    status: "running",
    args: JSON.stringify(args),
    startedAt: new Date().toLocaleTimeString(),
  };
}

function completeToolCall(
  tc: ToolCallEntry,
  result: string,
  startMs: number,
): ToolCallEntry {
  const dur = ((Date.now() - startMs) / 1000).toFixed(1);
  return { ...tc, status: "completed", result, duration: `${dur}s` };
}

function failToolCall(
  tc: ToolCallEntry,
  result: string,
  startMs: number,
): ToolCallEntry {
  const dur = ((Date.now() - startMs) / 1000).toFixed(1);
  return { ...tc, status: "failed", result, duration: `${dur}s` };
}

/** Heuristic: detect if the chat answer suggests preprocessing is needed */
function detectPreprocessNeeds(answer: string): boolean {
  const keywords = [
    "missing value",
    "null",
    "NaN",
    "impute",
    "imputation",
    "preprocessing",
    "empty cell",
    "결측",
    "누락",
    "전처리",
  ];
  const lower = answer.toLowerCase();
  return keywords.some((kw) => lower.includes(kw));
}

/** Extract a HITL proposal from the chat answer (best-effort parsing) */
function extractProposal(answer: string): HitlProposal {
  // Try to parse structured hints from the LLM answer
  const colMatch = answer.match(/['"](\w+)['"]\s*(?:column|컬럼)/i)
    ?? answer.match(/column\s*['"](\w+)['"]/i);
  const countMatch = answer.match(/(\d+)\s*(?:missing|null|결측|누락)/i);
  const percentMatch = answer.match(/([\d.]+)\s*%/);
  const strategyMatch = answer.match(/(?:mode|median|mean|최빈값|중앙값|평균)/i);

  return {
    column: colMatch?.[1] ?? "unknown",
    strategy: strategyMatch?.[0]?.toLowerCase() ?? "mode",
    fillValue: "auto",
    missingCount: countMatch ? parseInt(countMatch[1] ?? "0", 10) : 0,
    missingPercent: percentMatch ? parseFloat(percentMatch[1] ?? "0") : 0,
  };
}

function makeRawLog(label: string, payload: Record<string, unknown>, isError?: boolean): RawLogEntry {
  return {
    id: crypto.randomUUID(),
    label,
    payload: JSON.stringify(payload, null, 2),
    isError,
  };
}

/* ─────────────────────────────────────────────
   Hook
───────────────────────────────────────────── */

export function useAnalysisPipeline(): UseAnalysisPipelineReturn {
  // --- Core state ---
  const [state, setState] = useState<PipelineState>("empty");
  const [runningSubPhase, setRunningSubPhase] = useState<RunningSubPhase>("intake");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // --- API response accumulation ---
  const [fileName, setFileName] = useState("");
  const [datasetId, setDatasetId] = useState<number | null>(null);
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [sampleData, setSampleData] = useState<SampleResponse | null>(null);
  const [chatResponse, setChatResponse] = useState<ChatResponse | null>(null);
  const [ragResponse, setRagResponse] = useState<RagResponse | null>(null);
  const [reportResult, setReportResult] = useState<ReportResponse | null>(null);

  // --- Pipeline tracking ---
  const [toolCalls, setToolCalls] = useState<ToolCallEntry[]>([]);
  const [milestones, setMilestones] = useState<HistoryItem[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [rawLogs, setRawLogs] = useState<RawLogEntry[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorStep, setErrorStep] = useState<string | null>(null);
  const [hitlProposal, setHitlProposal] = useState<HitlProposal | null>(null);

  // --- Completed stage tracking ---
  const completedStagesRef = useRef<Set<string>>(new Set());

  // --- Abort controller ---
  const abortRef = useRef<AbortController | null>(null);

  // --- Elapsed timer ---
  useEffect(() => {
    let iv: ReturnType<typeof setInterval>;
    if (state === "running" || state === "needs-user") {
      iv = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    } else if (state === "empty") {
      setElapsedSeconds(0);
    }
    return () => clearInterval(iv);
  }, [state]);

  /* ─── Tool call helpers (mutate via setState) ─── */

  const addToolCall = useCallback((tc: ToolCallEntry) => {
    setToolCalls((prev) => [...prev, tc]);
  }, []);

  const updateToolCall = useCallback((id: string, patch: Partial<ToolCallEntry>) => {
    setToolCalls((prev) => prev.map((tc) => (tc.id === id ? { ...tc, ...patch } : tc)));
  }, []);

  const addMilestone = useCallback((item: HistoryItem) => {
    setMilestones((prev) => [...prev, item]);
  }, []);

  const addLog = useCallback((entry: RawLogEntry) => {
    setRawLogs((prev) => [...prev, entry]);
  }, []);

  const markStageCompleted = useCallback((stageKey: string) => {
    completedStagesRef.current.add(stageKey);
  }, []);

  /* ─── Error transition ─── */

  const transitionToError = useCallback(
    (step: string, message: string) => {
      setErrorStep(step);
      setErrorMessage(message);
      setState("error");
      addMilestone({
        status: "failed",
        title: `${step} failed`,
        subtext: message.slice(0, 80),
        timestamp: now(),
        selected: true,
      });
    },
    [addMilestone],
  );

  /* ─── Pipeline stages ─── */

  const runIntake = useCallback(
    async (sid: string, signal: AbortSignal): Promise<SampleResponse | null> => {
      setRunningSubPhase("intake");
      const tc = makeToolCall("fetch_sample", { source_id: sid });
      addToolCall(tc);
      addLog(makeRawLog("tool_call: fetch_sample", { source_id: sid }));
      const t0 = Date.now();
      try {
        const sample = await fetchSample(sid);
        if (signal.aborted) return null;
        const result = `${sample.columns.length} columns, ${sample.rows.length} sample rows`;
        updateToolCall(tc.id, completeToolCall(tc, result, t0));
        addLog(makeRawLog("tool_result: fetch_sample", { columns: sample.columns.length, rows: sample.rows.length }));
        setSampleData(sample);
        markStageCompleted("intake");
        addMilestone({
          status: "completed",
          title: "Schema inspected",
          subtext: result,
          timestamp: now(),
        });
        return sample;
      } catch (e: any) {
        if (signal.aborted) return null;
        updateToolCall(tc.id, failToolCall(tc, e.message, t0));
        addLog(makeRawLog("tool_error: fetch_sample", { error: e.message }, true));
        transitionToError("fetch_sample", e.message);
        return null;
      }
    },
    [addToolCall, updateToolCall, addMilestone, addLog, markStageCompleted, transitionToError],
  );

  const runAnalysis = useCallback(
    async (sid: string, signal: AbortSignal): Promise<ChatResponse | null> => {
      setRunningSubPhase("preprocessing");
      const tc = makeToolCall("chat_analysis", { source_id: sid, question: "Analyze dataset" });
      addToolCall(tc);
      addLog(makeRawLog("tool_call: chat_analysis", { source_id: sid }));
      const t0 = Date.now();
      try {
        const chat = await sendChat({
          question: "Analyze this dataset. Identify any missing values, data quality issues, and recommend preprocessing steps.",
          source_id: sid,
        });
        if (signal.aborted) return null;
        const summary = chat.answer.slice(0, 100) + (chat.answer.length > 100 ? "..." : "");
        updateToolCall(tc.id, completeToolCall(tc, summary, t0));
        addLog(makeRawLog("tool_result: chat_analysis", { session_id: chat.session_id, answer_length: chat.answer.length }));
        setSessionId(chat.session_id);
        setChatResponse(chat);
        markStageCompleted("preprocess");
        addMilestone({
          status: "completed",
          title: "Analysis complete",
          subtext: summary,
          timestamp: now(),
        });
        return chat;
      } catch (e: any) {
        if (signal.aborted) return null;
        updateToolCall(tc.id, failToolCall(tc, e.message, t0));
        addLog(makeRawLog("tool_error: chat_analysis", { error: e.message }, true));
        transitionToError("chat_analysis", e.message);
        return null;
      }
    },
    [addToolCall, updateToolCall, addMilestone, addLog, markStageCompleted, transitionToError],
  );

  const runRagPhase = useCallback(
    async (sid: string, signal: AbortSignal): Promise<RagResponse | null> => {
      setRunningSubPhase("rag");
      const tc = makeToolCall("rag_query", { source_id: sid, top_k: 5 });
      addToolCall(tc);
      addLog(makeRawLog("tool_call: rag_query", { source_id: sid, top_k: 5 }));
      const t0 = Date.now();
      try {
        const rag = await queryRag({
          query: "Analyze patterns and anomalies in the dataset",
          top_k: 5,
          source_filter: [sid],
        });
        if (signal.aborted) return null;
        // apiRequest returns undefined for 204
        if (!rag) {
          updateToolCall(tc.id, completeToolCall(tc, "No matching documents", t0));
          addLog(makeRawLog("tool_result: rag_query", { chunks: 0 }));
          markStageCompleted("rag");
          addMilestone({ status: "completed", title: "RAG search", subtext: "No matching documents", timestamp: now() });
          return null;
        }
        const result = `${rag.retrieved_chunks.length} chunks retrieved`;
        updateToolCall(tc.id, completeToolCall(tc, result, t0));
        addLog(makeRawLog("tool_result: rag_query", { chunks: rag.retrieved_chunks.length }));
        setRagResponse(rag);
        markStageCompleted("rag");
        addMilestone({ status: "completed", title: "RAG retrieved", subtext: result, timestamp: now() });
        return rag;
      } catch (e: any) {
        if (signal.aborted) return null;
        updateToolCall(tc.id, failToolCall(tc, e.message, t0));
        addLog(makeRawLog("tool_error: rag_query", { error: e.message }, true));
        transitionToError("rag_query", e.message);
        return null;
      }
    },
    [addToolCall, updateToolCall, addMilestone, addLog, markStageCompleted, transitionToError],
  );

  const runReportPhase = useCallback(
    async (sessId: number, signal: AbortSignal): Promise<ReportResponse | null> => {
      setRunningSubPhase("report");
      const tc = makeToolCall("create_report", { session_id: sessId });
      addToolCall(tc);
      addLog(makeRawLog("tool_call: create_report", { session_id: sessId }));
      const t0 = Date.now();
      try {
        const report = await createReport({ session_id: sessId });
        if (signal.aborted) return null;
        updateToolCall(tc.id, completeToolCall(tc, report.summary_text.slice(0, 80), t0));
        addLog(makeRawLog("tool_result: create_report", { report_id: report.report_id }));
        setReportResult(report);
        markStageCompleted("report");
        markStageCompleted("merge");
        markStageCompleted("viz");
        addMilestone({ status: "completed", title: "Report generated", subtext: report.report_id, timestamp: now() });
        return report;
      } catch (e: any) {
        if (signal.aborted) return null;
        updateToolCall(tc.id, failToolCall(tc, e.message, t0));
        addLog(makeRawLog("tool_error: create_report", { error: e.message }, true));
        transitionToError("create_report", e.message);
        return null;
      }
    },
    [addToolCall, updateToolCall, addMilestone, addLog, markStageCompleted, transitionToError],
  );

  /* ─── Main pipeline orchestration ─── */

  const runPipeline = useCallback(
    async (dsId: number, sid: string) => {
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      const { signal } = ctrl;

      // 1. Intake
      const sample = await runIntake(sid, signal);
      if (!sample || signal.aborted) return;

      // 2. Chat analysis
      const chat = await runAnalysis(sid, signal);
      if (!chat || signal.aborted) return;

      // 3. Check if preprocessing is needed → HITL gate
      if (detectPreprocessNeeds(chat.answer)) {
        const proposal = extractProposal(chat.answer);
        setHitlProposal(proposal);
        setState("needs-user");
        addMilestone({
          status: "needs-user",
          title: "Approval required",
          subtext: `${proposal.column} · ${proposal.missingCount} rows · ${proposal.strategy}`,
          timestamp: now(),
          selected: true,
        });
        // Pipeline pauses here — resumed by handleApprove/handleReject/handleEditInstruction
        return;
      }

      // 4. RAG
      await runRagPhase(sid, signal);
      if (signal.aborted) return;

      // 5. Report
      const reportSessId = chat.session_id;
      const report = await runReportPhase(reportSessId, signal);
      if (!report || signal.aborted) return;

      setState("success");
    },
    [runIntake, runAnalysis, runRagPhase, runReportPhase, addMilestone],
  );

  /* ─── Resume after HITL ─── */

  const resumeAfterApproval = useCallback(
    async (doPreprocess: boolean, editText?: string) => {
      setState("running");
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      const { signal } = ctrl;
      const sid = sourceId;
      const dsId = datasetId;
      const sessId = sessionId;

      if (!sid || dsId === null || sessId === null) {
        transitionToError("resume", "Missing session context");
        return;
      }

      // Optionally apply preprocessing
      if (doPreprocess && hitlProposal) {
        setRunningSubPhase("preprocessing");
        const tc = makeToolCall("preprocess_apply", {
          dataset_id: dsId,
          column: hitlProposal.column,
          strategy: hitlProposal.strategy,
        });
        addToolCall(tc);
        addLog(makeRawLog("tool_call: preprocess_apply", { dataset_id: dsId, column: hitlProposal.column }));
        const t0 = Date.now();
        try {
          await applyPreprocess({
            dataset_id: dsId,
            operations: [
              {
                op: "impute",
                params: {
                  column: hitlProposal.column,
                  strategy: hitlProposal.strategy,
                  fill_value: editText ?? hitlProposal.fillValue,
                },
              },
            ],
          });
          if (signal.aborted) return;
          updateToolCall(tc.id, completeToolCall(tc, "Preprocessing applied", t0));
          addLog(makeRawLog("tool_result: preprocess_apply", { success: true }));
          markStageCompleted("preprocess");
        } catch (e: any) {
          if (signal.aborted) return;
          updateToolCall(tc.id, failToolCall(tc, e.message, t0));
          addLog(makeRawLog("tool_error: preprocess_apply", { error: e.message }, true));
          transitionToError("preprocess_apply", e.message);
          return;
        }
      }

      // RAG
      await runRagPhase(sid, signal);
      if (signal.aborted) return;

      // Report
      const report = await runReportPhase(sessId, signal);
      if (!report || signal.aborted) return;

      setState("success");
    },
    [
      sourceId, datasetId, sessionId, hitlProposal,
      addToolCall, updateToolCall, addLog, markStageCompleted,
      runRagPhase, runReportPhase, transitionToError,
    ],
  );

  /* ─── Actions ─── */

  const startUpload = useCallback(
    (file: File) => {
      // Reset all state for new pipeline
      setToolCalls([]);
      setMilestones([]);
      setHistory([]);
      setRawLogs([]);
      setSampleData(null);
      setChatResponse(null);
      setRagResponse(null);
      setReportResult(null);
      setHitlProposal(null);
      setErrorMessage(null);
      setErrorStep(null);
      setElapsedSeconds(0);
      completedStagesRef.current = new Set();

      setFileName(file.name);
      setState("uploading");
      setUploadProgress(0);

      uploadFile(file, (percent) => {
        setUploadProgress(percent);
      })
        .then((dataset: DatasetResponse) => {
          setDatasetId(dataset.id);
          setSourceId(dataset.source_id);
          setUploadProgress(100);
          addMilestone({
            status: "completed",
            title: "Upload complete",
            subtext: `${dataset.filename} · ${dataset.source_id}`,
            timestamp: now(),
          });
          setState("running");
          runPipeline(dataset.id, dataset.source_id);
        })
        .catch((err: Error) => {
          transitionToError("upload", err.message);
        });
    },
    [addMilestone, runPipeline, transitionToError],
  );

  const startWithSample = useCallback(() => {
    // Create a minimal sample CSV file for the "Try Sample Dataset" flow
    const sampleContent = "id,name,region,price,date\n1,Product A,North,100,2024-01-01\n2,Product B,South,200,2024-01-02\n";
    const blob = new Blob([sampleContent], { type: "text/csv" });
    const file = new File([blob], "sample_data.csv", { type: "text/csv" });
    startUpload(file);
  }, [startUpload]);

  const handleApprove = useCallback(() => {
    setHistory((prev) => [
      ...prev,
      { status: "completed" as TimelineItemStatus, title: "Approved", subtext: "User confirmed strategy", timestamp: now() },
    ]);
    setHitlProposal(null);
    resumeAfterApproval(true);
  }, [resumeAfterApproval]);

  const handleReject = useCallback(() => {
    setHistory((prev) => [
      ...prev,
      { status: "failed" as TimelineItemStatus, title: "Rejected Changes", subtext: "User cancelled action", timestamp: now() },
    ]);
    setHitlProposal(null);
    resumeAfterApproval(false);
  }, [resumeAfterApproval]);

  const handleEditInstruction = useCallback(
    (text: string) => {
      setHistory((prev) => [
        ...prev,
        { status: "completed" as TimelineItemStatus, title: "User Edit", subtext: text, timestamp: now() },
      ]);
      resumeAfterApproval(true, text);
    },
    [resumeAfterApproval],
  );

  const handleRetry = useCallback(() => {
    if (sourceId && datasetId !== null) {
      setErrorMessage(null);
      setErrorStep(null);
      setState("running");
      runPipeline(datasetId, sourceId);
    }
  }, [sourceId, datasetId, runPipeline]);

  const handleSend = useCallback(
    (message: string) => {
      if (!sourceId || sessionId === null) return;
      const tc = makeToolCall("chat_followup", { question: message, session_id: sessionId });
      addToolCall(tc);
      const t0 = Date.now();
      sendChat({ question: message, session_id: sessionId, source_id: sourceId })
        .then((resp) => {
          updateToolCall(tc.id, completeToolCall(tc, resp.answer.slice(0, 80), t0));
          setChatResponse(resp);
          addMilestone({ status: "completed", title: "Follow-up", subtext: message.slice(0, 40), timestamp: now() });
        })
        .catch((e: Error) => {
          updateToolCall(tc.id, failToolCall(tc, e.message, t0));
        });
    },
    [sourceId, sessionId, addToolCall, updateToolCall, addMilestone],
  );

  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
    setState("empty");
    setUploadProgress(0);
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState("empty");
    setUploadProgress(0);
    setElapsedSeconds(0);
    setFileName("");
    setDatasetId(null);
    setSourceId(null);
    setSessionId(null);
    setSampleData(null);
    setChatResponse(null);
    setRagResponse(null);
    setReportResult(null);
    setToolCalls([]);
    setMilestones([]);
    setHistory([]);
    setRawLogs([]);
    setErrorMessage(null);
    setErrorStep(null);
    setHitlProposal(null);
    completedStagesRef.current = new Set();
  }, []);

  /* ─── Derived data: GenUI prop mappings ─── */

  const reportSections: ReportSection[] = (() => {
    if (state === "success" && reportResult) {
      return [
        { type: "paragraph" as const, content: reportResult.summary_text },
        ...(ragResponse
          ? [
              { type: "heading" as const, content: "Retrieved Evidence" },
              {
                type: "numbered-list" as const,
                items: ragResponse.retrieved_chunks.map(
                  (c) => `[score ${c.score.toFixed(2)}] ${c.snippet.slice(0, 120)}`,
                ),
              },
            ]
          : []),
      ];
    }
    if (state === "running") {
      const cols = sampleData?.columns?.length ?? 0;
      const rows = sampleData?.rows?.length ?? 0;
      const items: string[] = [];
      if (sampleData) items.push(`Loaded dataset schema — ${rows} sample rows x ${cols} columns detected`);
      if (chatResponse) items.push(chatResponse.answer.slice(0, 120));
      else items.push("Scanning for patterns...");
      items.push("Planning pipeline steps...");
      return [
        { type: "paragraph" as const, content: `Analyzing ${fileName}. Identifying preprocessing steps and patterns.` },
        { type: "heading" as const, content: "Steps in Progress" },
        { type: "numbered-list" as const, items },
      ];
    }
    if (state === "needs-user" && hitlProposal) {
      const p = hitlProposal;
      return [
        { type: "paragraph" as const, content: "Missing values found that need your attention before proceeding." },
        { type: "heading" as const, content: "Finding" },
        {
          type: "numbered-list" as const,
          items: [
            `${p.missingCount} rows in '${p.column}' column have null values (${p.missingPercent.toFixed(2)}%)`,
            `Recommended strategy: ${p.strategy} imputation -> '${p.fillValue}'`,
            "Downstream steps are blocked until this is resolved",
          ],
        },
        { type: "heading" as const, content: "Proposed Changes" },
        {
          type: "checklist" as const,
          items: [
            `Impute '${p.column}' nulls with ${p.strategy} value ('${p.fillValue}')`,
            `Flag imputed rows with a new boolean column '${p.column}_imputed'`,
          ],
        },
      ];
    }
    if (state === "error") {
      return [
        { type: "paragraph" as const, content: errorMessage ?? "An error occurred during analysis." },
      ];
    }
    return [];
  })();

  const derivedRunStatus: RunStatusData | undefined = (() => {
    if (state !== "running" && state !== "needs-user" && state !== "error") return undefined;
    const completedCount = toolCalls.filter((tc) => tc.status === "completed").length;
    const totalExpected = 5;
    const progress = Math.min(Math.round((completedCount / totalExpected) * 100), 100);
    const lastTool = toolCalls[toolCalls.length - 1]?.name ?? "";
    if (state === "needs-user") {
      return { phase: "Awaiting approval", progress, lastTool, elapsedTime: formatElapsed(elapsedSeconds) };
    }
    if (state === "error") {
      return { phase: `Failed — ${errorStep ?? "unknown"}`, progress, lastTool, elapsedTime: formatElapsed(elapsedSeconds) };
    }
    const phaseLabels: Record<RunningSubPhase, string> = {
      intake: "데이터 수집",
      preprocessing: "자동 전처리",
      rag: "RAG 분석",
      visualization: "시각화",
      report: "리포트 생성",
    };
    return {
      phase: phaseLabels[runningSubPhase],
      progress,
      lastTool,
      elapsedTime: formatElapsed(elapsedSeconds),
    };
  })();

  const derivedPipelineSteps: PipelineStep[] | undefined = (() => {
    if (state === "empty" || state === "uploading") return undefined;
    const currentKey = subPhaseToStageKey(runningSubPhase);
    const currentIdx = STAGES.indexOf(currentKey as typeof STAGES[number]);
    const completed = completedStagesRef.current;

    return STAGES.map((stageId, i) => {
      let status: PipelineStepStatus;
      let sublabel: string | undefined;
      const stageToolCount = toolCalls.filter((tc) => {
        // Associate tool calls to stages by name heuristics
        if (stageId === "intake") return tc.name === "fetch_sample";
        if (stageId === "preprocess") return tc.name === "chat_analysis" || tc.name === "preprocess_apply";
        if (stageId === "rag") return tc.name === "rag_query";
        if (stageId === "report") return tc.name === "create_report";
        return false;
      }).length;

      if (state === "error" && errorStep && stageId === subPhaseToStageKey(errorStep as RunningSubPhase)) {
        status = "failed";
        sublabel = `Failed — ${errorMessage?.slice(0, 40)}`;
      } else if (state === "needs-user" && stageId === "preprocess") {
        status = "needs-user";
        sublabel = `Awaiting approval — ${hitlProposal?.column ?? ""}`;
      } else if (completed.has(stageId) || state === "success") {
        status = "success";
      } else if (i === currentIdx && state === "running") {
        status = "running";
        sublabel = "Processing...";
      } else {
        status = "queued";
      }

      return {
        id: stageId,
        label: STAGE_LABELS[stageId] ?? stageId,
        status,
        sublabel,
        toolCount: status === "success" || status === "running" ? stageToolCount : undefined,
      };
    });
  })();

  const derivedDecisionChips: DecisionChip[] = (() => {
    if (state === "empty" || state === "uploading") return [];
    const CHIP_STAGES = ["Preprocess", "RAG", "Viz", "Report", "Mode"] as const;
    const completed = completedStagesRef.current;
    const stageKeyMap: Record<string, string> = {
      Preprocess: "preprocess",
      RAG: "rag",
      Viz: "viz",
      Report: "report",
    };

    return CHIP_STAGES.map((stage): DecisionChip => {
      if (stage === "Mode") return { stage, value: "Full" as ChipValue };

      const key = stageKeyMap[stage] ?? "";
      let value: ChipValue;

      if (state === "needs-user" && stage === "Preprocess") {
        value = "BLOCKED";
      } else if (state === "error" && errorStep && key === subPhaseToStageKey(errorStep as RunningSubPhase)) {
        value = "FAILED";
      } else if (state === "success" || completed.has(key)) {
        value = "DONE";
      } else {
        const currentKey = subPhaseToStageKey(runningSubPhase);
        const currentIdx = STAGES.indexOf(currentKey as typeof STAGES[number]);
        const stageIdx = STAGES.indexOf(key as typeof STAGES[number]);
        if (state === "running" && stageIdx === currentIdx) {
          value = "RUNNING";
        } else if (stageIdx > currentIdx) {
          value = "ON";
        } else {
          value = "ON";
        }
      }

      return { stage, value };
    });
  })();

  const derivedEvidence: EvidenceFooterProps = (() => {
    const cols = sampleData?.columns?.length ?? 0;
    const rows = sampleData?.rows?.length ?? 0;
    return {
      data: fileName || "-",
      scope: sampleData ? `${rows}x${cols}` : "-",
      compute: `v3 · ${formatElapsed(elapsedSeconds)}`,
      rag: ragResponse ? `${ragResponse.retrieved_chunks.length} chunks` : "OFF",
    };
  })();

  return {
    state,
    runningSubPhase,
    uploadProgress,
    elapsedSeconds,

    reportSections,
    toolCalls,
    runStatus: derivedRunStatus,
    pipelineSteps: derivedPipelineSteps,
    decisionChips: derivedDecisionChips,
    evidence: derivedEvidence,
    milestones,
    history,
    hitlProposal,
    rawLogs,

    startUpload,
    startWithSample,
    handleApprove,
    handleReject,
    handleEditInstruction,
    handleRetry,
    handleSend,
    handleCancel,
    reset,

    fileName,
    sourceId,
    sessionId,
  };
}
