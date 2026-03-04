const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
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

/** POST /chats/ */
export function sendChat(req: ChatRequest): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/chats/", {
    method: "POST",
    body: JSON.stringify(req),
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
