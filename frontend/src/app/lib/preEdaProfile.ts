import type { EdaPreprocessRecommendation } from "../../lib/api";

export interface NumericSnapshot {
  column: string;
  q1: number;
  median: number;
  q3: number;
}

export interface NumericColumnStat extends NumericSnapshot {
  count: number;
  mean: number;
  min: number;
  max: number;
  std: number;
}

export interface MissingColumnSummary {
  column: string;
  missingCount: number;
  missingRate: number;
}

export interface DistributionBin {
  label: string;
  value: number;
}

export interface ColumnDistribution {
  column: string;
  kind: "numeric" | "categorical";
  bins: DistributionBin[];
}

export interface CorrelationPair {
  left: string;
  right: string;
  value: number;
}

export interface OutlierSummary {
  column: string;
  outlierCount: number;
  outlierRate: number;
  lowerBound: number;
  upperBound: number;
}

export type ColumnRole =
  | "numeric"
  | "categorical"
  | "identifier"
  | "datetime"
  | "boolean"
  | "group-key";

export interface ColumnRoleSummary {
  column: string;
  role: ColumnRole;
  note: string;
  missingCount: number;
  missingRate: number;
  uniqueCount: number;
}

export interface PreprocessStrategy {
  id: string;
  label: string;
  description: string;
  fillValue: string;
  expectedImpact: string;
}

export interface PreprocessRecommendation {
  column: string;
  columnType: "numeric" | "categorical" | "datetime" | "boolean";
  strategy: string;
  fillValue: string;
  missingCount: number;
  missingPercent: number;
  /** AI가 이 전략을 추천한 이유 */
  rationale: string;
  /** 도메인 컨텍스트 경고 (센서 오류, 패턴 등) */
  domainWarning: string | null;
  /** 대안 전략 목록 (추천 전략 포함) */
  alternativeStrategies: PreprocessStrategy[];
}

export interface PreEdaProfile {
  sourceLabel: string;
  uploadedAt: string;
  rowCount: number;
  columnCount: number;
  columns: string[];
  sampleRows: Array<Record<string, string | null>>;
  numericColumns: string[];
  categoricalColumns: string[];
  datetimeColumns: string[];
  identifierColumns: string[];
  booleanColumns: string[];
  groupKeyColumns: string[];
  groupKeyCandidates: string[];
  columnRoleSummaries: ColumnRoleSummary[];
  missingColumns: MissingColumnSummary[];
  topMissingColumns: MissingColumnSummary[];
  numericSnapshots: NumericSnapshot[];
  numericColumnStats: NumericColumnStat[];
  distributions: ColumnDistribution[];
  correlationTopPairs: CorrelationPair[];
  outlierSummaries: OutlierSummary[];
  qualitySummary: string;
  summaryBullets: string[];
  serverRecommendation: EdaPreprocessRecommendation | null;
  recommendation: PreprocessRecommendation | null;
}

const DATETIME_NAME_RE = /(date|time|timestamp|created|updated|day|month|year)/i;
const GROUP_KEY_NAME_RE = /(batch|line|group|plant|factory|shift|store|shop|region|site|station|cluster|segment)/i;
const IDENTIFIER_NAME_RE = /(^id$|_id$|uuid|serial|token|reference|ref$|code$)/i;

const BOOLEAN_TRUE_VALUES = new Set(["true", "1", "yes", "y", "t"]);
const BOOLEAN_FALSE_VALUES = new Set(["false", "0", "no", "n", "f"]);

function isMissing(value: string | null | undefined): boolean {
  if (value == null) {
    return true;
  }
  const normalized = value.trim().toLowerCase();
  return (
    normalized === "" ||
    normalized === "null" ||
    normalized === "nan" ||
    normalized === "none" ||
    normalized === "n/a" ||
    normalized === "na" ||
    normalized === "-"
  );
}

function isNumeric(value: string): boolean {
  const normalized = value.trim().replace(/,/g, "");
  return normalized !== "" && Number.isFinite(Number(normalized));
}

function toNumeric(value: string): number {
  return Number(value.trim().replace(/,/g, ""));
}

function isDateLike(value: string): boolean {
  if (!value.trim() || isNumeric(value)) {
    return false;
  }
  const parsed = Date.parse(value);
  return Number.isFinite(parsed);
}

function normalizeBoolean(value: string): string | null {
  const normalized = value.trim().toLowerCase();
  if (BOOLEAN_TRUE_VALUES.has(normalized)) {
    return "true";
  }
  if (BOOLEAN_FALSE_VALUES.has(normalized)) {
    return "false";
  }
  return null;
}

function quantile(sorted: number[], ratio: number): number {
  if (sorted.length === 0) {
    return 0;
  }
  const index = (sorted.length - 1) * ratio;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  if (lower === upper) {
    return sorted[lower] ?? 0;
  }
  const lowerValue = sorted[lower] ?? 0;
  const upperValue = sorted[upper] ?? lowerValue;
  const weight = index - lower;
  return lowerValue + (upperValue - lowerValue) * weight;
}

function mean(values: number[]): number {
  if (values.length === 0) {
    return 0;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function standardDeviation(values: number[], center: number): number {
  if (values.length === 0) {
    return 0;
  }
  const variance =
    values.reduce((sum, value) => sum + (value - center) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function formatMetric(value: number): string {
  if (!Number.isFinite(value)) {
    return "0";
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
    return "0";
  }

  return value.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

function toRoundedMetric(value: number): number {
  return Number(formatMetric(value));
}

function parseCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];

    if (char === "\"") {
      if (inQuotes && next === "\"") {
        current += "\"";
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === "," && !inQuotes) {
      cells.push(current);
      current = "";
      continue;
    }

    current += char;
  }

  cells.push(current);
  return cells.map((cell) => cell.trim());
}

function parseCsvText(text: string): Array<Record<string, string | null>> {
  const lines = text
    .replace(/\r\n/g, "\n")
    .split("\n")
    .filter((line) => line.trim().length > 0);

  if (lines.length === 0) {
    return [];
  }

  const headers = parseCsvLine(lines[0]).map((header, index) => header || `column_${index + 1}`);
  const rows: Array<Record<string, string | null>> = [];

  for (const line of lines.slice(1)) {
    const values = parseCsvLine(line);
    const row: Record<string, string | null> = {};
    headers.forEach((header, index) => {
      const raw = values[index] ?? "";
      row[header] = isMissing(raw) ? null : raw;
    });
    rows.push(row);
  }

  return rows;
}

function parseJsonText(text: string): Array<Record<string, string | null>> {
  const raw = JSON.parse(text) as unknown;
  const array = Array.isArray(raw) ? raw : [];
  return array
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item) => {
      const row: Record<string, string | null> = {};
      Object.entries(item).forEach(([key, value]) => {
        row[key] = value == null ? null : String(value);
      });
      return row;
    });
}

function mostCommon(values: string[]): string {
  const counts = new Map<string, number>();
  values.forEach((value) => {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  });

  let topValue = "";
  let topCount = -1;
  counts.forEach((count, value) => {
    if (count > topCount) {
      topValue = value;
      topCount = count;
    }
  });

  return topValue || "N/A";
}

function buildCategoricalDistribution(values: string[], limit?: number): DistributionBin[] {
  const counts = new Map<string, number>();
  values.forEach((value) => {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  });

  const sortedEntries = [...counts.entries()]
    .sort((a, b) => {
      if (b[1] !== a[1]) {
        return b[1] - a[1];
      }
      return a[0].localeCompare(b[0]);
    });

  const visibleEntries =
    typeof limit === "number"
      ? sortedEntries.slice(0, limit)
      : sortedEntries;

  return visibleEntries
    .map(([label, value]) => ({
      label,
      value,
    }));
}

function buildNumericDistribution(values: number[], bucketCount = 8): DistributionBin[] {
  if (values.length === 0) {
    return [];
  }

  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);

  if (minValue === maxValue) {
    return [{ label: formatMetric(minValue), value: values.length }];
  }

  const step = (maxValue - minValue) / bucketCount;
  const counts = Array.from({ length: bucketCount }, () => 0);

  values.forEach((value) => {
    let index = Math.floor((value - minValue) / step);
    if (index >= bucketCount) {
      index = bucketCount - 1;
    }
    counts[index] += 1;
  });

  return counts.map((value, index) => {
    const start = minValue + step * index;
    const end = index === bucketCount - 1 ? maxValue : minValue + step * (index + 1);
    return {
      label: `${formatDistributionBound(start)}-${formatDistributionBound(end)}`,
      value,
    };
  });
}

function pearsonCorrelation(xs: Array<number | null>, ys: Array<number | null>): number | null {
  const validXs: number[] = [];
  const validYs: number[] = [];

  for (let index = 0; index < xs.length; index += 1) {
    const left = xs[index];
    const right = ys[index];
    if (left == null || right == null) {
      continue;
    }
    validXs.push(left);
    validYs.push(right);
  }

  if (validXs.length < 3) {
    return null;
  }

  const meanX = mean(validXs);
  const meanY = mean(validYs);

  let numerator = 0;
  let sumSqX = 0;
  let sumSqY = 0;

  for (let index = 0; index < validXs.length; index += 1) {
    const dx = validXs[index] - meanX;
    const dy = validYs[index] - meanY;
    numerator += dx * dy;
    sumSqX += dx ** 2;
    sumSqY += dy ** 2;
  }

  if (sumSqX === 0 || sumSqY === 0) {
    return null;
  }

  return numerator / Math.sqrt(sumSqX * sumSqY);
}

function roleNote(role: ColumnRole): string {
  switch (role) {
    case "numeric":
      return "기본 통계 / 상관관계 / 이상치 대상";
    case "categorical":
      return "빈도 분석 / bar chart 대상";
    case "identifier":
      return "미리보기 전용 / 통계·상관관계·이상치 제외";
    case "datetime":
      return "타입 분류 전용 / 시계열 key 후보";
    case "boolean":
      return "categorical로 간주하여 빈도 분석 포함";
    case "group-key":
      return "그룹별 비교 기준 컬럼";
    default:
      return "";
  }
}

function createFallbackProfile(file: File, uploadedAt: string): PreEdaProfile {
  return {
    sourceLabel: file.name,
    uploadedAt,
    rowCount: 0,
    columnCount: 0,
    columns: [],
    sampleRows: [],
    numericColumns: [],
    categoricalColumns: [],
    datetimeColumns: [],
    identifierColumns: [],
    booleanColumns: [],
    groupKeyColumns: [],
    groupKeyCandidates: [],
    columnRoleSummaries: [],
    missingColumns: [],
    topMissingColumns: [],
    numericSnapshots: [],
    numericColumnStats: [],
    distributions: [],
    correlationTopPairs: [],
    outlierSummaries: [],
    qualitySummary:
      "현재 브라우저에서는 CSV/JSON 기반 Pre-EDA만 즉시 계산합니다. 이 파일은 업로드 후 질문 흐름에 사용할 수 있습니다.",
    summaryBullets: [
      "CSV/JSON이 아닌 형식이라 브라우저 내 즉시 프로파일링은 생략했습니다.",
      "업로드 후 질문과 후속 리포트 흐름은 그대로 진행할 수 있습니다.",
    ],
    serverRecommendation: null,
    recommendation: null,
  };
}

function mapServerOperationToStrategyId(op: EdaPreprocessRecommendation["operations"][number]["op"]): string {
  if (op === "drop_missing") return "drop_rows";
  if (op === "drop_columns") return "drop_column";
  return "custom";
}

function mapServerOperationToLabel(op: EdaPreprocessRecommendation["operations"][number]["op"]): string {
  switch (op) {
    case "drop_missing":
      return "결측 행 제거";
    case "impute":
      return "결측값 대체";
    case "drop_columns":
      return "컬럼 제거";
    case "scale":
      return "스케일 조정";
    case "encode_categorical":
      return "범주형 인코딩";
    case "outlier":
      return "이상치 처리";
    case "parse_datetime":
      return "날짜형 변환";
    case "derived_column":
      return "파생 컬럼 생성";
    default:
      return op;
  }
}

function inferRecommendationColumnType(
  column: string,
  numericColumns: string[],
  categoricalColumns: string[],
  datetimeColumns: string[],
  booleanColumns: string[],
): PreprocessRecommendation["columnType"] {
  if (numericColumns.includes(column)) return "numeric";
  if (datetimeColumns.includes(column)) return "datetime";
  if (booleanColumns.includes(column)) return "boolean";
  if (categoricalColumns.includes(column)) return "categorical";
  return "categorical";
}

// Temporary adapter for the current single-column preprocess card.
// Stage 5 should remove this legacy projection and consume serverRecommendation directly.
export function buildLegacyRecommendationFromServerRecommendation(
  serverRecommendation: EdaPreprocessRecommendation | null,
  {
    missingColumns,
    numericColumns,
    categoricalColumns,
    datetimeColumns,
    booleanColumns,
  }: {
    missingColumns: MissingColumnSummary[];
    numericColumns: string[];
    categoricalColumns: string[];
    datetimeColumns: string[];
    booleanColumns: string[];
  },
): PreprocessRecommendation | null {
  const primaryOperation = serverRecommendation?.operations[0];
  const primaryColumn = (
    primaryOperation?.target_columns[0]
    ?? primaryOperation?.target_column
    ?? primaryOperation?.source_columns[0]
    ?? ""
  ).trim();
  if (!primaryOperation || !primaryColumn) {
    return null;
  }

  const strategyId = mapServerOperationToStrategyId(primaryOperation.op);
  const strategyLabel = mapServerOperationToLabel(primaryOperation.op);
  const missing = missingColumns.find((item) => item.column === primaryColumn) ?? null;
  const fillValue = strategyId === "drop_rows" || strategyId === "drop_column"
    ? "-"
    : "(모델 결정)";
  const alternativeStrategies: PreprocessStrategy[] = [
    {
      id: strategyId,
      label: strategyLabel,
      description: primaryOperation.reason,
      fillValue,
      expectedImpact: primaryOperation.reason,
    },
  ];

  return {
    column: primaryColumn,
    columnType: inferRecommendationColumnType(
      primaryColumn,
      numericColumns,
      categoricalColumns,
      datetimeColumns,
      booleanColumns,
    ),
    strategy: strategyLabel,
    fillValue,
    missingCount: missing?.missingCount ?? 0,
    missingPercent: missing ? Number((missing.missingRate * 100).toFixed(1)) : 0,
    rationale: primaryOperation.reason,
    domainWarning: null,
    alternativeStrategies,
  };
}

function buildRecommendation(
  topMissing: MissingColumnSummary | null,
  numericColumns: string[],
  categoricalColumns: string[],
  datetimeColumns: string[],
  booleanColumns: string[],
  numericVectors: Map<string, Array<number | null>>,
  nonMissingByColumn: Map<string, string[]>,
  numericColumnStats: NumericColumnStat[],
): PreprocessRecommendation | null {
  if (!topMissing || topMissing.missingRate < 0.003) {
    return null;
  }

  const col = topMissing.column;
  const isNumeric = numericColumns.includes(col);
  const isCategorical = categoricalColumns.includes(col);
  const isDatetime = datetimeColumns.includes(col);
  const isBoolean = booleanColumns.includes(col);

  const columnType: PreprocessRecommendation["columnType"] = isNumeric
    ? "numeric"
    : isCategorical
      ? "categorical"
      : isDatetime
        ? "datetime"
        : isBoolean
          ? "boolean"
          : "categorical";

  const missingPercent = Number((topMissing.missingRate * 100).toFixed(2));
  const alternatives: PreprocessStrategy[] = [];

  if (isNumeric) {
    const numValues = (numericVectors.get(col) ?? []).filter(
      (v): v is number => v !== null,
    );
    const medianVal = formatMetric(quantile(numValues, 0.5));
    const stat = numericColumnStats.find((s) => s.column === col);
    const meanVal = stat ? formatMetric(stat.mean) : medianVal;

    alternatives.push(
      {
        id: "median",
        label: "중앙값(Median) 대체",
        description: "이상치에 강건한 대표값으로 결측을 채웁니다.",
        fillValue: medianVal,
        expectedImpact: `분포 왜곡 최소화, ${topMissing.missingCount.toLocaleString()}건 복구`,
      },
      {
        id: "mean",
        label: "평균값(Mean) 대체",
        description: "정규 분포에 가까울 때 효과적이지만 이상치에 민감합니다.",
        fillValue: meanVal,
        expectedImpact: `전체 평균 유지, 이상치 있으면 편향 가능`,
      },
      {
        id: "drop_rows",
        label: "결측 행 제거",
        description: "결측이 포함된 행을 삭제합니다. 데이터 손실 발생.",
        fillValue: "-",
        expectedImpact: `${topMissing.missingCount.toLocaleString()}행 삭제 (${missingPercent}% 손실)`,
      },
      {
        id: "drop_column",
        label: "컬럼 제거",
        description: "결측률이 높으면 컬럼 자체를 제거하는 것이 나을 수 있습니다.",
        fillValue: "-",
        expectedImpact: `분석 대상에서 ${col} 컬럼 완전 제외`,
      },
    );

    const recommendedStrategy = alternatives[0]!;

    // Domain warning: check if values have suspicious patterns (e.g. sensor -999)
    const suspiciousValues = numValues.filter(
      (v) => v === -999 || v === -9999 || v === 9999 || v === -1,
    );
    const domainWarning =
      suspiciousValues.length > 0
        ? `${col} 컬럼에 센서 오류로 의심되는 값(${suspiciousValues[0]})이 ${suspiciousValues.length}건 감지되었습니다. 결측 외 추가 클리닝이 필요할 수 있습니다.`
        : null;

    return {
      column: col,
      columnType,
      strategy: recommendedStrategy.label,
      fillValue: recommendedStrategy.fillValue,
      missingCount: topMissing.missingCount,
      missingPercent,
      rationale: `${col} 컬럼은 numeric 타입으로, 중앙값 대체가 이상치 영향을 최소화하면서 분포를 보존합니다. 결측률 ${missingPercent}%는 행 삭제 시 데이터 손실이 크므로 대체를 권장합니다.`,
      domainWarning,
      alternativeStrategies: alternatives,
    };
  }

  // Categorical / other types
  const modeVal = mostCommon(nonMissingByColumn.get(col) ?? []);

  alternatives.push(
    {
      id: "mode",
      label: "최빈값(Mode) 대체",
      description: "가장 자주 나타나는 값으로 결측을 채웁니다.",
      fillValue: modeVal,
      expectedImpact: `최빈값 "${modeVal}"로 ${topMissing.missingCount.toLocaleString()}건 복구`,
    },
    {
      id: "unknown",
      label: '"Unknown" 대체',
      description: '결측을 별도 범주("Unknown")로 취급합니다.',
      fillValue: "Unknown",
      expectedImpact: `새 범주 추가, 원래 분포에 영향 없음`,
    },
    {
      id: "drop_rows",
      label: "결측 행 제거",
      description: "결측이 포함된 행을 삭제합니다.",
      fillValue: "-",
      expectedImpact: `${topMissing.missingCount.toLocaleString()}행 삭제 (${missingPercent}% 손실)`,
    },
    {
      id: "drop_column",
      label: "컬럼 제거",
      description: "결측률이 높으면 컬럼 자체를 제거합니다.",
      fillValue: "-",
      expectedImpact: `분석 대상에서 ${col} 컬럼 완전 제외`,
    },
  );

  const recommendedStrategy = alternatives[0]!;

  return {
    column: col,
    columnType,
    strategy: recommendedStrategy.label,
    fillValue: recommendedStrategy.fillValue,
    missingCount: topMissing.missingCount,
    missingPercent,
    rationale: `${col} 컬럼은 categorical 타입으로, 최빈값 대체가 기존 분포를 가장 잘 유지합니다. 결측률 ${missingPercent}%는 적당한 수준이므로 대체 후 분석을 이어가는 것을 권장합니다.`,
    domainWarning: null,
    alternativeStrategies: alternatives,
  };
}

export async function buildPreEdaProfile(file: File): Promise<PreEdaProfile | null> {
  const uploadedAt = new Date().toISOString();
  const text = await file.text();

  let rows: Array<Record<string, string | null>> = [];
  const lowerName = file.name.toLowerCase();

  if (lowerName.endsWith(".json")) {
    rows = parseJsonText(text);
  } else if (lowerName.endsWith(".csv") || lowerName.endsWith(".txt")) {
    rows = parseCsvText(text);
  } else {
    return createFallbackProfile(file, uploadedAt);
  }

  if (rows.length === 0) {
    return null;
  }

  const columns = Array.from(
    rows.reduce((set, row) => {
      Object.keys(row).forEach((key) => set.add(key));
      return set;
    }, new Set<string>()),
  );

  const nonMissingByColumn = new Map<string, string[]>();
  const missingByColumn = new Map<string, number>();

  columns.forEach((column) => {
    nonMissingByColumn.set(column, []);
    missingByColumn.set(column, 0);
  });

  rows.forEach((row) => {
    columns.forEach((column) => {
      const value = row[column];
      if (value == null || isMissing(value)) {
        missingByColumn.set(column, (missingByColumn.get(column) ?? 0) + 1);
      } else {
        nonMissingByColumn.get(column)?.push(String(value));
      }
    });
  });

  const numericColumns: string[] = [];
  const categoricalColumns: string[] = [];
  const datetimeColumns: string[] = [];
  const identifierColumns: string[] = [];
  const booleanColumns: string[] = [];
  const groupKeyColumns: string[] = [];
  const columnRoleSummaries: ColumnRoleSummary[] = [];

  columns.forEach((column) => {
    const values = nonMissingByColumn.get(column) ?? [];
    const uniqueCount = new Set(values).size;
    const uniqueRatio = values.length > 0 ? uniqueCount / values.length : 0;
    const numericCount = values.filter(isNumeric).length;
    const datetimeCount = values.filter(isDateLike).length;
    const booleanCount = values.filter((value) => normalizeBoolean(value) !== null).length;
    const missingCount = missingByColumn.get(column) ?? 0;
    const missingRate = rows.length > 0 ? missingCount / rows.length : 0;

    let role: ColumnRole = "categorical";

    if (values.length > 0 && booleanCount / values.length >= 0.9 && uniqueCount <= 2) {
      role = "boolean";
      booleanColumns.push(column);
    } else if (
      values.length > 0 &&
      (IDENTIFIER_NAME_RE.test(column) || uniqueRatio >= 0.98)
    ) {
      role = "identifier";
      identifierColumns.push(column);
    } else if (
      values.length > 0 &&
      (GROUP_KEY_NAME_RE.test(column) ||
        (uniqueCount >= 2 &&
          uniqueRatio >= 0.01 &&
          uniqueRatio <= 0.35 &&
          !DATETIME_NAME_RE.test(column)))
    ) {
      role = "group-key";
      groupKeyColumns.push(column);
    } else if (values.length > 0 && numericCount / values.length >= 0.8) {
      role = "numeric";
      numericColumns.push(column);
    } else if (
      values.length > 0 &&
      ((datetimeCount / values.length >= 0.8) || DATETIME_NAME_RE.test(column))
    ) {
      role = "datetime";
      datetimeColumns.push(column);
    } else {
      role = "categorical";
      categoricalColumns.push(column);
    }

    columnRoleSummaries.push({
      column,
      role,
      note: roleNote(role),
      missingCount,
      missingRate,
      uniqueCount,
    });
  });

  const numericColumnStats: NumericColumnStat[] = [];
  const numericVectors = new Map<string, Array<number | null>>();

  numericColumns.forEach((column) => {
    const vector = rows.map((row) => {
      const raw = row[column];
      return raw != null && isNumeric(raw) ? toNumeric(raw) : null;
    });
    numericVectors.set(column, vector);

    const values = vector.filter((value): value is number => value !== null).sort((a, b) => a - b);
    if (values.length === 0) {
      return;
    }

    const columnMean = mean(values);
    const q1 = quantile(values, 0.25);
    const median = quantile(values, 0.5);
    const q3 = quantile(values, 0.75);

    numericColumnStats.push({
      column,
      count: values.length,
      mean: toRoundedMetric(columnMean),
      min: toRoundedMetric(values[0]),
      max: toRoundedMetric(values[values.length - 1]),
      median: toRoundedMetric(median),
      std: toRoundedMetric(standardDeviation(values, columnMean)),
      q1: toRoundedMetric(q1),
      q3: toRoundedMetric(q3),
    });
  });

  const numericSnapshots: NumericSnapshot[] = numericColumnStats.slice(0, 4).map((stat) => ({
    column: stat.column,
    q1: stat.q1,
    median: stat.median,
    q3: stat.q3,
  }));

  const missingColumns = columns
    .map((column) => {
      const missingCount = missingByColumn.get(column) ?? 0;
      return {
        column,
        missingCount,
        missingRate: rows.length > 0 ? missingCount / rows.length : 0,
      };
    })
    .filter((item) => item.missingCount > 0)
    .sort((a, b) => b.missingCount - a.missingCount);

  const topMissingColumns = missingColumns.slice(0, 3);

  const distributions: ColumnDistribution[] = [
    ...numericColumns.slice(0, 6).map((column) => {
      const values = (numericVectors.get(column) ?? []).filter((value): value is number => value !== null);
      return {
        column,
        kind: "numeric" as const,
        bins: buildNumericDistribution(values),
      };
    }),
    ...[...categoricalColumns, ...booleanColumns, ...groupKeyColumns].slice(0, 8).map((column) => ({
      column,
      kind: "categorical" as const,
      bins: buildCategoricalDistribution(nonMissingByColumn.get(column) ?? []),
    })),
  ].filter((distribution) => distribution.bins.length > 0);

  const correlationTopPairs: CorrelationPair[] = [];
  for (let leftIndex = 0; leftIndex < numericColumns.length; leftIndex += 1) {
    const leftColumn = numericColumns[leftIndex];
    for (let rightIndex = leftIndex + 1; rightIndex < numericColumns.length; rightIndex += 1) {
      const rightColumn = numericColumns[rightIndex];
      const correlation = pearsonCorrelation(
        numericVectors.get(leftColumn) ?? [],
        numericVectors.get(rightColumn) ?? [],
      );
      if (correlation == null || Number.isNaN(correlation)) {
        continue;
      }
      correlationTopPairs.push({
        left: leftColumn,
        right: rightColumn,
        value: Number(correlation.toFixed(3)),
      });
    }
  }
  correlationTopPairs.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  const outlierSummaries: OutlierSummary[] = numericColumnStats
    .map((stat) => {
      const values = (numericVectors.get(stat.column) ?? []).filter((value): value is number => value !== null);
      const lowerBound = stat.q1 - 1.5 * (stat.q3 - stat.q1);
      const upperBound = stat.q3 + 1.5 * (stat.q3 - stat.q1);
      const outlierCount = values.filter((value) => value < lowerBound || value > upperBound).length;

      return {
        column: stat.column,
        outlierCount,
        outlierRate: values.length > 0 ? outlierCount / values.length : 0,
        lowerBound: toRoundedMetric(lowerBound),
        upperBound: toRoundedMetric(upperBound),
      };
    })
    .sort((a, b) => b.outlierCount - a.outlierCount);

  const topMissing = missingColumns[0];
  const recommendation = buildRecommendation(
    topMissing ?? null,
    numericColumns,
    categoricalColumns,
    datetimeColumns,
    booleanColumns,
    numericVectors,
    nonMissingByColumn,
    numericColumnStats,
  );

  const topCorrelation = correlationTopPairs[0];
  const topOutlier = outlierSummaries.find((item) => item.outlierCount > 0) ?? null;
  const sampleRows = rows.slice(0, 5).map((row) => {
    const normalized: Record<string, string | null> = {};
    columns.forEach((column) => {
      normalized[column] = row[column] ?? null;
    });
    return normalized;
  });

  const qualitySummary = [
    `전체 ${rows.length.toLocaleString()} rows / ${columns.length.toLocaleString()} columns입니다.`,
    `numeric ${numericColumns.length}개, categorical ${categoricalColumns.length}개, boolean ${booleanColumns.length}개, datetime ${datetimeColumns.length}개, group key ${groupKeyColumns.length}개로 분류했습니다.`,
    recommendation
      ? `${recommendation.column} 컬럼 결측 ${recommendation.missingCount.toLocaleString()}건(${recommendation.missingPercent}%)이 있어 질문 전 전처리 검토가 필요합니다.`
      : "치명적인 결측 이슈는 크지 않아 바로 질문 기반 Deep EDA로 이어갈 수 있습니다.",
    topCorrelation
      ? `${topCorrelation.left}와 ${topCorrelation.right}의 Pearson 상관계수는 ${topCorrelation.value}입니다.`
      : "numeric 컬럼 간 상관관계는 아직 뚜렷한 TOP pair가 없습니다.",
  ].join(" ");

  const summaryBullets = [
    `전체 ${rows.length.toLocaleString()} rows / ${columns.length.toLocaleString()} columns이며, group key는 ${groupKeyColumns.length > 0 ? groupKeyColumns.slice(0, 2).join(", ") : "미탐지"} 상태입니다.`,
    recommendation
      ? `${recommendation.column} 결측을 ${recommendation.strategy}로 보정하면 이후 Deep EDA 해석이 더 안정적입니다.`
      : "결측률이 큰 컬럼이 없어 Deep EDA를 바로 진행해도 되는 상태입니다.",
    topCorrelation
      ? `상관관계 TOP 1은 ${topCorrelation.left} ↔ ${topCorrelation.right} (${topCorrelation.value})입니다.`
      : "상관관계 TOP 분석은 numeric 컬럼이 더 필요하거나 변동성이 더 커야 의미가 생깁니다.",
    topOutlier
      ? `이상치가 가장 많은 컬럼은 ${topOutlier.column}이며 ${topOutlier.outlierCount.toLocaleString()}건(${(topOutlier.outlierRate * 100).toFixed(2)}%)입니다.`
      : "IQR 기준으로 눈에 띄는 이상치 컬럼은 아직 크지 않습니다.",
  ];

  return {
    sourceLabel: file.name,
    uploadedAt,
    rowCount: rows.length,
    columnCount: columns.length,
    columns,
    sampleRows,
    numericColumns,
    categoricalColumns,
    datetimeColumns,
    identifierColumns,
    booleanColumns,
    groupKeyColumns,
    groupKeyCandidates: groupKeyColumns,
    columnRoleSummaries,
    missingColumns,
    topMissingColumns,
    numericSnapshots,
    numericColumnStats,
    distributions,
    correlationTopPairs: correlationTopPairs.slice(0, 3),
    outlierSummaries,
    qualitySummary,
    summaryBullets,
    serverRecommendation: null,
    recommendation,
  };
}
