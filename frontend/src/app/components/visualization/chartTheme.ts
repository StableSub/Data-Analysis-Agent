export const VISUALIZATION_CHART_THEME = {
  cardClassName: "rounded-lg bg-white text-gray-900 border border-gray-200 p-4 shadow-sm",
  chartContainerClassName: "min-h-[260px] w-full",
  imageClassName: "w-full rounded-lg bg-white border border-gray-200 shadow-sm",
  captionClassName: "text-xs text-gray-600 whitespace-pre-wrap",
  titleClassName: "text-sm font-medium text-gray-900",
  emptyClassName: "rounded-lg bg-white text-gray-600 border border-gray-200 p-4 text-sm",
  barCursorClassName:
    "[&_.recharts-rectangle.recharts-tooltip-cursor]:!fill-[rgba(37,99,235,0.08)]",
  guideCursorClassName: "[&_.recharts-curve.recharts-tooltip-cursor]:!stroke-[#CBD5E1]",
  grid: "#E5E7EB",
  axis: "#D1D5DB",
  tick: "#111827",
  cursorFill: "rgba(37, 99, 235, 0.08)",
  cursorStroke: "#CBD5E1",
  activeBarOpacity: 0.82,
  tooltipClassName: "bg-white text-gray-900 border-gray-200 shadow-lg",
  colors: ["#2563EB", "#16A34A", "#F97316", "#DB2777", "#7C3AED", "#0891B2"],
} as const;
