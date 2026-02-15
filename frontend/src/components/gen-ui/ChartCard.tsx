import { FileCode2, LineChart } from 'lucide-react';

import { Badge } from '../ui/badge';
import { CardFrame } from './CardFrame';
import { CardAction, ChartCardProps } from './types';

interface ChartCardViewProps {
  card: ChartCardProps;
  onAction?: (card: ChartCardProps, action: CardAction) => void;
}

export function ChartCard({ card, onAction }: ChartCardViewProps) {
  const isHtml = card.artifact.kind === 'html' || card.artifact.mimeType.includes('html');

  return (
    <CardFrame card={card} onAction={(base, action) => onAction?.(base as ChartCardProps, action)}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary" className="bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300">
          <LineChart className="mr-1 h-3 w-3" />
          {card.chart.chartType}
        </Badge>
        {card.chart.spec?.x ? <Badge variant="outline">x: {card.chart.spec.x}</Badge> : null}
        {card.chart.spec?.y ? (
          <Badge variant="outline">y: {Array.isArray(card.chart.spec.y) ? card.chart.spec.y.join(', ') : card.chart.spec.y}</Badge>
        ) : null}
      </div>

      {isHtml ? (
        <div className="overflow-hidden rounded-lg border border-slate-200/80 dark:border-white/10">
          <iframe title={card.chart.title || card.title} src={card.artifact.uri} className="h-[360px] w-full bg-white" />
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200/80 dark:border-white/10">
          <img
            src={card.artifact.uri}
            alt={card.chart.title || card.title}
            className="h-auto w-full object-contain"
          />
        </div>
      )}

      {card.codeRef?.available ? (
        <p className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
          <FileCode2 className="h-3.5 w-3.5" />
          codeRef run: {card.codeRef.runId}
        </p>
      ) : null}
    </CardFrame>
  );
}
