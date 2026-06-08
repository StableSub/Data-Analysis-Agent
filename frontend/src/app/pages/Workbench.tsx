import React, { useState, useRef, useCallback, useEffect } from "react";
import { ToolCallIndicator } from "../components/genui/ToolCallIndicator";
import { WorkbenchCommandBar } from "../components/genui/WorkbenchCommandBar";
import { Dropzone } from "../components/genui/Dropzone";
import { WorkbenchLayout } from "../components/genui/WorkbenchLayout";
import { StatusBadge } from "../components/genui/StatusBadge";
import { GateBar } from "../components/genui/GateBar";
import {
  AssistantReportMessage,
  type RepairGuidance,
} from "../components/genui/AssistantReportMessage";
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
import {
  getCanonicalBackendSessionId,
  getSessionDeletionIds,
  useWorkbenchSessionStore,
  type WorkbenchSessionItem,
} from "../hooks/useWorkbenchSessionStore";
import {
  deleteChatSession,
  type ChatResponse,
  type EdaRecommendedOperation,
  fetchPendingApproval,
  getChatHistory,
  ApiError,
  listChatSessions,
  listDatasets,
  type ChatHistoryMessage,
  type GuidelineResponse,
  type PendingApprovalPayload,
  uploadGuidelineFile,
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

const compactPendingText = (value: string, maxLength = 180): string => {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (!normalized) {
    return "";
  }
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength).trimEnd()}...`;
};

const buildPendingApprovalChanges = (
  pendingApproval: PendingApprovalPayload | null,
): string[] => {
  if (!pendingApproval) {
    return ["승인 대기 중인 작업이 있습니다."];
  }

  if (pendingApproval.stage === "report") {
    const draftSummary = compactPendingText(pendingApproval.draft);
    return [
      draftSummary
        ? `초안 내용: ${draftSummary}`
        : "분석 결과 초안을 불러오지 못했습니다.",
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
      pendingApproval.plan.mode ? `mode: ${pendingApproval.plan.mode}` : "mode: -",
      pendingApproval.plan.reason || "시각화 계획 검토 필요",
      `preview rows: ${(pendingApproval.plan.preview_rows ?? []).length}`,
    ];
  }

  const operationItems =
    pendingApproval.plan.operations.length > 0
      ? pendingApproval.plan.operations.map((operation) => formatPendingOperation(operation))
      : ["제안된 전처리 operation 없음"];
  const guidance = pendingApproval.plan.guidance;

  return [
    ...(guidance?.why_this_matters
      ? [`왜 중요한가: ${guidance.why_this_matters}`]
      : []),
    ...(guidance?.expected_impact
      ? [`예상 효과: ${guidance.expected_impact}`]
      : []),
    ...(guidance?.skip_risk
      ? [`건너뛰면: ${guidance.skip_risk}`]
      : []),
    ...(pendingApproval.plan.planner_comment
      ? [`planner comment: ${pendingApproval.plan.planner_comment}`]
      : []),
    ...operationItems,
    ...((pendingApproval.plan.affected_columns ?? []).length > 0
      ? [`affected columns: ${(pendingApproval.plan.affected_columns ?? []).join(", ")}`]
      : []),
    ...(typeof pendingApproval.plan.row_count === "number"
      ? [`profile sample rows: ${pendingApproval.plan.row_count.toLocaleString()}`]
      : []),
  ].slice(0, 8);
};

const buildPendingApprovalPreview = (
  pendingApproval: PendingApprovalPayload | null,
): string | undefined => {
  if (!pendingApproval) {
    return undefined;
  }

  if (pendingApproval.stage === "report") {
    return compactPendingText(pendingApproval.draft, 600) || undefined;
  }

  if (pendingApproval.stage === "visualization") {
    const previewRows = pendingApproval.plan.preview_rows ?? [];
    if (previewRows.length === 0) {
      return undefined;
    }
    return compactPendingText(JSON.stringify(previewRows.slice(0, 3), null, 2), 600);
  }

  if (pendingApproval.plan.guidance?.why_this_matters) {
    return compactPendingText(pendingApproval.plan.guidance.why_this_matters, 360);
  }

  return pendingApproval.plan.planner_comment
    ? compactPendingText(pendingApproval.plan.planner_comment, 360)
    : undefined;
};

const ANALYSIS_FAILURE_MESSAGE = "응답을 생성하지 못했습니다.";

const buildRepairGuidance = (
  profile: ReturnType<typeof useAnalysisPipeline>["selectedPreEdaProfile"],
  response: ChatResponse | null,
  state: ReturnType<typeof useAnalysisPipeline>["state"],
): RepairGuidance | undefined => {
  const backendFeedback = response?.query_feedback;
  if (
    backendFeedback
    && backendFeedback.title.trim()
    && backendFeedback.message.trim()
    && backendFeedback.actions.length > 0
  ) {
    return backendFeedback;
  }

  const outputType = response?.output_type ?? "";
  const status = response?.status ?? "";
  const isPlanValidationFailure =
    response?.error_stage === "plan_validation" || outputType === "planning_failed";
  const isAnalysisRepairFailure =
    response?.error_stage === "analysis_repair_failed"
    || response?.error_code === "analysis_repair_failed"
    || outputType === "analysis_failed";
  const isClarification =
    outputType === "clarification" || status === "unanswerable" || status === "limited";
  const isFailure = state === "error" || status === "failed" || outputType.endsWith("_failed");

  if (!isClarification && !isFailure) {
    return undefined;
  }

  const metric = profile?.numericColumns[0] ?? profile?.columns[0] ?? "핵심 컬럼";
  const group = profile?.groupKeyColumns[0] ?? profile?.categoricalColumns[0] ?? null;
  const missing = profile?.topMissingColumns[0]?.column ?? null;
  const availableColumns = profile?.columns.slice(0, 6).join(", ") ?? "";
  const publicError = response?.public_error;
  const failedColumn = publicError?.failed_column?.trim() || metric;
  const failedOperation = publicError?.operation?.trim() || "분석";
  const reasonSummary = publicError?.reason_summary?.trim();
  const suggestedAction = publicError?.suggested_action?.trim();
  const actions: RepairGuidance["actions"] = [];

  if (isFailure && isPlanValidationFailure) {
    actions.push({
      label: "없는 컬럼은 실제 컬럼명으로 바꾸기",
      description: availableColumns
        ? `오류를 피하려면 데이터에 있는 컬럼명을 그대로 사용해 주세요. 사용 가능 컬럼: ${availableColumns}`
        : "오류를 피하려면 질문에 쓴 컬럼명이 현재 데이터에 실제로 있는지 먼저 확인해 주세요.",
    });

    if (missing) {
      actions.push({
        label: "결측 조건을 질문에 반영하기",
        description: `'${missing}' 값이 비어 있다면 평균/비율/원인 추정 전에 결측을 제외할지, 결측 자체를 볼지 적어 주세요.`,
      });
    }

    actions.push({
      label: "계산 방식까지 한 문장에 쓰기",
      description: "건수, 비율, 평균, 합계, 이상치 확인처럼 원하는 결과 형태와 기준 컬럼을 함께 적으면 계획 오류를 줄일 수 있습니다.",
    });

    return {
      title: "질문을 실행 가능한 형태로 다듬어 보세요",
      message: response?.error_message
        ?? "분석 목표, 기준 컬럼, 집계 방식 중 일부가 현재 데이터와 맞지 않습니다. 아래 항목을 보완해 질문을 다시 작성해 보세요.",
      actions: actions.slice(0, 3),
    };
  }

  if (isFailure && isAnalysisRepairFailure) {
    actions.push({
      label: "컬럼 타입에 맞는 연산 쓰기",
      description: reasonSummary
        ?? `'${failedColumn}'에 ${failedOperation}을 적용하려면 숫자, 날짜, 범주 같은 데이터 타입이 연산과 맞아야 합니다.`,
    });

    actions.push({
      label: "데이터 조건을 질문에 명시하기",
      description: suggestedAction ?? (
        missing
          ? `'${missing}' 결측이 많다면 결측을 제외할지, 결측 원인을 먼저 볼지 질문에 적어 주세요.`
          : "오류를 피하려면 숫자 변환, 날짜 형식, 결측 제외 같은 데이터 조건을 질문에 함께 적어 주세요."
      ),
    });

    actions.push({
      label: "한 번에 한 목적만 묻기",
      description: group
        ? `예: '${group}' 기준의 ${failedOperation}처럼 대상 컬럼, 기준, 연산을 하나씩 맞춰 질문해 주세요.`
        : "리포트, 원인 추정, 제품별 집계를 한 번에 섞기보다 먼저 핵심 계산 하나를 명확히 요청해 주세요.",
    });

    return {
      title: publicError?.stage || response?.error_stage
        ? `분석 실행 오류 해결 (${publicError?.stage ?? response?.error_stage} 단계)`
        : "분석 실행 오류 해결",
      message: response?.error_message
        ?? "자동 코드 수정으로도 실행 가능한 분석을 만들지 못했습니다. 오류를 피하려면 컬럼 타입, 결측 조건, 원하는 연산을 더 구체적으로 적어 주세요.",
      actions: actions.slice(0, 3),
    };
  }

  actions.push({
    label: "무엇을 계산할지 쓰기",
    description: "건수, 비율, 평균, 합계, 이상치 여부, 원인 추정처럼 원하는 결과 형태를 먼저 적어 주세요.",
  });

  if (group) {
    actions.push({
      label: "대상 컬럼과 기준을 함께 쓰기",
      description: `예: '${group}'별 '${metric}' 평균처럼 대상 컬럼과 그룹 기준을 한 문장에 같이 적어 주세요.`,
    });
  } else {
    actions.push({
      label: "대상 컬럼과 기준을 함께 쓰기",
      description: `예: '${metric}' 평균, 날짜별 건수처럼 분석 대상과 기준을 한 문장에 같이 적어 주세요.`,
    });
  }

  actions.push({
    label: "실제 컬럼명 그대로 쓰기",
    description: missing
      ? `'${missing}' 결측 조건과 함께, 오타나 없는 컬럼 대신 사용 가능 컬럼 중 이름을 그대로 적어 주세요${availableColumns ? `: ${availableColumns}` : "."}`
      : availableColumns
        ? `오류를 피하려면 오타나 없는 컬럼 대신 사용 가능 컬럼 중 이름을 그대로 적어 주세요: ${availableColumns}`
        : "오류를 피하려면 질문에 쓴 컬럼명이 현재 데이터에 있는지 확인해 주세요.",
  });

  return {
    title: isFailure ? "오류를 피하도록 질문을 조정하세요" : "좋은 분석 질문으로 바꾸는 방법",
    message: response?.error_message ?? (
      isFailure
        ? "오류가 난 질문은 바로 다시 실행하기보다 컬럼, 기준, 연산 조건을 먼저 점검해 보세요."
        : "현재 질문은 분석 기준이나 대상 컬럼이 부족합니다. 아래 요소를 채워 질문을 다시 작성해 보세요."
    ),
    actions: actions.slice(0, 3),
  };
};

const mergeServerHistoryVisualizations = (
  serverMessages: ChatHistoryMessage[],
  localMessages: ChatHistoryMessage[],
): ChatHistoryMessage[] => {
  const usedLocalIndexes = new Set<number>();

  return serverMessages.map((message) => {
    if (message.role !== "assistant" || message.visualization_result) {
      return message;
    }

    const localIndex = localMessages.findIndex(
      (candidate, index) =>
        !usedLocalIndexes.has(index)
        && candidate.role === "assistant"
        && candidate.content === message.content
        && Boolean(candidate.visualization_result),
    );

    if (localIndex < 0) {
      return message;
    }

    usedLocalIndexes.add(localIndex);
    return {
      ...message,
      visualization_result: localMessages[localIndex].visualization_result,
    };
  });
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
    evidence,
    chatResponse,
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
    bootstrapServerDatasets,
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
    mergeServerSessions,
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
  const pendingApprovalChanges = buildPendingApprovalChanges(pendingApproval);
  const pendingApprovalPreview = buildPendingApprovalPreview(pendingApproval);

  // UI-only local state
  type CanvasView = "current" | "pre-eda" | "deep-eda" | "report";
  const [canvasView, setCanvasView] = useState<CanvasView>("current");
  const canvasScrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const guidelineFileInputRef = useRef<HTMLInputElement>(null);
  const chatThreadEndRef = useRef<HTMLDivElement>(null);
  const initializedRef = useRef(false);
  const lastAutoOpenedPreEdaSourceRef = useRef<string | null>(null);
  const restoreRequestSeqRef = useRef(0);
  const expectedSessionIdRef = useRef<string | null>(activeSessionId);
  const [restoringSessionId, setRestoringSessionId] = useState<string | null>(null);
  const [guidelines, setGuidelines] = useState<GuidelineResponse[]>([]);
  const [selectedGuidelineSourceId, setSelectedGuidelineSourceId] = useState<string | null>(null);
  const [guidelineUploadProgress, setGuidelineUploadProgress] = useState<number | null>(null);

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
    const result = await pipeline.retrySelectedPreEda(selectedGuidelineSourceId);
    if (result === "ready") {
      toast.success("Pre-EDA 정보를 다시 불러왔습니다.");
      return;
    }
    if (result === "unavailable") {
      toast.error("Pre-EDA 정보를 다시 불러오지 못했습니다.");
    }
  }, [pipeline, selectedGuidelineSourceId]);

  const handleGuidelineSelectionChange = useCallback(
    async (event: React.ChangeEvent<HTMLSelectElement>) => {
      const nextGuidelineSourceId = event.target.value || null;
      setSelectedGuidelineSourceId(nextGuidelineSourceId);
      if (!selectedSourceId || state !== "ready") {
        return;
      }
      const result = await pipeline.retrySelectedPreEda(nextGuidelineSourceId);
      if (result === "ready") {
        toast.success(
          nextGuidelineSourceId
            ? "Guideline 기준으로 EDA 요약을 갱신했습니다."
            : "Guideline 요약을 제거하고 기본 EDA로 갱신했습니다.",
        );
      }
    },
    [pipeline, selectedSourceId, state],
  );

  const formatElapsed = (s: number) => {
    const m = Math.floor(s / 60).toString().padStart(2, "0");
    const sec = (s % 60).toString().padStart(2, "0");
    return `${m}:${sec}`;
  };

  const saveSessionSnapshot = useCallback(
    (targetSessionId: string | null) => {
      if (!targetSessionId) {
        return;
      }
      const snapshot = {
        ...captureSessionContext(),
        uploadedGuidelines: guidelines,
        selectedGuidelineSourceId,
        guidelinesScopedToSession: true,
      };
      updateSession(targetSessionId, {
        backendSessionId: snapshot.backendSessionId,
        context: snapshot,
      });
    },
    [captureSessionContext, guidelines, selectedGuidelineSourceId, updateSession],
  );

  const markExpectedSession = useCallback((sessionId: string | null) => {
    expectedSessionIdRef.current = sessionId;
  }, []);

  const beginSessionRestore = useCallback(
    (sessionId: string) => {
      markExpectedSession(sessionId);
      setRestoringSessionId(sessionId);
    },
    [markExpectedSession],
  );

  const finishSessionRestore = useCallback((sessionId: string) => {
    if (expectedSessionIdRef.current !== sessionId) {
      return;
    }
    setRestoringSessionId((current) => (current === sessionId ? null : current));
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

  const restoreSessionItem = useCallback(
    async (targetSession: WorkbenchSessionItem) => {
      const targetSessionId = targetSession.id;
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

      const backendSessionId = getCanonicalBackendSessionId(targetSession);

      if (backendSessionId !== null) {
        try {
          const history = await getChatHistory(backendSessionId);
          if (isStaleRestoreRequest()) {
            return;
          }
          const msgs = mergeServerHistoryVisualizations(history.messages ?? [], nextContext.chatHistory);
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
              if (error instanceof ApiError && error.status === 404) {
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
            backendSessionId,
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
          if (error instanceof ApiError && error.status === 404) {
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
      const nextGuidelines = nextContext.uploadedGuidelines ?? [];
      setGuidelines(nextGuidelines);
      setSelectedGuidelineSourceId(
        nextGuidelines.some((item) => item.source_id === nextContext.selectedGuidelineSourceId)
          ? nextContext.selectedGuidelineSourceId
          : null,
      );
    },
    [reconcileSessionDatasets, updateSession, restoreSessionContext],
  );

  const restoreSessionById = useCallback(
    async (targetSessionId: string) => {
      const targetSession = sessions.find((item) => item.id === targetSessionId);
      if (!targetSession) {
        return;
      }
      await restoreSessionItem(targetSession);
    },
    [sessions, restoreSessionItem],
  );

  const handleNewChat = useCallback(() => {
    saveSessionSnapshot(activeSessionId);
    const nextSession = createSession();
    markExpectedSession(nextSession.id);
    setRestoringSessionId(null);
    setGuidelines([]);
    setSelectedGuidelineSourceId(null);
    clearForNewDraft();
  }, [activeSessionId, saveSessionSnapshot, createSession, clearForNewDraft, markExpectedSession]);

  const handleSessionSelect = useCallback(
    async (targetSessionId: string) => {
      if (targetSessionId === activeSessionId) {
        return;
      }
      saveSessionSnapshot(activeSessionId);
      beginSessionRestore(targetSessionId);
      selectSession(targetSessionId);
      try {
        await restoreSessionById(targetSessionId);
      } finally {
        finishSessionRestore(targetSessionId);
      }
    },
    [activeSessionId, saveSessionSnapshot, beginSessionRestore, selectSession, restoreSessionById, finishSessionRestore],
  );

  const handleSessionDelete = useCallback(
    async (targetSessionId: string) => {
      const targetSession = sessions.find((item) => item.id === targetSessionId);
      if (!targetSession) {
        return;
      }

      const backendSessionId = getCanonicalBackendSessionId(targetSession);
      if (backendSessionId !== null) {
        try {
          await deleteChatSession(backendSessionId);
        } catch (error) {
          if (!(error instanceof ApiError && error.status === 404)) {
            toast.error("서버 세션 삭제에 실패했습니다.");
            return;
          }
        }
      }

      const deletionIds = getSessionDeletionIds(sessions, targetSessionId);
      const wasActive = activeSessionId !== null && deletionIds.has(activeSessionId);
      const remaining = sessions.filter((item) => !deletionIds.has(item.id));
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
      beginSessionRestore(fallbackSession.id);
      selectSession(fallbackSession.id);
      try {
        await restoreSessionById(fallbackSession.id);
      } finally {
        finishSessionRestore(fallbackSession.id);
      }
    },
    [
      sessions,
      activeSessionId,
      deleteSessionFromStore,
      clearForNewDraft,
      selectSession,
      restoreSessionById,
      beginSessionRestore,
      finishSessionRestore,
    ],
  );

  const handleSendMessage = useCallback(
    (value: string, modelId = "gpt-5-nano") => {
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

      handleSend(value, modelId, selectedGuidelineSourceId);
    },
    [ensureActiveSessionForInteraction, markSessionActivity, handleSend, selectedGuidelineSourceId],
  );

  const handleUseSuggestedQuestion = useCallback(
    (question: string) => {
      handleSendMessage(question);
      setCanvasView("deep-eda");
    },
    [handleSendMessage],
  );

  useEffect(() => {
    if (initializedRef.current) {
      return;
    }

    let cancelled = false;
    void (async () => {
      let baseContext = captureSessionContext();
      let nextSessions = sessions;
      let nextActiveSessionId = activeSessionId;

      const [datasetsResult, chatSessionsResult] = await Promise.allSettled([
        listDatasets(0, 100),
        listChatSessions(0, 100),
      ]);
      if (cancelled) {
        return;
      }
      initializedRef.current = true;

      if (datasetsResult.status === "fulfilled") {
        baseContext = bootstrapServerDatasets(datasetsResult.value.items);
      }

      if (chatSessionsResult.status === "fulfilled") {
        const merged = mergeServerSessions(chatSessionsResult.value.items, baseContext);
        nextSessions = merged.sessions;
        nextActiveSessionId = merged.activeSessionId;
      }

      const initialSessionId = nextActiveSessionId ?? nextSessions[0]?.id ?? null;
      const initialSession = initialSessionId
        ? nextSessions.find((item) => item.id === initialSessionId) ?? null
        : null;

      if (!initialSession) {
        markExpectedSession(null);
        restoreSessionContext(baseContext);
        setGuidelines(baseContext.uploadedGuidelines ?? []);
        setSelectedGuidelineSourceId(baseContext.selectedGuidelineSourceId ?? null);
        initializedRef.current = true;
        return;
      }

      beginSessionRestore(initialSession.id);
      if (activeSessionId !== initialSession.id) {
        selectSession(initialSession.id);
      }
      try {
        await restoreSessionItem(initialSession);
      } finally {
        finishSessionRestore(initialSession.id);
      }
      initializedRef.current = true;
    })();

    return () => {
      cancelled = true;
    };
  }, [
    activeSessionId,
    bootstrapServerDatasets,
    captureSessionContext,
    mergeServerSessions,
    beginSessionRestore,
    finishSessionRestore,
    restoreSessionContext,
    restoreSessionItem,
    selectSession,
    sessions,
  ]);

  useEffect(() => {
    if (!initializedRef.current || !activeSessionId || restoringSessionId !== null) {
      return;
    }
    if (state === "running" || state === "uploading") {
      return;
    }
    const snapshot = {
      ...captureSessionContext(),
      uploadedGuidelines: guidelines,
      selectedGuidelineSourceId,
      guidelinesScopedToSession: true,
    };
    updateActiveSession({
      backendSessionId: snapshot.backendSessionId,
      context: snapshot,
    });
  }, [activeSessionId, state, restoringSessionId, captureSessionContext, guidelines, selectedGuidelineSourceId, updateActiveSession]);

  useEffect(() => {
    if (!initializedRef.current || !activeSessionId || sessionId === null || restoringSessionId !== null) {
      return;
    }
    const snapshot = {
      ...captureSessionContext(),
      uploadedGuidelines: guidelines,
      selectedGuidelineSourceId,
      guidelinesScopedToSession: true,
    };
    updateActiveSession({
      backendSessionId: sessionId,
      context: {
        ...snapshot,
        backendSessionId: sessionId,
      },
    });
  }, [activeSessionId, sessionId, restoringSessionId, captureSessionContext, guidelines, selectedGuidelineSourceId, updateActiveSession]);

  /** Open file picker for real file selection */
  const openFilePicker = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const openGuidelineFilePicker = useCallback(() => {
    guidelineFileInputRef.current?.click();
  }, []);

  const handleFileSelected = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        const targetSession = ensureActiveSessionForInteraction();
        markSessionActivity(targetSession.id);
        pipeline.startUpload(file, selectedGuidelineSourceId);
      }
      // Reset so the same file can be re-selected
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [ensureActiveSessionForInteraction, markSessionActivity, pipeline, selectedGuidelineSourceId],
  );

  const handleGuidelineFileSelected = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) {
        return;
      }

      if (!file.name.toLowerCase().endsWith(".pdf")) {
        toast.error("Guideline은 PDF 파일만 업로드할 수 있습니다.");
        if (guidelineFileInputRef.current) guidelineFileInputRef.current.value = "";
        return;
      }

      const targetSession = ensureActiveSessionForInteraction();
      markSessionActivity(targetSession.id);
      setGuidelineUploadProgress(0);
      try {
        const uploaded = await uploadGuidelineFile(file, setGuidelineUploadProgress);
        setGuidelines((prev) => [uploaded, ...prev.filter((item) => item.source_id !== uploaded.source_id)]);
        setSelectedGuidelineSourceId(uploaded.source_id);
        const refreshResult = selectedSourceId
          ? await pipeline.retrySelectedPreEda(uploaded.source_id)
          : "noop";
        toast.success(
          refreshResult === "ready"
            ? "Guideline을 업로드하고 EDA 요약을 갱신했습니다."
            : "Guideline을 업로드하고 현재 채팅에 연결했습니다.",
        );
      } catch (error) {
        const message = error instanceof Error ? error.message : "Guideline 업로드에 실패했습니다.";
        toast.error(message);
      } finally {
        setGuidelineUploadProgress(null);
        if (guidelineFileInputRef.current) guidelineFileInputRef.current.value = "";
      }
    },
    [ensureActiveSessionForInteraction, markSessionActivity, pipeline, selectedSourceId],
  );

  /** Handle Dropzone onDrop — if FileList is empty (button click), open picker */
  const handleDrop = useCallback(
    (files: FileList) => {
      const file = files[0]; // noUncheckedIndexedAccess: may be undefined
      if (file) {
        const targetSession = ensureActiveSessionForInteraction();
        markSessionActivity(targetSession.id);
        pipeline.startUpload(file, selectedGuidelineSourceId);
      } else {
        openFilePicker();
      }
    },
    [ensureActiveSessionForInteraction, markSessionActivity, pipeline, openFilePicker, selectedGuidelineSourceId],
  );

  const formatSessionUpdatedAt = (value: string | null | undefined) => {
    if (!value) {
      return "활동 없음";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "활동 없음";
    }
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hour = String(date.getHours()).padStart(2, "0");
    const minute = String(date.getMinutes()).padStart(2, "0");
    return `${year}.${month}.${day} ${hour}시 ${minute}분`;
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
  const hasFailedResponse =
    chatResponse?.status === "failed"
    || chatResponse?.status === "cancelled"
    || Boolean(chatResponse?.error_stage || chatResponse?.error_message || chatResponse?.public_error);
  const hasFailedAnalysis =
    hasFailedResponse
    || state === "error"
    || latestAssistantContent === ANALYSIS_FAILURE_MESSAGE;
  const hasCompletedAnalysis =
    !hasFailedAnalysis
    && (
      (latestAssistantContent.length > 0 && latestAssistantContent !== ANALYSIS_FAILURE_MESSAGE)
      || (chatHistory.length === 0 && state === "success" && reportSections.length > 0)
    );
  const hasAnalysisSnapshot = hasCompletedAnalysis || hasFailedAnalysis;
  const repairGuidance = buildRepairGuidance(selectedPreEdaProfile, chatResponse, state);
  const shouldKeepChatThreadVisible =
    chatHistory.some((message) => message.role === "assistant")
    && (state === "running" || state === "needs-user");
  const effectiveCurrentView: Exclude<CanvasView, "current"> | null =
    state === "empty" || state === "uploading" || state === "error"
      ? null
      : shouldKeepChatThreadVisible
        ? "deep-eda"
        : state === "running" || state === "needs-user"
          ? null
          : hasCompletedAnalysis
            ? "deep-eda"
            : hasCompletedEda
              ? "pre-eda"
              : null;
  const displayedCanvasView: Exclude<CanvasView, "current"> | null =
    canvasView === "current" ? effectiveCurrentView : canvasView;

  useEffect(() => {
    if (canvasView !== "current" || displayedCanvasView !== "deep-eda" || chatHistory.length === 0) {
      return;
    }

    const frame = window.requestAnimationFrame(() => {
      chatThreadEndRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [canvasView, displayedCanvasView, chatHistory.length, state]);

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
          onNavigate: hasAnalysisSnapshot
            ? () => {
              setCanvasView("deep-eda");
            }
            : undefined,
        },
      ]
    : [];

  const selectedDatasetOverview = selectedPreEdaProfile?.datasetOverview ?? null;
  const preEdaSummarySections = [
    {
      type: "paragraph" as const,
      content:
        selectedDatasetOverview?.summary
          ?? selectedPreEdaProfile?.qualitySummary
          ?? (hasDatasetContext
            ? `${currentDatasetLabel}이(가) 현재 source로 선택되어 있습니다. 질문 전에 구조와 품질 맥락을 먼저 확인하고, 이후 질문이 들어오면 Analysis로 이어집니다.`
            : "데이터 업로드는 완료됐지만 아직 source가 선택되지 않았습니다. 상단에서 source를 고르면 해당 데이터 기준으로 질문을 이어갈 수 있습니다."),
    },
    ...(selectedDatasetOverview?.keyPoints.length
      ? [
          {
            type: "checklist" as const,
            items: selectedDatasetOverview.keyPoints,
          },
        ]
      : []),
    ...(selectedDatasetOverview && selectedPreEdaProfile?.qualitySummary
      ? [
          {
            type: "paragraph" as const,
            content: selectedPreEdaProfile.qualitySummary,
          },
        ]
      : []),
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
  const assistantChatCardClassName = "mx-0 w-full max-w-[1320px]";

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
              {selectedDataset.preEdaWarning ?? "잠시 후 다시 시도하면 최신 EDA 상태를 다시 조회합니다."}
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
        {(guidelines.length > 0 || guidelineUploadProgress !== null) && (
          <>
            <span className="text-[11px] font-medium text-[var(--genui-muted)] whitespace-nowrap">Guideline</span>
            {guidelineUploadProgress !== null ? (
              <span className="inline-flex h-7 min-w-0 max-w-[210px] items-center rounded-md border border-[var(--genui-border)] bg-[var(--genui-surface)] px-2 text-xs text-[var(--genui-text)]">
                업로드 중 {guidelineUploadProgress}%
              </span>
            ) : (
              <div className="relative min-w-0 w-full max-w-[210px]">
                <select
                  value={selectedGuidelineSourceId ?? ""}
                  onChange={handleGuidelineSelectionChange}
                  className="h-7 w-full min-w-0 appearance-none rounded-md border border-[var(--genui-border)] bg-[var(--genui-surface)] pl-2 pr-8 text-xs text-[var(--genui-text)] focus:outline-none focus:ring-1 focus:ring-[var(--genui-focus-ring)]"
                >
                  <option value="">선택 안 함 (일반 질문)</option>
                  {guidelines.map((guideline) => (
                    <option key={guideline.source_id} value={guideline.source_id}>
                      {guideline.filename}
                    </option>
                  ))}
                </select>
                <span className="pointer-events-none absolute inset-y-0 right-2 inline-flex items-center text-[var(--genui-muted)]">
                  <ChevronDown className="w-3.5 h-3.5" />
                </span>
              </div>
            )}
          </>
        )}
        {hasUploadedDatasets ? (
          <>
            <span
              className={`text-[11px] font-medium text-[var(--genui-muted)] whitespace-nowrap ${
                guidelines.length > 0 || guidelineUploadProgress !== null ? "ml-3" : ""
              }`}
            >
              데이터 소스
            </span>
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
                  : step.onNavigate
                    ? `${step.label} 오류 보기`
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
      <input
        ref={guidelineFileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={handleGuidelineFileSelected}
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
                <span className="text-xs font-semibold text-[var(--genui-text)]">EDA</span>
                <span className="text-sm text-[var(--genui-muted)]">데이터 프로파일 스냅샷</span>
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
                  onUseSuggestedQuestion={handleUseSuggestedQuestion}
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
                    const isLatestAssistantResponse =
                      chatResponse?.answer.trim() === msg.content.trim();
                    const messageVisualization = msg.visualization_result ?? null;
                    const messageVisualizationChart =
                      messageVisualization?.chart ?? messageVisualization?.chart_data ?? null;
                    const hasMessageVisualization =
                      hasVisualizationArtifact(messageVisualization)
                      || hasVisualizationChartData(messageVisualization);
                    const messageVisualizationMeta =
                      messageVisualizationChart?.chart_type ?? "Chart";

                    return (
                      <div key={msg.id} className="flex w-full justify-start">
                        <div className={cn("w-full space-y-4", assistantChatCardClassName)}>
                          <AssistantReportMessage
                            variant={isFailedMessage ? "error" : "final"}
                            title="AI 답변"
                            timestamp={messageTime}
                            sections={[{ type: "paragraph", content: msg.content }]}
                            layout="canvas"
                            maxBodyHeight={null}
                            evidence={isLatestAssistantResponse ? evidence : undefined}
                            repairGuidance={isLatestAssistantResponse ? repairGuidance : undefined}
                            onRepairAction={handleUseSuggestedQuestion}
                          />
                          {hasMessageVisualization && messageVisualization && (
                            <CardShell>
                              <CardHeader title="시각화 결과" meta={messageVisualizationMeta} />
                              <CardBody>
                                <VisualizationResultView visualization={messageVisualization} showCaption={false} />
                              </CardBody>
                            </CardShell>
                          )}
                        </div>
                      </div>
                    );
                  })}
                  {state === "running" && (
                    <div className="flex w-full justify-start">
                      <div className={cn("w-full space-y-4", assistantChatCardClassName)}>
                        <AssistantReportMessage
                          variant="streaming"
                          title={hasDatasetContext ? `Analyzing ${selectedDataset?.fileName || fileName || "Dataset"}` : "질문 처리 중"}
                          subtitle={hasDatasetContext ? selectedDataset?.fileName || fileName : "AI가 답변을 생성하고 있습니다."}
                          timestamp="Now"
                          sections={reportSections}
                          layout="canvas"
                          maxBodyHeight={null}
                          evidence={evidence}
                        />
                        {lastRunningTool && (
                          <div className="rounded-xl border border-[var(--genui-border)] bg-[var(--genui-panel)] px-4 py-3 shadow-sm">
                            <ToolCallIndicator status="running" label={lastRunningTool.name} sublabel="현재 질문 범위를 기준으로 계산 중입니다." />
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  <div ref={chatThreadEndRef} />
                </div>
              ) : reportSections.length > 0 ? (
                <AssistantReportMessage
                  variant={hasFailedAnalysis ? "error" : "final"}
                  title={hasFailedAnalysis ? "Analysis Failed" : "Analysis 결과"}
                  subtitle={hasDatasetContext ? currentDatasetLabel : undefined}
                  sections={reportSections}
                  layout="canvas"
                  maxBodyHeight={null}
                  evidence={evidence}
                  repairGuidance={repairGuidance}
                  onRepairAction={handleUseSuggestedQuestion}
                />
              ) : (
                <AssistantReportMessage
                  title="Analysis"
                  subtitle="아직 분석 결과가 없습니다."
                  sections={[{ type: "paragraph", content: "질문을 전송하면 Analysis 결과가 여기에 표시됩니다." }]}
                />
              )}
              {chatHistory.length === 0 && hasVisualizationPreview && latestVisualizationResult && (
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
                  layout="canvas"
                  maxBodyHeight={null}
                  evidence={evidence}
                  repairGuidance={repairGuidance}
                  onRepairAction={handleUseSuggestedQuestion}
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
                  onUseSuggestedQuestion={handleUseSuggestedQuestion}
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
                layout="canvas"
                maxBodyHeight={null}
                evidence={evidence}
                repairGuidance={repairGuidance}
                onRepairAction={handleUseSuggestedQuestion}
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
                  changes={pendingApprovalChanges}
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
                layout="canvas"
                maxBodyHeight={null}
                evidence={evidence}
                repairGuidance={repairGuidance}
                onRepairAction={handleUseSuggestedQuestion}
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
                layout="canvas"
                maxBodyHeight={null}
                evidence={evidence}
                repairGuidance={repairGuidance}
                onRepairAction={handleUseSuggestedQuestion}
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
                layout="canvas"
                maxBodyHeight={null}
                evidence={evidence}
                repairGuidance={repairGuidance}
                onRepairAction={handleUseSuggestedQuestion}
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
      onAddFiles={openGuidelineFilePicker}
    />
  );

  /* ── GATE BAR ── */
  const GateBarComponent = state === "needs-user" ? (
    <GateBar
      onApprove={pipeline.handleApprove}
      onCancel={pipeline.handleReject}
      onSubmitChange={pipeline.handleEditInstruction}
      approvalTitle={pendingApproval?.title}
      approvalDescription={pendingApproval?.summary}
      approvalItems={pendingApprovalChanges}
      approvalPreview={pendingApprovalPreview}
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
    <div className="h-full flex items-center px-4 w-full min-w-0">
      <span className="text-[15px] font-semibold tracking-tight text-[var(--genui-text)]">
        HADA
      </span>
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
