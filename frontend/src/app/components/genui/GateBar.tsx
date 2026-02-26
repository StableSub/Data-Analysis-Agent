import React, { useState } from "react";
import { Check, X, SendHorizontal, MessageSquarePlus } from "lucide-react";
import { cn } from "../../../lib/utils";

interface GateBarProps {
  onApprove: () => void;
  onReject: () => void;
  onSubmitChange: (text: string) => void;
  className?: string;
}

export function GateBar({ onApprove, onReject, onSubmitChange, className }: GateBarProps) {
  const [value, setValue] = useState("");
  const [isEditing, setIsEditing] = useState(false);

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
      "w-full max-w-md mx-auto flex flex-col gap-2 p-3 bg-[var(--genui-surface)]/95 backdrop-blur-md border border-[var(--genui-needs-user)]/30 rounded-2xl shadow-xl animate-in slide-in-from-bottom-4 duration-300",
      className
    )}>
      
      {/* 1. Approve (Primary Action) */}
      <button
        onClick={onApprove}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[var(--genui-needs-user)] text-white font-semibold rounded-xl shadow-md hover:bg-[var(--genui-needs-user)]/90 hover:scale-[1.02] active:scale-[0.98] transition-all group"
      >
        <div className="p-1 rounded-full bg-white/20 group-hover:bg-white/30 transition-colors">
          <Check className="w-4 h-4" />
        </div>
        <span>Approve & Continue</span>
      </button>

      {/* 2. Reject (Secondary Action) */}
      <button
        onClick={onReject}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[var(--genui-surface)] border border-[var(--genui-border)] text-[var(--genui-error)] font-medium rounded-xl hover:bg-[var(--genui-error)]/5 hover:border-[var(--genui-error)]/30 transition-all active:scale-[0.99]"
      >
        <X className="w-4 h-4" />
        <span>Reject</span>
      </button>

      {/* 3. Edit / Input (Tertiary Action) */}
      <div className="relative w-full">
        {!isEditing ? (
           <button 
             onClick={() => setIsEditing(true)}
             className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-[var(--genui-muted)] hover:text-[var(--genui-text)] hover:bg-[var(--genui-panel)] rounded-xl transition-colors text-sm"
           >
             <MessageSquarePlus className="w-4 h-4" />
             <span>Modify with instructions...</span>
           </button>
        ) : (
           <div className="animate-in fade-in zoom-in-95 duration-200 bg-[var(--genui-panel)] rounded-xl border border-[var(--genui-focus-ring)]/50 p-1">
              <textarea
                autoFocus
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={() => !value.trim() && setIsEditing(false)}
                placeholder="What should change? (e.g., 'Use median imputation')"
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
