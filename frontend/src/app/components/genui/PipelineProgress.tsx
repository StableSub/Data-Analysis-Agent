import React from "react";
import { motion } from "motion/react";
import { cn } from "../../../lib/utils";

interface PipelineProgressProps {
  label: string;
  percentage: number;
  status: "running" | "completed" | "failed";
  className?: string;
}

export function PipelineProgress({ label, percentage, status, className }: PipelineProgressProps) {
  const getStatusColor = () => {
    switch (status) {
      case "running": return "var(--genui-running)";
      case "completed": return "var(--genui-success)";
      case "failed": return "var(--genui-error)";
      default: return "var(--genui-muted)";
    }
  };

  return (
    <div className={cn("w-full space-y-2", className)}>
      <div className="flex justify-between items-center text-xs font-medium">
        <span className="text-[var(--genui-text)] truncate">{label}</span>
        <span className="text-[var(--genui-muted)]">{Math.min(100, Math.max(0, percentage))}%</span>
      </div>
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-[var(--genui-surface)]">
        <motion.div
          className="h-full rounded-full transition-all duration-300 ease-out"
          style={{ 
            backgroundColor: getStatusColor(),
            width: `${percentage}%`
          }}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
