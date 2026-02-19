import { Check, Loader2, X } from 'lucide-react';

export type ToolCallStatus = 'running' | 'completed' | 'failed';

interface ToolCallIndicatorProps {
  toolName: string;
  status: ToolCallStatus;
  error?: string;
}

const TOOL_NAME_MAP: Record<string, string> = {
  propose_preprocess_plan: '전처리 계획 생성',
  apply_preprocess_pipeline: '전처리 적용',
  csv_visualization_workflow: '시각화 생성',
  rag_ingest_pdf: '문서 인덱싱',
  retrieve_docs: '근거 검색',
  build_report_outline: '리포트 구성',
  export_report: '리포트 내보내기',
};

function labelOf(toolName: string): string {
  return TOOL_NAME_MAP[toolName] ?? toolName;
}

export function ToolCallIndicator({ toolName, status, error }: ToolCallIndicatorProps) {
  const label = labelOf(toolName);

  return (
    <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-genui-border bg-genui-idle-bg px-3 py-1.5 text-xs text-zinc-700 transition-colors duration-150 ease-out">
      {status === 'running' ? <Loader2 className="h-3.5 w-3.5 animate-spin text-genui-running" /> : null}
      {status === 'completed' ? <Check className="h-3.5 w-3.5 text-genui-success" /> : null}
      {status === 'failed' ? <X className="h-3.5 w-3.5 text-genui-error" /> : null}

      <span className="truncate font-medium">{label}</span>
      {status === 'failed' && error ? <span className="max-w-[220px] truncate text-genui-error">{error}</span> : null}
    </div>
  );
}
