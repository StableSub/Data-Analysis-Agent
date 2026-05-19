import type { ComponentType } from "react";

import type { VisualizationChartCard } from "../visualizationModel";
import { BarChartCard } from "./BarChartCard";
import { LineChartCard } from "./LineChartCard";
import { ScatterChartCard } from "./ScatterChartCard";
import { UnsupportedChartCard } from "./UnsupportedChartCard";

type ChartRenderer = ComponentType<{ card: VisualizationChartCard }>;

const CHART_RENDERERS: Record<string, ChartRenderer> = {
  bar: BarChartCard,
  hist: BarChartCard,
  line: LineChartCard,
  scatter: ScatterChartCard,
};

export function resolveChartRenderer(chartType: string): ChartRenderer {
  return CHART_RENDERERS[chartType] || UnsupportedChartCard;
}
