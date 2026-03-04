import { useState, useEffect, useRef, useCallback } from "react";
import {
  uploadFile,
  buildApiUrl,
  deleteDataset,
  type DatasetResponse,
  type ChatResponse,
  type ChatHistoryMessage,
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

export interface HitlProposal {
  column: string;
  strategy: string;
  fillValue: string;
  missingCount: number;
  missingPercent: number;
}

export interface UploadedDatasetMeta {
  datasetId: number;
  sourceId: string;
  fileName: string;
}

export interface VisualizationResultPayload {
  status?: string;
  source_id?: string;
  summary?: string;
  chart?: {
    chart_type?: string;
    x_key?: string;
    y_key?: string;
  };
  artifact?: {
    mime_type?: string;
    image_base64?: string;
    code?: string;
  };
}

export type PipelineSessionStateHint = "empty" | "ready" | "success" | "error";

export interface PipelineSessionContext {
  backendSessionId: number | null;
  fileName: string;
  uploadedDatasets: UploadedDatasetMeta[];
  selectedSourceId: string | null;
  chatHistory: ChatHistoryMessage[];
  latestAssistantAnswer: string | null;
  latestVisualizationResult: VisualizationResultPayload | null;
  stateHint: PipelineSessionStateHint;
  errorMessage: string | null;
}

interface ThoughtStep {
  phase: string;
  message: string;
  status?: "active" | "completed" | "failed";
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
  chatHistory: ChatHistoryMessage[];
  milestones: HistoryItem[];
  history: HistoryItem[];
  hitlProposal: HitlProposal | null;
  rawLogs: RawLogEntry[];
  latestVisualizationResult: VisualizationResultPayload | null;

  // Upload selection
  uploadedDatasets: UploadedDatasetMeta[];
  selectedSourceId: string | null;
  selectUploadedDataset: (sourceId: string | null) => void;
  removeUploadedDataset: (sourceId: string) => Promise<void>;

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

function makeRawLog(label: string, payload: Record<string, unknown>, isError?: boolean): RawLogEntry {
  return {
    id: crypto.randomUUID(),
    label,
    payload: JSON.stringify(payload, null, 2),
    isError,
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
  return { phase, message, status };
}

function parseVisualizationResult(payload: unknown): VisualizationResultPayload | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const data = payload as Record<string, unknown>;
  const artifactRaw = data.artifact;
  if (!artifactRaw || typeof artifactRaw !== "object") {
    return null;
  }
  const artifact = artifactRaw as Record<string, unknown>;
  const imageBase64 = artifact.image_base64;
  if (typeof imageBase64 !== "string" || !imageBase64) {
    return null;
  }

  const chartRaw = data.chart;
  const chart = chartRaw && typeof chartRaw === "object"
    ? chartRaw as Record<string, unknown>
    : {};

  return {
    status: typeof data.status === "string" ? data.status : "generated",
    source_id: typeof data.source_id === "string" ? data.source_id : undefined,
    summary: typeof data.summary === "string" ? data.summary : undefined,
    chart: {
      chart_type: typeof chart.chart_type === "string" ? chart.chart_type : undefined,
      x_key: typeof chart.x_key === "string" ? chart.x_key : undefined,
      y_key: typeof chart.y_key === "string" ? chart.y_key : undefined,
    },
    artifact: {
      mime_type: typeof artifact.mime_type === "string" ? artifact.mime_type : "image/png",
      image_base64: imageBase64,
      code: typeof artifact.code === "string" ? artifact.code : undefined,
    },
  };
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
  const [chatResponse, setChatResponse] = useState<ChatResponse | null>(null);
  const [streamingAnswer, setStreamingAnswer] = useState("");
  const [thoughtSteps, setThoughtSteps] = useState<ThoughtStep[]>([]);
  const [latestVisualizationResult, setLatestVisualizationResult] = useState<VisualizationResultPayload | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatHistoryMessage[]>([]);

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
  const [hitlProposal, setHitlProposal] = useState<HitlProposal | null>(null);

  // --- Completed stage tracking ---
  const completedStagesRef = useRef<Set<string>>(new Set());

  // --- Abort / retry refs ---
  const abortRef = useRef<AbortController | null>(null);
  const lastQuestionRef = useRef<string>("");
  const localMessageIdRef = useRef(0);

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

  const nextLocalMessageId = useCallback(() => {
    localMessageIdRef.current += 1;
    return Date.now() + localMessageIdRef.current;
  }, []);

  const startUpload = useCallback(
    (file: File) => {
      setChatResponse(null);
      setStreamingAnswer("");
      setThoughtSteps([]);
      setErrorMessage(null);
      setErrorStep(null);
      setHitlProposal(null);
      setUploadProgress(0);
      setFileName(file.name);
      setState("uploading");

      uploadFile(file, (percent) => {
        setUploadProgress(percent);
      })
        .then((dataset: DatasetResponse) => {
          setUploadProgress(100);
          setState("ready");
          setRunningSubPhase("intake");
          setFileName(dataset.filename || file.name);

          upsertUploadedDataset({
            datasetId: dataset.id,
            sourceId: dataset.source_id,
            fileName: dataset.filename || file.name,
          });

          addMilestone({
            status: "completed",
            title: "Upload complete",
            subtext: `${dataset.filename} · ${dataset.source_id}`,
            timestamp: now(),
          });
        })
        .catch((err: Error) => {
          transitionToError("upload", err.message);
        });
    },
    [addMilestone, transitionToError, upsertUploadedDataset],
  );

  const startWithSample = useCallback(() => {
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
  }, []);

  const handleReject = useCallback(() => {
    setHistory((prev) => [
      ...prev,
      { status: "failed" as TimelineItemStatus, title: "Rejected Changes", subtext: "User cancelled action", timestamp: now() },
    ]);
    setHitlProposal(null);
  }, []);

  const handleEditInstruction = useCallback((text: string) => {
    setHistory((prev) => [
      ...prev,
      { status: "completed" as TimelineItemStatus, title: "User Edit", subtext: text, timestamp: now() },
    ]);
  }, []);

  const handleSend = useCallback(
    (message: string) => {
      const question = message.trim();
      if (!question) return;

      setChatHistory((prev) => [
        ...prev,
        {
          id: nextLocalMessageId(),
          role: "user",
          content: question,
          created_at: new Date().toISOString(),
        },
      ]);

      lastQuestionRef.current = question;
      setErrorMessage(null);
      setErrorStep(null);
      setState("running");
      setRunningSubPhase("intake");
      setStreamingAnswer("");
      setChatResponse(null);
      setThoughtSteps([]);
      completedStagesRef.current = new Set();

      const request: { question: string; session_id?: number; source_id?: string } = {
        question,
      };
      if (sessionId !== null) request.session_id = sessionId;
      if (selectedSourceId) request.source_id = selectedSourceId;

      const tc = makeToolCall("chat_stream", request);
      addToolCall(tc);
      addLog(makeRawLog("tool_call: chat_stream", request));

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
              const nextSession = record.session_id;
              if (typeof nextSession === "number") {
                setSessionId(nextSession);
              }
              return;
            }

            if (eventName === "thought") {
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

            if (eventName === "done") {
              doneReceived = true;
              const answer = typeof record.answer === "string" ? record.answer : streamText;
              finalAnswer = answer;
              setStreamingAnswer(answer);

              const nextSession = record.session_id;
              const resolvedSessionId = typeof nextSession === "number" ? nextSession : sessionId;
              if (typeof resolvedSessionId === "number") {
                setSessionId(resolvedSessionId);
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
                  thought_steps: Array.isArray(doneThoughts) ? (doneThoughts as any[]) : [],
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
                  upsertUploadedDataset({
                    datasetId: 0,
                    sourceId: preprocess.output_source_id,
                    fileName:
                      typeof preprocess.output_filename === "string" && preprocess.output_filename
                        ? preprocess.output_filename
                        : `processed_${preprocess.output_source_id}`,
                  });
                }
              }

              setState("success");
              return;
            }

            if (eventName === "error") {
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

          const finalText = (finalAnswer || streamText).trim();
          if (!doneReceived && finalText) {
            setStreamingAnswer(finalText);
            if (sessionId !== null) {
              setChatResponse({ answer: finalText, session_id: sessionId, thought_steps: [] });
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
          }

          updateToolCall(tc.id, completeToolCall(tc, finalText.slice(0, 80) || "stream done", startMs));
          addMilestone({
            status: "completed",
            title: "Follow-up",
            subtext: question.slice(0, 40),
            timestamp: now(),
          });
          addLog(makeRawLog("tool_result: chat_stream", { answer_length: finalText.length }));
        } catch (error: unknown) {
          if (error instanceof DOMException && error.name === "AbortError") {
            return;
          }
          if (error instanceof Error && error.name === "AbortError") {
            return;
          }

          const message = error instanceof Error ? error.message : "채팅 요청에 실패했습니다.";
          updateToolCall(tc.id, failToolCall(tc, message, startMs));
          addLog(makeRawLog("tool_error: chat_stream", { error: message }, true));
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
      updateToolCall,
      addMilestone,
      appendThoughtStep,
      transitionToError,
      upsertUploadedDataset,
      nextLocalMessageId,
    ],
  );

  const handleRetry = useCallback(() => {
    if (!lastQuestionRef.current) {
      setState(uploadedDatasets.length > 0 ? "ready" : "empty");
      return;
    }
    handleSend(lastQuestionRef.current);
  }, [handleSend, uploadedDatasets.length]);

  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setUploadProgress(0);
    setStreamingAnswer("");
    setThoughtSteps([]);
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
    setHitlProposal(null);
    setLatestVisualizationResult(null);
    setChatHistory([]);
    lastQuestionRef.current = "";
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
    } else if (state === "success") {
      stateHint = "success";
    } else if (state === "ready") {
      stateHint = "ready";
    } else if (state === "running" || state === "uploading" || state === "needs-user") {
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
      fileName,
      uploadedDatasets: [...uploadedDatasets],
      selectedSourceId,
      chatHistory,
      latestAssistantAnswer,
      latestVisualizationResult,
      stateHint,
      errorMessage: stateHint === "error" ? errorMessage : null,
    };
  }, [
    chatResponse,
    state,
    uploadedDatasets,
    sessionId,
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
    const nextUploadedDatasets = Array.isArray(context.uploadedDatasets)
      ? context.uploadedDatasets
      : [];
    const nextStateHint: PipelineSessionStateHint = context.stateHint ?? "empty";
    const latestAnswer =
      typeof context.latestAssistantAnswer === "string" && context.latestAssistantAnswer.trim()
        ? context.latestAssistantAnswer
        : null;

    setSessionId(nextSessionId);
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
    setHitlProposal(null);
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
        thought_steps: [],
      });
    } else {
      setChatResponse(null);
    }

    if (nextStateHint === "success") {
      setState("success");
    } else if (nextStateHint === "ready") {
      setState("ready");
    } else if (nextStateHint === "error") {
      setState("error");
    } else {
      setState("empty");
    }

    lastQuestionRef.current = "";
    completedStagesRef.current = new Set();
  }, []);

  const clearForNewDraft = useCallback(() => {
    reset();
  }, [reset]);

  /* ─── Derived data: GenUI prop mappings ─── */

  const reportSections: ReportSection[] = (() => {
    if (state === "ready") {
      const selected = uploadedDatasets.find((item) => item.sourceId === selectedSourceId);
      const selectedText = selected
        ? `선택된 파일: ${selected.fileName}`
        : "선택된 파일 없음 (일반 질문으로 전송됩니다).";
      return [
        { type: "paragraph" as const, content: "업로드가 완료되었습니다. 파일을 선택한 뒤 질문하면 해당 데이터로 라우팅됩니다." },
        { type: "paragraph" as const, content: selectedText },
      ];
    }

    if (state === "running") {
      if (thoughtSteps.length > 0) {
        return [
          { type: "paragraph" as const, content: streamingAnswer || "질문을 처리 중입니다..." },
          {
            type: "numbered-list" as const,
            items: thoughtSteps.map((step) => step.message),
          },
        ];
      }
      return [{ type: "paragraph" as const, content: streamingAnswer || "질문을 처리 중입니다..." }];
    }

    if (state === "success" && chatResponse) {
      return [{ type: "paragraph" as const, content: chatResponse.answer }];
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
      } else if (state === "running" && i === currentIdx) {
        status = "running";
        const lastStageThought = [...thoughtSteps]
          .reverse()
          .find((step) => subPhaseToStageKey(mapThoughtPhaseToSubPhase(step.phase)) === stageId);
        sublabel = lastStageThought?.message ?? "Processing...";
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
    const ragUsed = thoughtSteps.some((step) => step.phase.startsWith("rag"));

    return {
      data: selectedDataset?.fileName || "-",
      scope: uploadedDatasets.length > 0 ? `${uploadedDatasets.length} files` : "-",
      compute: `v3 · ${formatElapsed(elapsedSeconds)}`,
      rag: ragUsed ? "ON" : "OFF",
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
    chatHistory,
    milestones,
    history,
    hitlProposal,
    rawLogs,
    latestVisualizationResult,

    uploadedDatasets,
    selectedSourceId,
    selectUploadedDataset,
    removeUploadedDataset,

    startUpload,
    startWithSample,
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
