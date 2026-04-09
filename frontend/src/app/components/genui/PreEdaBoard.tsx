import React, { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Code2,
  Lightbulb,
  LoaderCircle,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import type {
  EdaPreprocessRecommendation,
  EdaRecommendedOperation,
} from "../../../lib/api";
import { cn } from "../../../lib/utils";
import type { DistributionBin, PreEdaProfile, PreprocessStrategy } from "../../lib/preEdaProfile";
import {
  countAutoApplicableRecommendedOperations,
  formatRecommendedOperationLabel,
  getRecommendedOperationKey,
  isAutoApplicableRecommendedOperation,
} from "../../lib/preprocessRecommendation";
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
  recommendationMode?: "llm" | "fallback" | "none" | null;
  recommendationWarning?: string | null;
  applyError?: string | null;
  applyingOperationKey?: string | null;
  onApplyOperation?: (operation: EdaRecommendedOperation, index: number) => void;
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

function formatDistributionBound(value: number): string {
  if (!Number.isFinite(value)) {
    return "-";
  }

  return value.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
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

  return `${formatDistributionBound(start)}~${formatDistributionBound(end)}`;
}

function formatBarChartAxisLabel(label: string): string {
  return label.length > 5 ? `${label.slice(0, 5)}...` : label;
}

function formatDistributionAxisLabel(label: string, kind: "numeric" | "categorical"): string {
  const formatted = formatDistributionLabel(label);
  return kind === "categorical" ? formatBarChartAxisLabel(formatted) : formatted;
}

const DISTRIBUTION_VISIBLE_BAR_COUNT = 8;
const DISTRIBUTION_BAR_SLOT_WIDTH = 72;
const DISTRIBUTION_BAR_MAX_WIDTH = 30;
const PREVIEW_DISTRIBUTION_BAR_MAX_WIDTH = 19;

function getDistributionChartMinWidth(kind: "numeric" | "categorical", count: number): number | undefined {
  if (kind !== "categorical") {
    return undefined;
  }

  return Math.max(count, DISTRIBUTION_VISIBLE_BAR_COUNT) * DISTRIBUTION_BAR_SLOT_WIDTH;
}

function getDistributionBarMaxWidth(kind: "numeric" | "categorical", compact = false): number | undefined {
  if (kind !== "categorical") {
    return undefined;
  }

  return compact ? PREVIEW_DISTRIBUTION_BAR_MAX_WIDTH : DISTRIBUTION_BAR_MAX_WIDTH;
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
  const payloadLabel = payload[0]?.payload?.label;
  const displayLabel =
    typeof payloadLabel === "string"
      ? formatDistributionLabel(payloadLabel)
      : typeof label === "string"
        ? formatDistributionLabel(label)
        : "-";
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
      <p className="mt-1.5 text-[14px] leading-none font-semibold text-[var(--genui-text)]">
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

function buildRecommendationSummary(
  recommendation: EdaPreprocessRecommendation | null,
): string {
  if (!recommendation) {
    return "";
  }
  const summary = recommendation.summary.trim();
  if (summary) {
    return summary;
  }
  return `${recommendation.operations.length}개의 전처리 작업을 검토합니다.`;
}

function formatOperationPriority(
  priority: EdaRecommendedOperation["priority"],
): string {
  switch (priority) {
    case "high":
      return "HIGH";
    case "medium":
      return "MEDIUM";
    case "low":
      return "LOW";
    default:
      return priority;
  }
}

function getOperationPriorityClass(
  priority: EdaRecommendedOperation["priority"],
): string {
  switch (priority) {
    case "high":
      return "border-[var(--genui-warning)]/35 bg-[var(--genui-warning)]/10 text-[var(--genui-warning)]";
    case "medium":
      return "border-[var(--genui-running)]/35 bg-[var(--genui-running)]/10 text-[var(--genui-running)]";
    case "low":
      return "border-[var(--genui-border)] bg-[var(--genui-panel)] text-[var(--genui-muted)]";
    default:
      return "border-[var(--genui-border)] bg-[var(--genui-panel)] text-[var(--genui-muted)]";
  }
}

function formatOperationColumns(columns: string[]): string {
  if (columns.length === 0) {
    return "전체 데이터셋 기준";
  }
  if (columns.length === 1) {
    return columns[0] ?? "-";
  }
  return `${columns.slice(0, 3).join(", ")}${columns.length > 3 ? ` 외 ${columns.length - 3}개` : ""}`;
}

function PreprocessRecommendationCard({
  profile,
  recommendationMode = null,
  recommendationWarning = null,
  applyError = null,
  applyingOperationKey = null,
  onApplyOperation,
}: {
  profile: PreEdaProfile;
  recommendationMode?: "llm" | "fallback" | "none" | null;
  recommendationWarning?: string | null;
  applyError?: string | null;
  applyingOperationKey?: string | null;
  onApplyOperation?: (operation: EdaRecommendedOperation, index: number) => void;
}) {
  const serverRecommendation = profile.serverRecommendation;
  const legacyRecommendation = profile.recommendation;
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [editingDerivedKey, setEditingDerivedKey] = useState<string | null>(null);
  const [derivedDrafts, setDerivedDrafts] = useState<Record<string, { targetColumn: string; zeroDivision: string }>>({});
  const operations = serverRecommendation?.operations ?? [];
  const recommendationSummary = buildRecommendationSummary(serverRecommendation);
  const autoApplicableCount = countAutoApplicableRecommendedOperations(serverRecommendation);
  const manualOperationCount = operations.length - autoApplicableCount;
  const hasRunningOperation = Boolean(applyingOperationKey);

  const alts = legacyRecommendation?.alternativeStrategies ?? [];
  const activeStrategy: PreprocessStrategy | null = useMemo(() => {
    if (!legacyRecommendation || alts.length === 0) return null;
    if (selectedStrategyId) {
      const found = alts.find((s) => s.id === selectedStrategyId);
      return found ?? alts[0] ?? null;
    }
    return alts[0] ?? null;
  }, [legacyRecommendation, alts, selectedStrategyId]);

  const targetDistribution = useMemo(() => {
    if (!legacyRecommendation) return null;
    return profile.distributions.find((d) => d.column === legacyRecommendation.column) ?? null;
  }, [legacyRecommendation, profile.distributions]);

  const previewBins = useMemo(() => {
    if (!targetDistribution || !activeStrategy || !legacyRecommendation) return [];
    return simulatePreviewBins(
      targetDistribution.bins,
      activeStrategy.id,
      activeStrategy.fillValue,
      legacyRecommendation.missingCount,
    );
  }, [targetDistribution, activeStrategy, legacyRecommendation]);

  const chartConfig = useMemo(
    () => ({
      value: {
        label: "Count",
        color: "hsl(var(--chart-1, 173 58% 39%))",
      },
    }),
    [],
  );

  if (operations.length === 0) {
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
                {recommendationMode === "none"
                  ? "필수 전처리 항목이 감지되지 않아 바로 질문할 수 있습니다."
                  : "구조화된 전처리 추천이 없어 바로 질문할 수 있습니다."}
              </p>
            </div>
          </CardBody>
        </CardShell>
      </div>
    );
  }

  const columnTypeLabel =
    (legacyRecommendation?.columnType ?? "categorical") === "numeric" ? "수치형" :
    (legacyRecommendation?.columnType ?? "categorical") === "categorical" ? "범주형" :
    (legacyRecommendation?.columnType ?? "categorical") === "datetime" ? "날짜형" : "불리언";

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
          <div className="rounded-xl border border-[var(--genui-needs-user)]/25 bg-[var(--genui-needs-user)]/6 px-4 py-3.5">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[var(--genui-warning)] shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-[var(--genui-text)]">
                  {recommendationSummary}
                </p>
                <p className="mt-1 text-sm text-[var(--genui-muted)]">
                  {autoApplicableCount > 0
                    ? `${operations.length.toLocaleString()}개 추천 중 ${autoApplicableCount.toLocaleString()}개는 바로 적용 가능${manualOperationCount > 0 ? `, ${manualOperationCount.toLocaleString()}개는 수동 검토 필요` : ""}`
                    : `${operations.length.toLocaleString()}개 추천이 있으며 현재는 수동 검토가 필요합니다.`}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className="rounded-full border border-[var(--genui-border)] bg-[var(--genui-panel)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--genui-muted)]">
                    {recommendationMode === "fallback"
                      ? "Rule-based fallback"
                      : recommendationMode === "llm"
                        ? "LLM recommendation"
                        : recommendationMode === "none"
                          ? "No preprocess required"
                          : "Recommendation"}
                  </span>
                </div>
                {recommendationWarning && (
                  <p className="mt-2 text-xs leading-relaxed text-[var(--genui-muted)]">
                    {recommendationWarning}
                  </p>
                )}
              </div>
            </div>
          </div>

          {manualOperationCount > 0 && (
            <div className="rounded-lg border border-[var(--genui-warning)]/30 bg-[var(--genui-warning)]/8 px-3.5 py-3">
              <div className="flex items-start gap-2.5">
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-[var(--genui-warning)]" />
                <div>
                  <p className="text-sm font-medium text-[var(--genui-text)]">
                    수동 검토가 필요한 작업 포함
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-[var(--genui-muted)]">
                    자동 적용 가능한 작업은 아래에서 바로 실행할 수 있고, 나머지 작업은 추가 입력이 필요해 현재는 검토만 가능합니다.
                  </p>
                </div>
              </div>
            </div>
          )}

          {applyError && (
            <div className="rounded-lg border border-[var(--genui-danger)]/30 bg-[var(--genui-danger)]/8 px-3.5 py-3">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--genui-danger)]" />
                <div>
                  <p className="text-sm font-medium text-[var(--genui-text)]">
                    전처리 적용 실패
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-[var(--genui-muted)]">
                    {applyError}
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3.5 py-3">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-3.5 h-3.5 text-[var(--genui-muted)]" />
              <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--genui-muted)]">
                전처리 작업 목록
              </span>
            </div>
            <div className="space-y-2">
              {operations.map((operation, index) => {
                const autoApplicable = isAutoApplicableRecommendedOperation(operation);
                const operationKey = getRecommendedOperationKey(operation, index);
                const isApplying = applyingOperationKey === operationKey;
                const isDerived = operation.op === "derived_column";
                const draft = derivedDrafts[operationKey] ?? {
                  targetColumn: operation.target_column,
                  zeroDivision:
                    typeof operation.params?.zero_division === "string"
                      ? operation.params.zero_division
                      : "null",
                };

                return (
                  <div
                    key={operationKey}
                    className="rounded-lg border border-[var(--genui-border)] bg-[var(--genui-panel)] px-3 py-2.5"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-[var(--genui-text)]">
                          {index + 1}. {formatRecommendedOperationLabel(operation.op)}
                        </p>
                        <p className="mt-1 text-xs text-[var(--genui-muted)]">
                          대상: {formatOperationColumns(operation.target_columns)}
                        </p>
                      </div>
                      <span
                        className={cn(
                          "rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em]",
                          getOperationPriorityClass(operation.priority),
                        )}
                      >
                        {formatOperationPriority(operation.priority)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-[var(--genui-text)]">
                      {operation.reason}
                    </p>
                    {isDerived && (
                      <div className="mt-2 text-xs text-[var(--genui-muted)]">
                        원본: {operation.source_columns.join(", ")} · 변환: {operation.transform_type ?? "-"} · 결과: {operation.target_column}
                      </div>
                    )}
                    {isDerived && editingDerivedKey === operationKey && (
                      <div className="mt-3 rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3 py-3">
                        <div className="grid gap-3 sm:grid-cols-2">
                          <label className="space-y-1">
                            <span className="text-[11px] font-medium text-[var(--genui-muted)]">새 컬럼명</span>
                            <input
                              value={draft.targetColumn}
                              onChange={(event) => {
                                const value = event.target.value;
                                setDerivedDrafts((prev) => ({
                                  ...prev,
                                  [operationKey]: { ...draft, targetColumn: value },
                                }));
                              }}
                              className="w-full rounded-md border border-[var(--genui-border)] bg-[var(--genui-panel)] px-3 py-2 text-sm text-[var(--genui-text)]"
                            />
                          </label>
                          {operation.transform_type === "ratio" ? (
                            <label className="space-y-1">
                              <span className="text-[11px] font-medium text-[var(--genui-muted)]">0 나누기 처리</span>
                              <select
                                value={draft.zeroDivision}
                                onChange={(event) => {
                                  const value = event.target.value;
                                  setDerivedDrafts((prev) => ({
                                    ...prev,
                                    [operationKey]: { ...draft, zeroDivision: value },
                                  }));
                                }}
                                className="w-full rounded-md border border-[var(--genui-border)] bg-[var(--genui-panel)] px-3 py-2 text-sm text-[var(--genui-text)]"
                              >
                                <option value="null">NaN으로 처리</option>
                              </select>
                            </label>
                          ) : (
                            <div className="space-y-1">
                              <span className="text-[11px] font-medium text-[var(--genui-muted)]">변환 방식</span>
                              <div className="rounded-md border border-[var(--genui-border)] bg-[var(--genui-panel)] px-3 py-2 text-sm text-[var(--genui-text)]">
                                {operation.transform_type ?? "-"}
                              </div>
                            </div>
                          )}
                        </div>
                        <div className="mt-3 flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => setEditingDerivedKey(null)}
                            className="rounded-lg border border-[var(--genui-border)] bg-[var(--genui-panel)] px-3 py-2 text-xs font-semibold text-[var(--genui-text)]"
                          >
                            취소
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              onApplyOperation?.({
                                ...operation,
                                target_column: draft.targetColumn.trim(),
                                target_columns: draft.targetColumn.trim() ? [draft.targetColumn.trim()] : [],
                                params: operation.transform_type === "ratio"
                                  ? { ...(operation.params ?? {}), zero_division: draft.zeroDivision }
                                  : operation.params,
                              }, index);
                            }}
                            disabled={!draft.targetColumn.trim() || hasRunningOperation}
                            className={cn(
                              "rounded-lg px-3 py-2 text-xs font-semibold text-white",
                              !draft.targetColumn.trim() || hasRunningOperation
                                ? "cursor-not-allowed bg-[var(--genui-muted)]/60"
                                : "bg-[var(--genui-running)]",
                            )}
                          >
                            확인 후 적용
                          </button>
                        </div>
                      </div>
                    )}
                    <div className="mt-3 flex items-center justify-end">
                      {autoApplicable ? (
                        <button
                          type="button"
                          onClick={() => {
                            if (isDerived) {
                              setDerivedDrafts((prev) => ({
                                ...prev,
                                [operationKey]: prev[operationKey] ?? draft,
                              }));
                              setEditingDerivedKey((current) => current === operationKey ? null : operationKey);
                              return;
                            }
                            onApplyOperation?.(operation, index);
                          }}
                          disabled={!onApplyOperation || hasRunningOperation}
                          className={cn(
                            "inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-semibold text-white transition-all",
                            !onApplyOperation || hasRunningOperation
                              ? "cursor-not-allowed bg-[var(--genui-muted)]/60"
                              : "bg-[var(--genui-running)] hover:opacity-90 active:scale-[0.98]",
                          )}
                        >
                          {isApplying ? (
                          <>
                            <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                            적용 중...
                          </>
                        ) : (
                          isDerived ? "설정 후 적용" : "적용"
                        )}
                      </button>
                      ) : (
                        <span className="rounded-full border border-[var(--genui-warning)]/30 bg-[var(--genui-warning)]/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--genui-warning)]">
                          수동 작업 필요
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {legacyRecommendation && (
            <div>
              <div className="flex items-center gap-2 mb-2 px-0.5">
                <Lightbulb className="w-3.5 h-3.5 text-[var(--genui-muted)]" />
                <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--genui-muted)]">
                  대표 결측 처리 예시
                </span>
              </div>
              <p className="mb-2 text-xs text-[var(--genui-muted)]">
                아래 미리보기는 구조화 추천 중 대표적인 결측 처리 작업만 요약한 예시입니다. 실제 적용은 위 작업 목록에서 선택한 항목만 개별적으로 진행됩니다.
              </p>

              <div className="rounded-xl border border-[var(--genui-border)] bg-[var(--genui-surface)] px-4 py-3.5">
                <p className="text-sm font-semibold text-[var(--genui-text)]">
                  <span className="font-mono text-[var(--genui-needs-user)]">{legacyRecommendation.column}</span>
                  {" "}컬럼 예시
                </p>
                <p className="mt-1 text-sm text-[var(--genui-muted)]">
                  {legacyRecommendation.missingCount.toLocaleString()}건 ({legacyRecommendation.missingPercent}%) · {columnTypeLabel} 컬럼
                </p>
              </div>

              {legacyRecommendation.domainWarning && (
                <div className="mt-3 flex items-start gap-2.5 rounded-lg border border-[var(--genui-warning)]/30 bg-[var(--genui-warning)]/8 px-3.5 py-3">
                  <ShieldAlert className="w-4 h-4 text-[var(--genui-warning)] shrink-0 mt-0.5" />
                  <p className="text-xs leading-relaxed text-[var(--genui-text)]">
                    {legacyRecommendation.domainWarning}
                  </p>
                </div>
              )}

              {legacyRecommendation.rationale && (
                <div className="mt-3 rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3.5 py-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Lightbulb className="w-3.5 h-3.5 text-[var(--genui-running)]" />
                    <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--genui-muted)]">
                      예시 추천 근거
                    </span>
                  </div>
                  <p className="text-sm leading-relaxed text-[var(--genui-text)]">
                    {legacyRecommendation.rationale}
                  </p>
                </div>
              )}

              {alts.length > 0 && (
                <div className="mt-3">
                  <div className="flex items-center gap-2 mb-2 px-0.5">
                    <Sparkles className="w-3.5 h-3.5 text-[var(--genui-muted)]" />
                    <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--genui-muted)]">
                      예시 전략 비교
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

              {activeStrategy && (
                <div className="mt-3 rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-3.5 py-2.5">
                  <div className="flex items-center gap-2">
                    <Code2 className="w-3.5 h-3.5 text-[var(--genui-muted)]" />
                    <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--genui-muted)]">
                      예시 적용 코드
                    </span>
                  </div>
                  <pre className="mt-1.5 overflow-x-auto rounded-md bg-[var(--genui-panel)] border border-[var(--genui-border)] px-3 py-2 text-xs font-mono text-[var(--genui-text)] leading-relaxed">
                    {buildCodePreview(legacyRecommendation.column, activeStrategy.id, activeStrategy.fillValue)}
                  </pre>
                </div>
              )}

              {targetDistribution && activeStrategy && activeStrategy.id !== "drop_column" && (
                <div className="mt-3">
                  <button
                    type="button"
                    onClick={() => setShowPreview((v) => !v)}
                    className="flex items-center gap-1.5 text-xs font-medium text-[var(--genui-muted)] hover:text-[var(--genui-text)] transition-colors mb-2"
                  >
                    <ChevronDown className={cn(
                      "w-3.5 h-3.5 transition-transform duration-200",
                      showPreview ? "rotate-0" : "-rotate-90",
                    )} />
                    예시 분포 미리보기
                  </button>
                  {showPreview && (
                    <div className="grid gap-3 sm:grid-cols-2 animate-in fade-in slide-in-from-top-1 duration-200">
                      <div className="rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] p-2.5">
                        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--genui-muted)] mb-1.5 px-1">
                          Before (현재)
                        </p>
                        <div className={cn(targetDistribution.kind === "categorical" && "overflow-x-auto")}>
                          <ChartContainer
                            config={chartConfig}
                            className={cn("h-[120px] aspect-auto", targetDistribution.kind === "categorical" ? "w-auto min-w-full" : "w-full")}
                            style={{
                              minWidth: getDistributionChartMinWidth(targetDistribution.kind, targetDistribution.bins.length),
                            }}
                          >
                            <BarChart data={targetDistribution.bins} margin={{ top: 4, right: 4, left: 0, bottom: 4 }} barCategoryGap="14%">
                              <CartesianGrid vertical={false} strokeDasharray="3 3" opacity={0.3} />
                              <XAxis
                                dataKey="label"
                                tickLine={false}
                                axisLine={false}
                                tick={{ fontSize: 8, fill: "var(--genui-muted)" }}
                                interval={0}
                                minTickGap={4}
                                tickFormatter={(label) => formatDistributionAxisLabel(String(label), targetDistribution.kind)}
                              />
                              <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={36} tick={{ fontSize: 9, fill: "var(--genui-muted)" }} />
                              <Bar
                                dataKey="value"
                                fill="var(--color-value)"
                                radius={[4, 4, 0, 0]}
                                maxBarSize={getDistributionBarMaxWidth(targetDistribution.kind, true)}
                                opacity={0.6}
                              />
                            </BarChart>
                          </ChartContainer>
                        </div>
                      </div>
                      <div className="rounded-lg border border-[var(--genui-running)]/30 bg-[var(--genui-running)]/4 p-2.5">
                        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--genui-running)] mb-1.5 px-1">
                          After (예상)
                        </p>
                        <div className={cn(targetDistribution.kind === "categorical" && "overflow-x-auto")}>
                          <ChartContainer
                            config={chartConfig}
                            className={cn("h-[120px] aspect-auto", targetDistribution.kind === "categorical" ? "w-auto min-w-full" : "w-full")}
                            style={{
                              minWidth: getDistributionChartMinWidth(targetDistribution.kind, previewBins.length),
                            }}
                          >
                            <BarChart data={previewBins} margin={{ top: 4, right: 4, left: 0, bottom: 4 }} barCategoryGap="14%">
                              <CartesianGrid vertical={false} strokeDasharray="3 3" opacity={0.3} />
                              <XAxis
                                dataKey="label"
                                tickLine={false}
                                axisLine={false}
                                tick={{ fontSize: 8, fill: "var(--genui-muted)" }}
                                interval={0}
                                minTickGap={4}
                                tickFormatter={(label) => formatDistributionAxisLabel(String(label), targetDistribution.kind)}
                              />
                              <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={36} tick={{ fontSize: 9, fill: "var(--genui-muted)" }} />
                              <Bar
                                dataKey="value"
                                fill="var(--genui-running)"
                                radius={[4, 4, 0, 0]}
                                maxBarSize={getDistributionBarMaxWidth(targetDistribution.kind, true)}
                              />
                            </BarChart>
                          </ChartContainer>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
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
  recommendationMode = null,
  recommendationWarning = null,
  applyError = null,
  applyingOperationKey = null,
  onApplyOperation,
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
                <div className={cn(selectedDistribution.kind === "categorical" && "overflow-x-auto")}>
                  <ChartContainer
                    config={chartConfig}
                    className={cn(
                      "h-[220px] aspect-auto rounded-lg border border-[var(--genui-border)] bg-[var(--genui-surface)] px-2 py-2 [&_.recharts-tooltip-cursor]:opacity-0 [&_.recharts-rectangle.recharts-tooltip-cursor]:fill-transparent [&_.recharts-rectangle.recharts-tooltip-cursor]:stroke-transparent",
                      selectedDistribution.kind === "categorical" ? "w-auto min-w-full" : "w-full",
                    )}
                    style={{
                      minWidth: getDistributionChartMinWidth(selectedDistribution.kind, selectedDistribution.bins.length),
                    }}
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
                        tickFormatter={(label) => formatDistributionAxisLabel(String(label), selectedDistribution.kind)}
                        tick={{ fontSize: 9, fill: "var(--genui-muted)" }}
                      />
                      <YAxis
                        allowDecimals={false}
                        tickLine={false}
                        axisLine={false}
                        width={44}
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
                        maxBarSize={getDistributionBarMaxWidth(selectedDistribution.kind)}
                      />
                    </BarChart>
                  </ChartContainer>
                </div>
                <p className="text-xs text-[var(--genui-muted)]">
                  {selectedDistribution.kind === "numeric"
                    ? "numeric 컬럼은 binning 후 histogram으로 표시합니다."
                    : "categorical / boolean / group key 컬럼은 value counts 전체 항목을 가로 스크롤로 탐색할 수 있습니다."}
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
        profile={profile}
        recommendationMode={recommendationMode}
        recommendationWarning={recommendationWarning}
        applyError={applyError}
        applyingOperationKey={applyingOperationKey}
        onApplyOperation={onApplyOperation}
      />
    </div>
  );
}
