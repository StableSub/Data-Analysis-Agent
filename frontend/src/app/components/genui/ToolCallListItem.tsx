import React from "react";
import { Loader2, Check, X, ShieldCheck, ChevronRight } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { IndicatorStatus } from "./ToolCallIndicator";

export interface ToolCallEntry {
  id: string;
  /** Function/tool name, e.g. "detect_missing" */
  name: string;
  status: IndicatorStatus;
  /** Short stringified args shown as sublabel */
  args?: string;
  /** Result summary (shown in detail panel) */
  result?: string;
  /** Human-readable elapsed time */
  duration?: string;
  /** Timestamp string */
  startedAt?: string;
}

interface ToolCallListItemProps {
  status: IndicatorStatus;
  name: string;
  args?: string;
  duration?: string;
  selected?: boolean;
  onClick?: () => void;
  className?: string;
}

const STATUS_BADGE: Record<IndicatorStatus, { label: string; className: string }> = {
  running:      { label: "Running",  className: "bg-[var(--genui-running)]/10   text-[var(--genui-running)]   border-[var(--genui-running)]/20"   },
  completed:    { label: "Done",     className: "bg-[var(--genui-success)]/10   text-[var(--genui-success)]   border-[var(--genui-success)]/20"   },
  failed:       { label: "Failed",   className: "bg-[var(--genui-error)]/10     text-[var(--genui-error)]     border-[var(--genui-error)]/20"     },
  "needs-user": { label: "Awaiting", className: "bg-[var(--genui-needs-user)]/10 text-[var(--genui-needs-user)] border-[var(--genui-needs-user)]/20" },
};

function StatusIcon({ status }: { status: IndicatorStatus }) {
  switch (status) {
    case "running":
      return <Loader2 className="w-3.5 h-3.5 text-[var(--genui-running)] animate-spin" />;
    case "completed":
      return <Check className="w-3.5 h-3.5 text-[var(--genui-success)]" />;
    case "failed":
      return <X className="w-3.5 h-3.5 text-[var(--genui-error)]" />;
    case "needs-user":
      return <ShieldCheck className="w-3.5 h-3.5 text-[var(--genui-needs-user)] animate-pulse" />;
  }
}

export function ToolCallListItem({
  status,
  name,
  args,
  duration,
  selected,
  onClick,
  className,
}: ToolCallListItemProps) {
  const badge = STATUS_BADGE[status];

  return (
    <div
      onClick={onClick}
      className={cn(
        "flex items-center gap-2.5 px-3 py-2.5 rounded-lg transition-all select-none",
        onClick ? "cursor-pointer" : "",
        selected
          ? "bg-[var(--genui-panel)] border border-[var(--genui-border)] shadow-sm"
          : "border border-transparent hover:bg-[var(--genui-surface)] hover:border-[var(--genui-border)]",
        className
      )}
    >
      {/* Status icon */}
      <div className="w-4 h-4 flex items-center justify-center flex-shrink-0">
        <StatusIcon status={status} />
      </div>

      {/* Name + args */}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-mono font-semibold text-[var(--genui-text)] truncate">
          {name}
        </p>
        {args && (
          <p className="text-[10px] font-mono text-[var(--genui-muted)] truncate leading-tight mt-0.5">
            {args}
          </p>
        )}
      </div>

      {/* Right: duration + badge + chevron */}
      <div className="flex items-center gap-1.5 flex-shrink-0">
        {duration && (
          <span className="text-[10px] text-[var(--genui-muted)] tabular-nums">{duration}</span>
        )}
        <span
          className={cn(
            "text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider",
            badge.className
          )}
        >
          {badge.label}
        </span>
        {selected && (
          <ChevronRight className="w-3 h-3 text-[var(--genui-muted)]" />
        )}
      </div>
    </div>
  );
}
