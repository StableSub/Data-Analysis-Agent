import React from "react";
import { ExternalLink, CheckCircle2, XCircle, ShieldAlert, MinusCircle, Circle, Loader2, ArrowRight } from "lucide-react";
import { cn } from "../../../lib/utils";

/* ─────────────────────────────────────────────
   Types
───────────────────────────────────────────── */
export type ChipValue =
  | "ON"        // 실행됨 / 경로 활성화
  | "SKIP"      // 건너뜀
  | "BLOCKED"   // needs-user — 사용자 대기
  | "FAILED"    // 실패
  | "OFF"       // 비활성화
  | "DONE"      // 완료
  | "QUEUED"    // 대기 중
  | "RUNNING"   // 현재 진행
  | "Full"      // Mode 값
  | "Quick QA"; // Mode 값

export interface DecisionChip {
  /** Pipeline stage name: "Preprocess" | "RAG" | "Viz" | "Merge" | "Report" | "Mode" */
  stage: string;
  value: ChipValue;
  /**
   * Hover tooltip — 1 line explaining why this state.
   * Shown via title attribute (native, zero-dep).
   */
  tooltip?: string;
  /**
   * Navigation callback — clicking chip scrolls/focuses the right panel's
   * relevant section. Navigation only — no Approve/Reject/Submit (SSOT).
   * If undefined, chip is purely read-only (no cursor-pointer).
   */
  onNavigate?: () => void;
}

export interface DecisionChipsProps {
  chips: DecisionChip[];
  className?: string;
}

/* ─────────────────────────────────────────────
   Default tooltip per stage + value
───────────────────────────────────────────── */
function defaultTooltip(stage: string, value: ChipValue): string {
  switch (value) {
    case "ON":      return `${stage}: active and routing through this step`;
    case "DONE":    return `${stage}: completed successfully`;
    case "RUNNING": return `${stage}: currently executing`;
    case "BLOCKED": return `${stage}: blocked — awaiting user approval to proceed`;
    case "FAILED":  return `${stage}: failed — open Details for resolution`;
    case "SKIP":    return `${stage}: skipped by agent decision`;
    case "OFF":     return `${stage}: disabled in current plan`;
    case "QUEUED":  return `${stage}: queued — waiting for upstream steps to finish`;
    case "Full":    return `Mode: Full pipeline — all steps enabled`;
    case "Quick QA":return `Mode: Quick QA — lightweight validation only`;
    default:        return stage;
  }
}

/* ─────────────────────────────────────────────
   Visual config per value
   Note: status colours use --genui-* tokens only.
   No interactive/selected states — read-only.
───────────────────────────────────────────── */
interface ChipStyle {
  /** Container classes */
  cls: string;
  /** Small leading icon (status indicator, not interactive) */
  icon?: React.ReactNode;
  /** Display label (overrides value if different) */
  label: string;
}

function getChipStyle(value: ChipValue): ChipStyle {
  switch (value) {
    case "ON":
      return {
        cls:   "bg-[var(--genui-panel)] text-[var(--genui-text)] border-[var(--genui-border)]",
        icon:  <CheckCircle2 className="w-2.5 h-2.5 text-[var(--genui-success)] flex-shrink-0" />,
        label: "ON",
      };
    case "DONE":
      return {
        cls:   "bg-[var(--genui-success)]/8 text-[var(--genui-success)] border-[var(--genui-success)]/20",
        icon:  <CheckCircle2 className="w-2.5 h-2.5 flex-shrink-0" />,
        label: "DONE",
      };
    case "RUNNING":
      return {
        cls:   "bg-[var(--genui-running)]/8 text-[var(--genui-running)] border-[var(--genui-running)]/20",
        icon:  <Loader2 className="w-2.5 h-2.5 flex-shrink-0 animate-spin" />,
        label: "RUNNING",
      };
    case "BLOCKED":
      return {
        cls:   "bg-[var(--genui-needs-user)]/10 text-[var(--genui-needs-user)] border-[var(--genui-needs-user)]/25",
        icon:  <ShieldAlert className="w-2.5 h-2.5 flex-shrink-0 animate-pulse" />,
        label: "BLOCKED",
      };
    case "FAILED":
      return {
        cls:   "bg-[var(--genui-error)]/8 text-[var(--genui-error)] border-[var(--genui-error)]/20",
        icon:  <XCircle className="w-2.5 h-2.5 flex-shrink-0" />,
        label: "FAILED",
      };
    case "SKIP":
      return {
        cls:   "bg-[var(--genui-surface)] text-[var(--genui-muted)] border-[var(--genui-border)]",
        icon:  <MinusCircle className="w-2.5 h-2.5 flex-shrink-0 opacity-60" />,
        label: "SKIP",
      };
    case "OFF":
      return {
        cls:   "bg-[var(--genui-surface)] text-[var(--genui-muted)] border-[var(--genui-border)] opacity-50",
        icon:  <Circle className="w-2.5 h-2.5 flex-shrink-0 opacity-40" />,
        label: "OFF",
      };
    case "QUEUED":
      return {
        cls:   "bg-[var(--genui-surface)] text-[var(--genui-muted)] border-[var(--genui-border)]",
        icon:  <Circle className="w-2.5 h-2.5 flex-shrink-0 opacity-30" />,
        label: "QUEUED",
      };
    case "Full":
      return {
        cls:   "bg-[var(--genui-panel)] text-[var(--genui-text)] border-[var(--genui-border)]",
        label: "Full",
      };
    case "Quick QA":
      return {
        cls:   "bg-[var(--genui-panel)] text-[var(--genui-text)] border-[var(--genui-border)]",
        label: "Quick QA",
      };
  }
}

/* ─────────────────────────────────────────────
   Single chip
   Visual: read-only status tag.
   Format: [icon] Stage · VALUE [→ if nav]
   Hover: native title tooltip (1 line)
   Click: navigation only (SSOT — no CTA)
───────────────────────────────────────────── */
function Chip({ chip }: { chip: DecisionChip }) {
  const style      = getChipStyle(chip.value);
  const isNav      = !!chip.onNavigate;
  const tooltip    = chip.tooltip ?? defaultTooltip(chip.stage, chip.value);
  const navSuffix  = isNav ? " · click to view details" : "";

  return (
    <div
      onClick={isNav ? chip.onNavigate : undefined}
      role={isNav ? "link" : undefined}
      tabIndex={isNav ? 0 : undefined}
      onKeyDown={isNav ? (e) => (e.key === "Enter" || e.key === " ") && chip.onNavigate?.() : undefined}
      title={tooltip + navSuffix}
      aria-label={`${chip.stage} status: ${chip.value}${isNav ? " — click to view" : ""}`}
      className={cn(
        // ── Base: status tag appearance, NOT button appearance ──
        "inline-flex items-center gap-1.5 px-2 py-1 rounded-md border",
        "text-[10px] leading-none whitespace-nowrap select-none",
        "transition-opacity duration-150",
        style.cls,
        // Navigation affordance: subtle (not button-like)
        isNav
          ? "cursor-pointer hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--genui-focus-ring)]"
          : "cursor-default",
      )}
    >
      {/* Status icon (small, decorative) */}
      {style.icon}

      {/* Stage name — lighter weight */}
      <span className="text-[var(--genui-muted)] font-normal">{chip.stage}</span>

      {/* Middle dot separator */}
      <span className="opacity-30 font-bold">·</span>

      {/* Value label — semibold */}
      <span className="font-semibold">{style.label}</span>

      {/* Navigation arrow — only when navigable, very subtle */}
      {isNav && (
        <ArrowRight className="w-2 h-2 opacity-30 flex-shrink-0 ml-0.5" />
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────
   DecisionChips — public export
   Read-only routing status row. Max 5 chips.
   Place in WorkbenchLayout's centerSubHeader prop.
───────────────────────────────────────────── */
export function DecisionChips({ chips, className }: DecisionChipsProps) {
  const visible = chips.slice(0, 5);
  if (visible.length === 0) return null;

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* Section label — minimal, not a heading */}
      <span className="text-[9px] font-bold uppercase tracking-widest text-[var(--genui-muted)] flex-shrink-0 pr-1 border-r border-[var(--genui-border)]">
        Route
      </span>

      {/* Chips */}
      <div className="flex items-center gap-1.5 flex-wrap min-w-0">
        {visible.map((chip) => (
          <Chip key={`${chip.stage}-${chip.value}`} chip={chip} />
        ))}
      </div>

      {/* Overflow */}
      {chips.length > 5 && (
        <span className="text-[10px] text-[var(--genui-muted)] flex-shrink-0">
          +{chips.length - 5}
        </span>
      )}
    </div>
  );
}
