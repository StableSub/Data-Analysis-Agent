import { VISUALIZATION_CHART_THEME } from "../chartTheme";
import type { VisualizationTableCard } from "../visualizationModel";

interface FallbackTableCardProps {
  card: VisualizationTableCard;
}

export function FallbackTableCard({ card }: FallbackTableCardProps) {
  const columns = Object.keys(card.rows[0] || {}).slice(0, 8);

  if (columns.length === 0) {
    return null;
  }

  return (
    <div className={VISUALIZATION_CHART_THEME.cardClassName}>
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-left text-xs">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column} className="border-b border-gray-200 px-2 py-1 font-medium text-gray-700">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {card.rows.slice(0, 12).map((row, rowIndex) => (
              <tr key={rowIndex}>
                {columns.map((column) => (
                  <td key={column} className="border-b border-gray-100 px-2 py-1 text-gray-900">
                    {String(row[column] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
