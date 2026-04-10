import React, { useState, useRef, useEffect, useCallback } from "react";
import { cn } from "../../../lib/utils";
import {
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  RefreshCw,
  Bot,
  ArrowRight,
} from "lucide-react";
import { EvidenceFooter, type EvidenceFooterProps } from "./EvidenceFooter";
import {
  CodeBlock,
  LabelValueText,
  ReportTextContent,
} from "./ReportContentRenderer";

/* ─────────────────────────────────────────────
   Types
───────────────────────────────────────────── */
export type ReportVariant = "final" | "streaming" | "error";
/** Controls the card's accent border colour without overriding the variant */
export type ReportAccent = "default" | "needs-user" | "running";

export interface ReportSection {
  type: "heading" | "paragraph" | "numbered-list" | "checklist" | "code" | "spacer";
  content?: string;
  items?: string[];
  language?: string;
}

export interface AssistantReportMessageProps {
  variant?: ReportVariant;
  /** Start collapsed (summary only). Adds Expand/Collapse toggle. */
  defaultCollapsed?: boolean;
  title?: string;
  subtitle?: string;
  timestamp?: string;
  sections: ReportSection[];
  /** Number of sections visible when collapsed (default: 1) */
  collapsedSections?: number;
  /** px cap for body scroll area when expanded (default: 320). null disables the explicit cap. */
  maxBodyHeight?: number | null;
  className?: string;
  /**
   * Accent border override for non-error states.
   * "needs-user" → amber/yellow border to signal HITL pause.
   */
  accentVariant?: ReportAccent;
  /**
   * Error variant only — show "Review in Details →" nav text-link (SSOT-safe, no retry CTA).
   * Mutually exclusive with onRetry; prefer this in the Workbench center column.
   */
  onReviewDetails?: () => void;
  /**
   * Show a "Confirm & Retry" action button (Details panel only — SSOT).
   * Do NOT pass this in the Workbench center column.
   */
  onRetry?: () => void;
  /**
   * Evidence provenance footer — 4 pills (Data/Scope/Compute/RAG).
   * Pills are read-only + nav-only; no action CTA (SSOT).
   * Optional: omit for simple streaming cards where context isn't ready.
   */
  evidence?: EvidenceFooterProps;
  hideFooter?: boolean;
}

/* ─────────────────────────────────────────────
   Sub-component: Section renderer
───────────────────────────────────────────── */
function RenderSection({ section, isStreaming, isLast }: {
  section: ReportSection;
  isStreaming?: boolean;
  isLast?: boolean;
}) {
  switch (section.type) {
    case "heading":
      return (
        <h3 className="text-[11px] font-bold uppercase tracking-widest text-[var(--genui-muted)] pt-3 pb-1 border-b border-[var(--genui-border)] mb-2">
          {section.content ?? ""}
        </h3>
      );

    case "paragraph":
      return (
        <div className="mb-2">
          <ReportTextContent content={section.content ?? ""} isStreaming={isStreaming} isLast={isLast} />
        </div>
      );

    case "numbered-list":
      return (
        <ol className="space-y-1.5 mb-3 pl-1">
          {(section.items ?? []).map((item, i) => (
            <li key={i} className="flex gap-2.5 text-sm text-[var(--genui-text)] leading-snug">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-[var(--genui-surface)] border border-[var(--genui-border)] flex items-center justify-center text-[10px] font-bold text-[var(--genui-muted)] mt-0.5">
                {i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <LabelValueText text={item} />
                {isStreaming && isLast && i === (section.items?.length ?? 0) - 1 && (
                  <span className="inline-block w-[7px] h-[14px] ml-0.5 bg-[var(--genui-text)] align-middle animate-pulse rounded-[1px]" />
                )}
              </div>
            </li>
          ))}
        </ol>
      );

    case "checklist":
      return (
        <ul className="space-y-1.5 mb-3">
          {(section.items ?? []).map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-[var(--genui-text)] leading-snug">
              <span className="mt-0.5 flex-shrink-0 w-3.5 h-3.5 rounded border border-[var(--genui-border)] bg-[var(--genui-surface)]" />
              <div className="min-w-0 flex-1">
                <LabelValueText text={item} />
              </div>
            </li>
          ))}
        </ul>
      );

    case "code":
      return <CodeBlock code={section.content ?? ""} language={section.language} />;

    case "spacer":
      return <div className="h-3" />;

    default:
      return null;
  }
}

/* ─────────────────────────────────────────────
   Skeleton lines (streaming placeholder)
───────────────────────────────────────────── */
function SkeletonLines() {
  return (
    <div className="space-y-2 pt-1 opacity-50">
      <div className="h-3 bg-[var(--genui-border)] rounded animate-pulse w-full" />
      <div className="h-3 bg-[var(--genui-border)] rounded animate-pulse w-3/5" />
    </div>
  );
}

/* ─────────────────────────────────────────────
   Main component
───────────────────────────────────────────── */
export function AssistantReportMessage({
  variant = "final",
  defaultCollapsed = false,
  title = "Analysis Report",
  subtitle,
  timestamp,
  sections,
  collapsedSections = 1,
  maxBodyHeight = 320,
  className,
  accentVariant = "default",
  onReviewDetails,
  onRetry,
  evidence,
  hideFooter = false,
}: AssistantReportMessageProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [hasOverflow, setHasOverflow] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);

  const isStreaming = variant === "streaming";
  const isError = variant === "error";

  // Detect scroll overflow for the gradient indicator
  const checkOverflow = useCallback(() => {
    const el = bodyRef.current;
    if (!el) return;
    setHasOverflow(el.scrollHeight > el.clientHeight + 4);
  }, []);

  useEffect(() => {
    checkOverflow();
    const el = bodyRef.current;
    if (!el) return;
    const ro = new ResizeObserver(checkOverflow);
    ro.observe(el);
    el.addEventListener("scroll", checkOverflow);
    return () => {
      ro.disconnect();
      el.removeEventListener("scroll", checkOverflow);
    };
  }, [checkOverflow, collapsed]);

  const visibleSections = collapsed ? sections.slice(0, collapsedSections) : sections;

  /* ── Variant: error ── */
  if (isError) {
    return (
      <div
        className={cn(
          "w-full max-w-[860px] mx-auto rounded-xl border bg-[var(--genui-card)] shadow-[var(--genui-shadow-sm)] overflow-hidden",
          "border-[var(--genui-error)]/30",
          className
        )}
      >
        <div className="px-5 py-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-[var(--genui-error)] flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-semibold text-[var(--genui-text)]">{title}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded border border-[var(--genui-error)]/30 bg-[var(--genui-error)]/8 text-[var(--genui-error)] font-semibold uppercase tracking-wider">
                Needs Resolution
              </span>
            </div>
            <div className="mb-3 text-xs text-[var(--genui-muted)]">
              <ReportTextContent content={sections[0]?.content ?? "An error occurred while generating the report."} />
            </div>
            {/* Nav-only link — SSOT: no retry CTA in center column */}
            {onReviewDetails && (
              <button
                onClick={onReviewDetails}
                className="flex items-center gap-1 text-xs font-medium text-[var(--genui-text)] hover:underline opacity-75 hover:opacity-100 transition-opacity"
              >
                Review in Details <ArrowRight className="w-3 h-3" />
              </button>
            )}
            {/* Retry CTA — only in Details panel (SSOT) */}
            {onRetry && !onReviewDetails && (
              <button
                onClick={onRetry}
                className="flex items-center gap-1.5 text-xs font-semibold text-white bg-[var(--genui-error)] px-3 py-1.5 rounded-md hover:opacity-90 transition-opacity"
              >
                <RefreshCw className="w-3 h-3" />
                Confirm & Retry
              </button>
            )}

            {/* Evidence footer (error state) */}
            {evidence && (
              <div className="mt-3 pt-2.5 border-t border-[var(--genui-border)]">
                <EvidenceFooter {...evidence} />
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  /* ── Variant: final / streaming ── */
  const accentBorder =
    accentVariant === "needs-user"
      ? "border-[var(--genui-needs-user)]/50"
      : isStreaming
      ? "border-[var(--genui-running)]/40"
      : "border-[var(--genui-border)]";

  return (
    <div
        className={cn(
        "mx-auto flex min-h-0 w-full max-w-[860px] flex-col overflow-hidden rounded-xl border bg-[var(--genui-card)] shadow-[var(--genui-shadow-sm)] transition-all duration-300",
        accentBorder,
        className
      )}
    >
      {/* ── Header ── */}
      <div className="px-5 py-3.5 border-b border-[var(--genui-border)] bg-[var(--genui-panel)] flex items-center gap-3">
        {/* Bot avatar */}
        <div
          className={cn(
            "w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-white",
            isStreaming ? "bg-[var(--genui-running)] animate-pulse" : "bg-[var(--genui-running)]"
          )}
        >
          <Bot className="w-3.5 h-3.5" />
        </div>

        {/* Title + sub */}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-semibold text-[var(--genui-text)] truncate">{title}</span>
            {subtitle && (
              <span className="text-[11px] text-[var(--genui-muted)] truncate hidden sm:inline">
                {subtitle}
              </span>
            )}
          </div>
          {timestamp && (
            <span className="text-[10px] text-[var(--genui-muted)]">{timestamp}</span>
          )}
        </div>

        {/* Status pill */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {isStreaming ? (
            <span className="flex items-center gap-1 text-[10px] font-semibold text-[var(--genui-running)] bg-[var(--genui-running)]/10 px-2 py-0.5 rounded-full border border-[var(--genui-running)]/20">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--genui-running)] animate-pulse" />
              Generating…
            </span>
          ) : (
            <span className="text-[10px] font-semibold text-[var(--genui-success)] bg-[var(--genui-success)]/10 px-2 py-0.5 rounded-full border border-[var(--genui-success)]/20">
              Final
            </span>
          )}

          {/* Collapse toggle (final only, when defaultCollapsed enabled) */}
          {!isStreaming && defaultCollapsed && (
            <button
              onClick={() => setCollapsed((v) => !v)}
              className="flex items-center gap-1 text-[10px] font-medium text-[var(--genui-muted)] hover:text-[var(--genui-text)] bg-[var(--genui-surface)] border border-[var(--genui-border)] px-2 py-0.5 rounded transition-colors"
            >
              {collapsed ? (
                <>
                  <ChevronDown className="w-3 h-3" />
                  Expand
                </>
              ) : (
                <>
                  <ChevronUp className="w-3 h-3" />
                  Collapse
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* ── Body (scrollable) ── */}
      <div className="relative flex min-h-0 flex-1 flex-col">
        <div
          ref={bodyRef}
          className={cn(
            "min-h-0 flex-1 overflow-y-auto scroll-smooth px-5 py-4",
            // Only cap height when not collapsed (collapsed = naturally short)
            !collapsed && "overflow-y-auto"
          )}
          style={!collapsed && typeof maxBodyHeight === "number" ? { maxHeight: `${maxBodyHeight}px` } : undefined}
          onScroll={checkOverflow}
        >
          {visibleSections.map((section, i) => (
            <RenderSection
              key={i}
              section={section}
              isStreaming={isStreaming}
              isLast={i === visibleSections.length - 1}
            />
          ))}

          {/* Streaming skeleton */}
          {isStreaming && <SkeletonLines />}

          {/* Collapsed hint */}
          {collapsed && (
            <p className="text-xs text-[var(--genui-muted)] italic mt-1">
              {sections.length - collapsedSections} more section
              {sections.length - collapsedSections !== 1 ? "s" : ""} hidden…
            </p>
          )}
        </div>

        {/* Scroll fade indicator */}
        {hasOverflow && !collapsed && (
          <div
            className="pointer-events-none absolute bottom-0 left-0 right-0 h-10"
            style={{
              background:
                "linear-gradient(to bottom, transparent, var(--genui-card))",
            }}
          />
        )}
      </div>

      {/* ── Footer meta (final only) ── */}
      {!isStreaming && !collapsed && !hideFooter && (
        <div className="px-5 py-2.5 border-t border-[var(--genui-border)] bg-[var(--genui-panel)] flex items-center justify-between gap-4">
          <span className="text-[10px] text-[var(--genui-muted)] flex-shrink-0">
            {sections.filter((s) => s.type !== "spacer" && s.type !== "heading").length} content blocks
          </span>
          {/* Evidence pills — always 1 row, right-aligned */}
          {evidence ? (
            <EvidenceFooter {...evidence} />
          ) : (
            <span className="text-[10px] text-[var(--genui-muted)]">Scroll to see all ↑</span>
          )}
        </div>
      )}
    </div>
  );
}
