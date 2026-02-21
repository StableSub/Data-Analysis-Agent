import { CheckCircle2, Circle, Wand2 } from 'lucide-react';

import { CardFrame } from './CardFrame';
import { CardAction, PreprocessPlanCardProps } from './types';

interface PreprocessPlanCardViewProps {
  card: PreprocessPlanCardProps;
  onAction?: (card: PreprocessPlanCardProps, action: CardAction) => void;
}

export function PreprocessPlanCard({ card, onAction }: PreprocessPlanCardViewProps) {
  return (
    <CardFrame card={card} onAction={(base, action) => onAction?.(base as PreprocessPlanCardProps, action)}>
      {/* Plan Meta */}
      <div className="rounded-xl border border-slate-100 bg-slate-50 px-3.5 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-100">
            <Wand2 className="h-3.5 w-3.5 text-indigo-500" />
          </div>
          <span className="text-[11px] text-slate-400">plan: {card.plan.planId}</span>
        </div>
        {card.plan.rationale ? (
          <p className="mt-2 text-sm leading-relaxed text-slate-500">{card.plan.rationale}</p>
        ) : null}
      </div>

      {/* Steps */}
      <div className="space-y-2">
        {card.plan.steps.map((step, index) => (
          <div
            key={step.stepId}
            className={`rounded-xl border px-4 py-3 transition-colors ${
              step.enabled
                ? 'border-slate-100 bg-white hover:border-slate-200 hover:shadow-sm'
                : 'border-slate-100 bg-slate-50 opacity-50'
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 flex-1 items-start gap-3">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-slate-500">
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <p className={`text-sm font-medium ${step.enabled ? 'text-slate-800' : 'text-slate-400'}`}>
                    {step.title}
                  </p>
                  {step.why ? (
                    <p className="mt-0.5 text-xs leading-relaxed text-slate-400">{step.why}</p>
                  ) : null}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <span className="rounded-md border border-slate-100 bg-slate-50 px-2 py-0.5 text-[10px] text-slate-400">{step.type}</span>
                {step.enabled ? (
                  <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                    <CheckCircle2 className="h-3 w-3" />on
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] text-slate-400">
                    <Circle className="h-3 w-3" />off
                  </span>
                )}
              </div>
            </div>
            {step.risk ? (
              <div className="ml-8 mt-2 inline-flex items-center gap-1 rounded-lg border border-amber-100 bg-amber-50 px-2 py-0.5 text-[10px] text-amber-700">
                ⚠️ risk: {step.risk}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </CardFrame>
  );
}
