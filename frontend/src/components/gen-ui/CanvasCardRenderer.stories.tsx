import type { Meta, StoryObj } from '@storybook/react-vite';

import { CanvasCardRenderer } from './CanvasCardRenderer';
import type {
  ChartCardProps,
  DatasetSummaryCardProps,
  DocumentIndexCardProps,
  ErrorCardProps,
  PipelineRunCardProps,
  PreprocessPlanCardProps,
  RAGIngestCardProps,
  ReportBuilderCardProps,
  RetrievalEvidenceCardProps,
  WorkbenchCardProps,
} from './types';

const now = new Date().toISOString();

const datasetSummaryCard: DatasetSummaryCardProps = {
  cardId: 'card-dataset-summary-1',
  cardType: 'dataset_summary',
  title: 'Dataset Summary',
  subtitle: 'production_line_a.csv 자동 프로파일링',
  sessionId: 'session-storybook',
  source: { kind: 'dataset', datasetId: 'ds-100', fileId: 'file-100', runId: 'run-ds-100' },
  status: 'success',
  summary: '결측치/중복/스키마 정보를 기준으로 다음 단계를 추천했습니다.',
  dataset: {
    datasetId: 'ds-100',
    name: 'production_line_a.csv',
    fileType: 'csv',
    rows: 1482,
    cols: 12,
  },
  schema: {
    columns: [
      { name: 'timestamp', dtype: 'datetime', missingRate: 0, cardinality: 1200 },
      { name: 'line_id', dtype: 'category', missingRate: 0, cardinality: 8 },
      { name: 'defect_rate', dtype: 'float', missingRate: 0.021, cardinality: 843 },
      { name: 'temperature', dtype: 'float', missingRate: 0.005, cardinality: 994 },
    ],
  },
  quality: {
    missingRateTotal: 0.018,
    duplicateRowCount: 7,
  },
  preview: {
    columns: ['timestamp', 'line_id', 'defect_rate'],
    rows: [
      { timestamp: '2026-02-10 08:00:00', line_id: 'L1', defect_rate: 0.012 },
      { timestamp: '2026-02-10 09:00:00', line_id: 'L1', defect_rate: 0.014 },
    ],
  },
  recommendedNext: [
    { kind: 'preprocess_plan', label: '전처리 계획 생성' },
    { kind: 'visualize', label: '핵심 지표 시각화' },
    { kind: 'report', label: '리포트 초안 만들기' },
  ],
  actions: [{ type: 'add_to_report', label: '리포트에 추가' }, { type: 'dismiss', label: '닫기' }],
  createdAt: now,
};

const preprocessPlanCard: PreprocessPlanCardProps = {
  cardId: 'card-preprocess-plan-1',
  cardType: 'preprocess_plan',
  title: 'Preprocess Plan',
  subtitle: '결측치/타입/이상치 정리 제안',
  sessionId: 'session-storybook',
  source: { kind: 'pipeline', datasetId: 'ds-100', runId: 'run-pre-100' },
  status: 'needs_user',
  summary: '파이프라인 적용 전 단계별 리스크를 검토하세요.',
  plan: {
    planId: 'plan-100',
    datasetId: 'ds-100',
    rationale: '결측치와 타입 이슈를 먼저 처리하면 후속 시각화 정확도가 높아집니다.',
    steps: [
      {
        stepId: 'step-1',
        type: 'handle_missing',
        title: 'Handle Missing Values',
        why: '결측치가 차트 왜곡을 유발할 수 있습니다.',
        enabled: true,
        params: { strategy: 'median' },
      },
      {
        stepId: 'step-2',
        type: 'type_cast',
        title: 'Normalize Column Types',
        why: '수치/날짜 파싱 실패를 방지합니다.',
        enabled: true,
        params: { strict: false },
      },
      {
        stepId: 'step-3',
        type: 'outlier_treatment',
        title: 'Outlier Treatment',
        why: '극단값 영향도를 낮춥니다.',
        enabled: false,
        params: { method: 'iqr' },
        risk: '과도한 제거 시 유효 신호 손실 위험',
      },
    ],
  },
  actions: [
    { type: 'apply', label: '적용' },
    { type: 'edit', label: '고급 전처리' },
    { type: 'dismiss', label: '닫기' },
  ],
  createdAt: now,
};

const pipelineRunCard: PipelineRunCardProps = {
  cardId: 'card-pipeline-run-1',
  cardType: 'pipeline_run',
  title: 'Pipeline Run',
  subtitle: '전처리 실행 결과',
  sessionId: 'session-storybook',
  source: { kind: 'run', datasetId: 'ds-100', runId: 'run-pre-100' },
  status: 'success',
  run: {
    runId: 'run-pre-100',
    datasetId: 'ds-100',
    progress: {
      currentStep: 3,
      totalSteps: 3,
      message: '모든 단계 완료',
    },
  },
  result: {
    rowCountBefore: 1482,
    rowCountAfter: 1475,
    colCountBefore: 12,
    colCountAfter: 12,
    warnings: ['line_id 결측치 3건 보정'],
  },
  artifacts: [
    { artifactId: 'artifact-cleaned-preview', kind: 'table', label: 'Cleaned Preview' },
    { artifactId: 'artifact-log', kind: 'json', label: 'Run Log' },
  ],
  actions: [{ type: 'view_log', label: '실행 로그' }, { type: 'dismiss', label: '닫기' }],
  createdAt: now,
};

const chartCard: ChartCardProps = {
  cardId: 'card-chart-1',
  cardType: 'chart',
  title: 'Visualization Result',
  subtitle: '결함률 추이 라인 차트',
  sessionId: 'session-storybook',
  source: { kind: 'dataset', datasetId: 'ds-100', runId: 'run-chart-100' },
  status: 'success',
  chart: {
    chartId: 'chart-100',
    datasetId: 'ds-100',
    title: 'Defect Rate Trend',
    chartType: 'line',
    spec: { x: 'timestamp', y: 'defect_rate' },
  },
  artifact: {
    artifactId: 'artifact-chart-image',
    kind: 'image',
    mimeType: 'image/png',
    uri: 'https://dummyimage.com/1200x520/e5e7eb/111827&text=Defect+Rate+Trend',
    width: 1200,
    height: 520,
  },
  codeRef: { runId: 'run-chart-100', available: true },
  actions: [{ type: 'add_to_report', label: '리포트에 추가' }, { type: 'dismiss', label: '닫기' }],
  createdAt: now,
};

const ragIngestCard: RAGIngestCardProps = {
  cardId: 'card-rag-ingest-1',
  cardType: 'rag_ingest',
  title: 'RAG Ingest',
  subtitle: '문서 인덱싱 완료',
  sessionId: 'session-storybook',
  source: { kind: 'document', fileId: 'doc-1', runId: 'run-rag-ingest-1' },
  status: 'success',
  ingest: {
    indexId: 'idx-100',
    fileId: 'doc-1',
    filename: 'quality_manual.pdf',
    splitPolicy: { name: 'recursive', chunkSize: 800, chunkOverlap: 120 },
    embeddingModel: { provider: 'openai', name: 'text-embedding-3-small' },
    cache: { hit: false, cacheKey: 'cache-idx-100' },
    stages: [
      { name: 'load', status: 'success', message: '문서 로드' },
      { name: 'split', status: 'success', message: '청크 분할' },
      { name: 'embed', status: 'success', message: '임베딩 생성' },
      { name: 'store', status: 'success', message: '벡터 저장' },
    ],
  },
  documents: {
    totalPages: 14,
    totalChunks: 68,
  },
  createdAt: now,
};

const docIndexCard: DocumentIndexCardProps = {
  cardId: 'card-doc-index-1',
  cardType: 'doc_index',
  title: 'Document Index',
  subtitle: '활성 인덱스 메타데이터',
  sessionId: 'session-storybook',
  source: { kind: 'document', indexId: 'idx-100', runId: 'run-doc-index-1' },
  status: 'success',
  index: {
    indexId: 'idx-100',
    name: 'Main Knowledge Index',
    embeddingModel: { provider: 'openai', name: 'text-embedding-3-small' },
    splitPolicy: { name: 'recursive', chunkSize: 800, chunkOverlap: 120 },
  },
  corpus: {
    totalFiles: 2,
    totalChunks: 120,
    files: [
      { fileId: 'doc-1', filename: 'quality_manual.pdf', pages: 14, chunks: 68 },
      { fileId: 'doc-2', filename: 'inspection_guideline.pdf', pages: 11, chunks: 52 },
    ],
  },
  createdAt: now,
};

const retrievalEvidenceCard: RetrievalEvidenceCardProps = {
  cardId: 'card-retrieval-evidence-1',
  cardType: 'retrieval_evidence',
  title: 'Retrieval Evidence',
  subtitle: '문서 근거 검색 결과',
  sessionId: 'session-storybook',
  source: { kind: 'document', indexId: 'idx-100', runId: 'run-retrieve-1' },
  status: 'success',
  retrieval: {
    indexId: 'idx-100',
    query: '허용 결함률 기준',
    topK: 2,
    latencyMs: 48,
  },
  chunks: [
    {
      chunkId: 'chunk-a',
      score: 0.92,
      text: '제품군 A의 허용 결함률은 1.5% 이하이며 초과 시 재검수 절차를 개시한다.',
      source: { fileId: 'doc-1', filename: 'quality_manual.pdf', page: 12 },
    },
    {
      chunkId: 'chunk-b',
      score: 0.88,
      text: '라인 경고 임계치는 1.2%로 정의하며 지속 초과 시 운영자 알림을 전송한다.',
      source: { fileId: 'doc-1', filename: 'quality_manual.pdf', page: 13 },
    },
  ],
  actions: [{ type: 'add_to_report', label: '리포트에 추가' }, { type: 'dismiss', label: '닫기' }],
  createdAt: now,
};

const reportBuilderCard: ReportBuilderCardProps = {
  cardId: 'card-report-builder-1',
  cardType: 'report_builder',
  title: 'Report Builder',
  subtitle: '리포트 조립 초안',
  sessionId: 'session-storybook',
  source: { kind: 'report', runId: 'run-report-1' },
  status: 'needs_user',
  report: {
    reportId: 'report-100',
    title: 'Quality Analysis Report',
    sections: [
      { sectionId: 'sec-1', kind: 'exec_summary', title: 'Executive Summary', included: true },
      { sectionId: 'sec-2', kind: 'preprocessing', title: 'Preprocessing', included: true },
      { sectionId: 'sec-3', kind: 'visualizations', title: 'Visualizations', included: true },
      { sectionId: 'sec-4', kind: 'rag_evidence', title: 'Evidence', included: false },
    ],
  },
  exportOptions: {
    formats: ['pdf', 'html', 'md'],
    defaultFormat: 'pdf',
    theme: 'light',
  },
  exportAction: { type: 'apply', label: 'Export PDF', payload: { format: 'pdf' } },
  actions: [{ type: 'apply', label: 'Export PDF', payload: { format: 'pdf' } }, { type: 'dismiss', label: '닫기' }],
  createdAt: now,
};

const errorCard: ErrorCardProps = {
  cardId: 'card-error-1',
  cardType: 'error_card',
  title: '도구 실행 오류',
  subtitle: '일부 단계에서 실패가 발생했습니다.',
  sessionId: 'session-storybook',
  source: { kind: 'run', runId: 'run-error-1' },
  status: 'failed',
  summary: '실패한 단계만 재시도할 수 있습니다.',
  actions: [{ type: 'retry', label: '재시도', runId: 'run-error-1' }],
  error: {
    failedStep: 'csv_visualization_workflow',
    reason: '차트 렌더러 초기화 실패',
    originalCardType: 'chart',
    retryAction: { type: 'retry', label: '재시도', runId: 'run-error-1' },
  },
  createdAt: now,
};

const allCards: WorkbenchCardProps[] = [
  datasetSummaryCard,
  preprocessPlanCard,
  pipelineRunCard,
  chartCard,
  ragIngestCard,
  docIndexCard,
  retrievalEvidenceCard,
  reportBuilderCard,
  errorCard,
];

const meta = {
  title: 'GenUI/CanvasCardRenderer',
  component: CanvasCardRenderer,
  parameters: {
    layout: 'padded',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof CanvasCardRenderer>;

export default meta;

type Story = StoryObj<typeof meta>;

export const DatasetSummary: Story = {
  args: {
    card: datasetSummaryCard,
  },
};

export const PreprocessPlan: Story = {
  args: {
    card: preprocessPlanCard,
  },
};

export const PipelineRun: Story = {
  args: {
    card: pipelineRunCard,
  },
};

export const Chart: Story = {
  args: {
    card: chartCard,
  },
};

export const RAGIngest: Story = {
  args: {
    card: ragIngestCard,
  },
};

export const DocIndex: Story = {
  args: {
    card: docIndexCard,
  },
};

export const RetrievalEvidence: Story = {
  args: {
    card: retrievalEvidenceCard,
  },
};

export const ReportBuilder: Story = {
  args: {
    card: reportBuilderCard,
  },
};

export const ErrorCard: Story = {
  args: {
    card: errorCard,
  },
};

export const AllCardsGallery: Story = {
  render: () => (
    <div className="mx-auto grid w-full max-w-6xl gap-4">
      {allCards.map((card) => (
        <CanvasCardRenderer key={card.cardId} card={card} />
      ))}
    </div>
  ),
};
