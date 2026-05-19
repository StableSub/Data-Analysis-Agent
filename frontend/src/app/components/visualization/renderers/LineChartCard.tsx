import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "../../ui/chart";
import { VISUALIZATION_CHART_THEME } from "../chartTheme";
import type { VisualizationChartCard } from "../visualizationModel";

interface LineChartCardProps {
  card: VisualizationChartCard;
}

export function LineChartCard({ card }: LineChartCardProps) {
  return (
    <div className={VISUALIZATION_CHART_THEME.cardClassName}>
      <ChartContainer config={card.config} className="min-h-[260px] w-full">
        <LineChart data={card.rows}>
          <CartesianGrid vertical={false} stroke={VISUALIZATION_CHART_THEME.grid} />
          <XAxis
            dataKey="x"
            tick={{ fill: VISUALIZATION_CHART_THEME.tick, fontSize: 12 }}
            axisLine={{ stroke: VISUALIZATION_CHART_THEME.axis }}
            tickLine={{ stroke: VISUALIZATION_CHART_THEME.axis }}
          />
          <YAxis
            tick={{ fill: VISUALIZATION_CHART_THEME.tick, fontSize: 12 }}
            axisLine={{ stroke: VISUALIZATION_CHART_THEME.axis }}
            tickLine={{ stroke: VISUALIZATION_CHART_THEME.axis }}
          />
          <ChartTooltip
            content={<ChartTooltipContent className={VISUALIZATION_CHART_THEME.tooltipClassName} />}
          />
          {card.seriesKeys.length > 1 ? <ChartLegend content={<ChartLegendContent />} /> : null}
          {card.seriesKeys.map((key) => (
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
      </ChartContainer>
    </div>
  );
}
