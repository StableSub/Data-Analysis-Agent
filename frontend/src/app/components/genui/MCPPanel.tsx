import React, { useState } from "react";
import {
  Server, Activity, FileText, ChevronDown, ChevronUp,
  CheckCircle2, XCircle, Clock, Zap, Terminal, Copy, Check,
  Loader2, AlertTriangle,
} from "lucide-react";
import { cn } from "../../../lib/utils";

/* ─────────────────────────────────────────────
   Types
───────────────────────────────────────────── */
export type MCPServerStatus = "connected" | "disconnected" | "error";

export interface MCPServer {
  id: string;
  name: string;
  transport: "stdio" | "http" | "sse";
  status: MCPServerStatus;
  toolCount?: number;
  latencyMs?: number;
}

export interface MCPAction {
  id: string;
  serverName: string;
  tool: string;
  status: "success" | "failed" | "running";
  timestamp: string;
  durationMs?: number;
}

/** Raw SSE / tool payload lines for developer inspection */
export interface RawLogEntry {
  id: string;
  label: string;
  /** JSON payload string (pretty-printed) */
  payload: string;
  /** Error-level entry turns label red */
  isError?: boolean;
}

export interface MCPPanelProps {
  servers?: MCPServer[];
  recentActions?: MCPAction[];
  /** Raw stream / debug log entries — collapsed by default */
  rawLogs?: RawLogEntry[];
  className?: string;
}

/* ─────────────────────────────────────────────
   Default mock data
───────────────────────────────────────────── */
const DEFAULT_SERVERS: MCPServer[] = [
  { id: "s1", name: "filesystem",   transport: "stdio", status: "connected",    toolCount: 8,  latencyMs: 2  },
  { id: "s2", name: "brave-search", transport: "http",  status: "connected",    toolCount: 3,  latencyMs: 94 },
  { id: "s3", name: "postgres-mcp", transport: "stdio", status: "disconnected", toolCount: 12 },
  { id: "s4", name: "puppeteer",    transport: "stdio", status: "error",        toolCount: 6  },
];

const DEFAULT_ACTIONS: MCPAction[] = [
  { id: "a1", serverName: "filesystem",   tool: "read_file",  status: "success", timestamp: "10:00:12 AM", durationMs: 8   },
  { id: "a2", serverName: "brave-search", tool: "web_search", status: "success", timestamp: "10:00:15 AM", durationMs: 423 },
  { id: "a3", serverName: "filesystem",   tool: "write_file", status: "running", timestamp: "10:00:18 AM"                  },
  { id: "a4", serverName: "postgres-mcp", tool: "query",      status: "failed",  timestamp: "10:00:20 AM", durationMs: 34  },
];

export const RAW_LOGS_RUNNING: RawLogEntry[] = [
  {
    id: "rl1",
    label: "tool_call: detect_missing",
    payload: JSON.stringify({
      event: "tool_call",
      tool: "detect_missing",
      args: { columns: ["Price", "Region", "Date_Sold"] },
      ts: "2026-02-25T10:00:03.412Z",
    }, null, 2),
  },
  {
    id: "rl2",
    label: "tool_result: detect_missing",
    payload: JSON.stringify({
      event: "tool_result",
      tool: "detect_missing",
      result: { nulls: { Region: 142 }, total_rows: 14500, pct_missing: 0.98 },
      duration_ms: 412,
      ts: "2026-02-25T10:00:03.824Z",
    }, null, 2),
  },
];

export const RAW_LOGS_ERROR: RawLogEntry[] = [
  ...RAW_LOGS_RUNNING,
  {
    id: "rl3",
    label: "tool_call: cast_dtype",
    payload: JSON.stringify({
      event: "tool_call",
      tool: "cast_dtype",
      args: { column: "Price", dtype: "float64" },
      ts: "2026-02-25T10:00:06.001Z",
    }, null, 2),
  },
  {
    id: "rl4",
    label: "tool_error: cast_dtype",
    isError: true,
    payload: JSON.stringify({
      event: "tool_error",
      tool: "cast_dtype",
      error: "ParseError: non-numeric characters at rows #142, #991, #3847",
      affected_rows: [142, 991, 3847],
      duration_ms: 234,
      ts: "2026-02-25T10:00:06.235Z",
    }, null, 2),
  },
];

/* ─────────────────────────────────────────────
   Sub-components
───────────────────────────────────────────── */
const STATUS_DOT: Record<MCPServerStatus, string> = {
  connected:    "bg-[var(--genui-success)]",
  disconnected: "bg-[var(--genui-muted)]",
  error:        "bg-[var(--genui-error)]",
};

const STATUS_LABEL: Record<MCPServerStatus, string> = {
  connected:    "Connected",
  disconnected: "Offline",
  error:        "Error",
};

function ServerRow({ server }: { server: MCPServer }) {
  return (
    <div className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-[var(--genui-surface)] transition-colors">
      <div className="flex items-center gap-2.5 min-w-0">
        <div className={cn(
          "w-2 h-2 rounded-full flex-shrink-0",
          STATUS_DOT[server.status],
          server.status === "connected" && "animate-pulse",
        )} />
        <div className="min-w-0">
          <p className="text-xs font-semibold text-[var(--genui-text)] truncate font-mono">{server.name}</p>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="text-[10px] text-[var(--genui-muted)] bg-[var(--genui-surface)] border border-[var(--genui-border)] px-1 rounded">
              {server.transport}
            </span>
            {server.toolCount !== undefined && (
              <span className="text-[10px] text-[var(--genui-muted)]">{server.toolCount} tools</span>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {server.latencyMs !== undefined && server.status === "connected" && (
          <span className="text-[10px] tabular-nums text-[var(--genui-muted)]">{server.latencyMs}ms</span>
        )}
        <span className={cn(
          "text-[10px] font-medium px-1.5 py-0.5 rounded-full border",
          server.status === "connected"    && "text-[var(--genui-success)] bg-[var(--genui-success)]/10 border-[var(--genui-success)]/20",
          server.status === "disconnected" && "text-[var(--genui-muted)] bg-[var(--genui-surface)] border-[var(--genui-border)]",
          server.status === "error"        && "text-[var(--genui-error)] bg-[var(--genui-error)]/10 border-[var(--genui-error)]/20",
        )}>
          {STATUS_LABEL[server.status]}
        </span>
      </div>
    </div>
  );
}

function ActionRow({ action }: { action: MCPAction }) {
  const iconCls = cn(
    "w-3 h-3 flex-shrink-0",
    action.status === "success" && "text-[var(--genui-success)]",
    action.status === "failed"  && "text-[var(--genui-error)]",
    action.status === "running" && "text-[var(--genui-running)] animate-pulse",
  );
  return (
    <div className="flex items-start gap-2.5 px-3 py-2 rounded-lg hover:bg-[var(--genui-surface)] transition-colors">
      <div className="mt-0.5">
        {action.status === "success" && <CheckCircle2 className={iconCls} />}
        {action.status === "failed"  && <XCircle      className={iconCls} />}
        {action.status === "running" && <Loader2      className={cn(iconCls, "animate-spin")} />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[11px] text-[var(--genui-text)] font-mono truncate">{action.tool}</p>
        <p className="text-[10px] text-[var(--genui-muted)]">{action.serverName}</p>
      </div>
      <div className="flex-shrink-0 text-right">
        <p className="text-[10px] text-[var(--genui-muted)] tabular-nums">{action.timestamp}</p>
        {action.durationMs !== undefined && (
          <p className="text-[10px] text-[var(--genui-muted)] tabular-nums">{action.durationMs}ms</p>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Raw log entry (expandable)
───────────────────────────────────────────── */
function RawLogRow({ entry }: { entry: RawLogEntry }) {
  const [open, setOpen]     = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(entry.payload).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="border border-[var(--genui-border)] rounded-lg overflow-hidden mx-1 mb-1">
      {/* Row header */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-[var(--genui-surface)] transition-colors text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          {entry.isError
            ? <AlertTriangle className="w-3 h-3 text-[var(--genui-error)] flex-shrink-0" />
            : <Terminal      className="w-3 h-3 text-[var(--genui-muted)] flex-shrink-0" />
          }
          <span className={cn(
            "text-[10px] font-mono truncate",
            entry.isError ? "text-[var(--genui-error)]" : "text-[var(--genui-text)]",
          )}>
            {entry.label}
          </span>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
          {open && (
            <button
              onClick={handleCopy}
              className="flex items-center gap-0.5 text-[9px] text-[var(--genui-muted)] hover:text-[var(--genui-text)] transition-colors px-1.5 py-0.5 rounded border border-[var(--genui-border)] hover:border-[var(--genui-muted)]/40"
            >
              {copied
                ? <><Check className="w-2.5 h-2.5 text-[var(--genui-success)]" /> Copied</>
                : <><Copy  className="w-2.5 h-2.5" /> Copy</>
              }
            </button>
          )}
          {open
            ? <ChevronUp   className="w-3 h-3 text-[var(--genui-muted)]" />
            : <ChevronDown className="w-3 h-3 text-[var(--genui-muted)]" />
          }
        </div>
      </button>

      {/* Payload */}
      {open && (
        <div className="border-t border-[var(--genui-border)] bg-[var(--genui-surface)]">
          <pre className="px-3 py-2.5 text-[10px] font-mono leading-relaxed text-[var(--genui-text)] overflow-x-auto whitespace-pre max-h-40 overflow-y-auto">
            {entry.payload}
          </pre>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Collapsible section header
───────────────────────────────────────────── */
function SectionHeader({
  icon, label, count, open, onToggle, dot,
}: {
  icon: React.ReactNode;
  label: string;
  count?: number;
  open: boolean;
  onToggle: () => void;
  dot?: boolean;
}) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between px-3 py-2 hover:bg-[var(--genui-surface)] transition-colors group"
    >
      <div className="flex items-center gap-2">
        <span className="text-[var(--genui-muted)] relative">
          {icon}
          {dot && (
            <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-[var(--genui-error)] border border-[var(--genui-panel)]" />
          )}
        </span>
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--genui-muted)]">{label}</span>
        {count !== undefined && (
          <span className="text-[10px] font-bold text-[var(--genui-text)] bg-[var(--genui-panel)] border border-[var(--genui-border)] px-1.5 py-0.5 rounded tabular-nums">
            {count}
          </span>
        )}
      </div>
      {open
        ? <ChevronDown className="w-3 h-3 text-[var(--genui-muted)]" />
        : <ChevronUp   className="w-3 h-3 text-[var(--genui-muted)]" />
      }
    </button>
  );
}

/* ─────────────────────────────────────────────
   Summary bar
───────────────────────────────────────────── */
function SummaryBar({ servers }: { servers: MCPServer[] }) {
  const connected  = servers.filter(s => s.status === "connected").length;
  const offline    = servers.filter(s => s.status === "disconnected").length;
  const errors     = servers.filter(s => s.status === "error").length;
  const totalTools = servers.reduce((sum, s) => sum + (s.toolCount ?? 0), 0);

  return (
    <div className="flex items-center gap-3 px-3 py-2.5 bg-[var(--genui-panel)] border-b border-[var(--genui-border)]">
      <div className="flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-[var(--genui-success)]" />
        <span className="text-[10px] font-semibold text-[var(--genui-text)] tabular-nums">{connected}</span>
        <span className="text-[10px] text-[var(--genui-muted)]">online</span>
      </div>
      <div className="w-px h-3 bg-[var(--genui-border)]" />
      <div className="flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-[var(--genui-muted)]" />
        <span className="text-[10px] font-semibold text-[var(--genui-text)] tabular-nums">{offline}</span>
        <span className="text-[10px] text-[var(--genui-muted)]">offline</span>
      </div>
      {errors > 0 && (
        <>
          <div className="w-px h-3 bg-[var(--genui-border)]" />
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--genui-error)]" />
            <span className="text-[10px] font-semibold text-[var(--genui-error)] tabular-nums">{errors}</span>
            <span className="text-[10px] text-[var(--genui-muted)]">error</span>
          </div>
        </>
      )}
      <div className="ml-auto flex items-center gap-1">
        <Zap className="w-3 h-3 text-[var(--genui-muted)]" />
        <span className="text-[10px] text-[var(--genui-muted)] tabular-nums">{totalTools} tools</span>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   MCPPanel — public export
   Developer / advanced area inside Agent > MCP sub-tab.
   Sections:
     1. Summary bar (always)
     2. Connected Servers (collapsible, default open)
     3. Recent MCP Actions (collapsible, default open)
     4. Raw Stream / Logs (collapsible, default CLOSED)
───────────────────────────────────────────── */
export function MCPPanel({
  servers       = DEFAULT_SERVERS,
  recentActions = DEFAULT_ACTIONS,
  rawLogs,
  className,
}: MCPPanelProps) {
  const [serversOpen, setServersOpen] = useState(true);
  const [actionsOpen, setActionsOpen] = useState(true);
  // Raw Logs: collapsed by default — developer-only, not shown to casual users
  const [rawOpen, setRawOpen]         = useState(false);

  const errorLogs  = (rawLogs ?? []).filter(l => l.isError);
  const hasErrors  = errorLogs.length > 0;

  return (
    <div className={cn("flex flex-col h-full overflow-hidden bg-[var(--genui-surface)]", className)}>

      {/* Summary bar */}
      <SummaryBar servers={servers} />

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">

        {/* ── Connected Servers ── */}
        <div className="border-b border-[var(--genui-border)]">
          <SectionHeader
            icon={<Server className="w-3 h-3" />}
            label="Servers"
            count={servers.length}
            open={serversOpen}
            onToggle={() => setServersOpen(v => !v)}
          />
          {serversOpen && (
            <div className="px-1 pb-2 space-y-0.5">
              {servers.map(s => <ServerRow key={s.id} server={s} />)}
            </div>
          )}
        </div>

        {/* ── Recent MCP Actions ── */}
        <div className="border-b border-[var(--genui-border)]">
          <SectionHeader
            icon={<Activity className="w-3 h-3" />}
            label="Recent Actions"
            count={recentActions.length}
            open={actionsOpen}
            onToggle={() => setActionsOpen(v => !v)}
          />
          {actionsOpen && (
            <div className="px-1 pb-2 space-y-0.5">
              {recentActions.length === 0 ? (
                <p className="px-3 py-4 text-[11px] text-[var(--genui-muted)] text-center opacity-60">
                  No actions yet
                </p>
              ) : (
                recentActions.map(a => <ActionRow key={a.id} action={a} />)
              )}
            </div>
          )}
        </div>

        {/* ── Raw Stream / Logs (developer, collapsed by default) ── */}
        <div className="border-b border-[var(--genui-border)]">
          <SectionHeader
            icon={<Terminal className="w-3 h-3" />}
            label="Raw Stream / Logs"
            count={rawLogs?.length ?? 0}
            open={rawOpen}
            onToggle={() => setRawOpen(v => !v)}
            dot={hasErrors && !rawOpen}
          />
          {rawOpen && (
            <div className="py-2">
              {(!rawLogs || rawLogs.length === 0) ? (
                <p className="px-4 py-4 text-[11px] text-[var(--genui-muted)] text-center opacity-50">
                  No stream events captured yet
                </p>
              ) : (
                rawLogs.map(entry => <RawLogRow key={entry.id} entry={entry} />)
              )}
            </div>
          )}
        </div>

        {/* ── Developer Note ── */}
        <div className="px-3 py-4">
          <div className="flex items-start gap-2 rounded-lg border border-[var(--genui-border)] bg-[var(--genui-panel)] p-3">
            <FileText className="w-3.5 h-3.5 text-[var(--genui-muted)] flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="text-[10px] font-semibold text-[var(--genui-text)]">Developer Mode</p>
              <p className="text-[10px] text-[var(--genui-muted)] leading-relaxed">
                This tab is developer-only. Server names and raw payloads are
                not shown to end-users. Raw logs expand individual SSE frames;
                use <code className="bg-[var(--genui-surface)] px-0.5 rounded">Copy</code> to inspect payloads.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
