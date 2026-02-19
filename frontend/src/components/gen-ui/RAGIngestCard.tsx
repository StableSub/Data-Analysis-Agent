import { Database, FileSearch2 } from 'lucide-react';

import { Badge } from '../ui/badge';
import { CardFrame } from './CardFrame';
import { CardAction, RAGIngestCardProps } from './types';

interface RAGIngestCardViewProps {
  card: RAGIngestCardProps;
  onAction?: (card: RAGIngestCardProps, action: CardAction) => void;
}

export function RAGIngestCard({ card, onAction }: RAGIngestCardViewProps) {
  return (
    <CardFrame card={card} onAction={(base, action) => onAction?.(base as RAGIngestCardProps, action)}>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 text-sm">
        <div className="rounded-lg border border-genui-border bg-genui-card p-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">File</p>
          <p className="text-slate-900 dark:text-white">{card.ingest.filename}</p>
        </div>
        <div className="rounded-lg border border-genui-border bg-genui-card p-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">Embedding</p>
          <p className="text-slate-900 dark:text-white">{card.ingest.embeddingModel.provider}/{card.ingest.embeddingModel.name}</p>
        </div>
        <div className="rounded-lg border border-genui-border bg-genui-card p-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">Cache</p>
          <p className="text-slate-900 dark:text-white">{card.ingest.cache.hit ? 'hit' : 'miss'}</p>
        </div>
      </div>

      <div className="space-y-2">
        {card.ingest.stages.map((stage) => (
          <div key={stage.name} className="flex items-center justify-between rounded-lg border border-genui-border bg-genui-card px-3 py-2 text-sm">
            <span className="inline-flex items-center gap-1.5 text-slate-700 dark:text-slate-200">
              <Database className="h-3.5 w-3.5" />
              {stage.name}
            </span>
            <Badge variant="secondary" className="bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
              {stage.status}
            </Badge>
          </div>
        ))}
      </div>

      {card.documents ? (
        <p className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
          <FileSearch2 className="h-3.5 w-3.5" />
          pages: {card.documents.totalPages ?? '-'} / chunks: {card.documents.totalChunks ?? '-'}
        </p>
      ) : null}
    </CardFrame>
  );
}
