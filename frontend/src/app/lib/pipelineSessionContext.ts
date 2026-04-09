import type {
  PipelineSessionContext,
  PipelineSessionStateHint,
} from "../hooks/useAnalysisPipeline";

export function getRestoredFallbackStateHint(
  context: PipelineSessionContext,
): Exclude<PipelineSessionStateHint, "needs-user" | "error"> {
  const hasConversation =
    context.chatHistory.length > 0
    || (typeof context.latestAssistantAnswer === "string" && context.latestAssistantAnswer.trim().length > 0);

  if (hasConversation) {
    return "success";
  }
  if (context.uploadedDatasets.length > 0) {
    return "ready";
  }
  return "empty";
}

export function normalizeRestoredSessionContext(
  context: PipelineSessionContext,
): PipelineSessionContext {
  let nextBackendSessionId = context.backendSessionId ?? null;
  let nextRunId = context.runId ?? null;
  let nextTraceId = context.traceId ?? null;
  let nextPendingApproval = context.pendingApproval ?? null;
  let nextStateHint = context.stateHint ?? "empty";
  let nextErrorMessage = context.errorMessage ?? null;
  let changed = false;

  if (nextBackendSessionId === null) {
    if (nextRunId !== null) {
      nextRunId = null;
      changed = true;
    }
    if (nextTraceId !== null) {
      nextTraceId = null;
      changed = true;
    }
    if (nextPendingApproval !== null) {
      nextPendingApproval = null;
      changed = true;
    }
  }

  const hasValidPendingState =
    nextStateHint === "needs-user"
    && nextBackendSessionId !== null
    && typeof nextRunId === "string"
    && nextRunId.length > 0
    && nextPendingApproval !== null;

  if (nextStateHint === "needs-user" && !hasValidPendingState) {
    nextStateHint = getRestoredFallbackStateHint({
      ...context,
      backendSessionId: nextBackendSessionId,
      runId: nextRunId,
      traceId: nextTraceId,
      pendingApproval: nextPendingApproval,
    });
    changed = true;
  }

  if (nextStateHint !== "error" && nextErrorMessage !== null) {
    nextErrorMessage = null;
    changed = true;
  }

  if (!changed) {
    return context;
  }

  return {
    ...context,
    backendSessionId: nextBackendSessionId,
    runId: nextRunId,
    traceId: nextTraceId,
    pendingApproval: nextPendingApproval,
    stateHint: nextStateHint,
    errorMessage: nextErrorMessage,
  };
}
