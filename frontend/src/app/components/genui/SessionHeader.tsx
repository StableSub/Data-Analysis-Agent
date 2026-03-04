import React from "react";
import { cn } from "../../../lib/utils";

export function SessionHeader({ title, status, className }: { title: string; status?: string; className?: string }) {
  return (
    <div className={cn("flex items-center justify-between px-4 py-2 border-b border-[var(--genui-border)] bg-[var(--genui-panel)]", className)}>
      <div className="flex items-center gap-2">
        <span className="font-semibold text-sm text-[var(--genui-text)]">{title}</span>
        {status && (
           <span className="px-2 py-0.5 rounded-full bg-[var(--genui-surface)] text-xs text-[var(--genui-muted)] border border-[var(--genui-border)]">
             {status}
           </span>
        )}
      </div>
      <div className="flex items-center gap-2">
         {/* Sample Actions */}
         <button className="px-3 py-1 text-xs font-medium text-[var(--genui-text)] bg-[var(--genui-surface)] border border-[var(--genui-border)] rounded hover:bg-[var(--genui-border)]/10 transition-colors">
            Share
         </button>
         <button className="px-3 py-1 text-xs font-medium text-[var(--genui-text)] bg-[var(--genui-surface)] border border-[var(--genui-border)] rounded hover:bg-[var(--genui-border)]/10 transition-colors">
            Export
         </button>
      </div>
    </div>
  );
}
