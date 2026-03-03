import React from "react";
import { cn } from "../../../lib/utils";

export type StatusType = "empty" | "uploading" | "running" | "needs-user" | "error" | "success";

interface StatusBadgeProps {
  status: StatusType;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = {
    empty: { label: "No Dataset", color: "bg-[var(--genui-muted)]/20 text-[var(--genui-muted)] border-[var(--genui-border)]" },
    uploading: { label: "Uploading...", color: "bg-[var(--genui-running)]/10 text-[var(--genui-running)] border-[var(--genui-running)]/20" },
    running: { label: "Running", color: "bg-[var(--genui-running)] text-white border-transparent" },
    "needs-user": { label: "Needs Approval", color: "bg-[var(--genui-needs-user)] text-white border-transparent animate-pulse" },
    error: { label: "Error", color: "bg-[var(--genui-error)]/10 text-[var(--genui-error)] border-[var(--genui-error)]/20" },
    success: { label: "Ready", color: "bg-[var(--genui-success)]/10 text-[var(--genui-success)] border-[var(--genui-success)]/20" },
  };

  const { label, color } = config[status] || config.empty;

  return (
    <span className={cn(
      "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border shadow-sm transition-colors",
      color,
      className
    )}>
      {status === "running" && <span className="w-1.5 h-1.5 bg-white rounded-full mr-1.5 animate-pulse" />}
      {label}
    </span>
  );
}
