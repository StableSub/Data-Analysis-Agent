import React from "react";
import {
  Loader2, CheckCircle2, XCircle, ShieldCheck,
  Clock, ArrowRight,
} from "lucide-react";
import { cn } from "../../../lib/utils";

/* ─────────────────────────────────────────────
   Types
───────────────────────────────────────────── */
export type PipelineStepStatus =
  | "queued"
  | "running"
  | "success"
  | "failed"
  | "needs-user";

export interface PipelineStep {
  id: string;
  /** Display label: Intake / Preprocess / RAG / Visualization / Merge / Report */
  label: string;
  /** Secondary line — e.g. "Scanning missing values…" / "Awaiting approval" */
  sublabel?: string;
  status: PipelineStepStatus;
  /** How many tool calls belong to this stage (optional) */
  toolCount?: number;
}

export interface PipelineTrackerProps {
  steps: PipelineStep[];
  /** Optional nav handler — clicking a step row navigates to Tool detail */
  onStepClick?: (stepId: string) => void;
  className?: string;
}

/* ─────────────────────────────────────────────
   Status → icon / colour
───────────────────────────────────────────── */
function StepIcon({ status }: { status: PipelineStepStatus }) {
  switch (status) {
    case "queued":
      return (
        <div className="w-5 h-5 rounded-full border-2 border-[var(--genui-border)] bg-[var(--genui-surface)] flex items-center justify-center">
          <Clock className="w-2.5 h-2.5 text-[var(--genui-muted)]" />
        </div>
      );
    case "running":
      return (
        <div className="w-5 h-5 rounded-full bg-[var(--genui-running)]/15 border border-[var(--genui-running)]/30 flex items-center justify-center">
          <Loader2 className="w-3 h-3 text-[var(--genui-running)] animate-spin" />
        </div>
      );
    case "success":
      return (
        <div className="w-5 h-5 rounded-full bg-[var(--genui-success)]/15 border border-[var(--genui-success)]/30 flex items-center justify-center">
          <CheckCircle2 className="w-3 h-3 text-[var(--genui-success)]" />
        </div>
      );
    case "failed":
      return (
        <div className="w-5 h-5 rounded-full bg-[var(--genui-error)]/15 border border-[var(--genui-error)]/30 flex items-center justify-center">
          <XCircle className="w-3 h-3 text-[var(--genui-error)]" />
        </div>
      );
    case "needs-user":
      return (
        <div className="w-5 h-5 rounded-full bg-[var(--genui-needs-user)]/15 border border-[var(--genui-needs-user)]/40 flex items-center justify-center animate-pulse">
          <ShieldCheck className="w-3 h-3 text-[var(--genui-needs-user)]" />
        </div>
      );
  }
}

const STATUS_BADGE: Record<
  PipelineStepStatus,
  { label: string; cls: string } | null
> = {
  queued:       null,
  running:      { label: "Running",  cls: "bg-[var(--genui-running)]/10   text-[var(--genui-running)]   border-[var(--genui-running)]/20"   },
  success:      { label: "Done",     cls: "bg-[var(--genui-success)]/10   text-[var(--genui-success)]   border-[var(--genui-success)]/20"   },
  failed:       { label: "Failed",   cls: "bg-[var(--genui-error)]/10     text-[var(--genui-error)]     border-[var(--genui-error)]/20"     },
  "needs-user": { label: "Awaiting", cls: "bg-[var(--genui-needs-user)]/10 text-[var(--genui-needs-user)] border-[var(--genui-needs-user)]/20" },
};

/* ─────────────────────────────────────────────
   Connector line between steps
───────────────────────────────────────────── */
function Connector({ fromStatus }: { fromStatus: PipelineStepStatus }) {
  const isActive = fromStatus === "success";
  return (
    <div className="flex justify-center py-0.5 ml-2.5">
      <div
        className={cn(
          "w-px h-4",
          isActive
            ? "bg-[var(--genui-success)]/40"
            : "bg-[var(--genui-border)]",
        )}
      />
    </div>
  );
}

/* ─────────────────────────────────────────────
   Single step row
───────────────────────────────────────────── */
function StepRow({
  step,
  isFirst,
  isLast,
  onClick,
}: {
  step: PipelineStep;
  isFirst: boolean;
  isLast: boolean;
  onClick?: () => void;
}) {
  const badge = STATUS_BADGE[step.status];
  const isHighlighted = step.status === "running" || step.status === "needs-user" || step.status === "failed";

  return (
    <div
      onClick={onClick}
      className={cn(
        "flex items-start gap-3 px-3 py-2 rounded-lg transition-all select-none",
        onClick && "cursor-pointer",
        isHighlighted && step.status === "running"    && "bg-[var(--genui-running)]/5   border border-[var(--genui-running)]/15",
        isHighlighted && step.status === "needs-user" && "bg-[var(--genui-needs-user)]/8 border border-[var(--genui-needs-user)]/20",
        isHighlighted && step.status === "failed"     && "bg-[var(--genui-error)]/5     border border-[var(--genui-error)]/15",
        !isHighlighted && "border border-transparent hover:bg-[var(--genui-surface)]",
      )}
    >
      {/* Icon column */}
      <div className="flex-shrink-0 mt-0.5">
        <StepIcon status={step.status} />
      </div>

      {/* Label + sublabel */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-1">
          <span
            className={cn(
              "text-xs font-semibold leading-tight",
              step.status === "queued"
                ? "text-[var(--genui-muted)]"
                : step.status === "needs-user"
                ? "text-[var(--genui-needs-user)]"
                : step.status === "failed"
                ? "text-[var(--genui-error)]"
                : "text-[var(--genui-text)]",
            )}
          >
            {step.label}
          </span>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {badge && (
              <span
                className={cn(
                  "text-[9px] font-bold px-1.5 py-px rounded border uppercase tracking-widest leading-none",
                  badge.cls,
                )}
              >
                {badge.label}
              </span>
            )}
            {step.toolCount !== undefined && step.status === "success" && (
              <span className="text-[9px] text-[var(--genui-muted)] tabular-nums">
                {step.toolCount} calls
              </span>
            )}
            {onClick && (
              <ArrowRight className="w-2.5 h-2.5 text-[var(--genui-muted)] opacity-0 group-hover:opacity-100" />
            )}
          </div>
        </div>

        {step.sublabel && (
          <p
            className={cn(
              "text-[10px] leading-snug mt-0.5",
              step.status === "needs-user"
                ? "text-[var(--genui-needs-user)]/80"
                : step.status === "failed"
                ? "text-[var(--genui-error)]/80"
                : "text-[var(--genui-muted)]",
            )}
          >
            {step.sublabel}
          </p>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   PipelineTracker — public export
───────────────────────────────────────────── */
export function PipelineTracker({
  steps,
  onStepClick,
  className,
}: PipelineTrackerProps) {
  return (
    <div className={cn("space-y-0", className)}>
      {steps.map((step, i) => (
        <React.Fragment key={step.id}>
          <StepRow
            step={step}
            isFirst={i === 0}
            isLast={i === steps.length - 1}
            onClick={onStepClick ? () => onStepClick(step.id) : undefined}
          />
          {i < steps.length - 1 && <Connector fromStatus={step.status} />}
        </React.Fragment>
      ))}
    </div>
  );
}
