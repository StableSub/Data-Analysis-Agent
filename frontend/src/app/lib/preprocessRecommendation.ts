import type {
  EdaPreprocessRecommendation,
  EdaRecommendedOperation,
} from "../../lib/api";

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
    return derived.source_columns.some((column) => typeof column === "string" && column.trim());
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

export function buildSingleOperationRecommendation(
  operation: EdaRecommendedOperation,
): EdaPreprocessRecommendation {
  const targetColumns = operation.target_columns
    .filter((column) => typeof column === "string")
    .map((column) => column.trim())
    .filter(Boolean);

  return {
    summary: operation.reason.trim() || `${formatRecommendedOperationLabel(operation.op)} 작업을 적용합니다.`,
    operations: [
      {
        ...operation,
        target_columns: targetColumns,
        source_columns: operation.source_columns
          .filter((column) => typeof column === "string")
          .map((column) => column.trim())
          .filter(Boolean),
        target_column: operation.target_column.trim(),
      },
    ],
  };
}
