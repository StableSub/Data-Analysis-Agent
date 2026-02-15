import { Quote } from 'lucide-react';

import { Badge } from '../ui/badge';
import { CardFrame } from './CardFrame';
import { CardAction, RetrievalEvidenceCardProps } from './types';

interface RetrievalEvidenceCardViewProps {
  card: RetrievalEvidenceCardProps;
  onAction?: (card: RetrievalEvidenceCardProps, action: CardAction) => void;
}

export function RetrievalEvidenceCard({ card, onAction }: RetrievalEvidenceCardViewProps) {
  return (
    <CardFrame card={card} onAction={(base, action) => onAction?.(base as RetrievalEvidenceCardProps, action)}>
      <div className="rounded-lg border border-slate-200/80 p-3 text-sm dark:border-white/10">
        <p className="text-xs text-slate-500 dark:text-slate-400">Query</p>
        <p className="text-slate-900 dark:text-white">{card.retrieval.query}</p>
      </div>

      <div className="space-y-2">
        {card.chunks.map((chunk) => (
          <div key={chunk.chunkId} className="rounded-lg border border-slate-200/80 p-3 dark:border-white/10">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <p className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                <Quote className="h-3.5 w-3.5" />
                {chunk.source.filename} p.{chunk.source.page ?? '-'}
              </p>
              {typeof chunk.score === 'number' ? <Badge variant="outline">score {chunk.score.toFixed(3)}</Badge> : null}
            </div>
            <p className="text-sm text-slate-700 dark:text-slate-300">{chunk.text}</p>
          </div>
        ))}
      </div>
    </CardFrame>
  );
}
