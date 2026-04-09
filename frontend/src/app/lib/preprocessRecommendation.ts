import type {
  EdaPreprocessRecommendation,
  EdaRecommendedOperation,
  PreprocessOperation,
} from "../../lib/api";
import type { PreEdaProfile } from "./preEdaProfile";

const AUTO_APPLICABLE_OPS = new Set<EdaRecommendedOperation["op"]>([
  "drop_missing",
  "impute",
  "drop_columns",
  "scale",
  "encode_categorical",
  "outlier",
  "parse_datetime",
]);

export function formatRecommendedOperationLabel(op: EdaRecommendedOperation["op"]): string {
  switch (op) {
    case "drop_missing":
      return "결측 행 제거";
    case "impute":
      return "결측값 대체";
    case "drop_columns":
      return "컬럼 제거";
    case "scale":
      return "수치 스케일링";
    case "encode_categorical":
      return "범주형 인코딩";
    case "outlier":
      return "이상치 처리";
    case "parse_datetime":
      return "날짜형 파싱";
    case "derived_column":
      return "파생 컬럼 생성";
    default:
      return op;
  }
}

export function getRecommendedOperationKey(
  operation: EdaRecommendedOperation,
  index: number,
): string {
  const targetKey = operation.op === "derived_column"
    ? `${operation.target_column}:${operation.source_columns.join(",")}:${operation.transform_type ?? ""}`
    : operation.target_columns.join(",");
  return `${operation.op}:${targetKey}:${index}`;
}

function normalizeColumns(columns: string[]): string[] {
  return columns
    .filter((column) => typeof column === "string")
    .map((column) => column.trim())
    .filter(Boolean);
}

export function buildPreprocessOperationsFromRecommendedOperation(
  operation: EdaRecommendedOperation,
  profile: PreEdaProfile,
): PreprocessOperation[] {
  const targetColumns = normalizeColumns(operation.target_columns);

  if (operation.op === "derived_column") {
    const sourceColumns = normalizeColumns(operation.source_columns);
    const targetColumn = operation.target_column.trim();

    if (!targetColumn) {
      throw new Error("derived_column recommendation requires target_column");
    }
    if (!operation.transform_type || !["log1p", "sum", "difference", "ratio"].includes(operation.transform_type)) {
      throw new Error("derived_column recommendation requires supported transform_type");
    }
    if (sourceColumns.length === 0) {
      throw new Error("derived_column recommendation requires source_columns");
    }

    return [
      {
        op: "derived_column",
        name: targetColumn,
        source_columns: sourceColumns,
        transform_type: operation.transform_type,
        params: operation.params,
      },
    ];
  }

  if (targetColumns.length === 0) {
    throw new Error(`${operation.op} recommendation requires target_columns`);
  }

  switch (operation.op) {
    case "drop_missing":
      return [{ op: "drop_missing", columns: targetColumns, how: "any" }];
    case "impute": {
      const numericTargets = targetColumns.filter((column) => profile.numericColumns.includes(column));
      const nonNumericTargets = targetColumns.filter((column) => !profile.numericColumns.includes(column));
      const operations: PreprocessOperation[] = [];

      if (numericTargets.length > 0) {
        operations.push({
          op: "impute",
          columns: numericTargets,
          method: "median",
          value: null,
        });
      }
      if (nonNumericTargets.length > 0) {
        operations.push({
          op: "impute",
          columns: nonNumericTargets,
          method: "mode",
          value: null,
        });
      }

      return operations;
    }
    case "drop_columns":
      return [{ op: "drop_columns", columns: targetColumns }];
    case "scale":
      return [{ op: "scale", columns: targetColumns, method: "standardize" }];
    case "encode_categorical":
      return [{ op: "encode_categorical", columns: targetColumns, method: "one_hot" }];
    case "outlier":
      return [{ op: "outlier", columns: targetColumns, method: "iqr", strategy: "clip" }];
    case "parse_datetime":
      return [{ op: "parse_datetime", columns: targetColumns, format: null }];
    default:
      throw new Error(`${operation.op} recommendation is not supported`);
  }
}

export function isAutoApplicableRecommendedOperation(
  operation: EdaRecommendedOperation,
): boolean {
  if (operation.op === "derived_column") {
    const derived = operation as EdaRecommendedOperation;
    if (!derived.target_column.trim()) {
      return false;
    }
    if (!derived.transform_type || !["log1p", "sum", "difference", "ratio"].includes(derived.transform_type)) {
      return false;
    }
    const sourceColumns = derived.source_columns
      .filter((column) => typeof column === "string")
      .map((column) => column.trim())
      .filter(Boolean);
    if (sourceColumns.length === 0) {
      return false;
    }
    if (derived.transform_type === "log1p") {
      return sourceColumns.length === 1;
    }
    if (derived.transform_type === "sum") {
      return sourceColumns.length >= 2;
    }
    return sourceColumns.length === 2;
  }
  if (!AUTO_APPLICABLE_OPS.has(operation.op)) {
    return false;
  }
  return operation.target_columns.some((column) => typeof column === "string" && column.trim());
}

export function countAutoApplicableRecommendedOperations(
  recommendation: EdaPreprocessRecommendation | null | undefined,
): number {
  if (!recommendation) {
    return 0;
  }
  return recommendation.operations.filter((operation) => isAutoApplicableRecommendedOperation(operation)).length;
}
