import { GaugeCircle, Table2 } from 'lucide-react';

import { Progress } from '../ui/progress';
import { CardFrame } from './CardFrame';
import { CardAction, PipelineRunCardProps } from './types';

interface PipelineRunCardViewProps {
  card: PipelineRunCardProps;
  onAction?: (card: PipelineRunCardProps, action: CardAction) => void;
}

function formatNumber(value?: number): string {
  if (typeof value !== 'number') return '-';
  return new Intl.NumberFormat('ko-KR').format(value);
}

export function PipelineRunCard({ card, onAction }: PipelineRunCardViewProps) {
  const current = card.run.progress?.currentStep ?? 0;
  const total = card.run.progress?.totalSteps ?? 0;
  const progress = total > 0 ? (current / total) * 100 : 0;

  return (
    <CardFrame card={card} onAction={(base, action) => onAction?.(base as PipelineRunCardProps, action)}>
      <div className="rounded-lg border border-slate-200/80 p-3 dark:border-white/10">
        <p className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
          <GaugeCircle className="h-3.5 w-3.5" />
          run: {card.run.runId}
        </p>
        <div className="mt-2 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>{card.run.progress?.message || 'processing'}</span>
          <span>{current}/{total}</span>
        </div>
        <Progress value={progress} className="mt-1.5 h-2" />
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-lg border border-slate-200/80 p-3 dark:border-white/10">
          <p className="text-xs text-slate-500 dark:text-slate-400">Rows</p>
          <p className="text-slate-900 dark:text-white">{formatNumber(card.result?.rowCountBefore)} → {formatNumber(card.result?.rowCountAfter)}</p>
        </div>
        <div className="rounded-lg border border-slate-200/80 p-3 dark:border-white/10">
          <p className="text-xs text-slate-500 dark:text-slate-400">Columns</p>
          <p className="text-slate-900 dark:text-white">{formatNumber(card.result?.colCountBefore)} → {formatNumber(card.result?.colCountAfter)}</p>
        </div>
      </div>

      {card.artifacts?.length ? (
        <div className="rounded-lg border border-slate-200/80 p-3 text-xs dark:border-white/10">
          <p className="mb-2 inline-flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
            <Table2 className="h-3.5 w-3.5" />
            Artifacts
          </p>
          <ul className="space-y-1 text-slate-700 dark:text-slate-300">
            {card.artifacts.map((artifact) => (
              <li key={artifact.artifactId}>{artifact.label} ({artifact.kind})</li>
            ))}
          </ul>
        </div>
      ) : null}
    </CardFrame>
  );
}
