export interface VisualizationChartSeriesPayload {
  name?: string;
  y?: unknown[];
}

export interface VisualizationChartPayload {
  chart_type?: string;
  x_key?: string;
  y_key?: string;
  x?: unknown[];
  series?: VisualizationChartSeriesPayload[];
  caption?: string | null;
}

export interface VisualizationArtifactPayload {
  mime_type?: string;
  image_base64?: string;
  code?: string;
}

export interface VisualizationResultPayload {
  status?: string;
  source_id?: string;
  summary?: string;
  chart?: VisualizationChartPayload;
  chart_data?: VisualizationChartPayload;
  artifact?: VisualizationArtifactPayload;
}

function parseChartPayload(payload: unknown): VisualizationChartPayload | undefined {
  if (!payload || typeof payload !== "object") {
    return undefined;
  }
  const data = payload as Record<string, unknown>;
  const series = Array.isArray(data.series)
    ? data.series
        .filter((item) => item && typeof item === "object")
        .map((item) => {
          const seriesItem = item as Record<string, unknown>;
          return {
            name: typeof seriesItem.name === "string" ? seriesItem.name : undefined,
            y: Array.isArray(seriesItem.y) ? seriesItem.y : undefined,
          };
        })
    : undefined;

  return {
    chart_type: typeof data.chart_type === "string" ? data.chart_type : undefined,
    x_key: typeof data.x_key === "string" ? data.x_key : undefined,
    y_key: typeof data.y_key === "string" ? data.y_key : undefined,
    x: Array.isArray(data.x) ? data.x : undefined,
    series,
    caption: typeof data.caption === "string" ? data.caption : undefined,
  };
}

export function parseVisualizationResult(payload: unknown): VisualizationResultPayload | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const data = payload as Record<string, unknown>;
  const artifactRaw = data.artifact;
  const artifact =
    artifactRaw && typeof artifactRaw === "object"
      ? (artifactRaw as Record<string, unknown>)
      : null;
  const imageBase64 =
    artifact && typeof artifact.image_base64 === "string" ? artifact.image_base64 : undefined;

  const chart = parseChartPayload(data.chart);
  const chartData = parseChartPayload(data.chart_data);

  if (!imageBase64 && !hasVisualizationChartData({ chart, chart_data: chartData })) {
    return null;
  }

  return {
    status: typeof data.status === "string" ? data.status : "generated",
    source_id: typeof data.source_id === "string" ? data.source_id : undefined,
    summary: typeof data.summary === "string" ? data.summary : undefined,
    chart,
    chart_data: chartData,
    artifact: imageBase64
      ? {
          mime_type:
            artifact && typeof artifact.mime_type === "string" ? artifact.mime_type : "image/png",
          image_base64: imageBase64,
          code: artifact && typeof artifact.code === "string" ? artifact.code : undefined,
        }
      : undefined,
  };
}

export function hasVisualizationArtifact(
  visualization: VisualizationResultPayload | null | undefined,
): boolean {
  return Boolean(
    typeof visualization?.artifact?.image_base64 === "string" &&
      visualization.artifact.image_base64.length > 0,
  );
}

export function getVisualizationChartData(
  visualization: Pick<VisualizationResultPayload, "chart" | "chart_data"> | null | undefined,
): VisualizationChartPayload | null {
  const candidates = [visualization?.chart_data, visualization?.chart];
  for (const candidate of candidates) {
    if (
      candidate &&
      typeof candidate.chart_type === "string" &&
      Array.isArray(candidate.x) &&
      Array.isArray(candidate.series) &&
      candidate.series.length > 0
    ) {
      return candidate;
    }
  }
  return null;
}

export function hasVisualizationChartData(
  visualization: Pick<VisualizationResultPayload, "chart" | "chart_data"> | null | undefined,
): boolean {
  return getVisualizationChartData(visualization) !== null;
}
