import { CartesianGrid, Scatter, ScatterChart, XAxis, YAxis } from "recharts";

import { ChartContainer, ChartTooltip, ChartTooltipContent } from "../../ui/chart";
import { VISUALIZATION_CHART_THEME } from "../chartTheme";
import type { VisualizationChartCard } from "../visualizationModel";

interface ScatterChartCardProps {
  card: VisualizationChartCard;
}

export function ScatterChartCard({ card }: ScatterChartCardProps) {
  const fill = card.config.y?.color || VISUALIZATION_CHART_THEME.colors[0];

  return (
    <div className={VISUALIZATION_CHART_THEME.cardClassName}>
      <ChartContainer config={card.config} className="min-h-[260px] w-full">
        <ScatterChart>
          <CartesianGrid stroke={VISUALIZATION_CHART_THEME.grid} />
          <XAxis
            dataKey="x"
            name={card.xKey || "x"}
            tick={{ fill: VISUALIZATION_CHART_THEME.tick, fontSize: 12 }}
            axisLine={{ stroke: VISUALIZATION_CHART_THEME.axis }}
            tickLine={{ stroke: VISUALIZATION_CHART_THEME.axis }}
          />
          <YAxis
            dataKey="y"
            name={card.yKey || "y"}
            tick={{ fill: VISUALIZATION_CHART_THEME.tick, fontSize: 12 }}
            axisLine={{ stroke: VISUALIZATION_CHART_THEME.axis }}
            tickLine={{ stroke: VISUALIZATION_CHART_THEME.axis }}
          />
          <ChartTooltip
            content={<ChartTooltipContent className={VISUALIZATION_CHART_THEME.tooltipClassName} />}
          />
          <Scatter data={card.rows} fill={fill} />
        </ScatterChart>
      </ChartContainer>
    </div>
  );
}
