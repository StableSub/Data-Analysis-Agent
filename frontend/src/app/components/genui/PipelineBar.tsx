import React from "react";
import { ArrowRight } from "lucide-react";
import { motion } from "motion/react";
import { cn } from "../../../lib/utils";

/* ─────────────────────────────────────────────
   Types
───────────────────────────────────────────── */
export type PipelineBarVariant =
  | "hidden"      // idle / empty — nothing rendered
  | "ingest"      // uploading: determinate %
  | "running"     // indeterminate shimmer
  | "needs-user"  // awaiting approval, violet, pulse
  | "failed"      // error, red, fixed width
  | "completed";  // 100 % green

export type PipelineStage =
  | "Ingest" | "Preprocess" | "RAG"
  | "Visualization" | "Merge" | "Report" | "Data QA";

export interface PipelineBarProps {
  variant: PipelineBarVariant;
  /** Stage label: Ingest / Preprocess / RAG / … */
  stage?: PipelineStage | string;
  /** Short status message — 1 line */
  message?: string;
  /** Optional step fraction e.g. "2/6" */
  stepFraction?: string;
  /** Elapsed time e.g. "00:21" */
  elapsed?: string;
  /** 0–100 — only used when variant="ingest" (determinate) */
  percent?: number;
  /**
   * Navigates to Agent > Tools.
   * Visible on running / needs-user / failed.
   * No CTA action — navigation only (SSOT).
   */
  onViewDetails?: () => void;
  className?: string;
}

/* ─────────────────────────────────────────────
   Internal colour map
───────────────────────────────────────────── */
const VAR_COLOR: Record<PipelineBarVariant, string> = {
  hidden:       "transparent",
  ingest:       "var(--genui-running)",
  running:      "var(--genui-running)",
  "needs-user": "var(--genui-needs-user)",
  failed:       "var(--genui-error)",
  completed:    "var(--genui-success)",
};

const TEXT_CLASS: Record<PipelineBarVariant, string> = {
  hidden:       "",
  ingest:       "text-[var(--genui-running)]",
  running:      "text-[var(--genui-running)]",
  "needs-user": "text-[var(--genui-needs-user)]",
  failed:       "text-[var(--genui-error)]",
  completed:    "text-[var(--genui-success)]",
};

/* ─────────────────────────────────────────────
   Progress line sub-component
   Absolutely positioned at bottom-0 of parent <header>
───────────────────────────────────────────── */
function ProgressLine({
  variant,
  percent,
}: {
  variant: PipelineBarVariant;
  percent?: number;
}) {
  if (variant === "hidden" || variant === "completed") return null;

  const color = VAR_COLOR[variant];

  /* ── Determinate (ingest / uploading) ── */
  if (variant === "ingest") {
    const pct = Math.min(100, Math.max(0, percent ?? 0));
    return (
      <div
        className="absolute bottom-0 left-0 right-0 h-[3px]"
        style={{ backgroundColor: `color-mix(in srgb, ${color} 20%, transparent)` }}
      >
        <div
          className="h-full transition-all duration-300 ease-out rounded-r-sm"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    );
  }

  /* ── Needs-user: fixed 60 % + pulse ── */
  if (variant === "needs-user") {
    return (
      <div
        className="absolute bottom-0 left-0 right-0 h-[3px]"
        style={{ backgroundColor: `color-mix(in srgb, ${color} 20%, transparent)` }}
      >
        <div
          className="h-full animate-pulse rounded-r-sm"
          style={{ width: "60%", backgroundColor: color }}
        />
      </div>
    );
  }

  /* ── Failed: fixed 28 %, no animation ── */
  if (variant === "failed") {
    return (
      <div
        className="absolute bottom-0 left-0 right-0 h-[3px]"
        style={{ backgroundColor: `color-mix(in srgb, ${color} 20%, transparent)` }}
      >
        <div
          className="h-full rounded-r-sm"
          style={{ width: "28%", backgroundColor: color }}
        />
      </div>
    );
  }

  /* ── Running: indeterminate shimmer (motion) ── */
  return (
    <div
      className="absolute bottom-0 left-0 right-0 h-[3px] overflow-hidden"
      style={{ backgroundColor: `color-mix(in srgb, ${color} 18%, transparent)` }}
    >
      <motion.div
        className="absolute inset-y-0 w-[32%] rounded-full"
        style={{ backgroundColor: color }}
        initial={{ left: "-32%" }}
        animate={{ left: "132%" }}
        transition={{
          duration: 1.8,
          ease: "easeInOut",
          repeat: Infinity,
          repeatDelay: 0.25,
        }}
      />
    </div>
  );
}

/* ─────────────────────────────────────────────
   Dot indicator (before stage label)
───────────────────────────────────────────── */
function StageDot({ variant, color }: { variant: PipelineBarVariant; color: string }) {
  if (variant === "completed") return null;
  return (
    <span
      className={cn(
        "w-1.5 h-1.5 rounded-full flex-shrink-0",
        variant === "running" && "animate-pulse",
        variant === "needs-user" && "animate-pulse",
      )}
      style={{ backgroundColor: color }}
    />
  );
}

/* ─────────────────────────────────────────────
   Text strip sub-component
   Absolutely positioned at right-4 (sm) → right-[420px] (xl, avoids RightPanel)
───────────────────────────────────────────── */
function TextStrip({
  variant,
  stage,
  message,
  stepFraction,
  elapsed,
  onViewDetails,
}: PipelineBarProps) {
  if (variant === "hidden") return null;

  const color    = VAR_COLOR[variant];
  const textCls  = TEXT_CLASS[variant];
  const showLink = (variant === "running" || variant === "needs-user" || variant === "failed") && onViewDetails;
  const sep      = <span className="text-[var(--genui-border-strong)] select-none">·</span>;

  return (
    <div
      className={cn(
        "absolute top-0 bottom-[3px]",
        /* Shift inward on xl to stay within centre column */
        "right-4 xl:right-[420px]",
        "flex items-center gap-1.5 pointer-events-none select-none",
      )}
    >
      {/* Stage dot + label */}
      {stage && (
        <div className="flex items-center gap-1">
          <StageDot variant={variant} color={color} />
          <span className={cn("text-[11px] font-semibold leading-none", textCls)}>
            {stage}
          </span>
        </div>
      )}

      {/* Message */}
      {message && (
        <>
          {stage && sep}
          <span className="text-[11px] text-[var(--genui-muted)] max-w-[180px] truncate leading-none">
            {message}
          </span>
        </>
      )}

      {/* Step fraction */}
      {stepFraction && (
        <>
          {sep}
          <span className="text-[11px] text-[var(--genui-muted)] tabular-nums leading-none">
            {stepFraction}
          </span>
        </>
      )}

      {/* Elapsed */}
      {elapsed && (
        <>
          {sep}
          <span className="text-[11px] text-[var(--genui-muted)] tabular-nums font-mono leading-none">
            {elapsed}
          </span>
        </>
      )}

      {/* "View details →" nav link */}
      {showLink && (
        <>
          <span className="ml-0.5 text-[var(--genui-border-strong)] select-none">|</span>
          <button
            onClick={onViewDetails}
            className={cn(
              "pointer-events-auto flex items-center gap-0.5",
              "text-[11px] font-medium leading-none",
              "transition-opacity opacity-70 hover:opacity-100",
              textCls,
            )}
          >
            View details
            <ArrowRight className="w-2.5 h-2.5" />
          </button>
        </>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────
   PipelineBar — public export
   Renders a React Fragment; must be a child of a `position: relative` element.
   WorkbenchLayout's <header> has `relative` by default.
───────────────────────────────────────────── */
export function PipelineBar(props: PipelineBarProps) {
  if (props.variant === "hidden") return null;

  return (
    <>
      <TextStrip {...props} />
      <ProgressLine variant={props.variant} percent={props.percent} />
    </>
  );
}

/* ─────────────────────────────────────────────
   Gallery-only wrapper
   Use this in ComponentsGallery to preview PipelineBar
   inside a mock header container.
───────────────────────────────────────────── */
export function PipelineBarPreview({
  label,
  sessionTitle = "Q3 Sales Analysis",
  ...props
}: PipelineBarProps & { label?: string; sessionTitle?: string }) {
  return (
    <div className="space-y-2">
      {label && (
        <p className="text-[10px] font-semibold text-[var(--genui-muted)] uppercase tracking-wider">
          {label}
        </p>
      )}
      {/* Mock header */}
      <div className="relative h-12 rounded-xl border border-[var(--genui-border)] bg-[var(--genui-panel)] overflow-hidden flex items-center px-4 gap-3">
        {/* Session title (mock) */}
        <span className="text-sm font-semibold text-[var(--genui-text)] flex-shrink-0">
          {sessionTitle}
        </span>
        {/* Separator */}
        <div className="w-px h-4 bg-[var(--genui-border)]" />
        {/* PipelineBar text occupies remaining center; for preview we override positioning */}
        <div className="flex items-center gap-1.5 flex-1 min-w-0">
          {props.variant !== "hidden" && (
            <PreviewTextRow {...props} />
          )}
        </div>
        {/* Progress line at bottom */}
        <ProgressLine variant={props.variant} percent={props.percent} />
      </div>
    </div>
  );
}

/* Inline text row variant for the preview (doesn't use absolute positioning) */
function PreviewTextRow(props: PipelineBarProps) {
  const { variant, stage, message, stepFraction, elapsed, onViewDetails } = props;
  const color   = VAR_COLOR[variant];
  const textCls = TEXT_CLASS[variant];
  const showLink = (variant === "running" || variant === "needs-user" || variant === "failed") && onViewDetails;
  const sep = <span className="text-[var(--genui-border-strong)] select-none text-[11px]">·</span>;

  return (
    <div className="flex items-center gap-1.5 min-w-0">
      {stage && (
        <div className="flex items-center gap-1 flex-shrink-0">
          <StageDot variant={variant} color={color} />
          <span className={cn("text-[11px] font-semibold", textCls)}>{stage}</span>
        </div>
      )}
      {message && (
        <>
          {stage && sep}
          <span className="text-[11px] text-[var(--genui-muted)] truncate">{message}</span>
        </>
      )}
      {stepFraction && (
        <>{sep}<span className="text-[11px] text-[var(--genui-muted)] tabular-nums">{stepFraction}</span></>
      )}
      {elapsed && (
        <>{sep}<span className="text-[11px] text-[var(--genui-muted)] tabular-nums font-mono">{elapsed}</span></>
      )}
      {showLink && (
        <div className="flex items-center gap-0.5 ml-1 flex-shrink-0">
          <span className="text-[var(--genui-border-strong)] text-[11px]">|</span>
          <button
            onClick={onViewDetails}
            className={cn("flex items-center gap-0.5 text-[11px] font-medium opacity-70 hover:opacity-100 transition-opacity", textCls)}
          >
            View details <ArrowRight className="w-2.5 h-2.5" />
          </button>
        </div>
      )}
    </div>
  );
}
