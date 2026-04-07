const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Response types ---

export interface DatasetResponse {
  id: number;
  source_id: string;
  filename: string;
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
  trace_id?: string;
  thought_steps?: ThoughtStepPayload[];
  pending_approval?: PendingApprovalPayload;
}

export interface ThoughtStepPayload {
  phase: string;
  message: string;
  status: string;
  display_message?: string;
  detail_message?: string;
  audience?: "user" | "debug";
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
  trace_id?: string;
}

export interface PendingApprovalResponse {
  session_id: number;
  run_id: string;
  pending_approval: PendingApprovalPayload;
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

/** GET /chats/{session_id}/history */
export function getChatHistory(sessionId: number): Promise<ChatHistoryResponse> {
  return apiRequest<ChatHistoryResponse>(`/chats/${sessionId}/history`);
}

/** GET /chats/runs/{run_id}/pending-approval */
export function fetchPendingApproval(runId: string): Promise<PendingApprovalResponse> {
  return apiRequest<PendingApprovalResponse>(`/chats/runs/${runId}/pending-approval`);
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
