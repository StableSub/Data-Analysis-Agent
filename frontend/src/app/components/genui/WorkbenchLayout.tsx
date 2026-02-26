import React, { useState } from "react";
import { cn } from "../../../lib/utils";
import { SidebarClose, SidebarOpen } from "lucide-react";

/* ─────────────────────────────────────────────
   Sub-header height token — shared across all 3 columns
   to guarantee horizontal baseline alignment.
───────────────────────────────────────────── */
const SUB_H = "h-10"; // 40px: Left History / Center Route / Right Tabs

interface LayoutProps {
  leftPanel: React.ReactNode;
  mainContent: React.ReactNode;
  rightPanel: React.ReactNode;

  /** Session title row content (h-12 global header) */
  header: React.ReactNode;

  /**
   * Center column sub-header content.
   * Rendered in a fixed h-10 row aligned with:
   *   - Left History label bar (h-10)
   *   - Right RightPanelTabs tab bar (h-10)
   * When null/undefined, the row is still rendered (keeps grid stable).
   */
  centerSubHeader?: React.ReactNode;

  bottomBar?: React.ReactNode;
  gateBar?: React.ReactNode;

  /**
   * PipelineBar — absolutely positioned inside the session <header>.
   * Uses absolute text-strip + progress-line; does not affect layout.
   */
  pipelineBar?: React.ReactNode;
}

export function WorkbenchLayout({
  leftPanel,
  mainContent,
  rightPanel,
  header,
  centerSubHeader,
  bottomBar,
  gateBar,
  pipelineBar,
}: LayoutProps) {
  const [isLeftPanelOpen, setIsLeftPanelOpen] = useState(true);

  return (
    <div className="flex h-full w-full flex-col genui-scope bg-[var(--genui-surface)] overflow-hidden">

      {/* ── Row 1: Session header (h-12, full-width) ── */}
      <header className="h-12 flex-shrink-0 border-b border-[var(--genui-border)] bg-[var(--genui-panel)] z-20 flex items-center pr-4 relative">
        <div className="flex items-center h-full flex-1 min-w-0">
          {/* History toggle */}
          <button
            onClick={() => setIsLeftPanelOpen(!isLeftPanelOpen)}
            className="w-12 h-full flex-shrink-0 flex items-center justify-center border-r border-[var(--genui-border)] hover:bg-[var(--genui-surface)] transition-colors"
            title={isLeftPanelOpen ? "Close History" : "Open History"}
          >
            {isLeftPanelOpen
              ? <SidebarClose className="w-5 h-5 text-[var(--genui-text)]" />
              : <SidebarOpen  className="w-5 h-5 text-[var(--genui-text)]" />
            }
          </button>

          {/* Session title / StatusBadge */}
          <div className="flex-1 h-full pl-4 flex items-center min-w-0">
            {header}
          </div>
        </div>

        {/* PipelineBar: absolutely positions text-strip + progress-line */}
        {pipelineBar}
      </header>

      {/* ── Row 2+: 3-column body ── */}
      <div className="flex-1 flex overflow-hidden relative">

        {/* ── Left: History panel (collapsible) ── */}
        <aside
          className={cn(
            "flex-shrink-0 border-r border-[var(--genui-border)] bg-[var(--genui-panel)] flex flex-col z-10 relative shadow-sm transition-all duration-300 ease-in-out overflow-hidden",
            isLeftPanelOpen ? "w-72 opacity-100" : "w-0 opacity-0 border-r-0",
          )}
        >
          <div className="min-w-[18rem] h-full flex flex-col">
            {leftPanel}
          </div>
        </aside>

        {/* ── Center: Workbench canvas ── */}
        <main className="flex-1 flex flex-col bg-[var(--genui-surface)] relative overflow-hidden min-w-0 isolate">

          {/*
            Center sub-header (h-10) — always rendered for grid stability.
            Aligns horizontally with:
              • Left aside's inner History h-10 label row
              • Right aside's RightPanelTabs h-10 tab row
          */}
          <div
            className={cn(
              SUB_H,
              "flex-shrink-0 border-b border-[var(--genui-border)] bg-[var(--genui-panel)] flex items-center px-4 gap-3",
            )}
          >
            {centerSubHeader ?? null}
          </div>

          {/* Scrollable content */}
          <div className="flex-1 overflow-y-auto relative p-4 scroll-smooth">
            {mainContent}
          </div>

          {/* Sticky bottom: GateBar + CommandBar */}
          <div className="flex-shrink-0 sticky bottom-0 z-30 w-full flex flex-col items-center pointer-events-none">
            {gateBar && (
              <div className="w-full pointer-events-auto pb-2 px-4 animate-in slide-in-from-bottom-4 duration-300">
                {gateBar}
              </div>
            )}
            {bottomBar && (
              <div className="w-full pointer-events-auto bg-[var(--genui-surface)]/80 backdrop-blur-md border-t border-transparent shadow-[0_-4px_24px_rgba(0,0,0,0.04)] dark:shadow-[0_-4px_24px_rgba(0,0,0,0.2)]">
                <div className="max-w-3xl mx-auto px-4 py-4">
                  {bottomBar}
                </div>
              </div>
            )}
          </div>
        </main>

        {/* ── Right: Details / Agent panel (fixed) ── */}
        <aside className="w-[400px] flex-shrink-0 border-l border-[var(--genui-border)] bg-[var(--genui-panel)] flex flex-col z-10 relative shadow-sm hidden xl:flex">
          {rightPanel}
        </aside>
      </div>
    </div>
  );
}
