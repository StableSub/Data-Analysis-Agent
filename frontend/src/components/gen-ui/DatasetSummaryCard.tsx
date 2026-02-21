import { AlertTriangle, Database, Rows3 } from 'lucide-react';

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
  if (dtype === 'int' || dtype === 'float') return 'bg-indigo-50 text-indigo-600 border border-indigo-100';
  if (dtype === 'datetime') return 'bg-amber-50 text-amber-700 border border-amber-100';
  if (dtype === 'bool') return 'bg-violet-50 text-violet-600 border border-violet-100';
  if (dtype === 'category') return 'bg-emerald-50 text-emerald-700 border border-emerald-100';
  return 'bg-slate-50 text-slate-500 border border-slate-100';
}

export function DatasetSummaryCard({ card, onAction }: DatasetSummaryCardViewProps) {
  const completeness = typeof card.quality?.missingRateTotal === 'number' ? (1 - card.quality.missingRateTotal) * 100 : 0;

  return (
    <CardFrame card={card} onAction={(base, action) => onAction?.(base as DatasetSummaryCardProps, action)}>
      {/* Big Stat Tiles */}
      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-xl border border-indigo-100 bg-indigo-50 px-3 py-3">
          <div className="mb-1.5 flex items-center gap-1.5">
            <Rows3 className="h-3 w-3 text-indigo-400" />
            <span className="text-[10px] font-medium uppercase tracking-wider text-indigo-400">Rows</span>
          </div>
          <p className="text-xl font-semibold leading-none text-indigo-900">{formatNumber(card.dataset.rows)}</p>
        </div>
        <div className="rounded-xl border border-violet-100 bg-violet-50 px-3 py-3">
          <div className="mb-1.5 flex items-center gap-1.5">
            <Database className="h-3 w-3 text-violet-400" />
            <span className="text-[10px] font-medium uppercase tracking-wider text-violet-400">Cols</span>
          </div>
          <p className="text-xl font-semibold leading-none text-violet-900">{formatNumber(card.dataset.cols)}</p>
        </div>
        <div className={`rounded-xl border px-3 py-3 ${
          (card.quality?.missingRateTotal ?? 0) > 0.05
            ? 'border-amber-100 bg-amber-50'
            : 'border-emerald-100 bg-emerald-50'
        }`}>
          <div className="mb-1.5 flex items-center gap-1.5">
            <AlertTriangle className={`h-3 w-3 ${(card.quality?.missingRateTotal ?? 0) > 0.05 ? 'text-amber-500' : 'text-emerald-500'}`} />
            <span className={`text-[10px] font-medium uppercase tracking-wider ${(card.quality?.missingRateTotal ?? 0) > 0.05 ? 'text-amber-500' : 'text-emerald-500'}`}>Missing</span>
          </div>
          <p className={`text-xl font-semibold leading-none ${(card.quality?.missingRateTotal ?? 0) > 0.05 ? 'text-amber-900' : 'text-emerald-900'}`}>{formatPercent(card.quality?.missingRateTotal)}</p>
        </div>
      </div>

      {/* Completeness Bar */}
      <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
        <div className="mb-2.5 flex items-center justify-between">
          <span className="text-xs text-slate-500">Completeness</span>
          <span className={`text-xs font-semibold ${completeness >= 95 ? 'text-emerald-600' : completeness >= 80 ? 'text-amber-600' : 'text-red-600'}`}>
            {completeness.toFixed(1)}%
          </span>
        </div>
        <div className="h-2 w-full rounded-full bg-slate-200">
          <div
            className={`h-2 rounded-full transition-all ${completeness >= 95 ? 'bg-emerald-500' : completeness >= 80 ? 'bg-amber-500' : 'bg-red-500'}`}
            style={{ width: `${completeness}%` }}
          />
        </div>
      </div>

      {/* Schema Table */}
      {card.schema?.columns?.length ? (
        <div className="overflow-hidden rounded-xl border border-slate-100">
          <div className="border-b border-slate-100 bg-slate-50 px-4 py-2.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Schema Snapshot</p>
          </div>
          <div className="max-h-56 overflow-auto">
            <table className="w-full">
              <thead className="sticky top-0 bg-white">
                <tr className="border-b border-slate-100">
                  <th className="px-4 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-400">Column</th>
                  <th className="px-4 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-400">Type</th>
                  <th className="px-4 py-2 text-right text-[10px] font-semibold uppercase tracking-wider text-slate-400">Missing</th>
                  <th className="px-4 py-2 text-right text-[10px] font-semibold uppercase tracking-wider text-slate-400">Cardinality</th>
                </tr>
              </thead>
              <tbody>
                {card.schema.columns.map((column, index) => (
                  <tr key={column.name} className={`border-b border-slate-50 transition-colors hover:bg-slate-50 ${index % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'}`}>
                    <td className="px-4 py-2.5 text-xs font-medium text-slate-700">{column.name}</td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-medium ${typeClass(column.dtype)}`}>
                        {column.dtype}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-xs text-slate-500">{formatPercent(column.missingRate)}</td>
                    <td className="px-4 py-2.5 text-right text-xs text-slate-500">{formatNumber(column.cardinality)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {/* Preview */}
      {card.preview?.rows?.length ? (
        <div className="overflow-hidden rounded-xl border border-slate-100">
          <div className="border-b border-slate-100 bg-slate-50 px-4 py-2.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Preview {card.preview.truncated ? <span className="ml-1 normal-case text-slate-400">(truncated)</span> : ''}
            </p>
          </div>
          <div className="max-h-44 overflow-auto px-4 py-3">
            <pre className="text-[11px] leading-relaxed text-slate-500">{JSON.stringify(card.preview.rows.slice(0, 10), null, 2)}</pre>
          </div>
        </div>
      ) : null}
    </CardFrame>
  );
}
