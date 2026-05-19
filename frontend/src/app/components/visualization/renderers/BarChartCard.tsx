import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "../../ui/chart";
import { VISUALIZATION_CHART_THEME } from "../chartTheme";
import type { VisualizationChartCard } from "../visualizationModel";

interface BarChartCardProps {
  card: VisualizationChartCard;
}

export function BarChartCard({ card }: BarChartCardProps) {
  return (
    <div className={VISUALIZATION_CHART_THEME.cardClassName}>
      <ChartContainer
        config={card.config}
        className={`${VISUALIZATION_CHART_THEME.chartContainerClassName} ${VISUALIZATION_CHART_THEME.barCursorClassName}`}
      >
        <BarChart data={card.rows}>
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
            cursor={{ fill: VISUALIZATION_CHART_THEME.cursorFill }}
            content={<ChartTooltipContent className={VISUALIZATION_CHART_THEME.tooltipClassName} />}
          />
          {card.seriesKeys.length > 1 ? <ChartLegend content={<ChartLegendContent />} /> : null}
          {card.seriesKeys.map((key) => (
            <Bar
              key={key}
              dataKey={key}
              fill={`var(--color-${key})`}
              radius={4}
              activeBar={{
                fill: `var(--color-${key})`,
                fillOpacity: VISUALIZATION_CHART_THEME.activeBarOpacity,
                stroke: VISUALIZATION_CHART_THEME.cursorStroke,
                strokeWidth: 1,
              }}
            />
          ))}
        </BarChart>
      </ChartContainer>
    </div>
  );
}
