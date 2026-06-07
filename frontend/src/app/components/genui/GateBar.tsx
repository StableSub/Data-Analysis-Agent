import React, { useState } from "react";
import { Check, FileText, X, MessageSquarePlus } from "lucide-react";
import { cn } from "../../../lib/utils";

interface GateBarProps {
  onApprove: () => void;
  onCancel: () => void;
  onSubmitChange: (text: string) => void;
  approvalTitle?: string;
  approvalDescription?: string;
  approvalItems?: readonly string[];
  approvalPreview?: string;
  changePlaceholder?: string;
  approveLabel?: string;
  cancelLabel?: string;
  changeLabel?: string;
  className?: string;
}

export function GateBar({
  onApprove,
  onCancel,
  onSubmitChange,
  approvalTitle,
  approvalDescription,
  approvalItems,
  approvalPreview,
  changePlaceholder,
  approveLabel,
  cancelLabel,
  changeLabel,
  className,
}: GateBarProps) {
  const [value, setValue] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const normalizedApprovalTitle = approvalTitle?.trim() ?? "";
  const normalizedApprovalDescription = approvalDescription?.trim() ?? "";
  const normalizedApprovalPreview = approvalPreview?.trim() ?? "";
  const normalizedApprovalItems = (approvalItems ?? [])
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
  const hasApprovalDetails =
    normalizedApprovalTitle.length > 0 ||
    normalizedApprovalDescription.length > 0 ||
    normalizedApprovalItems.length > 0 ||
    normalizedApprovalPreview.length > 0;

  const handleSubmit = () => {
    if (value.trim()) {
      onSubmitChange(value);
      setValue("");
      setIsEditing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className={cn(
      "w-full max-w-2xl mx-auto flex flex-col gap-2 p-3 bg-[var(--genui-surface)]/95 backdrop-blur-md border border-[var(--genui-needs-user)]/30 rounded-2xl shadow-xl animate-in slide-in-from-bottom-4 duration-300",
      className
    )}>
      {hasApprovalDetails && (
        <section className="text-left border-b border-[var(--genui-border)]/70 pb-3 mb-1">
          <div className="flex items-start gap-2">
            <div className="mt-0.5 p-1.5 rounded-lg bg-[var(--genui-needs-user)]/10 text-[var(--genui-needs-user)]">
              <FileText className="w-4 h-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--genui-needs-user)]">
                승인 대상
              </p>
              {normalizedApprovalTitle ? (
                <h3 className="mt-0.5 text-sm font-semibold leading-snug text-[var(--genui-text)] break-words">
                  {normalizedApprovalTitle}
                </h3>
              ) : null}
              {normalizedApprovalDescription ? (
                <p className="mt-1 text-xs leading-relaxed text-[var(--genui-muted)] break-words">
                  {normalizedApprovalDescription}
                </p>
              ) : null}
            </div>
          </div>

          {normalizedApprovalItems.length > 0 && (
            <ul className="mt-2 space-y-1.5">
              {normalizedApprovalItems.map((item, index) => (
                <li key={`${index}-${item}`} className="flex items-start gap-2 text-xs leading-relaxed text-[var(--genui-text)]">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-[var(--genui-needs-user)]" />
                  <span className="min-w-0 break-words">{item}</span>
                </li>
              ))}
            </ul>
          )}

          {normalizedApprovalPreview ? (
            <pre className="mt-2 max-h-24 overflow-y-auto whitespace-pre-wrap break-words rounded-lg bg-[var(--genui-panel)] px-3 py-2 text-[11px] leading-relaxed text-[var(--genui-text)]">
              {normalizedApprovalPreview}
            </pre>
          ) : null}
        </section>
      )}
      
      {/* 1. Approve (Primary Action) */}
      <button
        onClick={onApprove}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[var(--genui-needs-user)] text-white font-semibold rounded-xl shadow-md hover:bg-[var(--genui-needs-user)]/90 hover:scale-[1.02] active:scale-[0.98] transition-all group"
      >
        <div className="p-1 rounded-full bg-white/20 group-hover:bg-white/30 transition-colors">
          <Check className="w-4 h-4" />
        </div>
        <span>{approveLabel ?? "Approve & Continue"}</span>
      </button>

      {/* 2. Cancel (Secondary Action) */}
      <button
        onClick={onCancel}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[var(--genui-surface)] border border-[var(--genui-border)] text-[var(--genui-error)] font-medium rounded-xl hover:bg-[var(--genui-error)]/5 hover:border-[var(--genui-error)]/30 transition-all active:scale-[0.99]"
      >
        <X className="w-4 h-4" />
        <span>{cancelLabel ?? "Cancel Run"}</span>
      </button>

      {/* 3. Edit / Input (Tertiary Action) */}
      <div className="relative w-full">
        {!isEditing ? (
           <button 
             onClick={() => setIsEditing(true)}
             className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-[var(--genui-muted)] hover:text-[var(--genui-text)] hover:bg-[var(--genui-panel)] rounded-xl transition-colors text-sm"
           >
             <MessageSquarePlus className="w-4 h-4" />
             <span>{changeLabel ?? "Request Changes..."}</span>
           </button>
        ) : (
           <div className="animate-in fade-in zoom-in-95 duration-200 bg-[var(--genui-panel)] rounded-xl border border-[var(--genui-focus-ring)]/50 p-1">
              <textarea
                autoFocus
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={() => !value.trim() && setIsEditing(false)}
                placeholder={changePlaceholder ?? "What should change? (e.g., 'Use median imputation')"}
                className="w-full bg-transparent border-none outline-none resize-none text-sm p-2 min-h-[60px] text-[var(--genui-text)] placeholder:text-[var(--genui-muted)]/70"
                rows={2}
              />
              <div className="flex justify-end gap-2 px-1 pb-1">
                 <button 
                   onClick={() => setIsEditing(false)}
                   className="text-xs px-2 py-1 text-[var(--genui-muted)] hover:text-[var(--genui-text)]"
                 >
                   Cancel
                 </button>
                 <button 
                   onClick={handleSubmit}
                   disabled={!value.trim()}
                   className="text-xs px-3 py-1 bg-[var(--genui-text)] text-[var(--genui-surface)] rounded font-medium disabled:opacity-50 hover:opacity-90 transition-opacity"
                 >
                   Submit
                 </button>
              </div>
           </div>
        )}
      </div>
    </div>
  );
}
