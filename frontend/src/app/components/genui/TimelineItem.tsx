import React from "react";
import { Circle, CheckCircle2, AlertCircle, Loader2, PlayCircle } from "lucide-react";
import { cn } from "../../../lib/utils";

export type TimelineItemStatus = "normal" | "running" | "completed" | "failed" | "needs-user";

interface TimelineItemProps {
  status: TimelineItemStatus;
  title: string;
  subtext?: string;
  timestamp?: string;
  selected?: boolean;
  /** Small pill badge shown below subtext — use instead of actionLabel for nav-only items */
  statusBadge?: string;
  actionLabel?: string;
  onAction?: () => void;
  onClick?: () => void;
  className?: string;
}

export function TimelineItem({ 
  status, 
  title, 
  subtext, 
  timestamp, 
  selected,
  statusBadge,
  actionLabel, 
  onAction, 
  onClick, 
  className 
}: TimelineItemProps) {
  
  const getIcon = () => {
    switch (status) {
      case "running": return <Loader2 className="w-4 h-4 text-[var(--genui-running)] animate-spin" />;
      case "completed": return <CheckCircle2 className="w-4 h-4 text-[var(--genui-success)]" />;
      case "failed": return <AlertCircle className="w-4 h-4 text-[var(--genui-error)]" />;
      case "needs-user": return <PlayCircle className="w-4 h-4 text-[var(--genui-needs-user)] animate-pulse" />;
      default: return <Circle className="w-3 h-3 text-[var(--genui-muted)]" />;
    }
  };

  const badgeColor =
    status === "failed"
      ? "bg-[var(--genui-error)]/10 text-[var(--genui-error)] border-[var(--genui-error)]/20"
      : status === "needs-user"
      ? "bg-[var(--genui-needs-user)]/10 text-[var(--genui-needs-user)] border-[var(--genui-needs-user)]/20"
      : "bg-[var(--genui-surface)] text-[var(--genui-muted)] border-[var(--genui-border)]";

  return (
    <div 
      className={cn(
        "relative flex w-full items-start gap-3 p-3 rounded-lg transition-all select-none",
        onClick ? "cursor-pointer group" : "",
        selected 
          ? "bg-[var(--genui-panel)] border border-[var(--genui-border)] shadow-sm" 
          : "border border-transparent hover:bg-[var(--genui-surface)] hover:border-[var(--genui-border)]",
        className
      )}
      onClick={onClick}
    >
      <div className="mt-0.5 flex-shrink-0">
        {getIcon()}
      </div>
      
      <div className="flex-1 min-w-0 flex flex-col gap-1">
        <div className="flex justify-between items-start gap-2">
          <span className={cn(
            "text-sm font-medium truncate leading-tight",
            selected ? "text-[var(--genui-text)]" : "text-[var(--genui-text)]/90"
          )}>
            {title}
          </span>
          {timestamp && (
            <span className="text-[10px] text-[var(--genui-muted)] whitespace-nowrap flex-shrink-0 opacity-70 group-hover:opacity-100 transition-opacity">
              {timestamp}
            </span>
          )}
        </div>
        
        {subtext && (
          <p className="text-xs text-[var(--genui-muted)] truncate leading-tight">
            {subtext}
          </p>
        )}

        {/* Status Badge (nav-only, replaces action CTA) */}
        {statusBadge && (
          <div className="pt-1 flex items-center gap-1.5">
            <span className={cn(
              "inline-flex items-center px-1.5 py-0.5 rounded border text-[10px] font-semibold uppercase tracking-wider",
              badgeColor
            )}>
              {statusBadge}
            </span>
            {/* Nav hint — appears on hover */}
            {onClick && (
              <span className="text-[10px] text-[var(--genui-muted)] opacity-0 group-hover:opacity-100 transition-opacity">
                → View in Details
              </span>
            )}
          </div>
        )}

        {/* Action Button Area (kept for non-error interactive use) */}
        {actionLabel && onAction && (
          <div className="pt-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAction();
              }}
              className={cn(
                "px-3 py-1.5 text-xs font-semibold rounded-md transition-colors shadow-sm w-full text-center",
                status === "needs-user" 
                  ? "bg-[var(--genui-needs-user)] text-white hover:bg-[var(--genui-needs-user)]/90" 
                  : status === "failed"
                    ? "bg-[var(--genui-error)] text-white hover:bg-[var(--genui-error)]/90"
                    : "bg-[var(--genui-surface)] border border-[var(--genui-border)] text-[var(--genui-text)] hover:bg-[var(--genui-panel)]"
              )}
            >
              {actionLabel}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}