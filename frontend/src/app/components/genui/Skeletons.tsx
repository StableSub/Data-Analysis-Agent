import React from "react";
import { cn } from "../../../lib/utils";

export function SkeletonLine({ width = "100%", className }: { width?: string; className?: string }) {
  return (
    <div 
      className={cn("h-4 rounded bg-[var(--genui-surface)] animate-pulse", className)}
      style={{ width }}
    />
  );
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn("p-4 rounded-lg border border-[var(--genui-border)] bg-[var(--genui-card)] space-y-3", className)}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-full bg-[var(--genui-surface)] animate-pulse" />
        <div className="space-y-1 flex-1">
          <SkeletonLine width="60%" />
          <SkeletonLine width="40%" className="h-3 opacity-60" />
        </div>
      </div>
      <SkeletonLine />
      <SkeletonLine width="80%" />
      <SkeletonLine width="90%" />
    </div>
  );
}
