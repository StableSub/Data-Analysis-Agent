const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function isApiErrorStatus(error: unknown, status: number): boolean {
  return error instanceof ApiError && error.status === status;
}

export function buildApiUrl(path: string): string {
  return path.startsWith("http") ? path : `${API_BASE}${path}`;
}

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const url = buildApiUrl(path);
  const res = await fetch(url, {
    ...options,
    headers: {
      ...(options?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Response types ---

export interface DatasetResponse {
  id: number;
  source_id: string;
  filename: string;
  storage_path: string;
  filesize: number | null;
}

export interface DatasetListResponse {
  total: number;
  items: DatasetResponse[];
}

export interface SampleResponse {
  source_id: string;
  columns: string[];
  rows: Record<string, any>[];
}

export interface ChatResponse {
  answer: string;
  session_id: number;
  run_id?: string;
  thought_steps?: {
    phase: string;
    message: string;
    status: string;
  }[];
  pending_approval?: PendingApprovalPayload;
}

export interface ChatHistoryMessage {
  id: number;
  role: string;
  content: string;
  created_at: string;
}

export interface ChatHistoryResponse {
  session_id: number;
  messages: ChatHistoryMessage[];
}

export interface RagChunk {
  source_id: string;
  chunk_id: number;
  score: number;
  snippet: string;
}

export interface RagResponse {
  answer: string;
  retrieved_chunks: RagChunk[];
  executed_at: string;
}

export interface ReportResponse {
  report_id: string;
  session_id: number;
  summary_text: string;
}

// --- Request types ---

export interface ChatRequest {
  question: string;
  session_id?: number;
  model_id?: string;
  source_id?: string;
}

export interface PendingApprovalColumnSummary {
  column: string;
  missing_rate: number;
}

export interface PreprocessPendingApprovalPlan {
  operations: Record<string, unknown>[];
  planner_comment?: string;
  top_missing_columns?: PendingApprovalColumnSummary[];
  affected_columns?: string[];
  row_count?: number | null;
}

export interface VisualizationPreviewRow {
  [key: string]: string | number | boolean | null;
}

export interface VisualizationPendingApprovalPlan {
  chart_type: string;
  x_key: string;
  y_key?: string;
  mode?: string;
  reason?: string;
  x_is_datetime?: boolean;
  preview_rows?: VisualizationPreviewRow[];
}

export interface ReportPendingApprovalReview {
  revision_count?: number;
}

export type PendingApprovalPayload =
  | {
      stage: "preprocess";
      kind: "plan_review";
      title: string;
      summary: string;
      source_id: string;
      plan: PreprocessPendingApprovalPlan;
    }
  | {
      stage: "visualization";
      kind: "plan_review";
      title: string;
      summary: string;
      source_id: string;
      plan: VisualizationPendingApprovalPlan;
    }
  | {
      stage: "report";
      kind: "draft_review";
      title: string;
      summary: string;
      source_id: string;
      draft: string;
      review?: ReportPendingApprovalReview;
      plan?: Record<string, never>;
    };

export interface ResumeRunRequest {
  decision: "approve" | "revise" | "cancel";
  stage: "preprocess" | "visualization" | "report";
  instruction?: string;
}

export interface PendingApprovalResponse {
  session_id: number;
  run_id: string;
  pending_approval: PendingApprovalPayload;
}

export interface RagQueryRequest {
  query: string;
  top_k?: number;
  source_filter?: string[];
}

export type PreprocessOpType =
  | "drop_missing"
  | "impute"
  | "drop_columns"
  | "rename_columns"
  | "scale"
  | "derived_column";

export interface PreprocessOperation {
  op: PreprocessOpType;
  params: Record<string, unknown>;
}

export interface PreprocessApplyRequest {
  dataset_id: number;
  operations: PreprocessOperation[];
}

export interface PreprocessApplyResponse {
  dataset_id: number;
}

export interface ReportCreateRequest {
  session_id: number;
  analysis_results?: Record<string, unknown>[];
  visualizations?: Record<string, unknown>[];
  insights?: unknown[];
}

export interface ManualVizRequest {
  source_id: string;
  chart_type: "bar" | "line" | "pie" | "scatter" | "heatmap";
  columns: { x: string; y: string; color?: string; group?: string };
  limit?: number;
}

export interface ManualVizResponse {
  chart_type: string;
  data: Record<string, unknown>[];
}

// --- Endpoint functions ---

/** GET /datasets/{source_id}/sample */
export function fetchSample(sourceId: string): Promise<SampleResponse> {
  return apiRequest<SampleResponse>(`/datasets/${sourceId}/sample`);
}

/** DELETE /datasets/{source_id} */
export function deleteDataset(sourceId: string): Promise<void> {
  return apiRequest<void>(`/datasets/${sourceId}`, {
    method: "DELETE",
  });
}

/** POST /chats/ */
export function sendChat(req: ChatRequest): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/chats/", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/** GET /chats/{session_id}/history */
export function getChatHistory(sessionId: number): Promise<ChatHistoryResponse> {
  return apiRequest<ChatHistoryResponse>(`/chats/${sessionId}/history`);
}

export function fetchPendingApproval(
  sessionId: number,
  runId: string,
): Promise<PendingApprovalResponse> {
  return apiRequest<PendingApprovalResponse>(`/chats/${sessionId}/runs/${runId}/pending-approval`);
}

export function resumeChatRun(
  sessionId: number,
  runId: string,
  req: ResumeRunRequest,
  signal?: AbortSignal,
): Promise<Response> {
  return fetch(buildApiUrl(`/chats/${sessionId}/runs/${runId}/resume`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });
}

/** DELETE /chats/{session_id} */
export function deleteChatSession(sessionId: number): Promise<void> {
  return apiRequest<void>(`/chats/${sessionId}`, {
    method: "DELETE",
  });
}

/** POST /rag/query */
export function queryRag(req: RagQueryRequest): Promise<RagResponse> {
  return apiRequest<RagResponse>("/rag/query", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/** POST /preprocess/apply */
export function applyPreprocess(req: PreprocessApplyRequest): Promise<PreprocessApplyResponse> {
  return apiRequest<PreprocessApplyResponse>("/preprocess/apply", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/** POST /report/ */
export function createReport(req: ReportCreateRequest): Promise<ReportResponse> {
  return apiRequest<ReportResponse>("/report/", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/** POST /vizualization/manual (note: backend uses "vizualization") */
export function createManualViz(req: ManualVizRequest): Promise<ManualVizResponse> {
  return apiRequest<ManualVizResponse>("/vizualization/manual", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/** POST /export/csv — returns raw Blob for download */
export function exportCsv(resultId: string): Promise<Blob> {
  const url = `${API_BASE}/export/csv`;
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ result_id: resultId }),
  }).then((res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.blob();
  });
}

// --- Analysis Run API (target contract from spec) ---

export interface ApiEnvelope<T> {
  status: string;
  message: string;
  data: T;
}

export interface AnalysisRunAccepted {
  analysis_run_id: string;
  final_status: string;
}

export interface AnalysisRunStatus {
  analysis_run_id: string;
  final_status: string;
  current_stage: string;
  retry_count: number;
  analysis_error?: string | null;
  clarification_message?: string | null;
  analysis_result_id?: string | null;
}

export interface AnalysisResultResponse {
  analysis_result_id: string;
  source_id: string;
  question: string;
  analysis_type: string;
  execution_status: string;
  result_json: unknown;
  table?: unknown;
  chart_data?: unknown;
  error_stage?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface VisualizationFromAnalysisResponse {
  visualization_status: string;
  chart_data?: unknown;
  fallback_table?: unknown;
}

export interface AnalysisRunRequest {
  question: string;
  source_id: string;
  session_id?: number;
  model_id?: string;
}

export interface ClarificationRequest {
  answer: string;
}

/** POST /api/analysis/run */
export function startAnalysisRun(
  req: AnalysisRunRequest,
): Promise<ApiEnvelope<AnalysisRunAccepted>> {
  return apiRequest<ApiEnvelope<AnalysisRunAccepted>>("/api/analysis/run", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/** GET /api/analysis/runs/{analysis_run_id} */
export function getAnalysisRunStatus(
  analysisRunId: string,
): Promise<ApiEnvelope<AnalysisRunStatus>> {
  return apiRequest<ApiEnvelope<AnalysisRunStatus>>(
    `/api/analysis/runs/${analysisRunId}`,
  );
}

/** POST /api/analysis/runs/{analysis_run_id}/clarification */
export function submitClarification(
  analysisRunId: string,
  req: ClarificationRequest,
): Promise<ApiEnvelope<AnalysisRunAccepted>> {
  return apiRequest<ApiEnvelope<AnalysisRunAccepted>>(
    `/api/analysis/runs/${analysisRunId}/clarification`,
    { method: "POST", body: JSON.stringify(req) },
  );
}

/** GET /api/analysis/results/{analysis_result_id} */
export function getAnalysisResult(
  analysisResultId: string,
): Promise<ApiEnvelope<AnalysisResultResponse>> {
  return apiRequest<ApiEnvelope<AnalysisResultResponse>>(
    `/api/analysis/results/${analysisResultId}`,
  );
}

/** POST /api/visualization/from-analysis */
export function createVisualizationFromAnalysis(
  analysisResultId: string,
): Promise<ApiEnvelope<VisualizationFromAnalysisResponse>> {
  return apiRequest<ApiEnvelope<VisualizationFromAnalysisResponse>>(
    "/api/visualization/from-analysis",
    { method: "POST", body: JSON.stringify({ analysis_result_id: analysisResultId }) },
  );
}

/** Build SSE URL for /api/analysis/runs/{id}/stream */
export function buildAnalysisStreamUrl(analysisRunId: string): string {
  return buildApiUrl(`/api/analysis/runs/${analysisRunId}/stream`);
}

// --- EDA API (server-driven Pre-EDA) ---

export interface EdaSummary {
  row_count: number;
  column_count: number;
  numeric_columns: string[];
  categorical_columns: string[];
  datetime_columns: string[];
  boolean_columns: string[];
  identifier_columns: string[];
  group_key_columns: string[];
  quality_summary: string;
  summary_bullets: string[];
}

export interface EdaQualityColumn {
  column: string;
  missing_count: number;
  missing_rate: number;
}

export interface EdaQuality {
  total_rows: number;
  missing_columns: EdaQualityColumn[];
}

export interface EdaCorrelationPair {
  col_a: string;
  col_b: string;
  correlation: number;
}

export interface EdaCorrelations {
  top_pairs: EdaCorrelationPair[];
}

export interface EdaOutlierColumn {
  column: string;
  outlier_count: number;
  lower_bound: number;
  upper_bound: number;
}

export interface EdaOutliers {
  outlier_columns: EdaOutlierColumn[];
}

export interface EdaDistributionBin {
  label: string;
  count: number;
}

export interface EdaDistribution {
  column: string;
  bins: EdaDistributionBin[];
}

export interface EdaInsight {
  summary: string;
  preprocess_recommendation: EdaPreprocessRecommendation | null;
}

export interface EdaPreprocessRecommendation {
  summary: string;
  operations: EdaRecommendedOperation[];
}

export interface EdaRecommendedOperation {
  op: string;
  target_columns: string[];
  reason: string;
  priority: "high" | "medium" | "low";
}

/** GET /eda/{source_id}/summary */
export function fetchEdaSummary(
  sourceId: string,
): Promise<ApiEnvelope<EdaSummary>> {
  return apiRequest<ApiEnvelope<EdaSummary>>(`/eda/${sourceId}/summary`);
}

/** GET /eda/{source_id}/quality */
export function fetchEdaQuality(
  sourceId: string,
): Promise<ApiEnvelope<EdaQuality>> {
  return apiRequest<ApiEnvelope<EdaQuality>>(`/eda/${sourceId}/quality`);
}

/** GET /eda/{source_id}/correlations/top */
export function fetchEdaCorrelations(
  sourceId: string,
): Promise<ApiEnvelope<EdaCorrelations>> {
  return apiRequest<ApiEnvelope<EdaCorrelations>>(
    `/eda/${sourceId}/correlations/top`,
  );
}

/** GET /eda/{source_id}/outliers */
export function fetchEdaOutliers(
  sourceId: string,
): Promise<ApiEnvelope<EdaOutliers>> {
  return apiRequest<ApiEnvelope<EdaOutliers>>(`/eda/${sourceId}/outliers`);
}

/** GET /eda/{source_id}/distribution?column=... */
export function fetchEdaDistribution(
  sourceId: string,
  column: string,
): Promise<ApiEnvelope<EdaDistribution>> {
  return apiRequest<ApiEnvelope<EdaDistribution>>(
    `/eda/${sourceId}/distribution?column=${encodeURIComponent(column)}`,
  );
}

/** GET /eda/{source_id}/insights */
export function fetchEdaInsights(
  sourceId: string,
): Promise<ApiEnvelope<EdaInsight>> {
  return apiRequest<ApiEnvelope<EdaInsight>>(`/eda/${sourceId}/insights`);
}

// --- Upload with XHR progress tracking ---

export function uploadFile(
  file: File,
  onProgress: (percent: number) => void,
): Promise<DatasetResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/datasets/`);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          reject(new Error(JSON.parse(xhr.responseText).detail));
        } catch {
          reject(new Error(`HTTP ${xhr.status}`));
        }
      }
    });

    xhr.addEventListener("error", () => reject(new Error("네트워크 오류")));
    xhr.addEventListener("abort", () => reject(new Error("업로드 취소됨")));

    const fd = new FormData();
    fd.append("file", file);
    xhr.send(fd);
  });
}
