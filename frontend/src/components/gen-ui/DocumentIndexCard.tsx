import { BookOpenText } from 'lucide-react';

import { CardFrame } from './CardFrame';
import { CardAction, DocumentIndexCardProps } from './types';

interface DocumentIndexCardViewProps {
  card: DocumentIndexCardProps;
  onAction?: (card: DocumentIndexCardProps, action: CardAction) => void;
}

export function DocumentIndexCard({ card, onAction }: DocumentIndexCardViewProps) {
  return (
    <CardFrame card={card} onAction={(base, action) => onAction?.(base as DocumentIndexCardProps, action)}>
      <div className="rounded-lg border border-genui-border bg-genui-card p-3 text-sm">
        <p className="text-xs text-slate-500 dark:text-slate-400">Index</p>
        <p className="text-slate-900 dark:text-white">{card.index.name} ({card.index.indexId})</p>
      </div>

      <div className="rounded-lg border border-genui-border bg-genui-card p-3">
        <p className="mb-2 inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
          <BookOpenText className="h-3.5 w-3.5" />
          Files ({card.corpus.totalFiles})
        </p>
        <ul className="space-y-1 text-sm text-slate-700 dark:text-slate-300">
          {card.corpus.files.map((file) => (
            <li key={file.fileId}>{file.filename} (p:{file.pages ?? '-'} / c:{file.chunks ?? '-'})</li>
          ))}
        </ul>
      </div>
    </CardFrame>
  );
}
