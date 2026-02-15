import { FileOutput } from 'lucide-react';

import { Badge } from '../ui/badge';
import { CardFrame } from './CardFrame';
import { CardAction, ReportBuilderCardProps } from './types';

interface ReportBuilderCardViewProps {
  card: ReportBuilderCardProps;
  onAction?: (card: ReportBuilderCardProps, action: CardAction) => void;
}

export function ReportBuilderCard({ card, onAction }: ReportBuilderCardViewProps) {
  return (
    <CardFrame card={card} onAction={(base, action) => onAction?.(base as ReportBuilderCardProps, action)}>
      <div className="rounded-lg border border-slate-200/80 p-3 text-sm dark:border-white/10">
        <p className="text-xs text-slate-500 dark:text-slate-400">Report</p>
        <p className="text-slate-900 dark:text-white">{card.report.title}</p>
      </div>

      <div className="space-y-2">
        {card.report.sections.map((section) => (
          <div key={section.sectionId} className="rounded-lg border border-slate-200/80 px-3 py-2 text-sm dark:border-white/10">
            <div className="flex items-center justify-between gap-2">
              <span className="text-slate-800 dark:text-slate-200">{section.title}</span>
              <Badge variant="secondary" className={section.included ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'}>
                {section.included ? 'included' : 'excluded'}
              </Badge>
            </div>
          </div>
        ))}
      </div>

      <div className="inline-flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
        <FileOutput className="h-3.5 w-3.5" />
        export: {card.exportOptions.formats.join(', ')} (default: {card.exportOptions.defaultFormat})
      </div>
    </CardFrame>
  );
}
