import type {
  ChatResponse,
  EvidencePackagePayload,
  EvidenceWarningPayload,
} from "../../lib/api";
import type {
  EvidenceDetailItem,
  EvidenceFooterProps,
} from "../components/genui/EvidenceFooter";

export interface EvidenceThoughtStep {
  readonly phase: string;
  readonly displayMessage?: string;
}

export interface BuildEvidenceFooterInput {
  readonly chatResponse: ChatResponse | null;
  readonly selectedFileName: string | undefined;
  readonly uploadedDatasetCount: number;
  readonly elapsedLabel: string;
  readonly thoughtSteps: readonly EvidenceThoughtStep[];
}

const METRIC_LABELS: Record<string, string> = {
  mean: "평균",
  sum: "합계",
  min: "최솟값",
  max: "최댓값",
  median: "중앙값",
  ratio: "비율",
  value_counts: "값 분포",
  top: "최빈값",
  correlation: "상관계수",
};

export function buildEvidenceFooterProps(
  input: BuildEvidenceFooterInput,
): EvidenceFooterProps {
  const evidencePackage = input.chatResponse?.evidence_package;
  const answerQuality = input.chatResponse?.answer_quality;
  const usedColumns = normalizeTextList(evidencePackage?.used_columns);
  const metricName = readText(evidencePackage?.analysis_metrics, "metric");
  const computeStatus = firstText(
    answerQuality?.status,
    evidencePackage?.analysis_quality_status,
    evidencePackage?.analysis_status,
  );
  const statusLabel = formatStatus(computeStatus);
  const data = firstText(evidencePackage?.filename, input.selectedFileName) ?? "-";
  const warningCount = Math.max(
    evidencePackage?.warnings?.length ?? 0,
    answerQuality?.warnings?.length ?? 0,
  );
  const ragCount = evidencePackage?.rag_retrieved_count;
  const guidelineCount = evidencePackage?.guideline_retrieved_count;
  const details = buildEvidenceDetails({
    evidencePackage,
    data,
    usedColumns,
    uploadedDatasetCount: input.uploadedDatasetCount,
    statusLabel,
    metricName,
    elapsedLabel: input.elapsedLabel,
    thoughtSteps: input.thoughtSteps,
    warnings: [
      ...(evidencePackage?.warnings ?? []),
      ...(answerQuality?.warnings ?? []),
    ],
    abstainReason: answerQuality?.abstain_reason,
  });

  return {
    data,
    scope: usedColumns.length > 0
      ? formatColumnValue(usedColumns)
      : formatFileScope(input.uploadedDatasetCount),
    compute: metricName
      ? `${formatMetricLabel(metricName)} · ${statusLabel}`
      : warningCount > 0
        ? `${statusLabel} · 한계 ${warningCount}개`
        : `${statusLabel} · ${input.elapsedLabel}`,
    rag: formatReferenceValue({
      ragCount,
      guidelineCount,
      thoughtSteps: input.thoughtSteps,
    }),
    details,
  };
}

function buildEvidenceDetails({
  evidencePackage,
  data,
  usedColumns,
  uploadedDatasetCount,
  statusLabel,
  metricName,
  elapsedLabel,
  thoughtSteps,
  warnings,
  abstainReason,
}: {
  readonly evidencePackage: EvidencePackagePayload | undefined;
  readonly data: string;
  readonly usedColumns: readonly string[];
  readonly uploadedDatasetCount: number;
  readonly statusLabel: string;
  readonly metricName: string | null;
  readonly elapsedLabel: string;
  readonly thoughtSteps: readonly EvidenceThoughtStep[];
  readonly warnings: readonly EvidenceWarningPayload[];
  readonly abstainReason: string | undefined;
}): readonly EvidenceDetailItem[] {
  return [
    {
      label: "데이터",
      value: data,
      description: evidencePackage
        ? "백엔드가 최종 답변 근거로 표시한 데이터셋입니다."
        : "현재 선택된 데이터셋을 기준으로 표시합니다.",
    },
    {
      label: "분석 범위",
      value: usedColumns.length > 0
        ? formatColumnValue(usedColumns)
        : formatFileScope(uploadedDatasetCount),
      description: usedColumns.length > 0
        ? `${formatList(usedColumns)} 컬럼만 계산에 반영했습니다.`
        : "답변 payload에 사용 컬럼 정보가 없어 파일 단위 범위만 확인됩니다. 정보가 부족하여 계산 컬럼은 정확하지 않을 수 있습니다.",
    },
    {
      label: "계산 근거",
      value: metricName
        ? `${formatMetricLabel(metricName)} · ${statusLabel}`
        : `${statusLabel} · ${elapsedLabel}`,
      description: firstText(
        summarizeAnalysisMetrics(
          evidencePackage?.analysis_metrics,
          evidencePackage?.analysis_table,
        ),
        evidencePackage?.analysis_summary,
        evidencePackage?.analysis_quality_reason,
        abstainReason,
      ) ?? "계산 세부 근거가 충분하지 않습니다. 정보가 부족하여 이 부분은 정확하지 않을 수 있습니다.",
    },
    {
      label: "참고와 한계",
      value: formatReferenceValue({
        ragCount: evidencePackage?.rag_retrieved_count,
        guidelineCount: evidencePackage?.guideline_retrieved_count,
        thoughtSteps,
      }),
      description: firstText(
        evidencePackage?.rag_evidence_summary,
        evidencePackage?.guideline_evidence_summary,
        firstWarningMessage(warnings),
      ) ?? "검색 문서나 가이드라인 근거는 사용하지 않았습니다. 원인 판단은 추가 정보가 부족하여 정확하지 않을 수 있습니다.",
    },
  ];
}

function summarizeAnalysisMetrics(
  analysis_metrics: Record<string, unknown> | undefined,
  analysisTable: readonly Record<string, unknown>[] | undefined,
): string | null {
  const total = readNumber(analysis_metrics, "total");
  const normalCount = readNumber(analysis_metrics, "normal_count");
  const defectCount = readNumber(analysis_metrics, "defect_count");
  const defectRate = readNumber(analysis_metrics, "defect_rate_pct");
  if (
    total !== null &&
    normalCount !== null &&
    defectCount !== null &&
    defectRate !== null
  ) {
    return `총 ${formatInteger(total)}건 중 정상 ${formatInteger(normalCount)}건, 불량 ${formatInteger(defectCount)}건, 불량률 ${formatPercentValue(defectRate)}를 계산했습니다.`;
  }

  const metricName = readText(analysis_metrics, "metric");
  if (total !== null && metricName) {
    return `총 ${formatInteger(total)}건을 기준으로 ${formatMetricLabel(metricName)}을 계산했습니다.`;
  }

  const tableSummary = summarizeAnalysisTable(analysisTable);
  if (tableSummary) {
    return tableSummary;
  }

  return null;
}

function summarizeAnalysisTable(
  analysisTable: readonly Record<string, unknown>[] | undefined,
): string | null {
  if (!analysisTable || analysisTable.length === 0) {
    return null;
  }

  const rows = analysisTable
    .slice(0, 3)
    .map((row) => {
      const value = firstText(readText(row, "value"), readText(row, "group")) ?? "-";
      const count = readNumber(row, "count");
      const ratio = readNumber(row, "ratio");
      if (count !== null && ratio !== null) {
        return `${value}: ${formatInteger(count)}건(${formatRatioValue(ratio)})`;
      }
      if (count !== null) {
        return `${value}: ${formatInteger(count)}건`;
      }
      return value;
    });

  return rows.length > 0 ? `상위 결과는 ${rows.join(", ")}입니다.` : null;
}

function normalizeTextList(value: readonly string[] | undefined): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => item.trim()).filter((item) => item.length > 0);
}

function firstText(
  ...values: readonly (string | null | undefined)[]
): string | null {
  for (const value of values) {
    const text = value?.trim();
    if (text) {
      return text;
    }
  }
  return null;
}

function readNumber(
  record: Record<string, unknown> | undefined,
  key: string,
): number | null {
  const value = record?.[key];
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return null;
}

function readText(
  record: Record<string, unknown> | undefined,
  key: string,
): string | null {
  const value = record?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function firstWarningMessage(
  warnings: readonly EvidenceWarningPayload[],
): string | null {
  for (const warning of warnings) {
    const message = warning.message?.trim();
    if (message) {
      return message;
    }
  }
  return null;
}

function formatMetricLabel(metricName: string): string {
  return METRIC_LABELS[metricName] ?? metricName;
}

function formatStatus(status: string | null): string {
  if (status === "answerable" || status === "complete" || status === "success") {
    return "답변 가능";
  }
  if (status === "limited" || status === "partial") {
    return "제한적 답변";
  }
  if (status === "unanswerable" || status === "missing") {
    return "근거 부족";
  }
  if (status === "failed") {
    return "계산 실패";
  }
  return "계산 완료";
}

function formatColumnValue(columns: readonly string[]): string {
  if (columns.length <= 2) {
    return columns.join(", ");
  }
  return `${columns.slice(0, 2).join(", ")} 외 ${columns.length - 2}개`;
}

function formatFileScope(uploadedDatasetCount: number): string {
  return uploadedDatasetCount > 0 ? `${uploadedDatasetCount}개 파일` : "-";
}

function formatReferenceValue({
  ragCount,
  guidelineCount,
  thoughtSteps,
}: {
  readonly ragCount: number | undefined;
  readonly guidelineCount: number | undefined;
  readonly thoughtSteps: readonly EvidenceThoughtStep[];
}): string {
  if (typeof ragCount === "number" || typeof guidelineCount === "number") {
    return `데이터 ${ragCount ?? 0} / 가이드 ${guidelineCount ?? 0}`;
  }
  const ragUsed = thoughtSteps.some(
    (step) => step.phase === "rag_retrieval"
      && step.displayMessage === "질문과 관련된 참고 정보를 찾았습니다.",
  );
  return ragUsed ? "검색 근거 사용" : "추가 참고 없음";
}

function formatList(values: readonly string[]): string {
  return values.map((value) => `'${value}'`).join(", ");
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 0 }).format(value);
}

function formatPercentValue(value: number): string {
  return `${value.toFixed(2)}%`;
}

function formatRatioValue(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}
