import { Loader2 } from 'lucide-react';

import { Progress } from '../ui/progress';

export type PipelinePhase =
  | 'idle'
  | 'thinking'
  | 'analyzing'
  | 'preprocessing'
  | 'visualizing'
  | 'searching'
  | 'reporting';

interface PipelineProgressProps {
  phase: PipelinePhase;
  progress: number;
}

const PHASE_LABELS: Record<PipelinePhase, string> = {
  idle: '대기 중',
  thinking: '질의 해석',
  analyzing: '데이터 분석',
  preprocessing: '전처리 실행',
  visualizing: '시각화 생성',
  searching: '문서 검색',
  reporting: '리포트 작성',
};

function clampProgress(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}

export function PipelineProgress({ phase, progress }: PipelineProgressProps) {
  const safe = clampProgress(progress);
  const percent = Math.round(safe * 100);

  return (
    <div className="rounded-[var(--genui-card-radius)] border border-genui-border bg-genui-running-bg p-3">
      <div className="mb-2 flex items-center justify-between gap-2 text-xs">
        <span className="inline-flex items-center gap-1.5 text-genui-running">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          {PHASE_LABELS[phase]}
        </span>
        <span className="tabular-nums text-zinc-700">{percent}%</span>
      </div>
      <Progress value={percent} className="h-1.5" />
    </div>
  );
}
