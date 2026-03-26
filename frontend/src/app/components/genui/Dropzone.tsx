import React, { useState } from "react";
import { UploadCloud, FileText, AlertCircle, X } from "lucide-react";
import { cn } from "../../../lib/utils";
import { GenUIChip } from "./GenUIChip";

interface DropzoneProps {
  status: "idle" | "dragover" | "uploading" | "disabled";
  onDrop?: (files: FileList) => void;
  progress?: number;
  fileName?: string;
  fileSize?: string;
  uploadStep?: "Uploading" | "Parsing" | "Validating";
  onCancel?: () => void;
  className?: string;
}

export function Dropzone({
  status,
  onDrop,
  progress = 0,
  fileName,
  fileSize,
  uploadStep,
  onCancel,
  className
}: DropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  if (status === "uploading") {
    return (
      <div className={cn(
        "relative w-full rounded-xl border border-[var(--genui-border)] bg-[var(--genui-panel)] p-8 shadow-sm flex flex-col items-center justify-center gap-6",
        className
      )}>
        <div className="w-full max-w-md space-y-4">
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-[var(--genui-surface)] flex items-center justify-center border border-[var(--genui-border)]">
                <FileText className="w-5 h-5 text-[var(--genui-running)]" />
              </div>
              <div>
                <h4 className="text-sm font-medium text-[var(--genui-text)] truncate max-w-[200px]">{fileName || "data.csv"}</h4>
                <p className="text-xs text-[var(--genui-muted)]">{fileSize || "14.2 MB"}</p>
              </div>
            </div>
            {onCancel && (
              <button 
                onClick={onCancel}
                className="p-1.5 rounded hover:bg-[var(--genui-surface)] text-[var(--genui-muted)] hover:text-[var(--genui-text)] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs">
               <span className="font-medium text-[var(--genui-running)]">{uploadStep || "Uploading..."}</span>
               <span className="text-[var(--genui-muted)]">{progress}%</span>
            </div>
            <div className="h-2 w-full bg-[var(--genui-surface)] rounded-full overflow-hidden">
               <div 
                 className="h-full bg-[var(--genui-running)] transition-all duration-300 ease-out"
                 style={{ width: `${progress}%` }}
               />
            </div>
          </div>
          
          <div className="flex justify-end gap-2 pt-2">
            <button 
              onClick={onCancel}
              className="px-3 py-1.5 text-xs font-medium text-[var(--genui-muted)] hover:text-[var(--genui-text)] transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  }

  const isOver = isDragging || status === "dragover";

  return (
    <div
      className={cn(
        "relative w-full rounded-xl border-2 border-dashed transition-all duration-200 flex flex-col items-center justify-center text-center p-12 gap-4",
        isOver
          ? "border-[var(--genui-focus-ring)] bg-[var(--genui-focus-ring)]/5"
          : "border-[var(--genui-border)] hover:border-[var(--genui-border-strong)] bg-[var(--genui-surface)]/50",
        status === "disabled" && "opacity-50 cursor-not-allowed",
        className
      )}
      onDragEnter={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        if (status === "disabled") return;
        if (e.dataTransfer.files.length > 0) {
          onDrop?.(e.dataTransfer.files);
        }
      }}
    >
      <div className={cn(
        "w-16 h-16 rounded-2xl flex items-center justify-center transition-colors",
        isOver ? "bg-[var(--genui-focus-ring)]/10 text-[var(--genui-focus-ring)]" : "bg-[var(--genui-panel)] border border-[var(--genui-border)] text-[var(--genui-muted)]"
      )}>
        <UploadCloud className="w-8 h-8" />
      </div>
      
      <div className="space-y-2 max-w-sm">
        <h3 className="text-lg font-semibold text-[var(--genui-text)]">
          CSV, XLSX, JSON 업로드
        </h3>
        <p className="text-sm text-[var(--genui-muted)]">
          파일당 최대 200MB • CSV, JSON, Excel(.xlsx, .xls)
        </p>
      </div>

      <div className="flex flex-col gap-3 w-full max-w-xs mt-4">
        <button
          onClick={() => onDrop?.(new DataTransfer().files)}
          className="w-full py-2.5 px-4 bg-[var(--genui-text)] text-[var(--genui-panel)] rounded-lg text-sm font-medium hover:opacity-90 transition-opacity shadow-sm"
        >
          데이터 업로드
        </button>
      </div>
    </div>
  );
}
