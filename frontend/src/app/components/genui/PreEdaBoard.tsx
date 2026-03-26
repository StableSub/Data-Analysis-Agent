import React, { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import type { PreEdaProfile } from "../../lib/preEdaProfile";
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

export function PreEdaBoard({ profile, summarySections, onApprovePreprocess }: PreEdaBoardProps) {
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

      <div className="grid gap-4 xl:grid-cols-12">
        <CardShell
          status={profile.recommendation ? "needs-user" : "success"}
          className="xl:col-span-12"
        >
          <CardHeader
            title="전처리 추천"
            meta="PREPROCESS"
            statusLabel={profile.recommendation ? "Review" : "Optional"}
            statusVariant={profile.recommendation ? "needs-user" : "success"}
            className="px-3.5 py-2.5"
          />
          <CardBody className="space-y-2.5 p-3">
            {profile.recommendation ? (
              <>
                <div className="rounded-lg border border-[var(--genui-needs-user)]/30 bg-[var(--genui-needs-user)]/8 px-3 py-2.5">
                  <p className="text-sm font-semibold text-[var(--genui-text)]">
                    {profile.recommendation.column}
                  </p>
                  <p className="mt-1 text-sm text-[var(--genui-text)]">
                    결측 {profile.recommendation.missingCount.toLocaleString()}건(
                    {profile.recommendation.missingPercent.toFixed(2)}%)이 있어 전처리가 필요합니다.
                  </p>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <ul className="space-y-1 text-sm text-[var(--genui-text)]">
                    <li>전략: {profile.recommendation.strategy}</li>
                    <li>기본 제안값: {profile.recommendation.fillValue}</li>
                  </ul>
                  {onApprovePreprocess && (
                    <button
                      type="button"
                      onClick={onApprovePreprocess}
                      className="shrink-0 rounded-lg bg-[var(--genui-running)] px-4 py-2 text-sm font-semibold text-white shadow-sm hover:opacity-90 transition-opacity"
                    >
                      승인하고 분석 시작
                    </button>
                  )}
                </div>
              </>
            ) : (
              <div className="rounded-xl border border-[var(--genui-border)] bg-[var(--genui-surface)] px-4 py-4 text-sm text-[var(--genui-text)]">
                전처리 없이 바로 질문할 수 있습니다.
              </div>
            )}
          </CardBody>
        </CardShell>
      </div>
    </div>
  );
}
