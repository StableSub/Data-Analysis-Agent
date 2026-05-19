import * as React from "react";

import { cn } from "../../../lib/utils";
import type { VisualizationResultPayload } from "../../../lib/visualization";
import { VISUALIZATION_CHART_THEME } from "./chartTheme";
import { ArtifactImageCard } from "./renderers/ArtifactImageCard";
import { FallbackTableCard } from "./renderers/FallbackTableCard";
import { resolveChartRenderer } from "./renderers/registry";
import { buildVisualizationCards, type VisualizationCard } from "./visualizationModel";

interface VisualizationResultViewProps {
  visualization: VisualizationResultPayload;
  className?: string;
  showCaption?: boolean;
}

function renderCard(card: VisualizationCard): React.ReactNode {
  if (card.kind === "artifact") {
    return <ArtifactImageCard card={card} />;
  }
  if (card.kind === "table") {
    return <FallbackTableCard card={card} />;
  }
  const ChartRenderer = resolveChartRenderer(card.chartType);
  return <ChartRenderer card={card} />;
}

export function VisualizationResultView({
  visualization,
  className,
  showCaption = true,
}: VisualizationResultViewProps) {
  const cards = buildVisualizationCards(visualization);
  const fallbackCaption = visualization.summary?.trim() || "시각화 결과";

  if (cards.length === 0) {
    return null;
  }

  return (
    <div className={cn("space-y-3", className)}>
      {cards.map((card) => {
        const caption = card.caption?.trim() || fallbackCaption;
        return (
          <div key={card.id} className="space-y-2">
            {renderCard(card)}
            {showCaption && caption ? (
              <p className={VISUALIZATION_CHART_THEME.captionClassName}>{caption}</p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
