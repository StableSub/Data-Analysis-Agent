import React, { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Code2,
  Lightbulb,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { cn } from "../../../lib/utils";
import type { DistributionBin, PreEdaProfile, PreprocessStrategy } from "../../lib/preEdaProfile";
import {
  AssistantReportMessage,
  type ReportSection,
} from "./AssistantReportMessage";
import { CardBody, CardHeader, CardShell } from "./CardShell";
import {
  ChartContainer,
  ChartTooltip,
} from "../ui/chart";

interface PreEdaBoardProps {
  profile: PreEdaProfile;
  summarySections: ReportSection[];
  /** 전처리 추천 승인 버튼 클릭 시 호출 */
  onApprovePreprocess?: () => void;
  approveActionMode?: "prepare" | "run" | "approved";
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2).replace(/\.00$/, "")}%`;
}

function formatMetric(value: number): string {
  if (!Number.isFinite(value)) {
    return "-";
  }
  if (Math.abs(value) >= 1000) {
    return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  if (Math.abs(value) >= 100) {
    return value.toFixed(1);
  }
  if (Math.abs(value) >= 10) {
    return value.toFixed(2);
  }
  return value.toFixed(3).replace(/\.?0+$/, "");
}

function formatDistributionLabel(label: string): string {
  if (!label.includes("-")) {
    return label;
  }

  const [startRaw, endRaw] = label.split("-");
  const start = Number(startRaw);
  const end = Number(endRaw);

  if (!Number.isFinite(start) || !Number.isFinite(end)) {
    return label;
  }

  return `${formatMetric(start)}~${formatMetric(end)}`;
}

interface DistributionTooltipEntry {
  value?: number | string;
  payload?: {
    label?: string;
  };
}

interface DistributionTooltipProps {
  active?: boolean;
  label?: string;
  payload?: DistributionTooltipEntry[];
}

function DistributionTooltipContent({
  active,
  label,
  payload,
}: DistributionTooltipProps) {
  if (!active || !payload?.length) {
    return null;
  }

  const value = payload[0]?.value;
  const displayLabel = typeof label === "string" ? formatDistributionLabel(label) : "-";
  const displayValue =
    typeof value === "number"
      ? value.toLocaleString()
      : typeof value === "string"
        ? value
        : "-";

  return (
    <div className="rounded-lg border border-[var(--genui-border-strong)] bg-[var(--genui-panel)] px-3 py-2 shadow-[0_12px_28px_rgba(15,23,42,0.14)]">
      <p className="text-sm font-semibold text-[var(--genui-text)]">{displayLabel}</p>
      <div className="mt-1 flex items-center gap-2 text-sm text-[var(--genui-text)]">
        <span className="inline-flex h-3 w-1 rounded-full bg-[var(--genui-running)]" />
        <span className="text-[var(--genui-muted)]">Count</span>
        <span className="ml-2 font-semibold text-[var(--genui-text)]">{displayValue}</span>
      </div>
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3 py-2.5">
      <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[var(--genui-muted)]">
        {label}
      </p>
      <p className="mt-1.5 text-[24px] leading-none font-semibold text-[var(--genui-text)]">
        {value}
      </p>
    </div>
  );
}

/** Generate a Python code snippet for the selected strategy */
function buildCodePreview(
  column: string,
  strategyId: string,
  fillValue: string,
): string {
  switch (strategyId) {
    case "median":
      return `df["${column}"].fillna(df["${column}"].median(), inplace=True)`;
    case "mean":
      return `df["${column}"].fillna(df["${column}"].mean(), inplace=True)`;
    case "mode":
      return `df["${column}"].fillna(df["${column}"].mode()[0], inplace=True)`;
    case "unknown":
    case "custom":
      return `df["${column}"].fillna("${fillValue}", inplace=True)`;
    case "drop_rows":
      return `df.dropna(subset=["${column}"], inplace=True)`;
    case "drop_column":
      return `df.drop(columns=["${column}"], inplace=True)`;
    default:
      return `df["${column}"].fillna(${JSON.stringify(fillValue)}, inplace=True)`;
  }
}

/** Simulate what distribution bins would look like after applying the strategy */
function simulatePreviewBins(
  originalBins: DistributionBin[],
  strategyId: string,
  fillValue: string,
  missingCount: number,
): DistributionBin[] {
  if (strategyId === "drop_rows" || strategyId === "drop_column") {
    // Just return original bins (rows removed don't change existing distribution shape)
    return originalBins.map((b) => ({ ...b }));
  }

  // For fill strategies, add missingCount to the matching bin or create a new one
  const bins = originalBins.map((b) => ({ ...b }));

  const targetLabel = strategyId === "median" || strategyId === "mean"
    ? null // numeric — distribute into nearest bin
    : fillValue;

  if (targetLabel) {
    const existing = bins.find((b) => b.label === targetLabel);
    if (existing) {
      existing.value += missingCount;
    } else {
      bins.push({ label: targetLabel, value: missingCount });
    }
  } else {
    // Numeric: spread into middle bin as approximation
    const midIdx = Math.floor(bins.length / 2);
    const midBin = bins[midIdx];
    if (midBin) {
      midBin.value += missingCount;
    }
  }

  return bins;
}

function PreprocessRecommendationCard({
  recommendation,
  profile,
  onApprovePreprocess,
  approveActionMode = "prepare",
}: {
  recommendation: PreEdaProfile["recommendation"];
  profile: PreEdaProfile;
  onApprovePreprocess?: () => void;
  approveActionMode?: "prepare" | "run" | "approved";
}) {
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const startsAnalysisOnApprove = approveActionMode === "run";
  const isApproved = approveActionMode === "approved";

  // Resolve currently selected strategy
  const alts = recommendation?.alternativeStrategies ?? [];
  const activeStrategy: PreprocessStrategy | null = useMemo(() => {
    if (!recommendation || alts.length === 0) return null;
    if (selectedStrategyId) {
      const found = alts.find((s) => s.id === selectedStrategyId);
      return found ?? alts[0] ?? null;
    }
    return alts[0] ?? null;
  }, [recommendation, alts, selectedStrategyId]);

  // Find the distribution for the target column (for preview)
  const targetDistribution = useMemo(() => {
    if (!recommendation) return null;
    return profile.distributions.find((d) => d.column === recommendation.column) ?? null;
  }, [recommendation, profile.distributions]);

  // Simulated preview bins
  const previewBins = useMemo(() => {
    if (!targetDistribution || !activeStrategy || !recommendation) return [];
    return simulatePreviewBins(
      targetDistribution.bins,
      activeStrategy.id,
      activeStrategy.fillValue,
      recommendation.missingCount,
    );
  }, [targetDistribution, activeStrategy, recommendation]);

  const chartConfig = useMemo(
    () => ({
      value: {
        label: "Count",
        color: "hsl(var(--chart-1, 173 58% 39%))",
      },
    }),
    [],
  );

  if (!recommendation) {
    return (
      <div className="grid gap-4 xl:grid-cols-12">
        <CardShell status="success" className="xl:col-span-12">
          <CardHeader
            title="전처리 추천"
            meta="PREPROCESS"
            statusLabel="Clean"
            statusVariant="success"
            className="px-3.5 py-2.5"
          />
          <CardBody className="p-3">
            <div className="flex items-center gap-2.5 rounded-xl border border-[var(--genui-success)]/20 bg-[var(--genui-success)]/5 px-4 py-3.5">
              <CheckCircle2 className="w-5 h-5 text-[var(--genui-success)] shrink-0" />
              <p className="text-sm text-[var(--genui-text)]">
                결측률이 낮아 전처리 없이 바로 질문할 수 있습니다.
              </p>
            </div>
          </CardBody>
        </CardShell>
      </div>
    );
  }

  const columnTypeLabel =
    (recommendation.columnType ?? "categorical") === "numeric" ? "수치형" :
    (recommendation.columnType ?? "categorical") === "categorical" ? "범주형" :
    (recommendation.columnType ?? "categorical") === "datetime" ? "날짜형" : "불리언";

  return (
    <div className="grid gap-4 xl:grid-cols-12">
      <CardShell status="needs-user" className="xl:col-span-12">
        <CardHeader
          title="전처리 추천"
          meta="AI RECOMMENDATION"
          statusLabel="Review"
          statusVariant="needs-user"
          className="px-3.5 py-2.5"
        />
        <CardBody className="space-y-3 p-3">

          {/* Step 1: Issue Summary Header */}
          <div className="rounded-xl border border-[var(--genui-needs-user)]/25 bg-[var(--genui-needs-user)]/6 px-4 py-3.5">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[var(--genui-warning)] shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-[var(--genui-text)]">
                  <span className="font-mono text-[var(--genui-needs-user)]">{recommendation.column}</span>
                  {" "}컬럼에 결측이 감지되었습니다
                </p>
                <p className="mt-1 text-sm text-[var(--genui-muted)]">
                  {recommendation.missingCount.toLocaleString()}건 ({recommendation.missingPercent}%) · {columnTypeLabel} 컬럼
                </p>
              </div>
            </div>
          </div>

          {/* Domain Warning (if any) */}
          {recommendation.domainWarning && (
            <div className="flex items-start gap-2.5 rounded-lg border border-[var(--genui-warning)]/30 bg-[var(--genui-warning)]/8 px-3.5 py-3">
              <ShieldAlert className="w-4 h-4 text-[var(--genui-warning)] shrink-0 mt-0.5" />
              <p className="text-xs leading-relaxed text-[var(--genui-text)]">
                {recommendation.domainWarning}
              </p>
            </div>
          )}

          {/* Step 2: AI Rationale */}
          {recommendation.rationale && (
            <div className="rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3.5 py-3">
              <div className="flex items-center gap-2 mb-2">
                <Lightbulb className="w-3.5 h-3.5 text-[var(--genui-running)]" />
                <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--genui-muted)]">
                  AI 추천 근거
                </span>
              </div>
              <p className="text-sm leading-relaxed text-[var(--genui-text)]">
                {recommendation.rationale}
              </p>
            </div>
          )}

          {/* Step 3: Strategy Selection */}
          {alts.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2 px-0.5">
                <Sparkles className="w-3.5 h-3.5 text-[var(--genui-muted)]" />
                <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--genui-muted)]">
                  전처리 전략 선택
                </span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {alts.map((strategy, index) => {
                  const isSelected = activeStrategy?.id === strategy.id;
                  const isRecommended = index === 0;
                  return (
                    <button
                      key={strategy.id}
                      type="button"
                      onClick={() => setSelectedStrategyId(strategy.id)}
                      className={cn(
                        "relative text-left rounded-xl border px-3.5 py-3 transition-all duration-200",
                        isSelected
                          ? "border-[var(--genui-running)] bg-[var(--genui-running)]/8 ring-1 ring-[var(--genui-running)]/30"
                          : "border-[var(--genui-border)] bg-[var(--genui-panel)] hover:border-[var(--genui-muted)] hover:bg-[var(--genui-surface)]",
                      )}
                    >
                      {isRecommended && (
                        <span className="absolute -top-2 right-3 rounded-full bg-[var(--genui-running)] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-white">
                          추천
                        </span>
                      )}
                      <p className="text-sm font-semibold text-[var(--genui-text)]">
                        {strategy.label}
                      </p>
                      <p className="mt-0.5 text-xs text-[var(--genui-muted)] leading-relaxed">
                        {strategy.description}
                      </p>
                      {strategy.fillValue !== "-" && (
                        <p className="mt-1.5 text-xs text-[var(--genui-muted)]">
                          대체값: <span className="font-mono font-semibold text-[var(--genui-text)]">{strategy.fillValue}</span>
                        </p>
                      )}
                      <p className="mt-1 text-[11px] text-[var(--genui-muted)]">
                        <ChevronRight className="inline w-3 h-3 -mt-px" />
                        {" "}{strategy.expectedImpact}
                      </p>
                    </button>
                  );
                })}

              </div>
            </div>
          )}

          {/* Code Preview Tooltip */}
          {activeStrategy && (
            <div className="rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3.5 py-2.5">
              <div className="flex items-center gap-2">
                <Code2 className="w-3.5 h-3.5 text-[var(--genui-muted)]" />
                <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--genui-muted)]">
                  적용될 코드
                </span>
              </div>
              <pre className="mt-1.5 overflow-x-auto rounded-md bg-[var(--genui-panel)] border border-[var(--genui-border)] px-3 py-2 text-xs font-mono text-[var(--genui-text)] leading-relaxed">
                {buildCodePreview(recommendation.column, activeStrategy.id, activeStrategy.fillValue)}
              </pre>
            </div>
          )}

          {/* Interactive Preview — Mini Histogram */}
          {targetDistribution && activeStrategy && activeStrategy.id !== "drop_column" && (
            <div>
              <button
                type="button"
                onClick={() => setShowPreview((v) => !v)}
                className="flex items-center gap-1.5 text-xs font-medium text-[var(--genui-muted)] hover:text-[var(--genui-text)] transition-colors mb-2"
              >
                <ChevronDown className={cn(
                  "w-3.5 h-3.5 transition-transform duration-200",
                  showPreview ? "rotate-0" : "-rotate-90",
                )} />
                전처리 후 예상 분포 미리보기
              </button>
              {showPreview && (
                <div className="grid gap-3 sm:grid-cols-2 animate-in fade-in slide-in-from-top-1 duration-200">
                  {/* Before */}
                  <div className="rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] p-2.5">
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--genui-muted)] mb-1.5 px-1">
                      Before (현재)
                    </p>
                    <ChartContainer config={chartConfig} className="h-[120px] w-full aspect-auto">
                      <BarChart data={targetDistribution.bins} margin={{ top: 4, right: 4, left: 0, bottom: 4 }} barCategoryGap="14%">
                        <CartesianGrid vertical={false} strokeDasharray="3 3" opacity={0.3} />
                        <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 9, fill: "var(--genui-muted)" }} interval={0} minTickGap={4} />
                        <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={28} tick={{ fontSize: 9, fill: "var(--genui-muted)" }} />
                        <Bar dataKey="value" fill="var(--color-value)" radius={[4, 4, 0, 0]} maxBarSize={28} opacity={0.6} />
                      </BarChart>
                    </ChartContainer>
                  </div>
                  {/* After */}
                  <div className="rounded-lg border border-[var(--genui-running)]/30 bg-[var(--genui-running)]/4 p-2.5">
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--genui-running)] mb-1.5 px-1">
                      After (예상)
                    </p>
                    <ChartContainer config={chartConfig} className="h-[120px] w-full aspect-auto">
                      <BarChart data={previewBins} margin={{ top: 4, right: 4, left: 0, bottom: 4 }} barCategoryGap="14%">
                        <CartesianGrid vertical={false} strokeDasharray="3 3" opacity={0.3} />
                        <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 9, fill: "var(--genui-muted)" }} interval={0} minTickGap={4} />
                        <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={28} tick={{ fontSize: 9, fill: "var(--genui-muted)" }} />
                        <Bar dataKey="value" fill="var(--genui-running)" radius={[4, 4, 0, 0]} maxBarSize={28} />
                      </BarChart>
                    </ChartContainer>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 4: Action Bar */}
          {(onApprovePreprocess || isApproved) && (
            <div className="flex items-center justify-between gap-3 rounded-xl border border-[var(--genui-border)] bg-[var(--genui-surface)] px-4 py-3">
              <div className="min-w-0">
                {isApproved ? (
                  <>
                    <p className="text-sm font-semibold text-[var(--genui-success)]">
                      전처리 추천이 승인되었습니다
                    </p>
                    <p className="mt-0.5 text-xs text-[var(--genui-muted)]">
                      질문을 입력하면 승인된 전략을 반영해 Deep EDA를 이어갑니다
                    </p>
                  </>
                ) : activeStrategy ? (
                  <>
                    <p className="text-sm text-[var(--genui-text)]">
                      선택된 전략: <span className="font-semibold">{activeStrategy.label}</span>
                    </p>
                    <p className="text-xs text-[var(--genui-muted)] mt-0.5">
                      {activeStrategy.fillValue !== "-" && activeStrategy.fillValue !== "(미입력)"
                        ? startsAnalysisOnApprove
                          ? <>대체값 <span className="font-mono">{activeStrategy.fillValue}</span> 적용 후 Deep EDA를 시작합니다</>
                          : <>대체값 <span className="font-mono">{activeStrategy.fillValue}</span> 적용을 승인하고, 이후 질문을 입력하면 Deep EDA를 시작합니다</>
                        : startsAnalysisOnApprove
                          ? "이 전략을 적용한 뒤 Deep EDA를 시작합니다"
                          : "이 전략을 승인하면 이후 질문을 입력할 때 Deep EDA를 시작합니다"}
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-[var(--genui-text)]">
                    전략: <span className="font-semibold">{recommendation.strategy}</span>
                    {recommendation.fillValue !== "-" && (
                      <span className="text-[var(--genui-muted)]"> · 대체값 <span className="font-mono">{recommendation.fillValue}</span></span>
                    )}
                  </p>
                )}
              </div>
              {onApprovePreprocess && (
                <button
                  type="button"
                  onClick={onApprovePreprocess}
                  className="shrink-0 flex items-center gap-2 rounded-lg bg-[var(--genui-running)] px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:opacity-90 active:scale-[0.98] transition-all"
                >
                  {startsAnalysisOnApprove ? "승인하고 분석 시작" : "승인하고 계속"}
                  <ChevronRight className="w-4 h-4" />
                </button>
              )}
            </div>
          )}

        </CardBody>
      </CardShell>
    </div>
  );
}

export function PreEdaBoard({
  profile,
  summarySections,
  onApprovePreprocess,
  approveActionMode = "prepare",
}: PreEdaBoardProps) {
  const previewColumns = profile.columns.slice(0, 5);
  const distributionOptions = profile.distributions;
  const [selectedDistributionColumn, setSelectedDistributionColumn] = useState(
    distributionOptions[0]?.column ?? "",
  );

  useEffect(() => {
    if (
      !selectedDistributionColumn ||
      !distributionOptions.some((item) => item.column === selectedDistributionColumn)
    ) {
      setSelectedDistributionColumn(distributionOptions[0]?.column ?? "");
    }
  }, [distributionOptions, selectedDistributionColumn]);

  const selectedDistribution = useMemo(
    () =>
      distributionOptions.find((item) => item.column === selectedDistributionColumn)
      ?? distributionOptions[0]
      ?? null,
    [distributionOptions, selectedDistributionColumn],
  );

  const chartConfig = useMemo(
    () => ({
      value: {
        label: "Count",
        color: "hsl(var(--chart-1, 173 58% 39%))",
      },
    }),
    [],
  );

  return (
    <div className="space-y-3 animate-in fade-in zoom-in-95 duration-300">
      <div className="grid items-start gap-3 xl:grid-cols-12">
        <CardShell className="h-fit xl:col-span-12">
          <CardHeader
            title="데이터 미리보기"
            meta="TOP 5 ROWS"
            statusLabel="Table"
            statusVariant="neutral"
            className="px-3.5 py-2.5"
          />
          <CardBody className="p-0 overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-[var(--genui-surface)]/80">
                <tr>
                  {previewColumns.map((column) => (
                    <th
                      key={column}
                      className="border-b border-[var(--genui-border)] px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-[var(--genui-muted)]"
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {profile.sampleRows.map((row, rowIndex) => (
                  <tr
                    key={`${rowIndex}-${previewColumns[0] ?? "row"}`}
                    className="odd:bg-[var(--genui-panel)] even:bg-[var(--genui-surface)]/30"
                  >
                    {previewColumns.map((column) => (
                      <td
                        key={`${rowIndex}-${column}`}
                        className="border-b border-[var(--genui-border)]/60 px-3 py-2 text-[13px] text-[var(--genui-text)]"
                      >
                        {row[column] ?? "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardBody>
        </CardShell>

      </div>

      <div className="grid gap-3 xl:grid-cols-12">
        <CardShell className="min-h-[206px] xl:col-span-6">
          <CardHeader
            title="데이터 개요 요약"
            meta="PRE-EDA"
            statusLabel="Ready"
            statusVariant="running"
            className="px-3.5 py-2.5"
          />
          <CardBody className="space-y-3 p-3">
            <div className="grid grid-cols-4 gap-2.5">
              <MetricTile label="Rows" value={profile.rowCount.toLocaleString()} />
              <MetricTile label="Columns" value={profile.columnCount.toLocaleString()} />
              <MetricTile label="Numeric" value={profile.numericColumns.length.toLocaleString()} />
              <MetricTile
                label="Categorical"
                value={profile.categoricalColumns.length.toLocaleString()}
              />
              <MetricTile label="Datetime" value={profile.datetimeColumns.length.toLocaleString()} />
              <MetricTile label="Boolean" value={profile.booleanColumns.length.toLocaleString()} />
              <MetricTile
                label="Identifier"
                value={profile.identifierColumns.length.toLocaleString()}
              />
              <MetricTile
                label="Group key"
                value={profile.groupKeyColumns.length > 0
                  ? `${profile.groupKeyColumns.length} 후보`
                  : "없음"}
              />
            </div>

            <div className="rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3 py-2.5">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--genui-muted)]">
                Quality Summary
              </p>
              <p className="mt-2 text-sm leading-relaxed text-[var(--genui-text)]">
                {profile.qualitySummary}
              </p>
            </div>
          </CardBody>
        </CardShell>

        <CardShell className="min-h-[206px] xl:col-span-6">
          <CardHeader
            title="결측치 분석"
            meta="NULL COUNT / NULL RATIO"
            statusLabel={profile.missingColumns.length > 0 ? "Quality" : "Clean"}
            statusVariant={profile.missingColumns.length > 0 ? "warning" : "success"}
            className="px-3.5 py-2.5"
          />
          <CardBody className="space-y-2.5 p-3">
            {profile.missingColumns.length > 0 ? (
              profile.missingColumns.slice(0, 3).map((item) => (
                <div
                  key={item.column}
                  className="rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3 py-2.5"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-[var(--genui-text)]">
                        {item.column}
                      </p>
                      <p className="text-xs text-[var(--genui-muted)]">
                        {item.missingCount.toLocaleString()} rows missing
                      </p>
                    </div>
                    <span className="text-base font-semibold text-[var(--genui-warning)]">
                      {formatPercent(item.missingRate)}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-xl border border-[var(--genui-border)] bg-[var(--genui-surface)] px-4 py-4 text-sm text-[var(--genui-text)]">
                결측 컬럼이 없어 전처리 없이 질문 흐름으로 넘어갈 수 있습니다.
              </div>
            )}
          </CardBody>
        </CardShell>
      </div>

      <div className="grid gap-3 xl:grid-cols-12">
        <CardShell className="min-h-[360px] xl:col-span-7">
          <CardHeader
            title="기본 통계"
            meta="NUMERIC ONLY"
            statusLabel={profile.numericColumnStats.length > 0 ? "mean / std / q1 / q3" : "No Numeric"}
            statusVariant="neutral"
            className="px-3.5 py-2.5"
          />
          <CardBody className="p-0 overflow-auto">
            {profile.numericColumnStats.length > 0 ? (
              <table className="min-w-full text-sm">
                <thead className="bg-[var(--genui-surface)]/80">
                  <tr>
                    {["column", "mean", "min", "max", "median", "std", "q1", "q3"].map((header) => (
                      <th
                        key={header}
                        className="border-b border-[var(--genui-border)] px-2.5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-[var(--genui-muted)]"
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {profile.numericColumnStats.map((item) => (
                    <tr key={item.column} className="odd:bg-[var(--genui-panel)] even:bg-[var(--genui-surface)]/30">
                      <td className="border-b border-[var(--genui-border)]/60 px-2.5 py-2.5 font-medium text-[var(--genui-text)]">
                        {item.column}
                      </td>
                      {[item.mean, item.min, item.max, item.median, item.std, item.q1, item.q3].map((value, index) => (
                        <td
                          key={`${item.column}-${index}`}
                          className="border-b border-[var(--genui-border)]/60 px-2.5 py-2.5 text-[13px] text-[var(--genui-text)]"
                        >
                          {formatMetric(value)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-4 text-sm text-[var(--genui-text)]">
                numeric 컬럼이 충분하지 않아 기본 통계를 계산하지 않았습니다.
              </div>
            )}
          </CardBody>
        </CardShell>

        <AssistantReportMessage
          className="max-w-none mx-0 h-full xl:col-span-5"
          title="Pre-EDA Summary"
          subtitle="질문 전 빠른 맥락"
          timestamp="방금 생성됨"
          sections={summarySections}
          maxBodyHeight={380}
        />
      </div>

      <div className="grid gap-3 xl:grid-cols-12">
        <CardShell className="xl:col-span-6">
          <CardHeader
            title="분포 시각화"
            meta="COLUMN DISTRIBUTION"
            statusLabel={selectedDistribution?.kind === "numeric" ? "Histogram" : "Bar Chart"}
            statusVariant="neutral"
            className="px-3.5 py-2.5"
          >
            {distributionOptions.length > 0 ? (
              <select
                value={selectedDistribution?.column ?? ""}
                onChange={(event) => setSelectedDistributionColumn(event.target.value)}
                className="h-8 rounded-md border border-[var(--genui-border)] bg-[var(--genui-panel)] px-2 text-xs text-[var(--genui-text)] focus:outline-none focus:ring-1 focus:ring-[var(--genui-focus-ring)]"
              >
                {distributionOptions.map((item) => (
                  <option key={item.column} value={item.column}>
                    {item.column}
                  </option>
                ))}
              </select>
            ) : null}
          </CardHeader>
          <CardBody className="space-y-2.5 p-3">
            {selectedDistribution ? (
              <>
                <ChartContainer
                  config={chartConfig}
                  className="h-[220px] w-full aspect-auto rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-2 py-2 [&_.recharts-tooltip-cursor]:opacity-0 [&_.recharts-rectangle.recharts-tooltip-cursor]:fill-transparent [&_.recharts-rectangle.recharts-tooltip-cursor]:stroke-transparent"
                >
                  <BarChart
                    data={selectedDistribution.bins}
                    margin={{ top: 8, right: 8, left: 0, bottom: 4 }}
                    barCategoryGap="18%"
                  >
                    <CartesianGrid vertical={false} strokeDasharray="3 3" opacity={0.35} />
                    <XAxis
                      dataKey="label"
                      tickLine={false}
                      axisLine={false}
                      interval={0}
                      minTickGap={8}
                      tickMargin={10}
                      tickFormatter={formatDistributionLabel}
                      tick={{ fontSize: 11, fill: "var(--genui-muted)" }}
                    />
                    <YAxis
                      allowDecimals={false}
                      tickLine={false}
                      axisLine={false}
                      width={36}
                      tick={{ fontSize: 11, fill: "var(--genui-muted)" }}
                    />
                    <ChartTooltip
                      cursor={false}
                      shared={false}
                      content={<DistributionTooltipContent />}
                    />
                    <Bar
                      dataKey="value"
                      fill="var(--color-value)"
                      radius={[6, 6, 0, 0]}
                      maxBarSize={44}
                    />
                  </BarChart>
                </ChartContainer>
                <p className="text-xs text-[var(--genui-muted)]">
                  {selectedDistribution.kind === "numeric"
                    ? "numeric 컬럼은 binning 후 histogram으로 표시합니다."
                    : "categorical / boolean / group key 컬럼은 value counts 기준 상위 항목을 표시합니다."}
                </p>
              </>
            ) : (
              <div className="rounded-xl border border-[var(--genui-border)] bg-[var(--genui-surface)] px-4 py-4 text-sm text-[var(--genui-text)]">
                분포 시각화 대상 컬럼이 아직 없습니다.
              </div>
            )}
          </CardBody>
        </CardShell>

        <CardShell className="xl:col-span-3">
          <CardHeader
            title="상관관계 TOP 분석"
            meta="PEARSON"
            statusLabel={profile.correlationTopPairs.length > 0 ? "Top 3" : "Insufficient"}
            statusVariant="neutral"
            className="px-3.5 py-2.5"
          />
          <CardBody className="space-y-2.5 p-3">
            {profile.correlationTopPairs.length > 0 ? (
              profile.correlationTopPairs.map((item, index) => (
                <div
                  key={`${item.left}-${item.right}`}
                  className="rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3 py-2.5"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-[var(--genui-text)]">
                        {index + 1}. {item.left} ↔ {item.right}
                      </p>
                      <p className="mt-1 text-xs text-[var(--genui-muted)]">
                        absolute corr 기준 상위 pair
                      </p>
                    </div>
                    <span className="text-lg font-semibold text-[var(--genui-text)]">
                      {item.value.toFixed(3)}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-xl border border-[var(--genui-border)] bg-[var(--genui-surface)] px-4 py-4 text-sm text-[var(--genui-text)]">
                numeric 컬럼이 충분하지 않아 상관관계 TOP 분석을 만들지 않았습니다.
              </div>
            )}
          </CardBody>
        </CardShell>

        <CardShell className="xl:col-span-3">
          <CardHeader
            title="이상치 탐지"
            meta="IQR"
            statusLabel={profile.outlierSummaries.some((item) => item.outlierCount > 0) ? "Detected" : "Stable"}
            statusVariant={profile.outlierSummaries.some((item) => item.outlierCount > 0) ? "warning" : "success"}
            className="px-3.5 py-2.5"
          />
          <CardBody className="space-y-2.5 p-3">
            {profile.outlierSummaries.length > 0 ? (
              profile.outlierSummaries.slice(0, 6).map((item) => (
                <div
                  key={item.column}
                  className="rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3 py-2.5"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-[var(--genui-text)]">{item.column}</p>
                      <p className="mt-1 text-xs text-[var(--genui-muted)]">
                        bound {formatMetric(item.lowerBound)} ~ {formatMetric(item.upperBound)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-base font-semibold text-[var(--genui-text)]">
                        {item.outlierCount.toLocaleString()}
                      </p>
                      <p className="text-xs text-[var(--genui-muted)]">
                        {formatPercent(item.outlierRate)}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-xl border border-[var(--genui-border)] bg-[var(--genui-surface)] px-4 py-4 text-sm text-[var(--genui-text)]">
                이상치 탐지 대상 numeric 컬럼이 없습니다.
              </div>
            )}
          </CardBody>
        </CardShell>
      </div>

      <PreprocessRecommendationCard
        recommendation={profile.recommendation}
        profile={profile}
        onApprovePreprocess={onApprovePreprocess}
        approveActionMode={approveActionMode}
      />
    </div>
  );
}
