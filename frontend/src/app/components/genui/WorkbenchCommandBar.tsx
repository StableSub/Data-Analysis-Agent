import React, { useState, useRef, useEffect } from "react";
import { 
  Plus, 
  SendHorizontal, 
  Square, 
  ChevronDown, 
  Check, 
  Mic,
  Sparkles
} from "lucide-react";
import { cn } from "../../../lib/utils";
import { AttachMenuPopover } from "./AttachMenuPopover";

interface WorkbenchCommandBarProps {
  status: "idle" | "focused" | "streaming" | "disabled" | "empty";
  placeholder?: string;
  onSend?: (value: string) => void;
  onStop?: () => void;
  /** Called when "Upload dataset" is selected from the attach menu */
  onUploadDataset?: () => void;
  /** Called when "Use sample dataset" is selected from the attach menu */
  onUseSample?: () => void;
  className?: string;
}

const MODELS = [
  { id: "gpt-5.3-codex", label: "GPT-5.3-Codex" },
  { id: "gpt-5.2-codex", label: "GPT-5.2-Codex" },
  { id: "gpt-5.1-codex-max", label: "GPT-5.1-Codex-Max" },
  { id: "gpt-5.2", label: "GPT-5.2" },
  { id: "gpt-5.1-codex-mini", label: "GPT-5.1-Codex-Mini" },
];

export function WorkbenchCommandBar({ 
  status = "idle", 
  placeholder = "Ask Gen-UI to analyze...", 
  onSend, 
  onStop,
  onUploadDataset,
  onUseSample,
  className 
}: WorkbenchCommandBarProps) {
  const [value, setValue] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [selectedModel, setSelectedModel] = useState(MODELS[0]);
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const [isAttachMenuOpen, setIsAttachMenuOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const attachMenuRef = useRef<HTMLDivElement>(null);

  // Close menus when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsModelMenuOpen(false);
      }
      if (attachMenuRef.current && !attachMenuRef.current.contains(event.target as Node)) {
        setIsAttachMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Auto-resize logic
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && status !== "disabled" && status !== "streaming") {
        onSend?.(value);
        setValue("");
      }
    }
  };

  // Only truly disable interaction if status is explicitly 'disabled'
  // 'empty' status should allow input
  const isDisabled = status === "disabled";
  const isStreaming = status === "streaming";

  return (
    <div className={cn("w-full max-w-3xl mx-auto relative", className)}>
      
      {/* --- Model Selection Popover --- */}
      {isModelMenuOpen && (
        <div 
          ref={menuRef}
          className="absolute bottom-full left-0 mb-2 w-64 bg-[var(--genui-surface)] border border-[var(--genui-border)] rounded-xl shadow-2xl overflow-hidden z-50 animate-in fade-in slide-in-from-bottom-2 duration-200"
        >
          <div className="px-3 py-2 text-xs font-medium text-[var(--genui-muted)] border-b border-[var(--genui-border)]">
            Select model
          </div>
          <div className="p-1">
            {MODELS.map((model) => (
              <button
                key={model.id}
                onClick={() => {
                  setSelectedModel(model);
                  setIsModelMenuOpen(false);
                }}
                className={cn(
                  "w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm transition-colors",
                  selectedModel.id === model.id 
                    ? "bg-[var(--genui-panel)] text-[var(--genui-text)] font-medium" 
                    : "text-[var(--genui-muted)] hover:bg-[var(--genui-surface)] hover:text-[var(--genui-text)]"
                )}
              >
                <span>{model.label}</span>
                {selectedModel.id === model.id && <Check className="w-4 h-4 text-[var(--genui-text)]" />}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* --- Main Container --- */}
      <div 
        className={cn(
          "relative flex flex-col w-full rounded-[26px] bg-[var(--genui-panel)] transition-all duration-300",
          isFocused 
            ? "ring-1 ring-[var(--genui-focus-ring)]/50 shadow-lg border border-[var(--genui-focus-ring)]" 
            : "border border-[var(--genui-border)] shadow-sm hover:border-[var(--genui-muted)]",
          isDisabled && "opacity-60 cursor-not-allowed bg-[var(--genui-surface)] border-dashed"
        )}
      >
        {/* Text Input Area */}
        <div className="px-4 pt-4 pb-2">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            disabled={isDisabled}
            placeholder={placeholder}
            className="w-full bg-transparent border-none outline-none resize-none text-[var(--genui-text)] placeholder:text-[var(--genui-muted)]/60 text-[15px] leading-relaxed max-h-[200px] min-h-[24px]"
            rows={1}
          />
        </div>

        {/* Bottom Toolbar */}
        <div className="flex items-center justify-between px-3 pb-3 pt-1">
          
          {/* Left Controls */}
          <div className="flex items-center gap-2">
            {/* Attach Button + Popover */}
            <div className="relative" ref={attachMenuRef}>
              <button
                onClick={() => {
                  setIsAttachMenuOpen((v) => !v);
                  setIsModelMenuOpen(false);
                }}
                className={cn(
                  "p-2 rounded-full transition-colors disabled:pointer-events-none",
                  isAttachMenuOpen
                    ? "bg-[var(--genui-surface)] text-[var(--genui-text)]"
                    : "text-[var(--genui-muted)] hover:text-[var(--genui-text)] hover:bg-[var(--genui-surface)]"
                )}
                disabled={isDisabled}
                title="Attach file"
              >
                <Plus className={cn("w-5 h-5 transition-transform duration-200", isAttachMenuOpen && "rotate-45")} />
              </button>

              <AttachMenuPopover
                open={isAttachMenuOpen}
                onClose={() => setIsAttachMenuOpen(false)}
                onUploadDataset={() => {
                  onUploadDataset?.();
                  setIsAttachMenuOpen(false);
                }}
                onAddFiles={() => setIsAttachMenuOpen(false)}
                onUseSample={() => {
                  onUseSample?.();
                  setIsAttachMenuOpen(false);
                }}
              />
            </div>

            {/* Model Selector Trigger */}
            <button 
              onClick={() => setIsModelMenuOpen(!isModelMenuOpen)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all border border-transparent",
                isModelMenuOpen 
                  ? "bg-[var(--genui-surface)] text-[var(--genui-text)] shadow-sm" 
                  : "bg-transparent text-[var(--genui-muted)] hover:bg-[var(--genui-surface)] hover:text-[var(--genui-text)]"
              )}
              disabled={isDisabled}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{selectedModel.label}</span>
              <ChevronDown className="w-3 h-3 opacity-50" />
            </button>
          </div>

          {/* Right Controls */}
          <div className="flex items-center gap-2">
            {/* Mic Button */}
            {!value && !isStreaming && (
              <button 
                className="p-2 rounded-full text-[var(--genui-muted)] hover:text-[var(--genui-text)] hover:bg-[var(--genui-surface)] transition-colors"
                disabled={isDisabled}
              >
                <Mic className="w-5 h-5" />
              </button>
            )}

            {/* Send / Stop Button */}
            {isStreaming ? (
              <button 
                onClick={onStop}
                className="w-8 h-8 flex items-center justify-center rounded-full bg-[var(--genui-text)] text-[var(--genui-surface)] hover:opacity-90 transition-all shadow-sm group"
                title="Stop generating"
              >
                <Square className="w-3.5 h-3.5 fill-current group-hover:scale-90 transition-transform" />
              </button>
            ) : (
              <button 
                onClick={() => {
                  if (value.trim()) {
                    onSend?.(value);
                    setValue("");
                  }
                }}
                disabled={isDisabled || !value.trim()}
                className={cn(
                  "w-8 h-8 flex items-center justify-center rounded-full transition-all duration-200",
                  value.trim() && !isDisabled
                    ? "bg-[var(--genui-text)] text-[var(--genui-surface)] shadow-md hover:scale-105 active:scale-95"
                    : "bg-[var(--genui-surface)] text-[var(--genui-muted)] cursor-not-allowed"
                )}
                title="Send message"
              >
                <SendHorizontal className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}