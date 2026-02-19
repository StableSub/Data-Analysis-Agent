export type CardStatus =
  | 'idle'
  | 'queued'
  | 'running'
  | 'success'
  | 'failed'
  | 'canceled'
  | 'needs_user';

export type Severity = 'info' | 'warning' | 'error' | 'success';

export type CardAction =
  | { type: 'pin'; label?: string }
  | { type: 'unpin'; label?: string }
  | { type: 'add_to_report'; label?: string; payload?: unknown }
  | { type: 'view_log'; label?: string; runId?: string }
  | { type: 'open_artifact'; label?: string; artifactId?: string }
  | { type: 'retry'; label?: string; runId?: string }
  | { type: 'cancel'; label?: string; runId?: string }
  | { type: 'apply'; label?: string; payload?: unknown }
  | { type: 'edit'; label?: string; payload?: unknown }
  | { type: 'dismiss'; label?: string };

export interface BaseCardProps {
  cardId: string;
  cardType: CardType;
  title: string;
  sessionId: string;
  threadId?: string;
  userId?: string;
  workspaceId?: string;
  source: {
    kind: 'dataset' | 'document' | 'pipeline' | 'run' | 'report' | 'mixed';
    datasetId?: string;
    fileId?: string;
    indexId?: string;
    runId?: string;
  };
  status: CardStatus;
  severity?: Severity;
  subtitle?: string;
  createdAt?: string;
  updatedAt?: string;
  summary?: string;
  badges?: Array<{ label: string; tone?: Severity }>;
  actions?: CardAction[];
  details?: Array<{
    label: string;
    contentType: 'markdown' | 'json';
    content: string | object;
    defaultOpen?: boolean;
  }>;
}

export interface DatasetSummaryCardProps extends BaseCardProps {
  cardType: 'dataset_summary';
  dataset: {
    datasetId: string;
    name: string;
    fileType: 'csv' | 'xlsx' | 'parquet' | 'json' | 'unknown';
    sizeBytes?: number;
    rows?: number;
    cols?: number;
    sampleStrategy?: { kind: 'head' | 'random'; n: number };
  };
  schema?: {
    columns: Array<{
      name: string;
      dtype: 'int' | 'float' | 'bool' | 'string' | 'datetime' | 'category' | 'unknown';
      nonNullCount?: number;
      missingCount?: number;
      missingRate?: number;
      exampleValues?: string[];
      cardinality?: number;
    }>;
  };
  quality?: {
    missingRateTotal?: number;
    duplicateRowCount?: number;
    outlierHint?: { method: 'iqr' | 'zscore'; count?: number; columns?: string[] };
    datetimeHint?: { hasDatetime: boolean; columns?: string[]; inferredFreq?: string };
  };
  preview?: {
    columns: string[];
    rows: Array<Record<string, unknown>>;
    truncated?: boolean;
  };
  recommendedNext?: Array<{
    kind: 'preprocess_plan' | 'visualize' | 'rag_ingest' | 'report';
    label: string;
    promptHint?: string;
  }>;
}

export type PreprocessStepType =
  | 'parse_datetime'
  | 'rename_columns'
  | 'type_cast'
  | 'handle_missing'
  | 'remove_duplicates'
  | 'outlier_treatment'
  | 'scaling'
  | 'encoding'
  | 'resampling'
  | 'feature_engineering';

export interface PreprocessPlanCardProps extends BaseCardProps {
  cardType: 'preprocess_plan';
  plan: {
    planId: string;
    datasetId: string;
    rationale?: string;
    steps: Array<{
      stepId: string;
      type: PreprocessStepType;
      title: string;
      why: string;
      risk?: string;
      enabled: boolean;
      params: Record<string, unknown>;
      expectedImpact?: {
        rowsChange?: 'increase' | 'decrease' | 'unknown';
        colsChange?: 'increase' | 'decrease' | 'unknown';
        qualityGain?: Array<'missing' | 'types' | 'outliers' | 'duplicates'>;
      };
    }>;
  };
  editable?: {
    allowToggleSteps: boolean;
    allowParamEdit: boolean;
    paramEditWhitelist?: string[];
  };
  apply?: {
    dryRunSupported?: boolean;
    onApplyAction?: CardAction;
    onEditAction?: CardAction;
  };
}

export interface PipelineRunCardProps extends BaseCardProps {
  cardType: 'pipeline_run';
  run: {
    runId: string;
    datasetId: string;
    planId?: string;
    startedAt?: string;
    finishedAt?: string;
    elapsedMs?: number;
    progress?: { currentStep?: number; totalSteps?: number; message?: string };
  };
  result?: {
    outputDatasetId?: string;
    rowCountBefore?: number;
    rowCountAfter?: number;
    colCountBefore?: number;
    colCountAfter?: number;
    warnings?: string[];
    errors?: string[];
  };
  previewDiff?: {
    before?: { columns: string[]; rows: Array<Record<string, unknown>>; truncated?: boolean };
    after?: { columns: string[]; rows: Array<Record<string, unknown>>; truncated?: boolean };
  };
  artifacts?: Array<{
    artifactId: string;
    kind: 'table' | 'json' | 'html' | 'image' | 'file';
    label: string;
    mimeType?: string;
    uri?: string;
  }>;
}

export interface ChartCardProps extends BaseCardProps {
  cardType: 'chart';
  chart: {
    chartId: string;
    datasetId: string;
    title?: string;
    chartType: 'line' | 'bar' | 'scatter' | 'hist' | 'box' | 'heatmap' | 'area' | 'table';
    spec?: {
      x?: string;
      y?: string | string[];
      color?: string;
      facet?: string;
      aggregation?: string;
      filters?: Record<string, unknown>;
    };
    summaryMessage?: string;
  };
  artifact: {
    artifactId: string;
    kind: 'image' | 'html';
    mimeType: string;
    uri: string;
    width?: number;
    height?: number;
  };
  codeRef?: {
    runId: string;
    available: boolean;
  };
}

export interface RAGIngestCardProps extends BaseCardProps {
  cardType: 'rag_ingest';
  ingest: {
    indexId: string;
    fileId: string;
    filename: string;
    splitPolicy: { name: 'recursive'; chunkSize: number; chunkOverlap: number };
    embeddingModel: { provider: string; name: string };
    cache: { hit: boolean; cacheKey: string };
    stages: Array<{
      name: 'load' | 'split' | 'embed' | 'store';
      status: CardStatus;
      message?: string;
      metrics?: Record<string, number>;
    }>;
  };
  documents?: {
    totalPages?: number;
    totalChunks?: number;
    sources?: Array<{ source: string; pages?: number }>;
  };
}

export interface DocumentIndexCardProps extends BaseCardProps {
  cardType: 'doc_index';
  index: {
    indexId: string;
    name: string;
    embeddingModel: { provider: string; name: string };
    splitPolicy: { name: 'recursive'; chunkSize: number; chunkOverlap: number };
    createdAt?: string;
    updatedAt?: string;
  };
  corpus: {
    files: Array<{
      fileId: string;
      filename: string;
      pages?: number;
      chunks?: number;
    }>;
    totalFiles: number;
    totalChunks?: number;
  };
  controls?: {
    setActiveAction?: CardAction;
    testRetrievalAction?: CardAction;
  };
}

export interface RetrievalEvidenceCardProps extends BaseCardProps {
  cardType: 'retrieval_evidence';
  retrieval: {
    indexId: string;
    query: string;
    topK: number;
    latencyMs?: number;
  };
  chunks: Array<{
    chunkId: string;
    score?: number;
    text: string;
    source: { fileId: string; filename: string; page?: number; uri?: string };
    spans?: Array<{ start: number; end: number }>;
  }>;
  citationPolicy?: {
    requireCitationsInAnswer: boolean;
    citationFormat: 'source_page' | 'inline';
  };
}

export type ReportSectionKind =
  | 'exec_summary'
  | 'data_overview'
  | 'preprocessing'
  | 'visualizations'
  | 'rag_evidence'
  | 'conclusions'
  | 'appendix';

export interface ReportBuilderCardProps extends BaseCardProps {
  cardType: 'report_builder';
  report: {
    reportId: string;
    title: string;
    subtitle?: string;
    sections: Array<{
      sectionId: string;
      kind: ReportSectionKind;
      title: string;
      included: boolean;
      description?: string;
      items?: Array<{
        refType: 'card' | 'artifact';
        refId: string;
        label?: string;
      }>;
    }>;
  };
  exportOptions: {
    formats: Array<'pdf' | 'html' | 'md'>;
    defaultFormat: 'pdf' | 'html' | 'md';
    includeRawData?: boolean;
    theme?: 'light' | 'dark';
  };
  exportAction: CardAction;
}

export interface ErrorCardProps extends BaseCardProps {
  cardType: 'error_card';
  error: {
    failedStep: string;
    reason: string;
    originalCardType?: CardType;
    retryAction?: CardAction;
  };
}

export const CARD_TYPES = [
  'dataset_summary',
  'preprocess_plan',
  'pipeline_run',
  'chart',
  'rag_ingest',
  'doc_index',
  'retrieval_evidence',
  'report_builder',
  'error_card',
] as const;

export type CardType = (typeof CARD_TYPES)[number];

export type WorkbenchCardProps =
  | DatasetSummaryCardProps
  | PreprocessPlanCardProps
  | PipelineRunCardProps
  | ChartCardProps
  | RAGIngestCardProps
  | DocumentIndexCardProps
  | RetrievalEvidenceCardProps
  | ReportBuilderCardProps
  | ErrorCardProps;
