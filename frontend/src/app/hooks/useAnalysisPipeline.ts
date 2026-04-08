import { useState, useEffect, useRef, useCallback } from "react";
import {
  uploadFile,
  buildApiUrl,
  deleteDataset,
  resumeChatRun,
  fetchEdaSummary,
  fetchEdaQuality,
  fetchEdaCorrelations,
  fetchEdaOutliers,
  fetchEdaInsights,
  type DatasetResponse,
  type ChatResponse,
  type ChatHistoryMessage,
  type PendingApprovalPayload,
  type ThoughtStepPayload,
} from "../../lib/api";
import {
  parseVisualizationResult,
  type VisualizationResultPayload,
} from "../../lib/visualization";
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
import {
  buildPreEdaProfile,
  type PreEdaProfile,
  type PreprocessRecommendation,
} from "../lib/preEdaProfile";

/* ─────────────────────────────────────────────
   Types
───────────────────────────────────────────── */

export type PipelineState =
  | "empty"
  | "uploading"
  | "ready"
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

export interface UploadedDatasetMeta {
  datasetId: number;
  sourceId: string;
  fileName: string;
  uploadedAt: string;
  preEdaProfile: PreEdaProfile | null;
  preprocessApproved: boolean;
}

export type PipelineSessionStateHint = "empty" | "ready" | "success" | "error" | "needs-user";

export interface PipelineSessionContext {
  backendSessionId: number | null;
  runId: string | null;
  traceId: string | null;
  fileName: string;
  uploadedDatasets: UploadedDatasetMeta[];
  selectedSourceId: string | null;
  chatHistory: ChatHistoryMessage[];
  latestAssistantAnswer: string | null;
  latestVisualizationResult: VisualizationResultPayload | null;
  pendingApproval: PendingApprovalPayload | null;
  stateHint: PipelineSessionStateHint;
  errorMessage: string | null;
}

interface LastQuestionRequest {
  question: string;
  sourceId: string | null;
}

interface ThoughtStep {
  phase: string;
  message: string;
  status?: "active" | "completed" | "failed";
  displayMessage: string;
  detailMessage?: string;
  audience?: "user" | "debug";
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
  thoughtSteps: ThoughtStep[];
  chatHistory: ChatHistoryMessage[];
  milestones: HistoryItem[];
  history: HistoryItem[];
  runId: string | null;
  pendingApproval: PendingApprovalPayload | null;
  rawLogs: RawLogEntry[];
  latestVisualizationResult: VisualizationResultPayload | null;
  selectedPreEdaProfile: PreEdaProfile | null;

  // Upload selection
  uploadedDatasets: UploadedDatasetMeta[];
  selectedSourceId: string | null;
  selectUploadedDataset: (sourceId: string | null) => void;
  removeUploadedDataset: (sourceId: string) => Promise<void>;

  // Actions
  startUpload: (file: File) => void;
  resumeRun: (decision: "approve" | "revise" | "cancel", instruction?: string) => void;
  handleApprove: () => void;
  handleReject: () => void;
  handleEditInstruction: (text: string) => void;
  handleRetry: () => void;
  handleSend: (message: string) => void;
  handleCancel: () => void;
  reset: () => void;
  captureSessionContext: () => PipelineSessionContext;
  restoreSessionContext: (context: PipelineSessionContext) => void;
  clearForNewDraft: () => void;

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
  intake: "질문 확인",
  preprocess: "데이터 준비",
  rag: "참고 정보 확인",
  viz: "시각화",
  merge: "결과 정리",
  report: "리포트",
};

/** Map RunningSubPhase to STAGES index key */
function subPhaseToStageKey(phase: RunningSubPhase): string {
  if (phase === "preprocessing") return "preprocess";
  if (phase === "visualization") return "viz";
  return phase;
}

function mapThoughtPhaseToSubPhase(phase: string): RunningSubPhase {
  if (phase === "analysis" || phase === "intake") return "intake";
  if (phase.startsWith("preprocess") || phase === "intent") return "preprocessing";
  if (phase.startsWith("rag")) return "rag";
  if (phase.startsWith("visualization")) return "visualization";
  if (phase.startsWith("report")) return "report";
  return "intake";
}

function now(): string {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function createTraceId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `trace-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
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

function makeRawLog(
  label: string,
  payload: Record<string, unknown>,
  isError?: boolean,
  traceId?: string | null,
): RawLogEntry {
  return {
    id: crypto.randomUUID(),
    label,
    traceId: traceId ?? undefined,
    payload: JSON.stringify(payload, null, 2),
    isError,
  };
}

function buildLocalPreprocessPendingApproval(
  recommendation: PreprocessRecommendation,
  sourceId: string,
): PendingApprovalPayload {
  return {
    stage: "preprocess",
    kind: "plan_review",
    title: "Preprocess plan review",
    summary: `${recommendation.column} 컬럼의 결측 ${recommendation.missingCount}건 (${recommendation.missingPercent.toFixed(1)}%)을 ${
      recommendation.strategy
    } 방식으로 처리한 뒤 Deep EDA를 진행합니다.`,
    source_id: sourceId,
    plan: {
      operations: [
        {
          op: "impute",
          column: recommendation.column,
          strategy: recommendation.strategy,
          fill_value: recommendation.fillValue,
          missing_count: recommendation.missingCount,
          missing_percent: recommendation.missingPercent,
        },
      ],
      planner_comment: `추천 전략: ${recommendation.strategy} -> ${recommendation.fillValue}`,
      top_missing_columns: [
        {
          column: recommendation.column,
          missing_rate: recommendation.missingPercent / 100,
        },
      ],
      affected_columns: [recommendation.column],
      row_count: null,
    },
  };
}

function parseThoughtStep(payload: unknown): ThoughtStep | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const data = payload as Record<string, unknown>;
  const message = typeof data.message === "string" ? data.message.trim() : "";
  if (!message) {
    return null;
  }
  const phase =
    typeof data.phase === "string" && data.phase.trim()
      ? data.phase.trim()
      : "analysis";
  const status =
    data.status === "active" || data.status === "completed" || data.status === "failed"
      ? data.status
      : undefined;
  const displayMessage =
    typeof data.display_message === "string" && data.display_message.trim()
      ? data.display_message.trim()
      : message;
  const detailMessage =
    typeof data.detail_message === "string" && data.detail_message.trim()
      ? data.detail_message.trim()
      : undefined;
  const audience =
    data.audience === "user" || data.audience === "debug"
      ? data.audience
      : undefined;
  return { phase, message, status, displayMessage, detailMessage, audience };
}

function pickVisualizationResultFromDoneRecord(
  record: Record<string, unknown>,
): VisualizationResultPayload | null {
  const direct = parseVisualizationResult(record.visualization_result);
  if (direct) {
    return direct;
  }

  const reportResult = record.report_result;
  if (!reportResult || typeof reportResult !== "object") {
    return null;
  }
  const report = reportResult as Record<string, unknown>;
  const visualizations = report.visualizations;
  if (!Array.isArray(visualizations) || visualizations.length === 0) {
    return null;
  }

  for (const candidate of visualizations) {
    const parsed = parseVisualizationResult(candidate);
    if (parsed) {
      return parsed;
    }
  }
  return null;
}

function parsePendingApproval(payload: unknown): PendingApprovalPayload | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const data = payload as Record<string, unknown>;
  const stageRaw = data.stage;
  if (stageRaw !== "preprocess" && stageRaw !== "visualization" && stageRaw !== "report") {
    return null;
  }
  const stage = stageRaw;
  const planRaw = data.plan;
  const plan = planRaw && typeof planRaw === "object"
    ? (planRaw as Record<string, unknown>)
    : {};

  if (stage === "report") {
    return {
      stage: "report",
      kind: "draft_review",
      title:
        typeof data.title === "string" && data.title.trim()
          ? data.title
          : "Report draft review",
      summary:
        typeof data.summary === "string" && data.summary.trim()
          ? data.summary
          : "리포트 초안을 검토한 뒤 승인 여부를 결정해 주세요.",
      source_id: typeof data.source_id === "string" ? data.source_id : "",
      draft: typeof data.draft === "string" ? data.draft : "",
      review: data.review && typeof data.review === "object"
        ? (data.review as { revision_count?: number })
        : undefined,
      plan: {},
    };
  }

  if (stage === "visualization") {
    const previewRows = Array.isArray(plan.preview_rows)
      ? plan.preview_rows
          .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
          .map((item) =>
            Object.fromEntries(
              Object.entries(item).map(([key, value]) => [
                key,
                typeof value === "string" ||
                typeof value === "number" ||
                typeof value === "boolean" ||
                value === null
                  ? value
                  : String(value),
              ]),
            ),
          )
      : [];

    return {
      stage: "visualization",
      kind: "plan_review",
      title:
        typeof data.title === "string" && data.title.trim()
          ? data.title
          : "Visualization plan review",
      summary:
        typeof data.summary === "string" && data.summary.trim()
          ? data.summary
          : "시각화 계획을 검토한 뒤 승인 여부를 결정해 주세요.",
      source_id: typeof data.source_id === "string" ? data.source_id : "",
      plan: {
        chart_type: typeof plan.chart_type === "string" ? plan.chart_type : "",
        x_key: typeof plan.x_key === "string" ? plan.x_key : "",
        y_key: typeof plan.y_key === "string" ? plan.y_key : "",
        mode: typeof plan.mode === "string" ? plan.mode : undefined,
        reason: typeof plan.reason === "string" ? plan.reason : undefined,
        x_is_datetime: typeof plan.x_is_datetime === "boolean" ? plan.x_is_datetime : undefined,
        preview_rows: previewRows,
      },
    };
  }

  const topMissingColumns = Array.isArray(plan.top_missing_columns)
    ? plan.top_missing_columns
        .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
        .map((item) => ({
          column: typeof item.column === "string" ? item.column : "",
          missing_rate: typeof item.missing_rate === "number" ? item.missing_rate : 0,
        }))
        .filter((item) => item.column)
    : [];

  const affectedColumns = Array.isArray(plan.affected_columns)
    ? plan.affected_columns.filter(
        (item): item is string => typeof item === "string" && item.trim().length > 0,
      )
    : [];

  const operations = Array.isArray(plan.operations)
    ? plan.operations.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    : [];

  return {
    stage: "preprocess",
    kind: "plan_review",
    title: typeof data.title === "string" && data.title.trim() ? data.title : "Preprocess plan review",
    summary:
      typeof data.summary === "string" && data.summary.trim()
        ? data.summary
        : "전처리 계획을 검토한 뒤 승인 여부를 결정해 주세요.",
    source_id: typeof data.source_id === "string" ? data.source_id : "",
    plan: {
      operations,
      planner_comment:
        typeof plan.planner_comment === "string" && plan.planner_comment.trim()
          ? plan.planner_comment
          : undefined,
      top_missing_columns: topMissingColumns,
      affected_columns: affectedColumns,
      row_count: typeof plan.row_count === "number" ? plan.row_count : null,
    },
  };
}

function approvalStageToSubPhase(
  stage: PendingApprovalPayload["stage"],
): RunningSubPhase {
  if (stage === "visualization") {
    return "visualization";
  }
  if (stage === "report") {
    return "report";
  }
  return "preprocessing";
}

function approvalStageCompletedStages(
  stage: PendingApprovalPayload["stage"],
): Set<string> {
  if (stage === "visualization") {
    return new Set(["intake", "preprocess", "rag"]);
  }
  if (stage === "report") {
    return new Set(["intake", "preprocess", "rag", "merge"]);
  }
  return new Set(["intake"]);
}

function approvalStageLabel(stage: PendingApprovalPayload["stage"]): string {
  if (stage === "visualization") {
    return "Visualization";
  }
  if (stage === "report") {
    return "Report";
  }
  return "Preprocess";
}

function approvalStageNeedsUserTitle(stage: PendingApprovalPayload["stage"]): string {
  if (stage === "report") {
    return "Report draft ready";
  }
  return "Approval required";
}

function approvalStageRevisionTitle(stage: PendingApprovalPayload["stage"]): string {
  if (stage === "report") {
    return "Report revision requested";
  }
  if (stage === "visualization") {
    return "Visualization revision requested";
  }
  return "Revision requested";
}

function approvalStageCancelTitle(stage: PendingApprovalPayload["stage"]): string {
  if (stage === "report") {
    return "Report cancelled";
  }
  return "Run cancelled";
}

function formatPendingValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join(", ");
  }
  if (typeof value === "string") {
    return value;
  }
  if (
    typeof value === "number" ||
    typeof value === "boolean" ||
    value === null
  ) {
    return String(value);
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  return "";
}

function formatPendingOperation(operation: Record<string, unknown>): string {
  const op = typeof operation.op === "string" && operation.op.trim() ? operation.op : "operation";
  const details = Object.entries(operation)
    .filter(([key, value]) => key !== "op" && value !== undefined && value !== "")
    .map(([key, value]) => `${key}: ${formatPendingValue(value)}`)
    .filter((value) => value.trim());

  return details.length > 0 ? `${op} (${details.join(" · ")})` : op;
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

  // --- Session / streaming state ---
  const [fileName, setFileName] = useState("");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [traceId, setTraceId] = useState<string | null>(null);
  const [chatResponse, setChatResponse] = useState<ChatResponse | null>(null);
  const [streamingAnswer, setStreamingAnswer] = useState("");
  const [thoughtSteps, setThoughtSteps] = useState<ThoughtStep[]>([]);
  const [latestVisualizationResult, setLatestVisualizationResult] = useState<VisualizationResultPayload | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatHistoryMessage[]>([]);
  const [pendingApproval, setPendingApproval] = useState<PendingApprovalPayload | null>(null);

  // --- Upload selection state ---
  const [uploadedDatasets, setUploadedDatasets] = useState<UploadedDatasetMeta[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);

  // --- Pipeline tracking ---
  const [toolCalls, setToolCalls] = useState<ToolCallEntry[]>([]);
  const [milestones, setMilestones] = useState<HistoryItem[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [rawLogs, setRawLogs] = useState<RawLogEntry[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorStep, setErrorStep] = useState<string | null>(null);

  // --- Completed stage tracking ---
  const completedStagesRef = useRef<Set<string>>(new Set());

  // --- Abort / retry refs ---
  const abortRef = useRef<AbortController | null>(null);
  const lastQuestionRef = useRef<LastQuestionRequest | null>(null);
  const localMessageIdRef = useRef(0);
  const nextLocalMessageId = useCallback(() => {
    localMessageIdRef.current += 1;
    return Date.now() + localMessageIdRef.current;
  }, []);

  // --- Elapsed timer ---
  useEffect(() => {
    let iv: ReturnType<typeof setInterval>;
    if (state === "running" || state === "needs-user") {
      iv = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    } else if (state === "empty" || state === "ready") {
      setElapsedSeconds(0);
    }
    return () => clearInterval(iv);
  }, [state]);

  /* ─── State helpers ─── */

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

  const upsertUploadedDataset = useCallback((nextDataset: UploadedDatasetMeta) => {
    setUploadedDatasets((prev) => {
      const index = prev.findIndex((item) => item.sourceId === nextDataset.sourceId);
      if (index < 0) {
        return [...prev, nextDataset];
      }
      const next = [...prev];
      next[index] = nextDataset;
      return next;
    });
  }, []);

  const updateUploadedDataset = useCallback(
    (sourceId: string, updater: (current: UploadedDatasetMeta) => UploadedDatasetMeta) => {
      setUploadedDatasets((prev) =>
        prev.map((item) => (item.sourceId === sourceId ? updater(item) : item)),
      );
    },
    [],
  );

  const appendThoughtStep = useCallback(
    (step: ThoughtStep) => {
      setThoughtSteps((prev) => {
        if (prev.some((item) => item.phase === step.phase && item.message === step.message)) {
          return prev;
        }
        return [...prev, step];
      });

      const subPhase = mapThoughtPhaseToSubPhase(step.phase);
      setRunningSubPhase(subPhase);

      if (step.status === "completed") {
        markStageCompleted(subPhaseToStageKey(subPhase));
      }
    },
    [markStageCompleted],
  );

  const consumeSseResponse = useCallback(
    async ({
      response,
      tc,
      startMs,
      requestTraceId,
      question,
      successMilestoneTitle,
      successMilestoneSubtext,
    }: {
      response: Response;
      tc: ToolCallEntry;
      startMs: number;
      requestTraceId: string;
      question?: string;
      successMilestoneTitle?: string;
      successMilestoneSubtext?: string;
    }) => {
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || "채팅 요청에 실패했습니다.");
      }

      if (!response.body) {
        throw new Error("스트리밍 응답을 받을 수 없습니다.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let streamText = "";
      let finalAnswer = "";
      let doneReceived = false;
      let approvalReceived = false;
      let activeTraceId = requestTraceId;
      let terminalErrorStep: string | null = null;
      let terminalErrorMessage: string | null = null;

      const handleEvent = (rawEvent: string) => {
        const lines = rawEvent.split("\n");
        let eventName = "message";
        const dataLines: string[] = [];

        for (const line of lines) {
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trim());
          }
        }

        const rawData = dataLines.join("\n");
        let payload: unknown = {};
        if (rawData) {
          try {
            payload = JSON.parse(rawData);
          } catch {
            payload = { message: rawData };
          }
        }

        const record = payload && typeof payload === "object"
          ? (payload as Record<string, unknown>)
          : {};

        if (eventName === "session") {
          const nextTraceId = record.trace_id;
          if (typeof nextTraceId === "string" && nextTraceId.trim()) {
            activeTraceId = nextTraceId;
            setTraceId(nextTraceId);
          }
          const nextSession = record.session_id;
          if (typeof nextSession === "number") {
            setSessionId(nextSession);
          }
          const nextRunId = record.run_id;
          if (typeof nextRunId === "string" && nextRunId.trim()) {
            setRunId(nextRunId);
          }
          addLog(
            makeRawLog(
              "sse: session",
              {
                session_id: nextSession,
                run_id: nextRunId,
                trace_id: activeTraceId,
              },
              false,
              activeTraceId,
            ),
          );
          return;
        }

        if (eventName === "thought") {
          addLog(makeRawLog("sse: thought", record, false, activeTraceId));
          const step = parseThoughtStep(record);
          if (step) {
            appendThoughtStep(step);
          }
          return;
        }

        if (eventName === "chunk") {
          const delta = record.delta;
          if (typeof delta === "string" && delta) {
            streamText += delta;
            setStreamingAnswer((prev) => prev + delta);
          }
          return;
        }

        if (eventName === "approval_required") {
          approvalReceived = true;

          const nextTraceId = record.trace_id;
          if (typeof nextTraceId === "string" && nextTraceId.trim()) {
            activeTraceId = nextTraceId;
            setTraceId(nextTraceId);
          }

          const nextSession = record.session_id;
          if (typeof nextSession === "number") {
            setSessionId(nextSession);
          }

          const nextRunId = record.run_id;
          if (typeof nextRunId === "string" && nextRunId.trim()) {
            setRunId(nextRunId);
          }

          const pending = parsePendingApproval(record.pending_approval);
          if (!pending) {
            throw new Error("승인 대기 payload를 해석할 수 없습니다.");
          }

          const approvalThoughts = record.thought_steps;
          if (Array.isArray(approvalThoughts)) {
            for (const item of approvalThoughts) {
              const step = parseThoughtStep(item);
              if (step) {
                appendThoughtStep(step);
              }
            }
          }

          setPendingApproval(pending);
          setStreamingAnswer("");
          setChatResponse(null);
          setState("needs-user");
          setRunningSubPhase(approvalStageToSubPhase(pending.stage));
          if (pending.stage === "report") {
            const nextCompletedStages = new Set(completedStagesRef.current);
            nextCompletedStages.add("merge");
            completedStagesRef.current = nextCompletedStages;
          } else {
            completedStagesRef.current = approvalStageCompletedStages(pending.stage);
          }

          updateToolCall(tc.id, {
            status: "needs-user",
            result: pending.summary,
            duration: `${((Date.now() - startMs) / 1000).toFixed(1)}s`,
          });
          addMilestone({
            status: "needs-user",
            title: approvalStageNeedsUserTitle(pending.stage),
            subtext: pending.title,
            timestamp: now(),
            selected: true,
          });
          addLog(
            makeRawLog(
              "sse: approval_required",
              {
                trace_id: activeTraceId,
                session_id: nextSession,
                run_id: nextRunId,
                pending_approval: pending,
              },
              false,
              activeTraceId,
            ),
          );
          return;
        }

        if (eventName === "done") {
          doneReceived = true;
          const nextTraceId = record.trace_id;
          if (typeof nextTraceId === "string" && nextTraceId.trim()) {
            activeTraceId = nextTraceId;
            setTraceId(nextTraceId);
          }
          const answer = typeof record.answer === "string" ? record.answer : streamText;
          const outputType = typeof record.output_type === "string" ? record.output_type : null;
          const isReportFailure = outputType === "report_failed";
          finalAnswer = answer;
          setStreamingAnswer(answer);
          setPendingApproval(null);
          if (isReportFailure) {
            terminalErrorStep = "report";
            terminalErrorMessage = answer.trim() || "리포트 생성에 실패했습니다.";
          }

          const nextSession = record.session_id;
          const resolvedSessionId = typeof nextSession === "number" ? nextSession : sessionId;
          if (typeof resolvedSessionId === "number") {
            setSessionId(resolvedSessionId);
          }

          const nextRunId = record.run_id;
          if (typeof nextRunId === "string" && nextRunId.trim()) {
            setRunId(nextRunId);
          }

          const doneThoughts = record.thought_steps;
          if (Array.isArray(doneThoughts)) {
            for (const item of doneThoughts) {
              const step = parseThoughtStep(item);
              if (step) {
                appendThoughtStep(step);
              }
            }
          }

          if (typeof resolvedSessionId === "number") {
            setChatResponse({
              answer,
              session_id: resolvedSessionId,
              run_id: typeof nextRunId === "string" ? nextRunId : undefined,
              trace_id: activeTraceId,
              thought_steps: Array.isArray(doneThoughts) ? doneThoughts as ThoughtStepPayload[] : [],
            });
          }

          if (answer.trim()) {
            setChatHistory((prev) => [
              ...prev,
              {
                id: nextLocalMessageId(),
                role: "assistant",
                content: answer,
                created_at: new Date().toISOString(),
              },
            ]);
          }

          const visualizationResult = pickVisualizationResultFromDoneRecord(record);
          if (visualizationResult) {
            setLatestVisualizationResult(visualizationResult);
          }

          const preprocessResult = record.preprocess_result;
          if (preprocessResult && typeof preprocessResult === "object") {
            const preprocess = preprocessResult as Record<string, unknown>;
            if (
              preprocess.status === "applied" &&
              typeof preprocess.output_source_id === "string" &&
              preprocess.output_source_id
            ) {
              setSelectedSourceId(preprocess.output_source_id);
              upsertUploadedDataset({
                datasetId: 0,
                sourceId: preprocess.output_source_id,
                fileName:
                  typeof preprocess.output_filename === "string" && preprocess.output_filename
                    ? preprocess.output_filename
                    : `processed_${preprocess.output_source_id}`,
                uploadedAt: new Date().toISOString(),
                preEdaProfile: null,
                preprocessApproved: true,
              });
            }
          }

          addLog(
            makeRawLog(
              "sse: done",
              {
                trace_id: activeTraceId,
                run_id: typeof nextRunId === "string" ? nextRunId : null,
                output_type: outputType,
                answer_length: answer.length,
              },
              isReportFailure,
              activeTraceId,
            ),
          );
          if (!isReportFailure) {
            setState("success");
          }
          return;
        }

        if (eventName === "error") {
          const nextTraceId = record.trace_id;
          if (typeof nextTraceId === "string" && nextTraceId.trim()) {
            activeTraceId = nextTraceId;
            setTraceId(nextTraceId);
          }
          addLog(makeRawLog("sse: error", record, true, activeTraceId));
          const message = typeof record.message === "string"
            ? record.message
            : "스트리밍 처리 중 오류가 발생했습니다.";
          throw new Error(message);
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
        while (true) {
          const separatorIndex = buffer.indexOf("\n\n");
          if (separatorIndex < 0) {
            break;
          }
          const rawEvent = buffer.slice(0, separatorIndex).trim();
          buffer = buffer.slice(separatorIndex + 2);
          if (!rawEvent) {
            continue;
          }
          handleEvent(rawEvent);
        }
      }

      const tail = decoder.decode();
      if (tail) {
        buffer += tail.replace(/\r\n/g, "\n");
      }
      if (buffer.trim()) {
        handleEvent(buffer.trim());
      }

      if (approvalReceived) {
        return;
      }

      if (terminalErrorMessage) {
        updateToolCall(tc.id, failToolCall(tc, terminalErrorMessage, startMs));
        transitionToError(terminalErrorStep ?? "chat_stream", terminalErrorMessage);
        return;
      }

      const finalText = (finalAnswer || streamText).trim();
      if (!doneReceived && finalText) {
        setStreamingAnswer(finalText);
        if (sessionId !== null) {
          setChatResponse({
            answer: finalText,
            session_id: sessionId,
            trace_id: activeTraceId,
            thought_steps: [],
          });
        }
        setChatHistory((prev) => [
          ...prev,
          {
            id: nextLocalMessageId(),
            role: "assistant",
            content: finalText,
            created_at: new Date().toISOString(),
          },
        ]);
        setState("success");
        addLog(
          makeRawLog(
            "sse: done",
            {
              trace_id: activeTraceId,
              run_id: runId,
              output_type: null,
              answer_length: finalText.length,
            },
            false,
            activeTraceId,
          ),
        );
      }

      updateToolCall(tc.id, completeToolCall(tc, finalText.slice(0, 80) || "stream done", startMs));
      if (successMilestoneTitle) {
        addMilestone({
          status: "completed",
          title: successMilestoneTitle,
          subtext: successMilestoneSubtext ?? question?.slice(0, 40),
          timestamp: now(),
        });
      }
    },
    [
      addLog,
      addMilestone,
      appendThoughtStep,
      nextLocalMessageId,
      runId,
      sessionId,
      updateToolCall,
      upsertUploadedDataset,
      transitionToError,
    ],
  );

  /* ─── Actions ─── */

  const selectUploadedDataset = useCallback(
    (sourceId: string | null) => {
      setSelectedSourceId(sourceId);
      if (!sourceId) {
        return;
      }
      const selected = uploadedDatasets.find((item) => item.sourceId === sourceId);
      if (selected) {
        setFileName(selected.fileName);
      }
    },
    [uploadedDatasets],
  );

  const removeUploadedDataset = useCallback(
    async (sourceId: string) => {
      await deleteDataset(sourceId);

      const nextDatasets = uploadedDatasets.filter((item) => item.sourceId !== sourceId);
      setUploadedDatasets(nextDatasets);

      if (selectedSourceId === sourceId) {
        setSelectedSourceId(null);
        setFileName("");
      } else if (nextDatasets.length === 0) {
        setFileName("");
      }

      if (state === "ready" && nextDatasets.length === 0) {
        setState("empty");
      }

      addMilestone({
        status: "completed",
        title: "Dataset deleted",
        subtext: sourceId,
        timestamp: now(),
      });
    },
    [uploadedDatasets, selectedSourceId, state, addMilestone],
  );

  const startUpload = useCallback(
    (file: File) => {
      setChatResponse(null);
      setStreamingAnswer("");
      setThoughtSteps([]);
      setErrorMessage(null);
      setErrorStep(null);
      setRunId(null);
      setPendingApproval(null);
      setUploadProgress(0);
      setFileName(file.name);

      if (!file.name.toLowerCase().endsWith(".csv")) {
        transitionToError("upload", "CSV 파일만 업로드할 수 있습니다.");
        return;
      }

      setState("uploading");

      const uploadedAt = new Date().toISOString();
      // 로컬 프로파일은 서버 EDA 실패 시 폴백용으로 병렬 준비
      const localProfilePromise = buildPreEdaProfile(file).catch(() => null);

      uploadFile(file, (percent) => {
        setUploadProgress(percent);
      })
        .then(async (dataset: DatasetResponse) => {
          setUploadProgress(100);
          setRunningSubPhase("intake");
          setFileName(dataset.filename || file.name);
          setSelectedSourceId(dataset.source_id);

          addMilestone({
            status: "completed",
            title: "Upload complete",
            subtext: `${dataset.filename} · ${dataset.source_id}`,
            timestamp: now(),
          });

          // 서버 EDA 우선 조회 시도
          let preEdaProfile: PreEdaProfile | null = null;
          try {
            const [summaryRes, qualityRes, corrRes, outlierRes, insightRes] =
              await Promise.all([
                fetchEdaSummary(dataset.source_id),
                fetchEdaQuality(dataset.source_id),
                fetchEdaCorrelations(dataset.source_id),
                fetchEdaOutliers(dataset.source_id),
                fetchEdaInsights(dataset.source_id),
              ]);

            const summary = summaryRes.data;
            const quality = qualityRes.data;
            const correlations = corrRes.data;
            const outliers = outlierRes.data;
            const insight = insightRes.data;

            preEdaProfile = {
              sourceLabel: dataset.filename || file.name,
              uploadedAt,
              rowCount: summary.row_count,
              columnCount: summary.column_count,
              columns: [
                ...summary.numeric_columns,
                ...summary.categorical_columns,
                ...summary.datetime_columns,
                ...summary.boolean_columns,
                ...summary.identifier_columns,
                ...summary.group_key_columns,
              ],
              sampleRows: [], // 서버 EDA는 sampleRows 미포함 — fetchSample로 별도 조회 가능
              numericColumns: summary.numeric_columns,
              categoricalColumns: summary.categorical_columns,
              datetimeColumns: summary.datetime_columns,
              identifierColumns: summary.identifier_columns,
              booleanColumns: summary.boolean_columns,
              groupKeyColumns: summary.group_key_columns,
              groupKeyCandidates: summary.group_key_columns,
              columnRoleSummaries: [],
              missingColumns: quality.missing_columns.map((c) => ({
                column: c.column,
                missingCount: c.missing_count,
                missingRate: c.missing_rate,
              })),
              topMissingColumns: quality.missing_columns
                .sort((a, b) => b.missing_rate - a.missing_rate)
                .slice(0, 3)
                .map((c) => ({
                  column: c.column,
                  missingCount: c.missing_count,
                  missingRate: c.missing_rate,
                })),
              numericSnapshots: [],
              numericColumnStats: [],
              distributions: [],
              correlationTopPairs: correlations.top_pairs.map((p) => ({
                left: p.col_a,
                right: p.col_b,
                value: p.correlation,
              })),
              outlierSummaries: outliers.outlier_columns.map((o) => ({
                column: o.column,
                outlierCount: o.outlier_count,
                outlierRate: 0,
                lowerBound: o.lower_bound,
                upperBound: o.upper_bound,
              })),
              qualitySummary: summary.quality_summary,
              summaryBullets: summary.summary_bullets,
              recommendation: insight.preprocess_recommendation
                ? {
                    column: insight.preprocess_recommendation.operations[0]?.target_columns[0] ?? "",
                    columnType: "categorical" as const,
                    strategy: insight.preprocess_recommendation.operations[0]?.op ?? "",
                    fillValue: "",
                    missingCount: 0,
                    missingPercent: 0,
                    rationale: "",
                    domainWarning: null,
                    alternativeStrategies: [],
                  }
                : null,
            };

            addMilestone({
              status: "completed",
              title: "Server EDA loaded",
              subtext: `${summary.row_count} rows · ${summary.column_count} cols`,
              timestamp: now(),
            });
          } catch {
            // 서버 EDA 미구현 또는 실패 → 로컬 프로파일로 폴백
            preEdaProfile = await localProfilePromise;
            addLog(makeRawLog("eda_fallback", {
              reason: "Server EDA unavailable, using local profile",
            }));
          }

          setState("ready");
          upsertUploadedDataset({
            datasetId: dataset.id,
            sourceId: dataset.source_id,
            fileName: dataset.filename || file.name,
            uploadedAt,
            preEdaProfile,
            preprocessApproved: !preEdaProfile?.recommendation,
          });
        })
        .catch((err: Error) => {
          transitionToError("upload", err.message);
        });
    },
    [addLog, addMilestone, transitionToError, upsertUploadedDataset],
  );

  const runQuestionStream = useCallback(
    (question: string, sourceIdOverride?: string | null) => {
      const requestSourceId = typeof sourceIdOverride === "string"
        ? (sourceIdOverride.trim() || null)
        : selectedSourceId;

      lastQuestionRef.current = {
        question,
        sourceId: requestSourceId,
      };

      setErrorMessage(null);
      setErrorStep(null);
      setState("running");
      setRunningSubPhase("intake");
      setStreamingAnswer("");
      setChatResponse(null);
      setThoughtSteps([]);
      setRunId(null);
      const nextTraceId = createTraceId();
      setTraceId(nextTraceId);
      setPendingApproval(null);
      completedStagesRef.current = new Set();

      const request: { question: string; session_id?: number; source_id?: string; trace_id: string } = {
        question,
        trace_id: nextTraceId,
      };
      if (sessionId !== null) request.session_id = sessionId;
      if (requestSourceId) request.source_id = requestSourceId;

      const tc = makeToolCall("chat_stream", request);
      addToolCall(tc);
      addLog(makeRawLog("tool_call: chat_stream", request, false, nextTraceId));

      const startMs = Date.now();
      const abortController = new AbortController();
      abortRef.current = abortController;

      void (async () => {
        try {
          const response = await fetch(buildApiUrl("/chats/stream"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(request),
            signal: abortController.signal,
          });

          await consumeSseResponse({
            response,
            tc,
            startMs,
            requestTraceId: nextTraceId,
            question,
            successMilestoneTitle: "Follow-up",
            successMilestoneSubtext: question.slice(0, 40),
          });
        } catch (error: unknown) {
          if (error instanceof DOMException && error.name === "AbortError") {
            return;
          }
          if (error instanceof Error && error.name === "AbortError") {
            return;
          }

          const message = error instanceof Error ? error.message : "채팅 요청에 실패했습니다.";
          updateToolCall(tc.id, failToolCall(tc, message, startMs));
          addLog(makeRawLog("tool_error: chat_stream", { error: message }, true, nextTraceId));
          transitionToError("chat_stream", message);
        } finally {
          abortRef.current = null;
        }
      })();
    },
    [
      sessionId,
      selectedSourceId,
      addToolCall,
      addLog,
      consumeSseResponse,
      transitionToError,
      updateToolCall,
    ],
  );

  const resumeRun = useCallback(
    (decision: "approve" | "revise" | "cancel", instruction?: string) => {
      if (sessionId === null || !runId || !pendingApproval) {
        return;
      }

      setErrorMessage(null);
      setErrorStep(null);
      setState("running");
      setRunningSubPhase(approvalStageToSubPhase(pendingApproval.stage));
      setStreamingAnswer("");
      setThoughtSteps([]);
      completedStagesRef.current = approvalStageCompletedStages(pendingApproval.stage);
      const nextTraceId = traceId || createTraceId();
      setTraceId(nextTraceId);

      const request = {
        decision,
        stage: pendingApproval.stage,
        instruction: instruction?.trim() || undefined,
        trace_id: nextTraceId,
      };

      const tc = makeToolCall("resume_run", request);
      addToolCall(tc);
      addLog(
        makeRawLog(
          "tool_call: resume_run",
          { session_id: sessionId, run_id: runId, ...request },
          false,
          nextTraceId,
        ),
      );

      const startMs = Date.now();
      const abortController = new AbortController();
      abortRef.current = abortController;

      void (async () => {
        try {
          const response = await resumeChatRun(
            sessionId,
            runId,
            request,
            abortController.signal,
          );

          await consumeSseResponse({
            response,
            tc,
            startMs,
            requestTraceId: nextTraceId,
            successMilestoneTitle:
              decision === "approve"
                ? `${approvalStageLabel(pendingApproval.stage)} approved`
                : decision === "revise"
                  ? approvalStageRevisionTitle(pendingApproval.stage)
                  : approvalStageCancelTitle(pendingApproval.stage),
            successMilestoneSubtext:
              decision === "approve"
                ? pendingApproval.title
                : instruction?.trim() || pendingApproval.title,
          });
        } catch (error: unknown) {
          if (error instanceof DOMException && error.name === "AbortError") {
            return;
          }
          if (error instanceof Error && error.name === "AbortError") {
            return;
          }

          const message = error instanceof Error ? error.message : "재개 요청에 실패했습니다.";
          updateToolCall(tc.id, failToolCall(tc, message, startMs));
          addLog(makeRawLog("tool_error: resume_run", { error: message }, true, nextTraceId));
          transitionToError("resume_run", message);
        } finally {
          abortRef.current = null;
        }
      })();
    },
    [
      sessionId,
      runId,
      pendingApproval,
      addToolCall,
      addLog,
      consumeSseResponse,
      traceId,
      transitionToError,
      updateToolCall,
    ],
  );

  const handleSend = useCallback(
    (message: string) => {
      const question = message.trim();
      if (!question || pendingApproval) return;

      lastQuestionRef.current = {
        question,
        sourceId: selectedSourceId,
      };

      setChatHistory((prev) => [
        ...prev,
        {
          id: nextLocalMessageId(),
          role: "user",
          content: question,
          created_at: new Date().toISOString(),
        },
      ]);

      setErrorMessage(null);
      setErrorStep(null);
      const selectedDataset =
        uploadedDatasets.find((item) => item.sourceId === selectedSourceId) ?? null;
      const recommendation = selectedDataset?.preEdaProfile?.recommendation ?? null;

      if (selectedSourceId && recommendation && !selectedDataset?.preprocessApproved) {
        setErrorMessage(null);
        setErrorStep(null);
        setChatResponse(null);
        setStreamingAnswer("");
        setThoughtSteps([]);
        setRunningSubPhase("preprocessing");
        setPendingApproval(buildLocalPreprocessPendingApproval(recommendation, selectedSourceId));
        setState("needs-user");
        completedStagesRef.current = new Set(["intake"]);
        return;
      }

      runQuestionStream(question, selectedSourceId);
    },
    [pendingApproval, nextLocalMessageId, uploadedDatasets, selectedSourceId, runQuestionStream],
  );

  const handleApprove = useCallback(() => {
    if (pendingApproval && sessionId !== null && runId) {
      resumeRun("approve");
      return;
    }

    setHistory((prev) => [
      ...prev,
      {
        status: "completed" as TimelineItemStatus,
        title: "Approved",
        subtext: pendingApproval?.title ?? "User confirmed strategy",
        timestamp: now(),
      },
    ]);

    if (pendingApproval?.source_id) {
      setSelectedSourceId(pendingApproval.source_id);
      updateUploadedDataset(pendingApproval.source_id, (current) => ({
        ...current,
        preprocessApproved: true,
      }));
    }

    setPendingApproval(null);

    if (lastQuestionRef.current?.question.trim()) {
      runQuestionStream(
        lastQuestionRef.current.question,
        pendingApproval?.source_id ?? lastQuestionRef.current.sourceId,
      );
      return;
    }

    setState(uploadedDatasets.length > 0 ? "ready" : "empty");
  }, [
    pendingApproval,
    sessionId,
    runId,
    resumeRun,
    setSelectedSourceId,
    updateUploadedDataset,
    runQuestionStream,
    uploadedDatasets.length,
  ]);

  const handleReject = useCallback(() => {
    setHistory((prev) => [
      ...prev,
      {
        status: "failed" as TimelineItemStatus,
        title:
          pendingApproval && sessionId !== null && runId
            ? approvalStageCancelTitle(pendingApproval.stage)
            : "Rejected Changes",
        subtext: pendingApproval?.title ?? "User cancelled action",
        timestamp: now(),
      },
    ]);

    if (pendingApproval && sessionId !== null && runId) {
      resumeRun("cancel");
      return;
    }

    setPendingApproval(null);
    setState(uploadedDatasets.length > 0 ? "ready" : "empty");
  }, [pendingApproval, sessionId, runId, resumeRun, uploadedDatasets.length]);

  const handleEditInstruction = useCallback((text: string) => {
    const nextText = text.trim();
    if (!nextText) {
      return;
    }

    setHistory((prev) => [
      ...prev,
      {
        status: "completed" as TimelineItemStatus,
        title:
          pendingApproval && sessionId !== null && runId
            ? approvalStageRevisionTitle(pendingApproval.stage)
            : "User Edit",
        subtext: nextText,
        timestamp: now(),
      },
    ]);

    if (pendingApproval && sessionId !== null && runId) {
      resumeRun("revise", nextText);
    }
  }, [pendingApproval, sessionId, runId, resumeRun]);

  const handleRetry = useCallback(() => {
    if (!lastQuestionRef.current?.question) {
      setState(uploadedDatasets.length > 0 ? "ready" : "empty");
      return;
    }
    runQuestionStream(lastQuestionRef.current.question, lastQuestionRef.current.sourceId);
  }, [runQuestionStream, uploadedDatasets.length]);

  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setUploadProgress(0);
    setStreamingAnswer("");
    setThoughtSteps([]);
    setPendingApproval(null);
    setRunId(null);
    setState(uploadedDatasets.length > 0 ? "ready" : "empty");
  }, [uploadedDatasets.length]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setState("empty");
    setUploadProgress(0);
    setElapsedSeconds(0);
    setFileName("");
    setSessionId(null);
    setRunId(null);
    setTraceId(null);
    setChatResponse(null);
    setStreamingAnswer("");
    setThoughtSteps([]);
    setUploadedDatasets([]);
    setSelectedSourceId(null);
    setToolCalls([]);
    setMilestones([]);
    setHistory([]);
    setRawLogs([]);
    setErrorMessage(null);
    setErrorStep(null);
    setPendingApproval(null);
    setLatestVisualizationResult(null);
    setChatHistory([]);
    lastQuestionRef.current = null;
    localMessageIdRef.current = 0;
    completedStagesRef.current = new Set();
  }, []);

  const captureSessionContext = useCallback((): PipelineSessionContext => {
    const latestAssistantAnswer =
      typeof chatResponse?.answer === "string" && chatResponse.answer.trim()
        ? chatResponse.answer
        : null;

    let stateHint: PipelineSessionStateHint = "empty";
    if (state === "error") {
      stateHint = "error";
    } else if (state === "needs-user" && pendingApproval) {
      stateHint = "needs-user";
    } else if (state === "success") {
      stateHint = "success";
    } else if (state === "ready") {
      stateHint = "ready";
    } else if (state === "running" || state === "uploading") {
      if (latestAssistantAnswer) {
        stateHint = "success";
      } else if (uploadedDatasets.length > 0) {
        stateHint = "ready";
      } else {
        stateHint = "empty";
      }
    }

    return {
      backendSessionId: sessionId,
      runId,
      traceId,
      fileName,
      uploadedDatasets: [...uploadedDatasets],
      selectedSourceId,
      chatHistory,
      latestAssistantAnswer,
      latestVisualizationResult,
      pendingApproval,
      stateHint,
      errorMessage: stateHint === "error" ? errorMessage : null,
    };
  }, [
    chatResponse,
    state,
    pendingApproval,
    uploadedDatasets,
    sessionId,
    runId,
    traceId,
    fileName,
    selectedSourceId,
    chatHistory,
    latestVisualizationResult,
    errorMessage,
  ]);

  const restoreSessionContext = useCallback((context: PipelineSessionContext) => {
    abortRef.current?.abort();
    abortRef.current = null;

    const nextSessionId = context.backendSessionId ?? null;
    const nextRunId = context.runId ?? null;
    const nextTraceId = context.traceId ?? null;
    const nextUploadedDatasets = Array.isArray(context.uploadedDatasets)
      ? context.uploadedDatasets
      : [];
    const nextStateHint: PipelineSessionStateHint = context.stateHint ?? "empty";
    const nextPendingApproval = context.pendingApproval ?? null;
    const latestAnswer =
      typeof context.latestAssistantAnswer === "string" && context.latestAssistantAnswer.trim()
        ? context.latestAssistantAnswer
        : null;

    setSessionId(nextSessionId);
    setRunId(nextRunId);
    setTraceId(nextTraceId);
    setFileName(context.fileName || "");
    setUploadedDatasets(nextUploadedDatasets);
    setSelectedSourceId(context.selectedSourceId ?? null);
    setLatestVisualizationResult(context.latestVisualizationResult ?? null);
    setChatHistory(context.chatHistory || []);

    setUploadProgress(0);
    setElapsedSeconds(0);
    setRunningSubPhase("intake");
    setStreamingAnswer("");
    setThoughtSteps([]);
    setToolCalls([]);
    setMilestones([]);
    setHistory([]);
    setRawLogs([]);
    setPendingApproval(nextPendingApproval);
    setErrorStep(null);

    if (nextStateHint === "error") {
      setErrorMessage(context.errorMessage ?? "세션에서 오류 상태를 복원했습니다.");
    } else {
      setErrorMessage(null);
    }

    if (latestAnswer && typeof nextSessionId === "number") {
      setChatResponse({
        answer: latestAnswer,
        session_id: nextSessionId,
        trace_id: nextTraceId ?? undefined,
        thought_steps: [],
      });
    } else {
      setChatResponse(null);
    }

    if (nextStateHint === "success") {
      setState("success");
    } else if (nextStateHint === "needs-user" && nextPendingApproval) {
      setState("needs-user");
      setRunningSubPhase(approvalStageToSubPhase(nextPendingApproval.stage));
      completedStagesRef.current = approvalStageCompletedStages(nextPendingApproval.stage);
    } else if (nextStateHint === "ready") {
      setState("ready");
    } else if (nextStateHint === "error") {
      setState("error");
    } else {
      setState("empty");
    }

    lastQuestionRef.current = null;
    if (!(nextStateHint === "needs-user" && nextPendingApproval)) {
      completedStagesRef.current = new Set();
    }
  }, []);

  const clearForNewDraft = useCallback(() => {
    reset();
  }, [reset]);

  /* ─── Derived data: GenUI prop mappings ─── */

  const selectedPreEdaProfile =
    uploadedDatasets.find((item) => item.sourceId === selectedSourceId)?.preEdaProfile ?? null;

  const reportSections: ReportSection[] = (() => {
    if (state === "ready") {
      const selected = uploadedDatasets.find((item) => item.sourceId === selectedSourceId);
      return [
        {
          type: "paragraph" as const,
          content: selectedPreEdaProfile?.qualitySummary
            ?? "업로드가 완료되었습니다. 파일을 선택한 뒤 질문하면 해당 데이터셋 기준으로 Deep EDA와 리포트가 이어집니다.",
        },
        ...(selectedPreEdaProfile?.summaryBullets?.length
          ? [{ type: "checklist" as const, items: selectedPreEdaProfile.summaryBullets }]
          : [
              {
                type: "paragraph" as const,
                content: selected
                  ? `선택된 파일: ${selected.fileName}`
                  : "선택된 파일 없음 (일반 질문으로 전송됩니다).",
              },
            ]),
      ];
    }

    if (state === "running") {
      if (thoughtSteps.length > 0) {
        return [
          { type: "paragraph" as const, content: streamingAnswer || "질문을 처리 중입니다..." },
          {
            type: "numbered-list" as const,
            items: thoughtSteps.map((step) => step.displayMessage),
          },
        ];
      }
      return [{ type: "paragraph" as const, content: streamingAnswer || "질문을 처리 중입니다..." }];
    }

    if (state === "success" && chatResponse) {
      return [{ type: "paragraph" as const, content: chatResponse.answer }];
    }

    if (state === "needs-user" && pendingApproval) {
      if (pendingApproval.stage === "report") {
        const paragraphs = pendingApproval.draft
          .split(/\n{2,}/)
          .map((item) => item.trim())
          .filter(Boolean);
        return [
          { type: "paragraph" as const, content: pendingApproval.summary },
          { type: "heading" as const, content: "Report Draft" },
          ...(paragraphs.length > 0
            ? paragraphs.map((item) => ({ type: "paragraph" as const, content: item }))
            : [{ type: "paragraph" as const, content: "리포트 초안을 불러오지 못했습니다." }]),
        ];
      }

      if (pendingApproval.stage === "visualization") {
        const plan = pendingApproval.plan;
        const planItems = [
          `Chart type: ${plan.chart_type || "-"}`,
          `X axis: ${plan.x_key || "-"}`,
          `Y axis: ${plan.y_key || "-"}`,
          `Mode: ${plan.mode || "-"}`,
          `Reason: ${plan.reason || pendingApproval.summary}`,
        ];
        return [
          { type: "paragraph" as const, content: pendingApproval.summary },
          { type: "heading" as const, content: "Planned Chart" },
          { type: "numbered-list" as const, items: planItems },
          ...((plan.preview_rows ?? []).length > 0
            ? [
                { type: "heading" as const, content: "Preview Rows" },
                {
                  type: "code" as const,
                  content: JSON.stringify(plan.preview_rows ?? [], null, 2),
                  language: "json",
                },
              ]
            : []),
        ];
      }

      const operationItems = pendingApproval.plan.operations.length > 0
        ? pendingApproval.plan.operations.map((operation) => formatPendingOperation(operation))
        : ["No preprocessing operations were proposed."];
      const topMissingItems = (pendingApproval.plan.top_missing_columns ?? []).map(
        (item) => `${item.column}: ${(item.missing_rate * 100).toFixed(1)}% missing`,
      );
      return [
        { type: "paragraph" as const, content: pendingApproval.summary },
        { type: "heading" as const, content: "Planned Operations" },
        {
          type: "numbered-list" as const,
          items: operationItems,
        },
        ...(topMissingItems.length > 0
          ? [
              { type: "heading" as const, content: "Top Missing Columns" },
              { type: "numbered-list" as const, items: topMissingItems },
            ]
          : []),
        ...(pendingApproval.plan.affected_columns && pendingApproval.plan.affected_columns.length > 0
          ? [
              { type: "heading" as const, content: "Affected Columns" },
              { type: "paragraph" as const, content: pendingApproval.plan.affected_columns.join(", ") },
            ]
          : []),
        ...(typeof pendingApproval.plan.row_count === "number"
          ? [
              {
                type: "paragraph" as const,
                content: `Estimated rows in profile sample: ${pendingApproval.plan.row_count.toLocaleString()}`,
              },
            ]
          : []),
      ];
    }

    if (state === "error") {
      return [{ type: "paragraph" as const, content: errorMessage ?? "An error occurred during analysis." }];
    }

    return [];
  })();

  const sourceId = selectedSourceId;

  const derivedRunStatus: RunStatusData | undefined = (() => {
    if (state !== "running" && state !== "needs-user" && state !== "error") return undefined;
    const completedCount = completedStagesRef.current.size;
    const totalExpected = sourceId ? 6 : 1;
    const progress = Math.min(Math.round((completedCount / totalExpected) * 100), 100);
    const lastTool = toolCalls[toolCalls.length - 1]?.name ?? "";

    if (state === "needs-user") {
      return {
        phase: pendingApproval
          ? `${approvalStageLabel(pendingApproval.stage)} ${pendingApproval.stage === "report" ? "draft review" : "plan review"}`
          : "Plan review",
        progress,
        lastTool,
        elapsedTime: formatElapsed(elapsedSeconds),
      };
    }
    if (state === "error") {
      return { phase: `Failed — ${errorStep ?? "unknown"}`, progress, lastTool, elapsedTime: formatElapsed(elapsedSeconds) };
    }

    const phaseLabels: Record<RunningSubPhase, string> = {
      intake: "질문 확인",
      preprocessing: "데이터 준비",
      rag: "참고 정보 확인",
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
    if (!sourceId) return undefined;
    if (state === "empty" || state === "uploading" || state === "ready") return undefined;

    const currentKey = subPhaseToStageKey(runningSubPhase);
    const currentIdx = STAGES.indexOf(currentKey as (typeof STAGES)[number]);
    const completed = completedStagesRef.current;

    return STAGES.map((stageId, i) => {
      let status: PipelineStepStatus = "queued";
      let sublabel: string | undefined;

      if (state === "error" && i === currentIdx) {
        status = "failed";
        sublabel = `Failed — ${errorMessage?.slice(0, 40)}`;
      } else if (
        state === "needs-user"
        && pendingApproval
        && stageId === (
          pendingApproval.stage === "visualization"
            ? "viz"
            : pendingApproval.stage === "report"
              ? "report"
              : "preprocess"
        )
      ) {
        status = "needs-user";
        sublabel = pendingApproval?.summary ?? "Awaiting approval";
      } else if (state === "running" && i === currentIdx) {
        status = "running";
        const lastStageThought = [...thoughtSteps]
          .reverse()
          .find((step) => subPhaseToStageKey(mapThoughtPhaseToSubPhase(step.phase)) === stageId);
        sublabel = lastStageThought?.displayMessage ?? "처리 중입니다.";
      } else if (completed.has(stageId) || (state === "success" && i <= currentIdx)) {
        status = "success";
      }

      const toolCount = thoughtSteps.filter(
        (step) => subPhaseToStageKey(mapThoughtPhaseToSubPhase(step.phase)) === stageId,
      ).length;

      return {
        id: stageId,
        label: STAGE_LABELS[stageId] ?? stageId,
        status,
        sublabel,
        toolCount: toolCount > 0 ? toolCount : undefined,
      };
    });
  })();

  const derivedDecisionChips: DecisionChip[] = (() => {
    if (!sourceId) return [];
    if (state === "empty" || state === "uploading" || state === "ready") return [];

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
      const currentKey = subPhaseToStageKey(runningSubPhase);
      const currentIdx = STAGES.indexOf(currentKey as (typeof STAGES)[number]);
      const stageIdx = STAGES.indexOf(key as (typeof STAGES)[number]);

      let value: ChipValue = "ON";
      if (state === "error" && stageIdx === currentIdx) {
        value = "FAILED";
      } else if (
        state === "needs-user"
        && pendingApproval
        && key === (
          pendingApproval.stage === "visualization"
            ? "viz"
            : pendingApproval.stage === "report"
              ? "report"
              : "preprocess"
        )
      ) {
        value = "BLOCKED";
      } else if (state === "running" && stageIdx === currentIdx) {
        value = "RUNNING";
      } else if (completed.has(key) || (state === "success" && stageIdx <= currentIdx)) {
        value = "DONE";
      }

      return { stage, value };
    });
  })();

  const derivedEvidence: EvidenceFooterProps = (() => {
    const selectedDataset = uploadedDatasets.find((item) => item.sourceId === sourceId);
    const ragUsed = thoughtSteps.some(
      (step) => step.phase === "rag_retrieval" && step.displayMessage === "질문과 관련된 참고 정보를 찾았습니다.",
    );

    return {
      data: selectedDataset?.fileName || "-",
      scope: uploadedDatasets.length > 0 ? `${uploadedDatasets.length} files` : "-",
      compute: `v3 · ${formatElapsed(elapsedSeconds)}`,
      rag: ragUsed ? "사용함" : "사용 안 함",
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
    thoughtSteps,
    chatHistory,
    milestones,
    history,
    runId,
    pendingApproval,
    rawLogs,
    latestVisualizationResult,
    selectedPreEdaProfile,

    uploadedDatasets,
    selectedSourceId,
    selectUploadedDataset,
    removeUploadedDataset,

    startUpload,
    resumeRun,
    handleApprove,
    handleReject,
    handleEditInstruction,
    handleRetry,
    handleSend,
    handleCancel,
    reset,
    captureSessionContext,
    restoreSessionContext,
    clearForNewDraft,

    fileName,
    sourceId,
    sessionId,
  };
}
