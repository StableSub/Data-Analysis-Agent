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
import type { VisualizationResultPayload } from "../../hooks/useAnalysisPipeline";
import type { PendingApprovalPayload } from "../../../lib/api";

function formatPendingValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join(", ");
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean" || value === null) {
    return String(value);
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  return "";
}

function formatPendingOperation(operation: Record<string, unknown>): string {
  const op = typeof operation.op === "string" && operation.op.trim() ? operation.op : "operation";
  const details = Object.entries(operation)
    .filter(([key, value]) => key !== "op" && value !== undefined && value !== "")
    .map(([key, value]) => `${key}: ${formatPendingValue(value)}`)
    .filter((value) => value.trim());
  return details.length > 0 ? `${op} (${details.join(" · ")})` : op;
}

interface DetailsPanelSelectedItem {
  visualization?: VisualizationResultPayload | null;
  hasDatasetContext?: boolean;
  pendingApproval?: PendingApprovalPayload | null;
}

interface DetailsPanelProps {
  state: "empty" | "uploading" | "ready" | "streaming" | "needs-user" | "error";
  selectedItem?: DetailsPanelSelectedItem;
  onAction?: (action: string, payload?: any) => void;
  className?: string;
}

export function DetailsPanel({ state, selectedItem, onAction, className }: DetailsPanelProps) {
  const visualization = selectedItem?.visualization ?? null;
  const hasVisualization =
    typeof visualization?.artifact?.image_base64 === "string" &&
    visualization.artifact.image_base64.length > 0;
  const hasDatasetContext = selectedItem?.hasDatasetContext ?? false;
  const pendingApproval = selectedItem?.pendingApproval ?? null;
  const chartType = visualization?.chart?.chart_type ?? "chart";
  const chartTitle = hasVisualization
    ? `${visualization?.chart?.x_key || "x"} vs ${visualization?.chart?.y_key || "y"}`
    : "Revenue Analysis";
  const chartMeta = hasVisualization
    ? `${chartType.toUpperCase()} Visualization`
    : "Visualization";
  const chartImageSrc = hasVisualization
    ? `data:${visualization?.artifact?.mime_type || "image/png"};base64,${visualization?.artifact?.image_base64}`
    : "";
  const insightSummary =
    typeof visualization?.summary === "string" && visualization.summary.trim()
      ? visualization.summary.trim()
      : hasDatasetContext
        ? "시각화 요청이 완료되면 결과 차트가 이 영역에 표시됩니다."
        : "데이터 소스를 선택하고 시각화 요청을 보내면 결과 차트가 표시됩니다.";

  // 1. EMPTY STATE: Help / orientation panel (no duplicate CTAs)
  if (state === "empty" || state === "ready") {
    return (
      <div className={cn("h-full flex flex-col p-5 space-y-7 overflow-y-auto", className)}>

        {/* ── Getting Started ── */}
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-[var(--genui-text)]">
            {state === "ready" ? "업로드 완료" : "Getting Started"}
          </h2>

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
    if (pendingApproval?.stage === "report") {
      return (
        <div className={cn("h-full flex flex-col p-4", className)}>
          <div className="mb-4 flex items-center gap-2 text-[var(--genui-needs-user)]">
            <ShieldCheck className="w-5 h-5" />
            <span className="text-sm font-bold uppercase tracking-wide">Decision Required</span>
          </div>

          <div className="flex-1 rounded-2xl border border-[var(--genui-needs-user)]/30 bg-[var(--genui-surface)] p-4 shadow-sm overflow-y-auto">
            <div className="space-y-2 pb-3 border-b border-[var(--genui-border)]">
              <p className="text-xs font-bold uppercase tracking-widest text-[var(--genui-needs-user)]">
                Report Draft
              </p>
              <h3 className="text-sm font-semibold text-[var(--genui-text)]">
                {pendingApproval.title}
              </h3>
              <p className="text-xs leading-relaxed text-[var(--genui-muted)]">
                {pendingApproval.summary}
              </p>
            </div>
            <div className="mt-4 whitespace-pre-wrap text-sm leading-6 text-[var(--genui-text)]">
              {pendingApproval.draft.trim() || "리포트 초안을 불러오지 못했습니다."}
            </div>
          </div>
        </div>
      );
    }

    const changeList = pendingApproval
      ? pendingApproval.stage === "visualization"
        ? [
            `chart type: ${pendingApproval.plan.chart_type || "-"}`,
            `x axis: ${pendingApproval.plan.x_key || "-"}`,
            `y axis: ${pendingApproval.plan.y_key || "-"}`,
            ...(pendingApproval.plan.mode
              ? [`mode: ${pendingApproval.plan.mode}`]
              : []),
            ...(pendingApproval.plan.reason
              ? [`reason: ${pendingApproval.plan.reason}`]
              : []),
            ...((pendingApproval.plan.preview_rows ?? []).length > 0
              ? [`preview rows: ${(pendingApproval.plan.preview_rows ?? []).length}`]
              : []),
          ]
        : [
            ...pendingApproval.plan.operations.map((operation) => formatPendingOperation(operation)),
            ...(pendingApproval.plan.top_missing_columns ?? []).map(
              (item) => `missing: ${item.column} (${(item.missing_rate * 100).toFixed(1)}%)`,
            ),
            ...((pendingApproval.plan.affected_columns ?? []).length > 0
              ? [`affected columns: ${(pendingApproval.plan.affected_columns ?? []).join(", ")}`]
              : []),
          ]
      : [];
    return (
      <div className={cn("h-full flex flex-col p-4", className)}>
         <div className="mb-4 flex items-center gap-2 text-[var(--genui-needs-user)]">
            <ShieldCheck className="w-5 h-5" />
            <span className="text-sm font-bold uppercase tracking-wide">Decision Required</span>
         </div>
         
         <ApprovalCard 
            title={pendingApproval?.title ?? "Plan review"}
            description={pendingApproval?.summary ?? "계획을 검토한 뒤 승인 여부를 결정해 주세요."}
            changes={changeList.length > 0 ? changeList : ["Approve to continue with the proposed plan."]}
            status="pending"
            hideActions={true}
            className="w-full flex-1 flex flex-col shadow-none border-none bg-transparent"
         />
         {pendingApproval?.stage === "visualization" && (pendingApproval.plan.preview_rows ?? []).length > 0 ? (
           <div className="mt-4 rounded-xl border border-[var(--genui-border)] bg-[var(--genui-panel)] p-3">
             <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--genui-muted)]">
               Preview Rows
             </p>
             <pre className="mt-2 overflow-x-auto text-[11px] leading-relaxed text-[var(--genui-text)]">
               {JSON.stringify(pendingApproval.plan.preview_rows ?? [], null, 2)}
             </pre>
           </div>
         ) : null}
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
            <CardHeader
              title={chartTitle}
              meta={chartMeta}
              statusLabel={hasVisualization ? "Generated" : "Live"}
              statusVariant="neutral"
            />
            <CardBody className="flex-1 bg-[var(--genui-surface)]/30 rounded-lg border border-[var(--genui-border)] mt-4 p-4">
                <div className="space-y-4">
                    {hasVisualization ? (
                      <img
                        src={chartImageSrc}
                        alt={`${chartType} visualization`}
                        className="h-48 w-full rounded border border-[var(--genui-border)] bg-white dark:bg-[#212121] object-contain"
                      />
                    ) : (
                      <div className="h-48 bg-[var(--genui-surface)] rounded border border-dashed border-[var(--genui-border)] flex items-center justify-center">
                        <BarChart3 className="w-8 h-8 text-[var(--genui-muted)]/50" />
                      </div>
                    )}
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium text-[var(--genui-text)]">Analysis Insights</h4>
                      <ul className="space-y-2">
                        {hasVisualization ? (
                          <>
                            <li className="flex gap-2 text-xs text-[var(--genui-muted)]">
                               <Lightbulb className="w-3 h-3 text-[var(--genui-warning)] flex-shrink-0" />
                               <span>{insightSummary}</span>
                            </li>
                            <li className="flex gap-2 text-xs text-[var(--genui-muted)]">
                               <Lightbulb className="w-3 h-3 text-[var(--genui-warning)] flex-shrink-0" />
                               <span>
                                 시각화: {visualization?.chart?.x_key || "x"} vs {visualization?.chart?.y_key || "y"} ({chartType})
                               </span>
                            </li>
                          </>
                        ) : (
                          <>
                            <li className="flex gap-2 text-xs text-[var(--genui-muted)]">
                               <Lightbulb className="w-3 h-3 text-[var(--genui-warning)] flex-shrink-0" />
                               <span>{insightSummary}</span>
                            </li>
                            <li className="flex gap-2 text-xs text-[var(--genui-muted)]">
                               <Lightbulb className="w-3 h-3 text-[var(--genui-warning)] flex-shrink-0" />
                               <span>
                                 {hasDatasetContext
                                   ? "차트/시각화 관련 질문을 보내면 이 패널이 자동으로 갱신됩니다."
                                   : "현재는 일반 질문 경로입니다. 상단에서 데이터 소스를 먼저 선택해 주세요."}
                               </span>
                            </li>
                          </>
                        )}
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
