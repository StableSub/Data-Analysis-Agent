import React from "react";
import { cn } from "../../../lib/utils";

export type ChipVariant = "neutral" | "running" | "success" | "warning" | "error" | "needs-user";

interface GenUIChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: ChipVariant;
  label: string;
}

export function GenUIChip({ variant = "neutral", label, className, ...props }: GenUIChipProps) {
  const baseStyles = "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border transition-colors";
  
  const variants = {
    neutral: "bg-[var(--genui-surface)] border-[var(--genui-border)] text-[var(--genui-text)]",
    running: "bg-[var(--genui-running)]/10 border-[var(--genui-running)]/20 text-[var(--genui-running)]",
    success: "bg-[var(--genui-success)]/10 border-[var(--genui-success)]/20 text-[var(--genui-success)]",
    warning: "bg-[var(--genui-warning)]/10 border-[var(--genui-warning)]/20 text-[var(--genui-warning)]",
    error: "bg-[var(--genui-error)]/10 border-[var(--genui-error)]/20 text-[var(--genui-error)]",
    "needs-user": "bg-[var(--genui-needs-user)]/10 border-[var(--genui-needs-user)]/20 text-[var(--genui-needs-user)]",
  };

  return (
    <span className={cn(baseStyles, variants[variant], className)} {...props}>
      {label}
    </span>
  );
}
