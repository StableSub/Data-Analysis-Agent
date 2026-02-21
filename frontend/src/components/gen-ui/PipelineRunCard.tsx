import { GaugeCircle, Table2 } from 'lucide-react';

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
      {/* Run Progress */}
      <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3.5">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-100">
              <GaugeCircle className="h-3.5 w-3.5 text-indigo-500" />
            </div>
            <span className="text-[11px] text-slate-400">run: {card.run.runId}</span>
          </div>
          <span className="font-mono text-[11px] text-slate-400">{current} / {total}</span>
        </div>
        <div className="mb-1.5 flex items-center justify-between">
          <span className="text-xs text-slate-400">{card.run.progress?.message ?? 'processing'}</span>
          <span className="text-xs font-semibold text-indigo-600">{total > 0 ? Math.round(progress) : 0}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
          <div
            className="h-1.5 rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Before → After Stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-indigo-400">Rows</p>
          <div className="flex items-baseline gap-1.5">
            <span className="text-sm font-medium text-slate-400">{formatNumber(card.result?.rowCountBefore)}</span>
            <span className="text-[10px] text-slate-300">→</span>
            <span className="text-base font-bold text-indigo-900">{formatNumber(card.result?.rowCountAfter)}</span>
          </div>
        </div>
        <div className="rounded-xl border border-violet-100 bg-violet-50 px-4 py-3">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-violet-400">Columns</p>
          <div className="flex items-baseline gap-1.5">
            <span className="text-sm font-medium text-slate-400">{formatNumber(card.result?.colCountBefore)}</span>
            <span className="text-[10px] text-slate-300">→</span>
            <span className="text-base font-bold text-violet-900">{formatNumber(card.result?.colCountAfter)}</span>
          </div>
        </div>
      </div>

      {/* Artifacts */}
      {card.artifacts?.length ? (
        <div className="overflow-hidden rounded-xl border border-slate-100">
          <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-3.5 py-2.5">
            <Table2 className="h-3.5 w-3.5 text-slate-400" />
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Artifacts</p>
            <span className="ml-auto rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] text-slate-400">{card.artifacts.length}</span>
          </div>
          <ul className="divide-y divide-slate-50">
            {card.artifacts.map((artifact) => (
              <li key={artifact.artifactId} className="flex items-center justify-between px-3.5 py-2.5 hover:bg-slate-50">
                <span className="text-xs text-slate-700">{artifact.label}</span>
                <span className="rounded-md border border-slate-100 bg-slate-50 px-2 py-0.5 text-[10px] text-slate-400">{artifact.kind}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </CardFrame>
  );
}
