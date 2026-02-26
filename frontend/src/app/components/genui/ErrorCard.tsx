import React from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";
import { cn } from "../../../lib/utils";
import { CardShell, CardHeader, CardBody, CardFooter } from "./CardShell";

interface ErrorCardProps {
  title: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorCard({ title, message, onRetry, className }: ErrorCardProps) {
  return (
    <CardShell
      className={cn("bg-[var(--genui-surface)]/50 border-[var(--genui-error)]/30", className)}
      status="error"
    >
      <CardHeader 
        title={title} 
        meta="Error"
        statusLabel="Failed"
        statusVariant="error"
      />
      <CardBody className="flex flex-col gap-4 text-[var(--genui-text)]">
        <div className="flex items-start gap-3 p-3 bg-[var(--genui-error)]/5 rounded-md border border-[var(--genui-error)]/10">
          <AlertTriangle className="w-5 h-5 text-[var(--genui-error)] mt-0.5 flex-shrink-0" />
          <p className="text-sm leading-relaxed">{message}</p>
        </div>
      </CardBody>
      <CardFooter>
        <button 
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium bg-[var(--genui-surface)] border border-[var(--genui-border-strong)] rounded hover:bg-[var(--genui-border)]/10 transition-colors text-[var(--genui-text)]"
        >
          <RefreshCcw className="w-3.5 h-3.5" />
          Retry Action
        </button>
      </CardFooter>
    </CardShell>
  );
}
