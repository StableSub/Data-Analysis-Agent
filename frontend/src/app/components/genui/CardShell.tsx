import React from "react";
import { cn } from "../../../lib/utils";
import { GenUIChip, type ChipVariant } from "./GenUIChip";

interface CardShellProps extends React.HTMLAttributes<HTMLDivElement> {
  status?: "default" | "running" | "success" | "error" | "needs-user";
  selected?: boolean;
}

interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  meta?: string;
  statusLabel?: string;
  statusVariant?: ChipVariant;
}

interface CardBodyProps extends React.HTMLAttributes<HTMLDivElement> {}

interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {}

export function CardShell({ status = "default", selected, className, children, ...props }: CardShellProps) {
  const statusStyles = {
    default: "border-[var(--genui-border)] hover:border-[var(--genui-border-strong)]",
    running: "border-[var(--genui-running)] shadow-[var(--genui-shadow-md)]",
    success: "border-[var(--genui-success)] shadow-sm",
    error: "border-[var(--genui-error)] shadow-sm",
    "needs-user": "border-[var(--genui-needs-user)] shadow-[var(--genui-shadow-md)]",
  };

  return (
    <div
      className={cn(
        "bg-[var(--genui-card)] rounded-lg border transition-all duration-200 overflow-hidden",
        "flex flex-col",
        statusStyles[status],
        selected && "ring-2 ring-[var(--genui-focus-ring)] ring-offset-1",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, meta, statusLabel, statusVariant, className, children, ...props }: CardHeaderProps) {
  return (
    <div className={cn("px-4 py-3 border-b border-[var(--genui-border)] flex justify-between items-center bg-[var(--genui-surface)]/50", className)} {...props}>
      <div className="flex flex-col gap-0.5">
        <h3 className="text-sm font-semibold text-[var(--genui-text)] leading-none">{title}</h3>
        {meta && <span className="text-[11px] text-[var(--genui-muted)] uppercase tracking-wider">{meta}</span>}
      </div>
      <div className="flex items-center gap-2">
        {children}
        {statusLabel && <GenUIChip label={statusLabel} variant={statusVariant || "neutral"} />}
      </div>
    </div>
  );
}

export function CardBody({ className, children, ...props }: CardBodyProps) {
  return (
    <div className={cn("p-4 text-sm text-[var(--genui-text)] flex-1 overflow-auto", className)} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ className, children, ...props }: CardFooterProps) {
  return (
    <div className={cn("px-4 py-3 border-t border-[var(--genui-border)] bg-[var(--genui-surface)]/30 flex justify-end gap-2", className)} {...props}>
      {children}
    </div>
  );
}
