import { AlertCircle, CheckCircle2, Clock3, PauseCircle, Pin, PlayCircle, XCircle } from 'lucide-react';

import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { BaseCardProps, CardAction } from './types';

interface CardFrameProps {
  card: BaseCardProps;
  onAction?: (card: BaseCardProps, action: CardAction) => void;
  children: React.ReactNode;
}

function statusLabel(status: BaseCardProps['status']): string {
  if (status === 'queued') return 'Queued';
  if (status === 'running') return 'Running';
  if (status === 'success') return 'Success';
  if (status === 'failed') return 'Failed';
  if (status === 'canceled') return 'Canceled';
  if (status === 'needs_user') return 'Need Input';
  return 'Idle';
}

function statusClass(status: BaseCardProps['status']): string {
  if (status === 'success') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300';
  if (status === 'failed') return 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300';
  if (status === 'running') return 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
  if (status === 'queued') return 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300';
  if (status === 'needs_user') return 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300';
  return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
}

function statusIcon(status: BaseCardProps['status']) {
  if (status === 'running') return <PlayCircle className="h-3.5 w-3.5" />;
  if (status === 'queued') return <Clock3 className="h-3.5 w-3.5" />;
  if (status === 'success') return <CheckCircle2 className="h-3.5 w-3.5" />;
  if (status === 'failed') return <XCircle className="h-3.5 w-3.5" />;
  if (status === 'canceled') return <PauseCircle className="h-3.5 w-3.5" />;
  if (status === 'needs_user') return <AlertCircle className="h-3.5 w-3.5" />;
  return <Clock3 className="h-3.5 w-3.5" />;
}

function actionLabel(action: CardAction): string {
  if (action.label) return action.label;
  switch (action.type) {
    case 'add_to_report':
      return 'Add to Report';
    case 'view_log':
      return 'View Log';
    case 'open_artifact':
      return 'Open Artifact';
    case 'retry':
      return 'Retry';
    case 'cancel':
      return 'Cancel';
    case 'apply':
      return 'Apply';
    case 'edit':
      return 'Edit';
    case 'dismiss':
      return 'Dismiss';
    case 'pin':
      return 'Pin';
    case 'unpin':
      return 'Unpin';
  }
}

function actionVariant(action: CardAction): 'outline' | 'default' | 'secondary' | 'destructive' {
  if (action.type === 'apply') return 'default';
  if (action.type === 'cancel') return 'destructive';
  if (action.type === 'retry') return 'secondary';
  return 'outline';
}

export function CardFrame({ card, onAction, children }: CardFrameProps) {
  return (
    <Card className="border-slate-200/80 shadow-sm dark:border-white/10 dark:bg-[#1c1c1e]">
      <CardHeader className="space-y-3 border-b border-slate-200/80 pb-4 dark:border-white/10">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base text-slate-900 dark:text-white">{card.title}</CardTitle>
            {card.subtitle ? (
              <CardDescription className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                {card.subtitle}
              </CardDescription>
            ) : null}
          </div>

          <div className="flex items-center gap-2">
            <Badge className={statusClass(card.status)}>
              <span className="mr-1 inline-flex items-center">{statusIcon(card.status)}</span>
              {statusLabel(card.status)}
            </Badge>
            {card.source.runId ? (
              <Badge variant="secondary" className="bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300">
                run:{card.source.runId}
              </Badge>
            ) : null}
          </div>
        </div>

        {card.badges?.length ? (
          <div className="flex flex-wrap items-center gap-2">
            {card.badges.map((badge) => (
              <Badge key={badge.label} variant="secondary" className="bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                {badge.tone === 'success' ? <CheckCircle2 className="mr-1 h-3 w-3" /> : null}
                {badge.label}
              </Badge>
            ))}
          </div>
        ) : null}
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        {card.summary ? <p className="text-sm text-slate-600 dark:text-slate-300">{card.summary}</p> : null}

        {children}

        {card.details?.length ? (
          <div className="space-y-2">
            {card.details.map((detail) => (
              <details key={detail.label} open={detail.defaultOpen} className="rounded-lg border border-slate-200/80 px-3 py-2 text-xs dark:border-white/10">
                <summary className="cursor-pointer text-slate-700 dark:text-slate-200">{detail.label}</summary>
                <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[11px] text-slate-700 dark:bg-[#202024] dark:text-slate-300">
                  {typeof detail.content === 'string' ? detail.content : JSON.stringify(detail.content, null, 2)}
                </pre>
              </details>
            ))}
          </div>
        ) : null}

        {card.actions?.length ? (
          <div className="flex flex-wrap items-center gap-2 border-t border-slate-200/80 pt-3 dark:border-white/10">
            {card.actions.map((action, index) => (
              <Button key={`${action.type}-${index}`} size="sm" variant={actionVariant(action)} onClick={() => onAction?.(card, action)}>
                {action.type === 'pin' || action.type === 'unpin' ? <Pin className="mr-1.5 h-3.5 w-3.5" /> : null}
                {actionLabel(action)}
              </Button>
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
