import { VISUALIZATION_CHART_THEME } from "../chartTheme";
import type { VisualizationArtifactCard } from "../visualizationModel";

interface ArtifactImageCardProps {
  card: VisualizationArtifactCard;
}

export function ArtifactImageCard({ card }: ArtifactImageCardProps) {
  return (
    <img
      src={`data:${card.mimeType};base64,${card.imageBase64}`}
      alt={`${card.title} visualization`}
      className={VISUALIZATION_CHART_THEME.imageClassName}
    />
  );
}
