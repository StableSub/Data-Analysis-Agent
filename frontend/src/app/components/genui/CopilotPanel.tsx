import React, { useState } from "react";
import {
  Activity, Clock, Zap, ChevronDown, ChevronUp,
  Terminal, ArrowRight, Filter, ShieldCheck,
} from "lucide-react";
import { cn } from "../../../lib/utils";
import { ToolCallListItem, type ToolCallEntry } from "./ToolCallListItem";
import { PipelineTracker, type PipelineStep } from "./PipelineTracker";

/* ─────────────────────────────────────────────
   Types (re-exported)
───────────────────────────────────────────── */
export type { ToolCallEntry, PipelineStep };

export interface RunStatusData {
  /** Current phase label, e.g. "Preprocessing" */
  phase: string;
  /** 0–100 */
  progress?: number;
  /** Last completed tool name */
  lastTool?: string;
  /** Human-readable elapsed time */
  elapsedTime?: string;
}

/** Awaiting approval summary (needs-user state) — nav only, no CTA */
export interface AwaitingInfo {
  title: string;
  description?: string;
  /** Navigation only → Details panel (SSOT: no Approve/Reject here) */
  onViewDetails?: () => void;
}

export interface CopilotPanelProps {
  runStatus?: RunStatusData;
  toolCalls?: ToolCallEntry[];
  pipelineSteps?: PipelineStep[];
  awaitingInfo?: AwaitingInfo;
  defaultSelectedId?: string;
  className?: string;
}

type FilterType = "all" | "latest" | "errors";

/* ─────────────────────────────────────────────
   Sort priority for tool calls in "All" view
───────────────────────────────────────────── */
const SORT_PRIORITY: Record<string, number> = {
  "needs-user": 0,
  "running":    1,
  "failed":     2,
  "completed":  3,
};

/* ─────────────────────────────────────────────
   Sub-component: RunStatus
───────────────────────────────────────────── */
function RunStatus({ data }: { data: RunStatusData }) {
  return (
    <div className="px-4 py-3 border-b border-[var(--genui-border)] space-y-3 bg-[var(--genui-panel)]">
      <div className="flex items-center gap-1.5">
        <Activity className="w-3 h-3 text-[var(--genui-running)]" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--genui-muted)]">
          Run Status
        </span>
      </div>

      {/* Phase + Elapsed grid */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-[var(--genui-surface)] rounded-lg px-3 py-2 border border-[var(--genui-border)]">
          <p className="text-[10px] text-[var(--genui-muted)] mb-0.5">Phase</p>
          <p className="text-xs font-semibold text-[var(--genui-text)] truncate">{data.phase}</p>
        </div>
        {data.elapsedTime && (
          <div className="bg-[var(--genui-surface)] rounded-lg px-3 py-2 border border-[var(--genui-border)]">
            <p className="text-[10px] text-[var(--genui-muted)] mb-0.5 flex items-center gap-1">
              <Clock className="w-2.5 h-2.5" /> Elapsed
            </p>
            <p className="text-xs font-semibold text-[var(--genui-text)] tabular-nums">
              {data.elapsedTime}
            </p>
          </div>
        )}
      </div>

      {/* Progress bar */}
      {data.progress !== undefined && (
        <div className="space-y-1">
          <div className="flex justify-between text-[10px] text-[var(--genui-muted)]">
            <span>Progress</span>
            <span className="tabular-nums">{data.progress}%</span>
          </div>
          <div className="h-1.5 bg-[var(--genui-surface)] rounded-full overflow-hidden border border-[var(--genui-border)]">
            <div
              className="h-full bg-[var(--genui-running)] rounded-full transition-all duration-500 ease-out"
              style={{ width: `${data.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Last tool */}
      {data.lastTool && (
        <div className="flex items-center gap-1.5 text-[10px] text-[var(--genui-muted)]">
          <Zap className="w-3 h-3 flex-shrink-0" />
          <span>Last tool:</span>
          <code className="text-[var(--genui-text)] font-mono bg-[var(--genui-surface)] px-1 rounded border border-[var(--genui-border)]">
            {data.lastTool}
          </code>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Sub-component: AwaitingCard (needs-user)
   Nav link only — SSOT: no Approve/Reject here
───────────────────────────────────────────── */
function AwaitingCard({ info }: { info: AwaitingInfo }) {
  return (
    <div className="mx-3 my-2 rounded-xl border border-[var(--genui-needs-user)]/30 bg-[var(--genui-needs-user)]/6 px-3 py-2.5 flex items-start gap-2.5">
      {/* Icon */}
      <div className="flex-shrink-0 mt-0.5 w-5 h-5 rounded-full bg-[var(--genui-needs-user)]/15 border border-[var(--genui-needs-user)]/30 flex items-center justify-center">
        <ShieldCheck className="w-2.5 h-2.5 text-[var(--genui-needs-user)] animate-pulse" />
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--genui-needs-user)] mb-0.5">
          Awaiting Decision
        </p>
        <p className="text-xs font-semibold text-[var(--genui-text)] leading-snug">
          {info.title}
        </p>
        {info.description && (
          <p className="text-[10px] text-[var(--genui-muted)] mt-0.5 leading-snug">
            {info.description}
          </p>
        )}

        {/* Navigation link only — SSOT: Approve/Reject stays in GateBar */}
        {info.onViewDetails && (
          <button
            onClick={info.onViewDetails}
            className="mt-1.5 flex items-center gap-0.5 text-[10px] font-medium text-[var(--genui-needs-user)] opacity-75 hover:opacity-100 transition-opacity"
          >
            View in Details
            <ArrowRight className="w-2.5 h-2.5" />
          </button>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Sub-component: CollapsibleSection
───────────────────────────────────────────── */
function SectionHeader({
  icon,
  label,
  count,
  open,
  onToggle,
}: {
  icon: React.ReactNode;
  label: string;
  count?: number;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-[var(--genui-surface)] transition-colors sticky top-0 bg-[var(--genui-surface)] z-10 border-b border-[var(--genui-border)]"
    >
      <div className="flex items-center gap-1.5">
        {icon}
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--genui-muted)]">
          {label}
        </span>
        {count !== undefined && count > 0 && (
          <span className="text-[10px] font-bold text-[var(--genui-text)] bg-[var(--genui-panel)] border border-[var(--genui-border)] px-1.5 py-0.5 rounded tabular-nums">
            {count}
          </span>
        )}
      </div>
      {open
        ? <ChevronUp className="w-3 h-3 text-[var(--genui-muted)]" />
        : <ChevronDown className="w-3 h-3 text-[var(--genui-muted)]" />
      }
    </button>
  );
}

/* ─────────────────────────────────────────────
   Sub-component: Filter toggles
───────────────────────────────────────────── */
function FilterToggle({
  current,
  onChange,
  errorCount,
}: {
  current: FilterType;
  onChange: (f: FilterType) => void;
  errorCount: number;
}) {
  const tabs: { id: FilterType; label: string; badge?: number }[] = [
    { id: "all",    label: "All" },
    { id: "latest", label: "Latest" },
    { id: "errors", label: "Errors", badge: errorCount },
  ];

  return (
    <div className="flex items-center gap-0.5 px-3 py-1.5 bg-[var(--genui-panel)] border-b border-[var(--genui-border)]">
      <Filter className="w-2.5 h-2.5 text-[var(--genui-muted)] mr-1 flex-shrink-0" />
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={cn(
            "flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold transition-all",
            current === t.id
              ? "bg-[var(--genui-surface)] text-[var(--genui-text)] shadow-sm"
              : "text-[var(--genui-muted)] hover:text-[var(--genui-text)]",
          )}
        >
          {t.label}
          {t.badge !== undefined && t.badge > 0 && (
            <span className="text-[9px] font-bold bg-[var(--genui-error)]/15 text-[var(--genui-error)] border border-[var(--genui-error)]/20 px-1 py-px rounded-full tabular-nums">
              {t.badge}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Sub-component: ToolCallDetail pane
───────────────────────────────────────────── */
function ToolCallDetail({ call }: { call: ToolCallEntry }) {
  const [open, setOpen] = useState(true);

  return (
    <div className="border-t border-[var(--genui-border)] flex-shrink-0 bg-[var(--genui-panel)]">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-[var(--genui-surface)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-3 h-3 text-[var(--genui-muted)]" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--genui-muted)]">
            Call Detail
          </span>
          <code className="text-[10px] font-mono text-[var(--genui-text)] bg-[var(--genui-surface)] px-1 rounded border border-[var(--genui-border)]">
            {call.name}
          </code>
        </div>
        {open
          ? <ChevronUp className="w-3 h-3 text-[var(--genui-muted)]" />
          : <ChevronDown className="w-3 h-3 text-[var(--genui-muted)]" />
        }
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 max-h-52 overflow-y-auto">
          {call.args && (
            <div>
              <p className="text-[10px] font-semibold text-[var(--genui-muted)] uppercase tracking-wider mb-1">
                Arguments
              </p>
              <pre className="text-[11px] font-mono bg-[var(--genui-surface)] border border-[var(--genui-border)] rounded-lg p-2.5 overflow-x-auto text-[var(--genui-text)] whitespace-pre-wrap leading-relaxed">
                {call.args}
              </pre>
            </div>
          )}
          {call.result && (
            <div>
              <p className="text-[10px] font-semibold text-[var(--genui-muted)] uppercase tracking-wider mb-1">
                Result
              </p>
              <pre className="text-[11px] font-mono bg-[var(--genui-surface)] border border-[var(--genui-border)] rounded-lg p-2.5 overflow-x-auto text-[var(--genui-text)] whitespace-pre-wrap leading-relaxed">
                {call.result}
              </pre>
            </div>
          )}
          {call.startedAt && (
            <p className="text-[10px] text-[var(--genui-muted)] tabular-nums">
              Started at {call.startedAt}
              {call.duration && ` · took ${call.duration}`}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Main CopilotPanel
───────────────────────────────────────────── */
export function CopilotPanel({
  runStatus,
  toolCalls = [],
  pipelineSteps,
  awaitingInfo,
  defaultSelectedId,
  className,
}: CopilotPanelProps) {
  const lastId = toolCalls.length > 0 ? toolCalls[toolCalls.length - 1].id : null;
  const [selectedId, setSelectedId] = useState<string | null>(
    defaultSelectedId ?? lastId
  );
  const [filter, setFilter] = useState<FilterType>("all");
  const [pipelineOpen, setPipelineOpen] = useState(true);
  const [toolsOpen, setToolsOpen] = useState(true);

  const selectedCall = toolCalls.find((tc) => tc.id === selectedId) ?? null;

  /* ── Tool call filtering + sorting ── */
  const errorCount = toolCalls.filter(
    (tc) => tc.status === "failed" || tc.status === "needs-user"
  ).length;

  const filteredCalls = (() => {
    // For "errors" filter: show only failed + needs-user, chronological
    if (filter === "errors") {
      return toolCalls.filter(
        (tc) => tc.status === "failed" || tc.status === "needs-user"
      );
    }
    // For "latest": last 4 in chronological order
    if (filter === "latest") {
      return toolCalls.slice(-4);
    }
    // "all": pin running/needs-user to top, rest chronological
    const pinned = toolCalls.filter(
      (tc) => tc.status === "running" || tc.status === "needs-user"
    );
    const rest = toolCalls.filter(
      (tc) => tc.status !== "running" && tc.status !== "needs-user"
    );
    return [...pinned, ...rest];
  })();

  return (
    <div className={cn("flex flex-col h-full overflow-hidden", className)}>

      {/* ── Run Status (always visible if present) ── */}
      {runStatus && <RunStatus data={runStatus} />}

      {/* ── Awaiting approval card (needs-user only, optional) ── */}
      {awaitingInfo && <AwaitingCard info={awaitingInfo} />}

      {/* ── Scrollable body ── */}
      <div className="flex-1 overflow-y-auto min-h-0">

        {/* ── PIPELINE section ── */}
        {pipelineSteps && pipelineSteps.length > 0 && (
          <div>
            <SectionHeader
              icon={<Activity className="w-3 h-3 text-[var(--genui-muted)]" />}
              label="Pipeline"
              count={pipelineSteps.length}
              open={pipelineOpen}
              onToggle={() => setPipelineOpen((v) => !v)}
            />
            {pipelineOpen && (
              <div className="px-2 py-2 bg-[var(--genui-surface)]">
                <PipelineTracker steps={pipelineSteps} />
              </div>
            )}
          </div>
        )}

        {/* ── TOOL CALLS section ── */}
        <div>
          <SectionHeader
            icon={<Terminal className="w-3 h-3 text-[var(--genui-muted)]" />}
            label="Tool Calls"
            count={toolCalls.length}
            open={toolsOpen}
            onToggle={() => setToolsOpen((v) => !v)}
          />

          {toolsOpen && (
            <>
              {/* Filter bar */}
              {toolCalls.length > 0 && (
                <FilterToggle
                  current={filter}
                  onChange={setFilter}
                  errorCount={errorCount}
                />
              )}

              {/* List */}
              {filteredCalls.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 px-4 text-center opacity-50">
                  <Terminal className="w-5 h-5 text-[var(--genui-muted)] mb-2" />
                  <p className="text-xs text-[var(--genui-muted)]">
                    {filter === "errors" ? "No errors so far" : "No tool calls yet"}
                  </p>
                </div>
              ) : (
                <div className="px-2 py-2 space-y-0.5">
                  {filteredCalls.map((tc) => (
                    <ToolCallListItem
                      key={tc.id}
                      status={tc.status}
                      name={tc.name}
                      /* args omitted from list — shown in detail pane only */
                      duration={tc.duration}
                      selected={selectedId === tc.id}
                      onClick={() =>
                        setSelectedId((prev) => (prev === tc.id ? null : tc.id))
                      }
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* ── Tool Call Detail (slide-in when item selected) ── */}
      {selectedCall && <ToolCallDetail call={selectedCall} />}
    </div>
  );
}
