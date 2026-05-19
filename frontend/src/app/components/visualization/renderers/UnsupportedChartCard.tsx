import { VISUALIZATION_CHART_THEME } from "../chartTheme";
import type { VisualizationChartCard } from "../visualizationModel";

interface UnsupportedChartCardProps {
  card: VisualizationChartCard;
}

export function UnsupportedChartCard({ card }: UnsupportedChartCardProps) {
  return (
    <div className={VISUALIZATION_CHART_THEME.emptyClassName}>
      <p className="font-medium text-gray-900">아직 지원하지 않는 차트 유형입니다.</p>
      <p className="mt-1">chart_type: {card.chartType}</p>
    </div>
  );
}
