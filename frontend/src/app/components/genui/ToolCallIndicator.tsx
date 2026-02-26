import React from "react";
import { Loader2, Check, X, ShieldCheck } from "lucide-react";
import { cn } from "../../../lib/utils";

export type IndicatorStatus = "running" | "completed" | "failed" | "needs-user";

interface ToolCallIndicatorProps {
  status: IndicatorStatus;
  label: string;
  /** Optional sublabel — shown as a second line in smaller text */
  sublabel?: string;
  className?: string;
}

export function ToolCallIndicator({ status, label, sublabel, className }: ToolCallIndicatorProps) {
  const labelColors: Record<IndicatorStatus, string> = {
    running:      "text-[var(--genui-running)]",
    completed:    "text-[var(--genui-text)]",
    failed:       "text-[var(--genui-error)]",
    "needs-user": "text-[var(--genui-needs-user)]",
  };

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* Status icon */}
      <div className="relative flex items-center justify-center w-5 h-5 flex-shrink-0">
        {status === "running" && (
          <Loader2 className="w-4 h-4 text-[var(--genui-running)] animate-spin" />
        )}
        {status === "completed" && (
          <div className="rounded-full bg-[var(--genui-success)]/10 p-0.5">
            <Check className="w-3.5 h-3.5 text-[var(--genui-success)]" />
          </div>
        )}
        {status === "failed" && (
          <div className="rounded-full bg-[var(--genui-error)]/10 p-0.5">
            <X className="w-3.5 h-3.5 text-[var(--genui-error)]" />
          </div>
        )}
        {status === "needs-user" && (
          <div className="rounded-full bg-[var(--genui-needs-user)]/10 p-0.5 animate-pulse">
            <ShieldCheck className="w-3.5 h-3.5 text-[var(--genui-needs-user)]" />
          </div>
        )}
      </div>

      {/* Label */}
      <div className="flex flex-col min-w-0">
        <span className={cn("text-sm font-medium truncate", labelColors[status])}>
          {label}
        </span>
        {sublabel && (
          <span className="text-xs text-[var(--genui-muted)] truncate leading-tight">
            {sublabel}
          </span>
        )}
      </div>

      {/* needs-user awaiting badge */}
      {status === "needs-user" && (
        <span className="flex-shrink-0 text-[10px] font-bold uppercase tracking-wider text-[var(--genui-needs-user)] bg-[var(--genui-needs-user)]/10 border border-[var(--genui-needs-user)]/25 px-1.5 py-0.5 rounded animate-pulse">
          Awaiting
        </span>
      )}
    </div>
  );
}