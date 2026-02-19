import { AlertCircle, RotateCw } from 'lucide-react';

import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { CardAction, ErrorCardProps } from './types';

interface ErrorCardViewProps {
  card: ErrorCardProps;
  onAction?: (card: ErrorCardProps, action: CardAction) => void;
}

export function ErrorCard({ card, onAction }: ErrorCardViewProps) {
  const retryAction = card.error.retryAction ?? card.actions?.find((action) => action.type === 'retry');

  return (
    <Card className="rounded-[var(--genui-card-radius)] border-genui-error-muted bg-genui-error-bg shadow-[var(--genui-card-shadow)]">
      <CardContent className="space-y-3 p-4">
        <div className="flex items-start gap-2">
          <AlertCircle className="mt-0.5 h-4 w-4 text-genui-error" />
          <div>
            <p className="text-sm font-semibold text-genui-error">{card.title}</p>
            {card.subtitle ? <p className="text-xs text-zinc-600">{card.subtitle}</p> : null}
          </div>
        </div>

        <div className="space-y-1 text-sm">
          <p className="text-zinc-800">실패 단계: {card.error.failedStep}</p>
          <p className="line-clamp-3 text-zinc-600">{card.error.reason}</p>
          {card.error.originalCardType ? (
            <p className="text-xs text-zinc-500">원본 카드: {card.error.originalCardType}</p>
          ) : null}
        </div>

        {retryAction ? (
          <Button variant="outline" size="sm" onClick={() => onAction?.(card, retryAction)}>
            <RotateCw className="mr-1.5 h-3.5 w-3.5" />
            재시도
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
