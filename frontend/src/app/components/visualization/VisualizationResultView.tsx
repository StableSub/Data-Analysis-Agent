import * as React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  Scatter,
  ScatterChart,
  XAxis,
  YAxis,
} from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "../ui/chart";
import { cn } from "../../../lib/utils";
import {
  getVisualizationChartData,
  hasVisualizationArtifact,
  type VisualizationResultPayload,
} from "../../../lib/visualization";

const CHART_COLORS = [
  "#2563eb",
  "#db2777",
  "#16a34a",
  "#d97706",
  "#7c3aed",
  "#0891b2",
];

type ChartRow = Record<string, unknown>;

function buildChartConfig(visualization: VisualizationResultPayload) {
  const chartData = getVisualizationChartData(visualization);
  const config: Record<string, { label: string; color: string }> = {};

  if (!chartData) {
    return config;
  }

  chartData.series?.forEach((series, index) => {
    const key = series.name?.trim() || `series_${index + 1}`;
    config[key] = {
      label: key,
      color: CHART_COLORS[index % CHART_COLORS.length],
    };
  });

  return config;
}

function buildChartRows(visualization: VisualizationResultPayload): ChartRow[] {
  const chartData = getVisualizationChartData(visualization);
  if (!chartData || !Array.isArray(chartData.x) || !Array.isArray(chartData.series)) {
    return [];
  }

  if (chartData.chart_type === "scatter") {
    const firstSeries = chartData.series[0];
    if (!firstSeries || !Array.isArray(firstSeries.y)) {
      return [];
    }

    return chartData.x.map((xValue, index) => ({
      x: xValue,
      y: firstSeries.y?.[index] ?? null,
    }));
  }

  return chartData.x.map((xValue, index) => {
    const row: ChartRow = { x: xValue };
    chartData.series?.forEach((series, seriesIndex) => {
      const key = series.name?.trim() || `series_${seriesIndex + 1}`;
      row[key] = Array.isArray(series.y) ? (series.y[index] ?? null) : null;
    });
    return row;
  });
}

interface VisualizationResultViewProps {
  visualization: VisualizationResultPayload;
  className?: string;
  showCaption?: boolean;
}

export function VisualizationResultView({
  visualization,
  className,
  showCaption = true,
}: VisualizationResultViewProps) {
  const hasArtifact = hasVisualizationArtifact(visualization);
  const chartData = getVisualizationChartData(visualization);
  const chartRows = buildChartRows(visualization);
  const chartConfig = buildChartConfig(visualization);
  const caption =
    chartData?.caption?.trim() || visualization.summary?.trim() || "시각화 결과";

  if (hasArtifact) {
    return (
      <div className={cn("space-y-2", className)}>
        <img
          src={`data:${visualization.artifact?.mime_type || "image/png"};base64,${visualization.artifact?.image_base64}`}
          alt={`${visualization.chart?.chart_type || "chart"} visualization`}
          className="w-full rounded-lg bg-white dark:bg-[#212121] border border-gray-200 dark:border-white/10"
        />
        {showCaption && caption ? (
          <p className="text-xs text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{caption}</p>
        ) : null}
      </div>
    );
  }

  if (!chartData || chartRows.length === 0) {
    return null;
  }

  const seriesKeys = Object.keys(chartConfig);

  return (
    <div className={cn("space-y-2", className)}>
      <div className="rounded-lg bg-white dark:bg-[#212121] border border-gray-200 dark:border-white/10 p-3">
        <ChartContainer config={chartConfig} className="min-h-[240px] w-full">
          {chartData.chart_type === "line" ? (
            <LineChart data={chartRows}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="x" />
              <YAxis />
              <ChartTooltip content={<ChartTooltipContent />} />
              {seriesKeys.length > 1 ? (
                <ChartLegend content={<ChartLegendContent />} />
              ) : null}
              {seriesKeys.map((key) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={`var(--color-${key})`}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          ) : chartData.chart_type === "scatter" ? (
            <ScatterChart>
              <CartesianGrid />
              <XAxis dataKey="x" name={visualization.chart?.x_key || "x"} />
              <YAxis dataKey="y" name={visualization.chart?.y_key || "y"} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Scatter data={chartRows} fill={CHART_COLORS[0]} />
            </ScatterChart>
          ) : (
            <BarChart data={chartRows}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="x" />
              <YAxis />
              <ChartTooltip content={<ChartTooltipContent />} />
              {seriesKeys.length > 1 ? (
                <ChartLegend content={<ChartLegendContent />} />
              ) : null}
              {seriesKeys.map((key) => (
                <Bar key={key} dataKey={key} fill={`var(--color-${key})`} radius={4} />
              ))}
            </BarChart>
          )}
        </ChartContainer>
      </div>
      {showCaption && caption ? (
        <p className="text-xs text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{caption}</p>
      ) : null}
    </div>
  );
}
