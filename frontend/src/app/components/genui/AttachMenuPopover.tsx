import React from "react";
import { Upload, ImageIcon, Database, X } from "lucide-react";
import { cn } from "../../../lib/utils";

export interface AttachMenuItem {
  icon: React.ReactNode;
  label: string;
  description: string;
  onClick?: () => void;
}

export interface AttachMenuPopoverProps {
  open: boolean;
  onClose: () => void;
  onUploadDataset?: () => void;
  onAddFiles?: () => void;
  onUseSample?: () => void;
  className?: string;
}

export function AttachMenuPopover({
  open,
  onClose,
  onUploadDataset,
  onAddFiles,
  onUseSample,
  className,
}: AttachMenuPopoverProps) {
  if (!open) return null;

  const items: AttachMenuItem[] = [
    {
      icon: <Upload className="w-4 h-4" />,
      label: "Upload dataset",
      description: "CSV, JSON, Excel (.xlsx)",
      onClick: onUploadDataset,
    },
    {
      icon: <ImageIcon className="w-4 h-4" />,
      label: "Add photos & files",
      description: "PNG, JPG, PDF, DOCX",
      onClick: onAddFiles,
    },
    {
      icon: <Database className="w-4 h-4" />,
      label: "Use sample dataset",
      description: "Try with Q3 Sales data",
      onClick: onUseSample,
    },
  ];

  return (
    <div
      className={cn(
        "absolute bottom-full left-0 mb-3 w-72",
        "bg-[var(--genui-surface)] border border-[var(--genui-border)]",
        "rounded-2xl shadow-2xl overflow-hidden z-50",
        "animate-in fade-in slide-in-from-bottom-2 duration-200",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--genui-border)] bg-[var(--genui-panel)]">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--genui-muted)]">
          Attach
        </span>
        <button
          onClick={onClose}
          className="w-5 h-5 flex items-center justify-center rounded text-[var(--genui-muted)] hover:text-[var(--genui-text)] hover:bg-[var(--genui-surface)] transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Menu items */}
      <div className="p-2 space-y-0.5">
        {items.map((item) => (
          <button
            key={item.label}
            onClick={() => {
              item.onClick?.();
              onClose();
            }}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left hover:bg-[var(--genui-panel)] transition-colors group"
          >
            {/* Icon container */}
            <span className="w-9 h-9 flex items-center justify-center rounded-lg bg-[var(--genui-panel)] border border-[var(--genui-border)] text-[var(--genui-muted)] group-hover:text-[var(--genui-text)] group-hover:border-[var(--genui-border-strong,var(--genui-border))] transition-colors flex-shrink-0">
              {item.icon}
            </span>
            <div className="min-w-0">
              <p className="text-sm font-medium text-[var(--genui-text)] leading-tight">
                {item.label}
              </p>
              <p className="text-xs text-[var(--genui-muted)] leading-tight mt-0.5">
                {item.description}
              </p>
            </div>
          </button>
        ))}
      </div>

      {/* Footer hint */}
      <div className="px-4 py-2 border-t border-[var(--genui-border)] bg-[var(--genui-panel)]">
        <p className="text-[10px] text-[var(--genui-muted)]">
          Max file size: 50 MB per file
        </p>
      </div>
    </div>
  );
}
