import {
  CardAction,
  DatasetSummaryCardProps,
  PreprocessPlanCardProps,
  PipelineRunCardProps,
  ChartCardProps,
  RAGIngestCardProps,
  DocumentIndexCardProps,
  RetrievalEvidenceCardProps,
  ReportBuilderCardProps,
  WorkbenchCardProps,
} from './types';
import { DatasetSummaryCard } from './DatasetSummaryCard';
import { PreprocessPlanCard } from './PreprocessPlanCard';
import { PipelineRunCard } from './PipelineRunCard';
import { ChartCard } from './ChartCard';
import { RAGIngestCard } from './RAGIngestCard';
import { DocumentIndexCard } from './DocumentIndexCard';
import { RetrievalEvidenceCard } from './RetrievalEvidenceCard';
import { ReportBuilderCard } from './ReportBuilderCard';

interface CanvasCardRendererProps {
  card: WorkbenchCardProps;
  onAction?: (card: WorkbenchCardProps, action: CardAction) => void;
}

export function CanvasCardRenderer({ card, onAction }: CanvasCardRendererProps) {
  if (card.cardType === 'dataset_summary') {
    return <DatasetSummaryCard card={card as DatasetSummaryCardProps} onAction={onAction as any} />;
  }
  if (card.cardType === 'preprocess_plan') {
    return <PreprocessPlanCard card={card as PreprocessPlanCardProps} onAction={onAction as any} />;
  }
  if (card.cardType === 'pipeline_run') {
    return <PipelineRunCard card={card as PipelineRunCardProps} onAction={onAction as any} />;
  }
  if (card.cardType === 'chart') {
    return <ChartCard card={card as ChartCardProps} onAction={onAction as any} />;
  }
  if (card.cardType === 'rag_ingest') {
    return <RAGIngestCard card={card as RAGIngestCardProps} onAction={onAction as any} />;
  }
  if (card.cardType === 'doc_index') {
    return <DocumentIndexCard card={card as DocumentIndexCardProps} onAction={onAction as any} />;
  }
  if (card.cardType === 'retrieval_evidence') {
    return <RetrievalEvidenceCard card={card as RetrievalEvidenceCardProps} onAction={onAction as any} />;
  }
  if (card.cardType === 'report_builder') {
    return <ReportBuilderCard card={card as ReportBuilderCardProps} onAction={onAction as any} />;
  }
  return null;
}
