import React from "react";
import { Database, Table2, Cpu, BookOpen, ArrowRight } from "lucide-react";
import { cn } from "../../../lib/utils";

/* ─────────────────────────────────────────────
   Types
   4 pills fixed order: Data / Scope / Compute / RAG
───────────────────────────────────────────── */
export interface EvidenceFooterProps {
  /** e.g. "sales_data_Q3.csv" */
  data?: string;
  /** e.g. "14,500×24" or "142 missing" */
  scope?: string;
  /** e.g. "v3 · 00:21" or "job#81" */
  compute?: string;
  /** e.g. "12 chunks" or "OFF" */
  rag?: string;
  /**
   * Navigation callbacks — SSOT: nav only, no action CTA.
   * Data/Scope → Details panel (Dataset profile)
   * Compute/RAG → Agent > Tools (run status / tool call)
   */
  onDataNavigate?: () => void;
  onScopeNavigate?: () => void;
  onComputeNavigate?: () => void;
  onRagNavigate?: () => void;
  className?: string;
}

/* ─────────────────────────────────────────────
   Single pill
   Format: [icon] Key · value
   Max ~22 chars including key, ellipsis on value
───────────────────────────────────────────── */
interface PillProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  onNavigate?: () => void;
}

function Pill({ icon, label, value, onNavigate }: PillProps) {
  const isNav = !!onNavigate;
  const tooltip = `${label}: ${value}${isNav ? " — click to view" : ""}`;

  return (
    <div
      onClick={onNavigate}
      title={tooltip}
      role={isNav ? "link" : undefined}
      tabIndex={isNav ? 0 : undefined}
      onKeyDown={isNav ? (e) => (e.key === "Enter" || e.key === " ") && onNavigate?.() : undefined}
      className={cn(
        // Base: neutral tag — NOT a button
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-md border flex-shrink-0",
        "text-[10px] leading-none select-none whitespace-nowrap",
        "bg-[var(--genui-surface)] border-[var(--genui-border)] transition-colors duration-100",
        isNav
          ? "cursor-pointer hover:border-[var(--genui-muted)]/60 hover:bg-[var(--genui-panel)] focus-visible:outline focus-visible:outline-2"
          : "cursor-default",
      )}
    >
      {/* Decorative icon */}
      <span className="text-[var(--genui-muted)] flex-shrink-0">{icon}</span>

      {/* Key label */}
      <span className="text-[var(--genui-muted)] font-medium flex-shrink-0">{label}</span>

      {/* Separator */}
      <span className="text-[var(--genui-muted)] opacity-30">·</span>

      {/* Value — truncated to ~16 chars */}
      <span
        className="text-[var(--genui-text)] font-semibold truncate"
        style={{ maxWidth: "9rem" }}
      >
        {value}
      </span>

      {/* Nav arrow (very subtle) */}
      {isNav && (
        <ArrowRight className="w-2 h-2 text-[var(--genui-muted)] opacity-30 flex-shrink-0 ml-0.5" />
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────
   EvidenceFooter — public export

   Always renders exactly 4 pills in fixed order.
   Omitted values fall back to "-" (never hidden,
   so layout stays stable).

   Place: below card body, above action area.
   Separated from body by a thin divider (caller
   or rendered here via the `withDivider` opt).
───────────────────────────────────────────── */
export function EvidenceFooter({
  data    = "-",
  scope   = "-",
  compute = "-",
  rag     = "OFF",
  onDataNavigate,
  onScopeNavigate,
  onComputeNavigate,
  onRagNavigate,
  className,
}: EvidenceFooterProps) {
  return (
    <div
      className={cn(
        // 1-line, no-wrap, scrollable if needed (rare)
        "flex items-center gap-1.5 overflow-x-auto overflow-y-hidden",
        "scrollbar-none", // hide scrollbar if overflows
        className,
      )}
      style={{ scrollbarWidth: "none" }}
    >
      <Pill
        icon={<Database className="w-2.5 h-2.5" />}
        label="Data"
        value={data}
        onNavigate={onDataNavigate}
      />
      <Pill
        icon={<Table2 className="w-2.5 h-2.5" />}
        label="Scope"
        value={scope}
        onNavigate={onScopeNavigate}
      />
      <Pill
        icon={<Cpu className="w-2.5 h-2.5" />}
        label="Compute"
        value={compute}
        onNavigate={onComputeNavigate}
      />
      <Pill
        icon={<BookOpen className="w-2.5 h-2.5" />}
        label="RAG"
        value={rag}
        onNavigate={onRagNavigate}
      />
    </div>
  );
}
