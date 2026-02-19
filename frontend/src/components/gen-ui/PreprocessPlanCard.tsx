import { CheckCircle2, Circle, Wand2 } from 'lucide-react';

import { Badge } from '../ui/badge';
import { CardFrame } from './CardFrame';
import { CardAction, PreprocessPlanCardProps } from './types';

interface PreprocessPlanCardViewProps {
  card: PreprocessPlanCardProps;
  onAction?: (card: PreprocessPlanCardProps, action: CardAction) => void;
}

export function PreprocessPlanCard({ card, onAction }: PreprocessPlanCardViewProps) {
  return (
    <CardFrame card={card} onAction={(base, action) => onAction?.(base as PreprocessPlanCardProps, action)}>
      <div className="rounded-lg border border-genui-border bg-genui-card p-3">
        <p className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
          <Wand2 className="h-3.5 w-3.5" />
          plan: {card.plan.planId}
        </p>
        {card.plan.rationale ? (
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{card.plan.rationale}</p>
        ) : null}
      </div>

      <div className="space-y-2">
        {card.plan.steps.map((step, index) => (
          <div key={step.stepId} className="rounded-lg border border-genui-border bg-genui-card p-3 text-sm">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-slate-900 dark:text-white">{index + 1}. {step.title}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{step.why}</p>
              </div>
              <Badge variant="secondary" className="bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                {step.type}
              </Badge>
            </div>
            <div className="mt-2 flex items-center gap-2 text-xs">
              {step.enabled ? (
                <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400"><CheckCircle2 className="h-3.5 w-3.5" />enabled</span>
              ) : (
                <span className="inline-flex items-center gap-1 text-slate-500 dark:text-slate-400"><Circle className="h-3.5 w-3.5" />disabled</span>
              )}
              {step.risk ? <span className="text-amber-600 dark:text-amber-400">risk: {step.risk}</span> : null}
            </div>
          </div>
        ))}
      </div>
    </CardFrame>
  );
}
