import { type ComponentType, useEffect, useMemo, useRef, useState } from 'react';
import {
  BarChart3,
  Bot,
  Check,
  Database,
  FileText,
  FolderUp,
  Loader2,
  Pencil,
  Plus,
  Search,
  Send,
  Sparkles,
  Trash2,
  Wand2,
  X,
} from 'lucide-react';
import { toast } from 'sonner';

import { CanvasCardRenderer } from '../gen-ui';
import type { CardAction, WorkbenchCardProps } from '../gen-ui';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { ScrollArea } from '../ui/scroll-area';
import { Textarea } from '../ui/textarea';

export type CanvasWorkflow = 'preprocess' | 'visualization' | 'rag' | 'report';

type SessionFile = {
  id: string;
  name: string;
  type: 'dataset' | 'document';
  size: number;
  selected?: boolean;
};

type SessionSummary = {
  id: string;
  title: string;
  updatedAt: Date | string;
  messageCount: number;
};

type SessionMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date | string;
};

interface AgenticCanvasPanelProps {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  messages: SessionMessage[];
  files: SessionFile[];
  onOpenUpload: () => void;
  onUploadFile: (file: File, type: 'dataset' | 'document') => Promise<void> | void;
  onNewSession: () => void;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, title: string) => void;
  onToggleFile: (fileId: string) => void;
  onRemoveFile: (fileId: string) => void;
  onAddMessage: (sessionId: string, role: 'user' | 'assistant', content: string) => void;
}

type WorkflowMeta = {
  label: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  prompt: string;
  assistantReply: string;
};

type SessionCardItem = {
  id: string;
  createdAt: string;
  type: 'card';
  card: WorkbenchCardProps;
};

type SessionRecommendationItem = {
  id: string;
  createdAt: string;
  type: 'recommendations';
  datasetFileId: string;
  fileName: string;
};

type SessionArtifactItem = SessionCardItem | SessionRecommendationItem;

type RenderableTimelineItem =
  | {
      key: string;
      createdAt: string;
      type: 'message';
      message: SessionMessage;
    }
  | {
      key: string;
      createdAt: string;
      type: 'artifact';
      artifact: SessionArtifactItem;
    };

const WORKFLOWS: Record<CanvasWorkflow, WorkflowMeta> = {
  preprocess: {
    label: 'Preprocess',
    description: '결측/타입/중복을 정리합니다',
    icon: Wand2,
    prompt: '업로드한 데이터셋 전처리 계획을 제안해줘.',
    assistantReply: '전처리 계획을 생성했습니다. 적용 전에 핵심 리스크를 같이 확인해보세요.',
  },
  visualization: {
    label: 'Visualization',
    description: '질문 의도 기반 차트를 생성합니다',
    icon: BarChart3,
    prompt: '핵심 지표를 시각화해서 보여줘.',
    assistantReply: '주요 차트를 준비했습니다. 리포트에 추가할 차트도 바로 선택할 수 있습니다.',
  },
  rag: {
    label: 'RAG',
    description: '문서 근거를 검색합니다',
    icon: Search,
    prompt: '문서에서 근거를 찾아 답변해줘.',
    assistantReply: '문서 근거를 검색했습니다. 출처와 페이지를 함께 확인해보세요.',
  },
  report: {
    label: 'Report',
    description: '결과를 리포트로 조립합니다',
    icon: FileText,
    prompt: '현재 결과를 리포트 초안으로 구성해줘.',
    assistantReply: '리포트 빌더 초안을 준비했습니다. 필요한 섹션만 선택해 내보내면 됩니다.',
  },
};

const WORKFLOW_ORDER: CanvasWorkflow[] = ['preprocess', 'visualization', 'rag', 'report'];

const DATASET_EXTENSIONS = new Set(['csv', 'xlsx', 'xls', 'parquet', 'json']);
const DOCUMENT_EXTENSIONS = new Set(['pdf', 'doc', 'docx', 'txt', 'md']);

function nowIso(): string {
  return new Date().toISOString();
}

function parseTime(value: Date | string): Date {
  return value instanceof Date ? value : new Date(value);
}

function formatClock(value: Date | string): string {
  return parseTime(value).toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatRelative(value: Date | string): string {
  const date = parseTime(value);
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return '방금';
  if (diffMin < 60) return `${diffMin}분 전`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}시간 전`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay === 1) return '어제';
  return `${diffDay}일 전`;
}

function formatFileSize(size: number): string {
  if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  if (size >= 1024) return `${Math.round(size / 1024)} KB`;
  return `${size} B`;
}

function classifyFileType(fileName: string): 'dataset' | 'document' | null {
  const extension = fileName.split('.').pop()?.toLowerCase();
  if (!extension) return null;
  if (DATASET_EXTENSIONS.has(extension)) return 'dataset';
  if (DOCUMENT_EXTENSIONS.has(extension)) return 'document';
  return null;
}

function createDatasetSummaryCard(file: SessionFile, sessionId: string): WorkbenchCardProps {
  const cardId = `dataset-summary-${file.id}-${Date.now()}`;
  return {
    cardId,
    cardType: 'dataset_summary',
    title: 'Dataset Summary',
    subtitle: `${file.name} 자동 프로파일링`,
    sessionId,
    source: {
      kind: 'dataset',
      datasetId: file.id,
      fileId: file.id,
      runId: `run-profile-${file.id}`,
    },
    status: 'success',
    summary: '업로드 직후 생성된 요약입니다. 상세 통계는 다음 단계에서 확장됩니다.',
    badges: [{ label: 'auto-profiled', tone: 'success' }],
    actions: [{ type: 'pin' }, { type: 'view_log' }, { type: 'add_to_report' }],
    dataset: {
      datasetId: file.id,
      name: file.name,
      fileType: (file.name.split('.').pop()?.toLowerCase() as 'csv' | 'xlsx' | 'parquet' | 'json' | undefined) ?? 'unknown',
      sizeBytes: file.size,
      rows: undefined,
      cols: undefined,
    },
    schema: {
      columns: [
        { name: 'column_1', dtype: 'unknown', missingRate: 0, cardinality: undefined },
        { name: 'column_2', dtype: 'unknown', missingRate: 0, cardinality: undefined },
      ],
    },
    quality: {
      missingRateTotal: 0,
      duplicateRowCount: 0,
    },
    recommendedNext: [
      { kind: 'preprocess_plan', label: '전처리 계획 생성' },
      { kind: 'visualize', label: '핵심 지표 시각화' },
      { kind: 'report', label: '리포트 초안 만들기' },
    ],
  };
}

function createWorkflowCard(workflow: CanvasWorkflow, sessionId: string, sourceFileId?: string): WorkbenchCardProps {
  const suffix = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

  if (workflow === 'preprocess') {
    return {
      cardId: `preprocess-plan-${suffix}`,
      cardType: 'preprocess_plan',
      title: 'Preprocess Plan',
      subtitle: '자동 전처리 계획 제안',
      sessionId,
      source: { kind: 'pipeline', datasetId: sourceFileId, runId: `run-pre-${suffix}` },
      status: 'needs_user',
      summary: '결측/타입/중복 순서로 처리하면 품질 개선 효과가 큽니다.',
      actions: [
        { type: 'apply', payload: { planId: `plan-${suffix}` } },
        { type: 'edit', payload: { planId: `plan-${suffix}` } },
        { type: 'dismiss' },
      ],
      plan: {
        planId: `plan-${suffix}`,
        datasetId: sourceFileId ?? 'dataset-active',
        rationale: '결측과 타입 이슈를 먼저 정리하면 이후 차트/리포트 품질이 안정됩니다.',
        steps: [
          {
            stepId: `step-missing-${suffix}`,
            type: 'handle_missing',
            title: 'Handle missing values',
            why: '결측치로 인한 분석 편향을 줄입니다.',
            enabled: true,
            params: { strategy: 'median' },
          },
          {
            stepId: `step-type-${suffix}`,
            type: 'type_cast',
            title: 'Normalize column types',
            why: '수치/날짜 타입 안정화로 후속 처리 실패를 방지합니다.',
            enabled: true,
            params: { strict: false },
          },
        ],
      },
      editable: {
        allowToggleSteps: true,
        allowParamEdit: false,
      },
    };
  }

  if (workflow === 'visualization') {
    return {
      cardId: `chart-${suffix}`,
      cardType: 'chart',
      title: 'Visualization Result',
      subtitle: '요청 기반 차트 렌더',
      sessionId,
      source: { kind: 'dataset', datasetId: sourceFileId, runId: `run-vis-${suffix}` },
      status: 'success',
      summary: '핵심 지표 추이를 라인 차트로 요약했습니다.',
      actions: [{ type: 'add_to_report' }, { type: 'view_log' }, { type: 'dismiss' }],
      chart: {
        chartId: `chart-${suffix}`,
        datasetId: sourceFileId ?? 'dataset-active',
        title: 'Defect Rate Trend',
        chartType: 'line',
        spec: { x: 'captured_at', y: 'defect_rate' },
        summaryMessage: '오전 이후 결함률이 완만하게 상승하는 패턴입니다.',
      },
      artifact: {
        artifactId: `artifact-chart-${suffix}`,
        kind: 'image',
        mimeType: 'image/png',
        uri: 'https://dummyimage.com/1200x520/e4e4e7/18181b&text=Visualization+Artifact',
        width: 1200,
        height: 520,
      },
      codeRef: { runId: `run-vis-${suffix}`, available: true },
    };
  }

  if (workflow === 'rag') {
    return {
      cardId: `retrieval-${suffix}`,
      cardType: 'retrieval_evidence',
      title: 'Retrieval Evidence',
      subtitle: '문서 근거 검색 결과',
      sessionId,
      source: { kind: 'document', indexId: 'idx-active', runId: `run-rag-${suffix}` },
      status: 'success',
      summary: '질문과 관련된 상위 근거 2건을 추출했습니다.',
      actions: [{ type: 'add_to_report' }, { type: 'view_log' }, { type: 'dismiss' }],
      retrieval: { indexId: 'idx-active', query: '허용 결함률 기준', topK: 2, latencyMs: 48 },
      chunks: [
        {
          chunkId: `chunk-a-${suffix}`,
          score: 0.92,
          text: '제품군 A의 허용 결함률은 1.5% 이하이며 초과 시 재검수 절차를 개시한다.',
          source: { fileId: 'doc-1', filename: 'quality_manual.pdf', page: 12 },
        },
        {
          chunkId: `chunk-b-${suffix}`,
          score: 0.88,
          text: '라인 경고 임계치는 1.2%로 정의하며 지속 초과 시 운영자 알림을 전송한다.',
          source: { fileId: 'doc-1', filename: 'quality_manual.pdf', page: 13 },
        },
      ],
      citationPolicy: {
        requireCitationsInAnswer: true,
        citationFormat: 'source_page',
      },
    };
  }

  return {
    cardId: `report-${suffix}`,
    cardType: 'report_builder',
    title: 'Report Builder',
    subtitle: '아티팩트 기반 리포트 조립',
    sessionId,
    source: { kind: 'report', runId: `run-report-${suffix}` },
    status: 'needs_user',
    summary: '현재 결과를 바탕으로 리포트 섹션 초안을 생성했습니다.',
    actions: [{ type: 'apply', label: 'Export PDF', payload: { format: 'pdf' } }, { type: 'dismiss' }],
    report: {
      reportId: `report-${suffix}`,
      title: 'Quality Analysis Report',
      sections: [
        { sectionId: `sec-1-${suffix}`, kind: 'exec_summary', title: 'Executive Summary', included: true },
        { sectionId: `sec-2-${suffix}`, kind: 'preprocessing', title: 'Preprocessing Steps', included: true },
        { sectionId: `sec-3-${suffix}`, kind: 'visualizations', title: 'Key Visualizations', included: true },
        { sectionId: `sec-4-${suffix}`, kind: 'rag_evidence', title: 'RAG Evidence', included: false },
      ],
    },
    exportOptions: {
      formats: ['pdf', 'html', 'md'],
      defaultFormat: 'pdf',
      theme: 'light',
    },
    exportAction: { type: 'apply', label: 'Export PDF', payload: { format: 'pdf' } },
  };
}

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function AgenticCanvasPanel({
  sessions,
  activeSessionId,
  messages,
  files,
  onOpenUpload,
  onUploadFile,
  onNewSession,
  onSelectSession,
  onDeleteSession,
  onRenameSession,
  onToggleFile,
  onRemoveFile,
  onAddMessage,
}: AgenticCanvasPanelProps) {
  const [draft, setDraft] = useState('');
  const [isResponding, setIsResponding] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isDropUploading, setIsDropUploading] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [sessionArtifacts, setSessionArtifacts] = useState<Record<string, SessionArtifactItem[]>>({});

  const processedDatasetIdsRef = useRef<Record<string, Set<string>>>({});
  const timeoutIdsRef = useRef<number[]>([]);

  useEffect(() => {
    return () => {
      timeoutIdsRef.current.forEach((timerId) => window.clearTimeout(timerId));
      timeoutIdsRef.current = [];
    };
  }, []);

  useEffect(() => {
    const sessionIdSet = new Set(sessions.map((session) => session.id));

    setSessionArtifacts((previous) => {
      const nextEntries = Object.entries(previous).filter(([sessionId]) => sessionIdSet.has(sessionId));
      return Object.fromEntries(nextEntries);
    });

    const nextProcessed: Record<string, Set<string>> = {};
    for (const [sessionId, datasetIds] of Object.entries(processedDatasetIdsRef.current)) {
      if (sessionIdSet.has(sessionId)) {
        nextProcessed[sessionId] = datasetIds;
      }
    }
    processedDatasetIdsRef.current = nextProcessed;
  }, [sessions]);

  const activeArtifacts = useMemo(
    () => (activeSessionId ? sessionArtifacts[activeSessionId] ?? [] : []),
    [activeSessionId, sessionArtifacts],
  );

  const selectedFiles = useMemo(() => files.filter((file) => file.selected), [files]);
  const datasetFiles = useMemo(() => files.filter((file) => file.type === 'dataset'), [files]);

  const renderableTimeline = useMemo<RenderableTimelineItem[]>(() => {
    const messageItems: RenderableTimelineItem[] = messages.map((message) => ({
      key: `message-${message.id}`,
      createdAt: parseTime(message.timestamp).toISOString(),
      type: 'message',
      message,
    }));

    const artifactItems: RenderableTimelineItem[] = activeArtifacts.map((artifact) => ({
      key: `artifact-${artifact.id}`,
      createdAt: artifact.createdAt,
      type: 'artifact',
      artifact,
    }));

    return [...messageItems, ...artifactItems].sort((a, b) => {
      const first = new Date(a.createdAt).getTime();
      const second = new Date(b.createdAt).getTime();
      if (first !== second) return first - second;
      return a.key.localeCompare(b.key);
    });
  }, [activeArtifacts, messages]);

  const isInitialState = renderableTimeline.length === 0 && datasetFiles.length === 0;

  const appendArtifact = (sessionId: string, artifact: SessionArtifactItem) => {
    setSessionArtifacts((previous) => ({
      ...previous,
      [sessionId]: [...(previous[sessionId] ?? []), artifact],
    }));
  };

  const pushMockConversation = (sessionId: string, userPrompt: string, workflow?: CanvasWorkflow) => {
    const content = userPrompt.trim();
    if (!content || isResponding) return;

    onAddMessage(sessionId, 'user', content);
    setDraft('');
    setIsResponding(true);

    const delay = 400 + Math.floor(Math.random() * 401);
    const timerId = window.setTimeout(() => {
      const assistantText = workflow
        ? WORKFLOWS[workflow].assistantReply
        : '요청을 확인했습니다. 다음 액션을 선택하면 바로 이어서 진행하겠습니다.';

      onAddMessage(sessionId, 'assistant', assistantText);

      if (workflow) {
        const sourceDatasetId = datasetFiles[datasetFiles.length - 1]?.id;
        const card = createWorkflowCard(workflow, sessionId, sourceDatasetId);
        appendArtifact(sessionId, {
          id: makeId('card'),
          createdAt: nowIso(),
          type: 'card',
          card,
        });
      }

      setIsResponding(false);
    }, delay);

    timeoutIdsRef.current.push(timerId);
  };

  const handleSend = () => {
    if (!activeSessionId) {
      toast.error('활성 세션이 없습니다. 새 세션을 만들어 주세요.');
      return;
    }
    pushMockConversation(activeSessionId, draft);
  };

  const handleWorkflowShortcut = (workflow: CanvasWorkflow) => {
    if (!activeSessionId) {
      toast.error('활성 세션이 없습니다.');
      return;
    }
    if (!datasetFiles.length) {
      toast.message('먼저 데이터셋 파일을 업로드해 주세요.');
      return;
    }

    pushMockConversation(activeSessionId, WORKFLOWS[workflow].prompt, workflow);
  };

  const handleDropUpload = async (dropped: FileList | File[]) => {
    const droppedFiles = Array.from(dropped);
    if (droppedFiles.length === 0) return;

    setIsDropUploading(true);
    let uploaded = 0;

    for (const file of droppedFiles) {
      const type = classifyFileType(file.name);
      if (!type) {
        toast.error(`${file.name}: 지원하지 않는 파일 형식입니다.`);
        continue;
      }

      try {
        await Promise.resolve(onUploadFile(file, type));
        uploaded += 1;
      } catch (error) {
        const message = error instanceof Error ? error.message : '업로드 실패';
        toast.error(`${file.name}: ${message}`);
      }
    }

    if (uploaded > 0) {
      toast.success(`${uploaded}개 파일 업로드 완료`);
    }

    setIsDropUploading(false);
  };

  const handleCardAction = (card: WorkbenchCardProps, action: CardAction) => {
    if (!activeSessionId) return;

    if (action.type === 'dismiss') {
      setSessionArtifacts((previous) => ({
        ...previous,
        [activeSessionId]: (previous[activeSessionId] ?? []).filter(
          (item) => item.type !== 'card' || item.card.cardId !== card.cardId,
        ),
      }));
      return;
    }

    if (action.type === 'pin' || action.type === 'unpin') {
      setSessionArtifacts((previous) => ({
        ...previous,
        [activeSessionId]: (previous[activeSessionId] ?? []).map((item) => {
          if (item.type !== 'card' || item.card.cardId !== card.cardId) return item;
          const hasPinned = item.card.badges?.some((badge) => badge.label === 'pinned');

          if (action.type === 'pin' && !hasPinned) {
            return {
              ...item,
              card: {
                ...item.card,
                badges: [...(item.card.badges ?? []), { label: 'pinned', tone: 'info' }],
              },
            };
          }

          if (action.type === 'unpin' && hasPinned) {
            return {
              ...item,
              card: {
                ...item.card,
                badges: (item.card.badges ?? []).filter((badge) => badge.label !== 'pinned'),
              },
            };
          }

          return item;
        }),
      }));
      return;
    }

    toast.message(`${action.type} 액션이 선택되었습니다.`);
  };

  const applyRename = (sessionId: string) => {
    const title = editingTitle.trim();
    if (!title) {
      setEditingSessionId(null);
      setEditingTitle('');
      return;
    }

    onRenameSession(sessionId, title);
    setEditingSessionId(null);
    setEditingTitle('');
  };

  useEffect(() => {
    if (!activeSessionId) return;

    const sessionSet = processedDatasetIdsRef.current[activeSessionId] ?? new Set<string>();
    processedDatasetIdsRef.current[activeSessionId] = sessionSet;

    const newDatasets = files.filter((file) => file.type === 'dataset' && !sessionSet.has(file.id));
    if (!newDatasets.length) return;

    newDatasets.forEach((file, index) => {
      sessionSet.add(file.id);
      const startDelay = index * 900;

      const startTimer = window.setTimeout(() => {
        onAddMessage(activeSessionId, 'assistant', `\"${file.name}\" 데이터셋을 감지했습니다. 자동 프로파일링을 시작합니다.`);
      }, startDelay);

      const completeTimer = window.setTimeout(() => {
        onAddMessage(activeSessionId, 'assistant', '프로파일링이 완료되었습니다. 다음 작업 방향을 선택해 주세요.');

        const summaryCard = createDatasetSummaryCard(file, activeSessionId);
        appendArtifact(activeSessionId, {
          id: makeId('card'),
          createdAt: nowIso(),
          type: 'card',
          card: summaryCard,
        });

        appendArtifact(activeSessionId, {
          id: makeId('recommendation'),
          createdAt: nowIso(),
          type: 'recommendations',
          datasetFileId: file.id,
          fileName: file.name,
        });
      }, startDelay + 650);

      timeoutIdsRef.current.push(startTimer, completeTimer);
    });
  }, [activeSessionId, files, onAddMessage]);

  return (
    <div className="h-full w-full overflow-hidden bg-white">
      <div className="flex h-full w-full overflow-hidden">
        <aside className="flex h-full w-72 flex-col border-r border-zinc-200 bg-white">
          <div className="border-b border-zinc-200 px-4 py-4">
            <Button className="h-10 w-full justify-start gap-2" onClick={onNewSession}>
              <Plus className="h-4 w-4" />
              New Session
            </Button>
          </div>

          <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex items-center justify-between px-4 pb-2 pt-3">
              <p className="text-xs font-medium tracking-wide text-zinc-500">대화 기록</p>
              <Badge variant="secondary" className="bg-zinc-100 text-zinc-700">
                {sessions.length}
              </Badge>
            </div>

            <ScrollArea className="min-h-0 flex-1 px-2">
              <div className="space-y-1 pb-3">
                {sessions.length === 0 ? (
                  <p className="px-3 py-4 text-sm text-zinc-500">세션이 없습니다.</p>
                ) : (
                  sessions.map((session) => {
                    const isActive = session.id === activeSessionId;
                    const isEditing = editingSessionId === session.id;

                    return (
                      <div
                        key={session.id}
                        className={`group rounded-lg border px-2 py-2 ${
                          isActive ? 'border-zinc-900 bg-zinc-100' : 'border-transparent hover:border-zinc-200 hover:bg-zinc-50'
                        }`}
                      >
                        {isEditing ? (
                          <div className="flex items-center gap-1">
                            <Input
                              value={editingTitle}
                              onChange={(event) => setEditingTitle(event.target.value)}
                              onKeyDown={(event) => {
                                if (event.key === 'Enter') {
                                  event.preventDefault();
                                  applyRename(session.id);
                                }
                                if (event.key === 'Escape') {
                                  setEditingSessionId(null);
                                  setEditingTitle('');
                                }
                              }}
                              className="h-8"
                              autoFocus
                            />
                            <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => applyRename(session.id)}>
                              <Check className="h-4 w-4" />
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-8 w-8"
                              onClick={() => {
                                setEditingSessionId(null);
                                setEditingTitle('');
                              }}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        ) : (
                          <div className="flex items-start gap-2">
                            <button
                              type="button"
                              onClick={() => onSelectSession(session.id)}
                              className="min-w-0 flex-1 text-left"
                            >
                              <p className={`truncate text-sm ${isActive ? 'font-medium text-zinc-900' : 'text-zinc-700'}`}>
                                {session.title}
                              </p>
                              <p className="mt-0.5 text-xs text-zinc-500">
                                {session.messageCount}개 메시지 · {formatRelative(session.updatedAt)}
                              </p>
                            </button>

                            <div className="flex items-center gap-0.5 opacity-100 md:opacity-0 md:group-hover:opacity-100">
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8 text-zinc-500"
                                onClick={() => {
                                  setEditingSessionId(session.id);
                                  setEditingTitle(session.title);
                                }}
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8 text-zinc-500 hover:text-rose-600"
                                onClick={() => {
                                  if (window.confirm('이 세션을 삭제하시겠습니까?')) {
                                    onDeleteSession(session.id);
                                  }
                                }}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </ScrollArea>
          </div>

          <div className="border-t border-zinc-200 px-4 py-3">
            <p className="mb-2 text-xs font-medium tracking-wide text-zinc-500">Workflow 바로가기</p>
            <div className="grid grid-cols-2 gap-2">
              {WORKFLOW_ORDER.map((workflow) => {
                const meta = WORKFLOWS[workflow];
                const Icon = meta.icon;
                return (
                  <button
                    key={workflow}
                    type="button"
                    onClick={() => handleWorkflowShortcut(workflow)}
                    className="rounded-lg border border-zinc-200 bg-white p-2 text-left transition-colors hover:bg-zinc-50"
                  >
                    <div className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-zinc-200 bg-zinc-50 text-zinc-700">
                      <Icon className="h-4 w-4" />
                    </div>
                    <p className="mt-2 text-xs font-medium text-zinc-900">{meta.label}</p>
                    <p className="mt-0.5 text-[11px] text-zinc-500">{meta.description}</p>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex min-h-0 flex-col border-t border-zinc-200">
            <div className="flex items-center justify-between px-4 py-3">
              <p className="text-xs font-medium tracking-wide text-zinc-500">소스 파일</p>
              <Badge variant="secondary" className="bg-zinc-100 text-zinc-700">
                {files.length}
              </Badge>
            </div>

            <ScrollArea className="max-h-56 px-2 pb-3">
              <div className="space-y-1">
                {files.length === 0 ? (
                  <p className="px-3 py-4 text-sm text-zinc-500">업로드된 파일이 없습니다.</p>
                ) : (
                  files.map((file) => (
                    <div key={file.id} className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-2 py-2">
                      <button
                        type="button"
                        onClick={() => onToggleFile(file.id)}
                        className={`h-4 w-4 rounded border ${file.selected ? 'border-emerald-500 bg-emerald-500' : 'border-zinc-300 bg-white'}`}
                        aria-label={file.selected ? 'selected file' : 'unselected file'}
                      >
                        {file.selected ? <Check className="h-3 w-3 text-white" /> : null}
                      </button>

                      <div className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-zinc-200 bg-zinc-50">
                        {file.type === 'dataset' ? (
                          <Database className="h-4 w-4 text-emerald-600" />
                        ) : (
                          <FileText className="h-4 w-4 text-zinc-600" />
                        )}
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-medium text-zinc-900">{file.name}</p>
                        <p className="text-[11px] text-zinc-500">{formatFileSize(file.size)}</p>
                      </div>

                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8 text-zinc-500 hover:text-rose-600"
                        onClick={() => onRemoveFile(file.id)}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </div>
        </aside>

        <main className="flex min-w-0 flex-1 flex-col overflow-hidden bg-white">
          <div className="border-b border-zinc-200 px-6 py-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs tracking-wide text-zinc-500">AGENTIC WORKBENCH</p>
                <h2 className="mt-1 text-lg text-zinc-900">대화형 데이터 분석</h2>
                <p className="text-sm text-zinc-600">데이터셋 업로드 후 자동 분석을 시작하고 다음 작업을 추천합니다.</p>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" onClick={onOpenUpload} className="h-9">
                  <Plus className="mr-1.5 h-4 w-4" />
                  Upload
                </Button>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              <Badge variant="outline">Sessions: {sessions.length}</Badge>
              <Badge variant="outline">Messages: {messages.length}</Badge>
              <Badge variant="outline">Selected files: {selectedFiles.length}</Badge>
            </div>
          </div>

          <div
            className="relative flex-1 overflow-hidden"
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={async (event) => {
              event.preventDefault();
              setIsDragging(false);
              await handleDropUpload(event.dataTransfer.files);
            }}
          >
            {isDragging ? (
              <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-white/90">
                <div className="rounded-xl border border-dashed border-zinc-400 bg-white px-6 py-5 text-center shadow-sm">
                  <FolderUp className="mx-auto h-6 w-6 text-zinc-600" />
                  <p className="mt-2 text-sm text-zinc-700">파일을 놓으면 자동 업로드합니다</p>
                </div>
              </div>
            ) : null}

            <ScrollArea className="h-full bg-zinc-50/30">
              {isInitialState ? (
                <div className="mx-auto flex min-h-full w-full max-w-4xl flex-col items-center justify-center px-6 py-8">
                  <Card className="w-full max-w-2xl border-zinc-200 bg-white shadow-sm">
                    <CardHeader className="pb-3 text-center">
                      <div className="mx-auto inline-flex h-11 w-11 items-center justify-center rounded-xl border border-zinc-200 bg-zinc-50 text-zinc-700">
                        <Sparkles className="h-5 w-5" />
                      </div>
                      <CardTitle className="mt-2 text-zinc-900">데이터셋을 드랍하거나 업로드하세요</CardTitle>
                      <CardDescription>
                        업로드 후 AI가 자동으로 요약하고 다음 단계(Preprocess/Visualization/RAG/Report)를 추천합니다.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div
                        className="rounded-xl border border-dashed border-zinc-300 bg-white px-4 py-6 text-center"
                        onDragOver={(event) => event.preventDefault()}
                        onDrop={async (event) => {
                          event.preventDefault();
                          await handleDropUpload(event.dataTransfer.files);
                        }}
                      >
                        <FolderUp className="mx-auto h-5 w-5 text-zinc-500" />
                        <p className="mt-2 text-sm text-zinc-700">여기에 파일을 드랍하면 자동 분류 업로드됩니다</p>
                        <p className="mt-1 text-xs text-zinc-500">
                          dataset: csv/xlsx/xls/parquet/json, document: pdf/doc/docx/txt/md
                        </p>
                        {isDropUploading ? (
                          <p className="mt-2 inline-flex items-center gap-1 text-xs text-zinc-600">
                            <Loader2 className="h-3.5 w-3.5 animate-spin" /> 업로드 중...
                          </p>
                        ) : null}
                      </div>

                      <div className="flex justify-center">
                        <Button onClick={onOpenUpload}>
                          <Plus className="mr-1.5 h-4 w-4" />
                          파일 선택
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <div className="mx-auto w-full max-w-4xl space-y-4 px-6 py-6">
                  {renderableTimeline.map((item) => {
                    if (item.type === 'artifact') {
                      if (item.artifact.type === 'card') {
                        return (
                          <CanvasCardRenderer
                            key={item.key}
                            card={item.artifact.card}
                            onAction={(card, action) => handleCardAction(card, action)}
                          />
                        );
                      }

                      return (
                        <Card key={item.key} className="border-zinc-200 bg-white shadow-sm">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-base text-zinc-900">다음 단계 추천</CardTitle>
                            <CardDescription>
                              {item.artifact.fileName} 분석을 기준으로 아래 작업 중 하나를 선택하세요.
                            </CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                              {WORKFLOW_ORDER.map((workflow) => {
                                const meta = WORKFLOWS[workflow];
                                const Icon = meta.icon;
                                return (
                                  <button
                                    key={`${item.artifact.id}-${workflow}`}
                                    type="button"
                                    onClick={() => {
                                      if (!activeSessionId) return;
                                      pushMockConversation(activeSessionId, meta.prompt, workflow);
                                    }}
                                    className="rounded-lg border border-zinc-200 bg-white px-3 py-3 text-left transition-colors hover:bg-zinc-50"
                                  >
                                    <div className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-zinc-200 bg-zinc-50 text-zinc-700">
                                      <Icon className="h-4 w-4" />
                                    </div>
                                    <p className="mt-2 text-sm font-medium text-zinc-900">{meta.label}</p>
                                    <p className="mt-0.5 text-xs text-zinc-500">{meta.description}</p>
                                  </button>
                                );
                              })}
                            </div>
                          </CardContent>
                        </Card>
                      );
                    }

                    const message = item.message;
                    if (message.role === 'user') {
                      return (
                        <div key={item.key} className="flex justify-end">
                          <div className="max-w-[75%] rounded-2xl bg-zinc-900 px-4 py-3 text-sm text-white shadow-sm">
                            <p className="whitespace-pre-wrap">{message.content}</p>
                            <p className="mt-1 text-right text-[11px] text-zinc-300">{formatClock(message.timestamp)}</p>
                          </div>
                        </div>
                      );
                    }

                    return (
                      <div key={item.key} className="flex justify-start gap-2">
                        <div className="mt-1 inline-flex h-7 w-7 items-center justify-center rounded-full border border-zinc-200 bg-white text-zinc-700">
                          <Bot className="h-3.5 w-3.5" />
                        </div>
                        <div className="max-w-[75%] rounded-2xl border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-800 shadow-sm">
                          <p className="whitespace-pre-wrap">{message.content}</p>
                          <p className="mt-1 text-[11px] text-zinc-500">{formatClock(message.timestamp)}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </ScrollArea>
          </div>

          <div className="border-t border-zinc-200 bg-white px-6 py-4">
            {selectedFiles.length > 0 ? (
              <div className="mb-2 flex flex-wrap gap-1.5">
                {selectedFiles.map((file) => (
                  <Badge key={file.id} variant="outline" className="border-zinc-200 text-zinc-600">
                    {file.type === 'dataset' ? <Database className="mr-1 h-3 w-3" /> : <FileText className="mr-1 h-3 w-3" />}
                    {file.name}
                  </Badge>
                ))}
              </div>
            ) : null}

            <div className="mx-auto flex w-full max-w-4xl items-end gap-2">
              <Button size="icon" variant="outline" onClick={onOpenUpload} disabled={isResponding || isDropUploading}>
                <Plus className="h-4 w-4" />
              </Button>

              <Textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="데이터셋을 업로드하면 자동 분석을 시작합니다. 필요하면 직접 질문도 입력할 수 있습니다."
                className="min-h-[52px] max-h-28 border-zinc-200 bg-white"
                rows={1}
                disabled={!activeSessionId || isDropUploading}
              />

              <Button size="icon" onClick={handleSend} disabled={isResponding || isDropUploading || !draft.trim() || !activeSessionId}>
                {isResponding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
