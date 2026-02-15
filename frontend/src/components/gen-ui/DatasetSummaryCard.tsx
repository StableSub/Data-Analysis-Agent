import { AlertTriangle, Database, Rows3 } from 'lucide-react';

import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { CardFrame } from './CardFrame';
import { CardAction, DatasetSummaryCardProps } from './types';

interface DatasetSummaryCardViewProps {
  card: DatasetSummaryCardProps;
  onAction?: (card: DatasetSummaryCardProps, action: CardAction) => void;
}

function formatPercent(value: number | undefined): string {
  if (typeof value !== 'number') return '-';
  return `${(value * 100).toFixed(1)}%`;
}

function formatNumber(value: number | undefined): string {
  if (typeof value !== 'number') return '-';
  return new Intl.NumberFormat('ko-KR').format(value);
}

type DatasetColumnDType = NonNullable<DatasetSummaryCardProps['schema']>['columns'][number]['dtype'];

function typeClass(dtype: DatasetColumnDType): string {
  if (dtype === 'int' || dtype === 'float') return 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
  if (dtype === 'datetime') return 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300';
  if (dtype === 'bool') return 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300';
  if (dtype === 'category') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300';
  return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
}

export function DatasetSummaryCard({ card, onAction }: DatasetSummaryCardViewProps) {
  const completeness = typeof card.quality?.missingRateTotal === 'number' ? (1 - card.quality.missingRateTotal) * 100 : 0;

  return (
    <CardFrame card={card} onAction={(base, action) => onAction?.(base as DatasetSummaryCardProps, action)}>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <div className="rounded-lg border border-slate-200/80 bg-white px-3 py-2 dark:border-white/10 dark:bg-[#202024]">
          <div className="mb-1 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <Rows3 className="h-3.5 w-3.5" /> Rows
          </div>
          <p className="text-sm font-medium text-slate-900 dark:text-white">{formatNumber(card.dataset.rows)}</p>
        </div>
        <div className="rounded-lg border border-slate-200/80 bg-white px-3 py-2 dark:border-white/10 dark:bg-[#202024]">
          <div className="mb-1 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <Database className="h-3.5 w-3.5" /> Cols
          </div>
          <p className="text-sm font-medium text-slate-900 dark:text-white">{formatNumber(card.dataset.cols)}</p>
        </div>
        <div className="rounded-lg border border-slate-200/80 bg-white px-3 py-2 dark:border-white/10 dark:bg-[#202024]">
          <div className="mb-1 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <AlertTriangle className="h-3.5 w-3.5" /> Missing
          </div>
          <p className="text-sm font-medium text-slate-900 dark:text-white">{formatPercent(card.quality?.missingRateTotal)}</p>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200/80 p-3 dark:border-white/10">
        <div className="mb-2 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>Completeness</span>
          <span className="font-medium text-slate-700 dark:text-slate-200">{completeness.toFixed(1)}%</span>
        </div>
        <Progress value={completeness} className="h-2 bg-slate-200 dark:bg-slate-700" />
      </div>

      {card.schema?.columns?.length ? (
        <div className="rounded-lg border border-slate-200/80 dark:border-white/10">
          <div className="border-b border-slate-200/80 px-3 py-2 text-xs font-medium text-slate-600 dark:border-white/10 dark:text-slate-300">
            Schema Snapshot
          </div>
          <div className="max-h-56 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500 dark:bg-[#202024] dark:text-slate-400">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Column</th>
                  <th className="px-3 py-2 text-left font-medium">Type</th>
                  <th className="px-3 py-2 text-right font-medium">Missing</th>
                  <th className="px-3 py-2 text-right font-medium">Cardinality</th>
                </tr>
              </thead>
              <tbody>
                {card.schema.columns.map((column) => (
                  <tr key={column.name} className="border-t border-slate-100 dark:border-white/10">
                    <td className="px-3 py-2 text-slate-800 dark:text-slate-200">{column.name}</td>
                    <td className="px-3 py-2">
                      <Badge variant="secondary" className={typeClass(column.dtype)}>
                        {column.dtype}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-right text-slate-600 dark:text-slate-300">
                      {formatPercent(column.missingRate)}
                    </td>
                    <td className="px-3 py-2 text-right text-slate-600 dark:text-slate-300">
                      {formatNumber(column.cardinality)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {card.preview?.rows?.length ? (
        <div className="rounded-lg border border-slate-200/80 dark:border-white/10">
          <div className="border-b border-slate-200/80 px-3 py-2 text-xs font-medium text-slate-600 dark:border-white/10 dark:text-slate-300">
            Preview {card.preview.truncated ? '(truncated)' : ''}
          </div>
          <div className="max-h-56 overflow-auto px-3 py-2 text-xs text-slate-700 dark:text-slate-300">
            <pre>{JSON.stringify(card.preview.rows.slice(0, 10), null, 2)}</pre>
          </div>
        </div>
      ) : null}
    </CardFrame>
  );
}
