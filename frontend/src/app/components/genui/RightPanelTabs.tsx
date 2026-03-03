import React, { useState, type ReactNode } from "react";
import { cn } from "../../../lib/utils";

/* ─────────────────────────────────────────────
   Types
───────────────────────────────────────────── */
export type RightTabId   = "details" | "agent";
export type AgentSubTab  = "tools"   | "mcp";

export interface RightPanelTabsProps {
  /** Uncontrolled default tab */
  defaultTab?: RightTabId;
  /** Controlled active tab */
  activeTab?: RightTabId;
  onTabChange?: (tab: RightTabId) => void;

  /**
   * Pulsing dot on the Agent tab when new tool-call/MCP events arrive.
   * Dot disappears once Agent tab is active.
   */
  agentHasNew?: boolean;
  /**
   * Optional extra dot on the MCP sub-toggle when MCP-specific events
   * arrive while the Tools sub-tab is focused.
   */
  mcpHasNew?: boolean;

  detailsContent: ReactNode;
  /** CopilotKit runtime: RunStatus + ToolCallList + ToolCallDetails */
  toolsContent: ReactNode;
  /** MCP servers / actions / logs */
  mcpContent: ReactNode;

  className?: string;
}

/* ─────────────────────────────────────────────
   Top-level tab button
───────────────────────────────────────────── */
function TopTabBtn({
  label,
  active,
  hasNew,
  onClick,
}: {
  label: string;
  active: boolean;
  hasNew?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "relative flex items-center gap-1.5 px-4 py-3 text-xs font-semibold transition-all",
        "border-b-2 -mb-px leading-none select-none",
        active
          ? "text-[var(--genui-text)] border-[var(--genui-text)]"
          : "text-[var(--genui-muted)] border-transparent hover:text-[var(--genui-text)] hover:border-[var(--genui-border)]"
      )}
    >
      {label}
      {hasNew && !active && (
        <span
          className="w-1.5 h-1.5 rounded-full bg-[var(--genui-running)] flex-shrink-0 animate-pulse"
          aria-label="New activity"
        />
      )}
    </button>
  );
}

/* ─────────────────────────────────────────────
   Agent sub-tab segmented control
───────────────────────────────────────────── */
function AgentSegmentedControl({
  active,
  mcpHasNew,
  onChange,
}: {
  active: AgentSubTab;
  mcpHasNew?: boolean;
  onChange: (t: AgentSubTab) => void;
}) {
  return (
    <div className="flex-shrink-0 px-3 py-2 border-b border-[var(--genui-border)] bg-[var(--genui-panel)]">
      <div className="flex items-center gap-0.5 bg-[var(--genui-surface)] border border-[var(--genui-border)] rounded-md p-0.5 w-full">
        {(["tools", "mcp"] as AgentSubTab[]).map((sub) => {
          const labels: Record<AgentSubTab, string> = { tools: "Tools", mcp: "MCP" };
          const isActive = active === sub;
          const showDot  = sub === "mcp" && mcpHasNew && !isActive;
          return (
            <button
              key={sub}
              onClick={() => onChange(sub)}
              className={cn(
                "flex-1 relative flex items-center justify-center gap-1 py-1 rounded text-[11px] font-semibold transition-all select-none",
                isActive
                  ? "bg-[var(--genui-panel)] shadow-sm text-[var(--genui-text)]"
                  : "text-[var(--genui-muted)] hover:text-[var(--genui-text)]"
              )}
            >
              {labels[sub]}
              {showDot && (
                <span className="w-1 h-1 rounded-full bg-[var(--genui-running)] animate-pulse absolute top-1 right-1" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   RightPanelTabs (public component)
───────────────────────────────────────────── */
export function RightPanelTabs({
  defaultTab    = "details",
  activeTab: controlledTab,
  onTabChange,
  agentHasNew   = false,
  mcpHasNew     = false,
  detailsContent,
  toolsContent,
  mcpContent,
  className,
}: RightPanelTabsProps) {
  const [internalTab, setInternalTab] = useState<RightTabId>(defaultTab);
  const [agentSubTab, setAgentSubTab]  = useState<AgentSubTab>("tools");

  const activeTab = controlledTab ?? internalTab;

  const handleTabChange = (tab: RightTabId) => {
    setInternalTab(tab);
    onTabChange?.(tab);
  };

  return (
    <div className={cn("flex flex-col h-full overflow-hidden", className)}>

      {/* ── Top tab bar — h-10 to align with Left History + Center Route bars ── */}
      <div className="h-10 flex-shrink-0 flex items-end px-3 gap-0 border-b border-[var(--genui-border)] bg-[var(--genui-panel)]">
        <TopTabBtn
          label="Details"
          active={activeTab === "details"}
          onClick={() => handleTabChange("details")}
        />
        <TopTabBtn
          label="Agent"
          active={activeTab === "agent"}
          hasNew={agentHasNew && activeTab !== "agent"}
          onClick={() => handleTabChange("agent")}
        />
      </div>

      {/* ── Tab content ── */}
      <div className="flex-1 overflow-hidden bg-[var(--genui-surface)] relative flex flex-col">

        {/* Details pane */}
        <div
          className={cn(
            "absolute inset-0 overflow-y-auto transition-opacity duration-200",
            activeTab === "details" ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
          )}
        >
          {detailsContent}
        </div>

        {/* Agent pane */}
        <div
          className={cn(
            "absolute inset-0 flex flex-col transition-opacity duration-200",
            activeTab === "agent" ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
          )}
        >
          {/* Sub-tab segmented control */}
          <AgentSegmentedControl
            active={agentSubTab}
            mcpHasNew={mcpHasNew}
            onChange={setAgentSubTab}
          />

          {/* Sub-tab content */}
          <div className="flex-1 overflow-hidden relative">
            {/* Tools sub-pane */}
            <div
              className={cn(
                "absolute inset-0 overflow-hidden transition-opacity duration-150",
                agentSubTab === "tools" ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
              )}
            >
              {toolsContent}
            </div>

            {/* MCP sub-pane */}
            <div
              className={cn(
                "absolute inset-0 overflow-y-auto transition-opacity duration-150",
                agentSubTab === "mcp" ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
              )}
            >
              {mcpContent}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}