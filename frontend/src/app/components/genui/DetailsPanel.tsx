import React from "react";
import { 
  FileSpreadsheet, 
  X, 
  RotateCcw, 
  Check, 
  ShieldCheck, 
  AlertTriangle, 
  BarChart3, 
  Lightbulb,
  TableProperties,
} from "lucide-react";
import { cn } from "../../../lib/utils";
import { CardShell, CardHeader, CardBody, CardFooter } from "./CardShell";
import { ApprovalCard } from "./ApprovalCard";
import { ErrorCard } from "./ErrorCard";
import { SkeletonLine } from "./Skeletons";

interface DetailsPanelProps {
  state: "empty" | "uploading" | "streaming" | "needs-user" | "error";
  selectedItem?: any; 
  onAction?: (action: string, payload?: any) => void;
  className?: string;
}

export function DetailsPanel({ state, selectedItem, onAction, className }: DetailsPanelProps) {

  // 1. EMPTY STATE: Help / orientation panel (no duplicate CTAs)
  if (state === "empty") {
    return (
      <div className={cn("h-full flex flex-col p-5 space-y-7 overflow-y-auto", className)}>

        {/* ── Getting Started ── */}
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-[var(--genui-text)]">Getting Started</h2>

          <div className="space-y-4">
            {[
              {
                step: "1",
                title: "Upload Data",
                desc: "Drag & drop a CSV or Excel file into the center panel, or use the + button in the command bar.",
              },
              {
                step: "2",
                title: "Review Plan",
                desc: "The agent proposes a preprocessing plan. Approve, reject, or edit each step.",
              },
              {
                step: "3",
                title: "Iterate",
                desc: "Inspect generated artifacts here and refine them by continuing the conversation.",
              },
            ].map(({ step, title, desc }) => (
              <div key={step} className="flex gap-3">
                <div className="w-6 h-6 rounded-full bg-[var(--genui-surface)] border border-[var(--genui-border)] flex items-center justify-center flex-shrink-0 text-[11px] font-bold text-[var(--genui-muted)] mt-0.5">
                  {step}
                </div>
                <div className="space-y-0.5">
                  <p className="text-xs font-semibold text-[var(--genui-text)]">{title}</p>
                  <p className="text-xs text-[var(--genui-muted)] leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Single text link — format reference, no CTA weight */}
          <a
            href="#"
            onClick={(e) => e.preventDefault()}
            className="inline-flex items-center gap-1 text-[11px] text-[var(--genui-muted)] hover:text-[var(--genui-text)] underline underline-offset-2 transition-colors"
          >
            Supported formats
          </a>
        </div>

        {/* ── Divider ── */}
        <div className="border-t border-[var(--genui-border)]" />

        {/* ── Example Artifacts ── */}
        <div className="space-y-3">
          <div className="space-y-0.5">
            <h2 className="text-sm font-semibold text-[var(--genui-text)]">Example Artifacts</h2>
            <p className="text-[11px] text-[var(--genui-muted)]">These cards appear after upload.</p>
          </div>

          {/* Skeleton card — Dataset Summary */}
          <div className="rounded-xl border border-[var(--genui-border)] bg-[var(--genui-panel)] overflow-hidden opacity-60">
            {/* Card header */}
            <div className="flex items-center justify-between px-3 py-2.5 border-b border-[var(--genui-border)]">
              <div className="flex items-center gap-2">
                <TableProperties className="w-3.5 h-3.5 text-[var(--genui-muted)]" />
                <span className="text-[11px] font-semibold text-[var(--genui-text)]">Dataset Summary</span>
              </div>
              <span className="text-[10px] text-[var(--genui-muted)] bg-[var(--genui-surface)] border border-[var(--genui-border)] px-1.5 py-0.5 rounded">
                Table
              </span>
            </div>
            {/* Skeleton rows */}
            <div className="px-3 py-2.5 space-y-2">
              {[["Rows", "w-8"], ["Columns", "w-6"], ["Missing", "w-10"]].map(([label, w]) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-[10px] text-[var(--genui-muted)]">{label}</span>
                  <div className={`h-2 ${w} bg-[var(--genui-border)] rounded animate-pulse`} />
                </div>
              ))}
            </div>
          </div>

          {/* Skeleton card — Chart */}
          <div className="rounded-xl border border-[var(--genui-border)] bg-[var(--genui-panel)] overflow-hidden opacity-60">
            {/* Card header */}
            <div className="flex items-center justify-between px-3 py-2.5 border-b border-[var(--genui-border)]">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-3.5 h-3.5 text-[var(--genui-muted)]" />
                <span className="text-[11px] font-semibold text-[var(--genui-text)]">Revenue by Region</span>
              </div>
              <span className="text-[10px] text-[var(--genui-muted)] bg-[var(--genui-surface)] border border-[var(--genui-border)] px-1.5 py-0.5 rounded">
                Chart
              </span>
            </div>
            {/* Mini bar chart skeleton */}
            <div className="px-3 py-3">
              <div className="flex items-end gap-1.5 h-12">
                {[60, 85, 45, 70, 55, 90, 40].map((h, i) => (
                  <div
                    key={i}
                    className="flex-1 rounded-sm bg-[var(--genui-border)] animate-pulse"
                    style={{ height: `${h}%`, animationDelay: `${i * 80}ms` }}
                  />
                ))}
              </div>
              <div className="flex justify-between mt-1.5">
                {["N", "S", "E", "W", "C", "NE", "SW"].map((l) => (
                  <span key={l} className="text-[9px] text-[var(--genui-muted)] flex-1 text-center">{l}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

      </div>
    );
  }

  // 2. UPLOADING STATE: File Details + Cancel
  if (state === "uploading") {
    return (
      <div className={cn("h-full flex flex-col p-6 space-y-6", className)}>
        <h2 className="text-lg font-semibold text-[var(--genui-text)]">File Details</h2>
        
        <div className="p-4 bg-[var(--genui-surface)] rounded-lg border border-[var(--genui-border)] space-y-4">
          <div className="flex items-start gap-3">
             <div className="p-2 bg-[var(--genui-panel)] rounded border border-[var(--genui-border)]">
                <FileSpreadsheet className="w-6 h-6 text-[var(--genui-muted)]" />
             </div>
             <div className="space-y-1">
                <p className="text-sm font-medium text-[var(--genui-text)]">sales_data_Q3.csv</p>
                <p className="text-xs text-[var(--genui-muted)]">24.5 MB • CSV</p>
             </div>
          </div>
          
          <div className="space-y-2 pt-2 border-t border-[var(--genui-border)]/50">
             <div className="flex justify-between text-xs">
                <span className="text-[var(--genui-muted)]">Status</span>
                <span className="text-[var(--genui-running)] font-medium animate-pulse">Processing...</span>
             </div>
             <div className="flex justify-between text-xs">
                <span className="text-[var(--genui-muted)]">Rows Est.</span>
                <span className="text-[var(--genui-text)]">~14,000</span>
             </div>
          </div>
        </div>

        <button 
          onClick={() => onAction?.("cancel-upload")}
          className="w-full py-2 px-4 border border-[var(--genui-error)]/30 text-[var(--genui-error)] rounded-lg text-sm font-medium hover:bg-[var(--genui-error)]/5 transition-colors flex items-center justify-center gap-2"
        >
          <X className="w-4 h-4" />
          Cancel Upload
        </button>
      </div>
    );
  }

  // 3. HITL STATE: Full Approval Card
  if (state === "needs-user") {
    return (
      <div className={cn("h-full flex flex-col p-4", className)}>
         <div className="mb-4 flex items-center gap-2 text-[var(--genui-needs-user)]">
            <ShieldCheck className="w-5 h-5" />
            <span className="text-sm font-bold uppercase tracking-wide">Decision Required</span>
         </div>
         
         {/* Reusing ApprovalCard but ensuring it fits the panel */}
         <ApprovalCard 
            title="Impute Missing Values"
            description="The column 'Region' has 142 missing values (2.1%). I recommend filling them with the mode value 'North'."
            changes={[
              "Fill NaN in 'Region' with 'North'",
              "Log imputation event in metadata",
              "Recalculate distribution stats"
            ]}
            status="pending"
            hideActions={true}
            className="w-full flex-1 flex flex-col shadow-none border-none bg-transparent"
         />
      </div>
    );
  }

  // 4. ERROR STATE: Resolution Options
  if (state === "error") {
    return (
      <div className={cn("h-full flex flex-col p-6 space-y-6 overflow-y-auto", className)}>
        <div className="flex items-center gap-2 text-[var(--genui-error)] border-b border-[var(--genui-border)] pb-4">
           <AlertTriangle className="w-5 h-5" />
           <h2 className="text-lg font-semibold">Resolution Required</h2>
        </div>

        <div className="space-y-4">
           <div className="space-y-2">
              <h3 className="text-sm font-medium text-[var(--genui-text)]">Error Cause</h3>
              <p className="text-sm text-[var(--genui-muted)] bg-[var(--genui-surface)] p-3 rounded border border-[var(--genui-border)]">
                 ParseError: Column 'Price' contains non-numeric character '$' at row 142.
              </p>
           </div>

           <div className="space-y-3">
              <h3 className="text-sm font-medium text-[var(--genui-text)]">Resolution Options</h3>
              
              <label className="flex items-start gap-3 p-3 rounded-lg border border-[var(--genui-border)] hover:bg-[var(--genui-surface)] cursor-pointer transition-colors group">
                 <input type="radio" name="resolve" className="mt-1 accent-[var(--genui-running)]" defaultChecked />
                 <div className="space-y-1">
                    <span className="text-sm font-medium text-[var(--genui-text)]">Auto-clean non-numeric chars</span>
                    <p className="text-xs text-[var(--genui-muted)]">Remove '$', ',' and convert to Float.</p>
                 </div>
              </label>

              <label className="flex items-start gap-3 p-3 rounded-lg border border-[var(--genui-border)] hover:bg-[var(--genui-surface)] cursor-pointer transition-colors group">
                 <input type="radio" name="resolve" className="mt-1 accent-[var(--genui-running)]" />
                 <div className="space-y-1">
                    <span className="text-sm font-medium text-[var(--genui-text)]">Drop invalid rows</span>
                    <p className="text-xs text-[var(--genui-muted)]">Exclude 1 row from analysis.</p>
                 </div>
              </label>
           </div>
        </div>

        <div className="pt-4 mt-auto">
           <button 
             onClick={() => onAction?.("resolve-retry")}
             className="w-full py-2 px-4 bg-[var(--genui-text)] text-[var(--genui-surface)] rounded-lg text-sm font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
           >
             <RotateCcw className="w-4 h-4" />
             Confirm & Retry
           </button>
        </div>
      </div>
    );
  }

  // 5. DEFAULT / STREAMING: Artifact Details
  return (
    <div className={cn("h-full flex flex-col p-4", className)}>
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-[var(--genui-border)]">
           <span className="text-xs font-semibold uppercase text-[var(--genui-muted)]">Selected Artifact</span>
           <span className="text-[10px] text-[var(--genui-running)] bg-[var(--genui-running)]/10 px-2 py-0.5 rounded-full">Active</span>
        </div>

        <CardShell status="default" className="flex-1 flex flex-col border-none shadow-none bg-transparent p-0">
            <CardHeader title="Revenue Analysis" meta="Visualization" statusLabel="Live" statusVariant="neutral" />
            <CardBody className="flex-1 bg-[var(--genui-surface)]/30 rounded-lg border border-[var(--genui-border)] mt-4 p-4">
                <div className="space-y-4">
                    <div className="h-48 bg-[var(--genui-surface)] rounded border border-dashed border-[var(--genui-border)] flex items-center justify-center">
                      <BarChart3 className="w-8 h-8 text-[var(--genui-muted)]/50" />
                    </div>
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium text-[var(--genui-text)]">Analysis Insights</h4>
                      <ul className="space-y-2">
                        <li className="flex gap-2 text-xs text-[var(--genui-muted)]">
                           <Lightbulb className="w-3 h-3 text-[var(--genui-warning)] flex-shrink-0" />
                           <span>North region outperforms South by 15%.</span>
                        </li>
                        <li className="flex gap-2 text-xs text-[var(--genui-muted)]">
                           <Lightbulb className="w-3 h-3 text-[var(--genui-warning)] flex-shrink-0" />
                           <span>Q3 spike correlates with marketing campaign.</span>
                        </li>
                      </ul>
                    </div>
                </div>
            </CardBody>
        </CardShell>
        
        <div className="mt-4 pt-4 border-t border-[var(--genui-border)] flex gap-2">
           <button className="flex-1 py-2 text-xs font-medium text-[var(--genui-text)] border border-[var(--genui-border)] rounded hover:bg-[var(--genui-surface)]">
              Download PNG
           </button>
           <button className="flex-1 py-2 text-xs font-medium text-[var(--genui-text)] border border-[var(--genui-border)] rounded hover:bg-[var(--genui-surface)]">
              View Data
           </button>
        </div>
    </div>
  );
}