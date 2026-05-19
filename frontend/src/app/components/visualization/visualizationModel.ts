import {
  getVisualizationCharts,
  hasVisualizationArtifact,
  type VisualizationChartPayload,
  type VisualizationResultPayload,
} from "../../../lib/visualization";
import { VISUALIZATION_CHART_THEME } from "./chartTheme";

export type VisualizationCardKind = "chart" | "artifact" | "table";
export type VisualizationChartType =
  | "bar"
  | "line"
  | "scatter"
  | "hist"
  | "box"
  | "pie"
  | "heatmap"
  | string;

export type ChartRow = Record<string, unknown>;
export type ChartConfig = Record<string, { label: string; color: string }>;

export interface VisualizationChartCard {
  kind: "chart";
  id: string;
  chartType: VisualizationChartType;
  title: string;
  caption?: string;
  xKey?: string;
  yKey?: string;
  rows: ChartRow[];
  seriesKeys: string[];
  config: ChartConfig;
}

export interface VisualizationArtifactCard {
  kind: "artifact";
  id: string;
  title: string;
  caption?: string;
  mimeType: string;
  imageBase64: string;
}

export interface VisualizationTableCard {
  kind: "table";
  id: string;
  title: string;
  caption?: string;
  rows: ChartRow[];
}

export type VisualizationCard =
  | VisualizationChartCard
  | VisualizationArtifactCard
  | VisualizationTableCard;

function seriesKey(index: number): string {
  return `series_${index + 1}`;
}

function chartTitle(chart: VisualizationChartPayload, fallback: string): string {
  const caption = chart.caption?.trim();
  if (caption) {
    return caption;
  }
  const axisText = [chart.x_key, chart.y_key].filter(Boolean).join(" / ");
  return axisText || fallback;
}

function buildChartConfig(chart: VisualizationChartPayload): ChartConfig {
  const config: ChartConfig = {};
  chart.series?.forEach((series, index) => {
    const key = seriesKey(index);
    config[key] = {
      label: series.name?.trim() || key,
      color: VISUALIZATION_CHART_THEME.colors[index % VISUALIZATION_CHART_THEME.colors.length],
    };
  });
  return config;
}

function buildChartRows(chart: VisualizationChartPayload): ChartRow[] {
  if (!Array.isArray(chart.x) || !Array.isArray(chart.series)) {
    return [];
  }

  if (chart.chart_type === "scatter") {
    const firstSeries = chart.series[0];
    if (!Array.isArray(firstSeries?.y)) {
      return [];
    }
    return chart.x.map((xValue, index) => ({
      x: xValue,
      y: firstSeries.y?.[index] ?? null,
    }));
  }

  return chart.x.map((xValue, index) => {
    const row: ChartRow = { x: xValue };
    chart.series?.forEach((series, seriesIndex) => {
      row[seriesKey(seriesIndex)] = Array.isArray(series.y) ? (series.y[index] ?? null) : null;
    });
    return row;
  });
}

function buildChartCard(chart: VisualizationChartPayload, index: number): VisualizationChartCard | null {
  const rows = buildChartRows(chart);
  const config = buildChartConfig(chart);
  const seriesKeys = Object.keys(config);
  if (rows.length === 0 || seriesKeys.length === 0) {
    return null;
  }

  return {
    kind: "chart",
    id: `chart-${index}`,
    chartType: chart.chart_type || "bar",
    title: chartTitle(chart, `시각화 ${index + 1}`),
    caption: chart.caption || undefined,
    xKey: chart.x_key,
    yKey: chart.y_key,
    rows,
    seriesKeys: chart.chart_type === "scatter" ? ["y"] : seriesKeys,
    config: chart.chart_type === "scatter" ? { y: config[seriesKeys[0]] } : config,
  };
}

export function buildVisualizationCards(visualization: VisualizationResultPayload): VisualizationCard[] {
  const cards: VisualizationCard[] = [];

  getVisualizationCharts(visualization).forEach((chart, index) => {
    const card = buildChartCard(chart, index);
    if (card) {
      cards.push(card);
    }
  });

  if (hasVisualizationArtifact(visualization) && visualization.artifact?.image_base64) {
    cards.push({
      kind: "artifact",
      id: "artifact-0",
      title: visualization.chart?.chart_type || "시각화 이미지",
      caption: visualization.summary || undefined,
      mimeType: visualization.artifact.mime_type || "image/png",
      imageBase64: visualization.artifact.image_base64,
    });
  }

  if (Array.isArray(visualization.fallback_table) && visualization.fallback_table.length > 0) {
    cards.push({
      kind: "table",
      id: "table-0",
      title: "시각화 결과 표",
      caption: visualization.summary || undefined,
      rows: visualization.fallback_table,
    });
  }

  return cards;
}
