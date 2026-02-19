import { type ComponentType, useEffect, useMemo, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  BarChart3,
  Bot,
  Check,
  Database,
  FileText,
  FolderUp,
  Loader2,
  PanelLeftClose,
  PanelLeftOpen,
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../ui/alert-dialog';
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
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
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
    <div className="h-full w-full overflow-hidden bg-[#0a0a0b]">
      <div className="flex h-full w-full overflow-hidden">
        <motion.aside
          initial={false}
          animate={{ width: sidebarOpen ? 288 : 0 }}
          transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
          className="glass-panel flex h-full flex-col overflow-hidden border-r border-white/10"
          style={{ minWidth: 0 }}
        >
          <div className="border-b border-white/10 px-4 py-3">
            <Button className="h-9 w-full justify-start gap-2 border-white/[0.2] bg-black/60 text-white transition-all hover:bg-black/80 hover:text-white" variant="outline" onClick={onNewSession}>
              <Plus className="h-4 w-4" />
              New Session
            </Button>
          </div>

          <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex items-center justify-between px-4 pb-2 pt-3">
              <p className="text-xs font-semibold tracking-wide text-white/85 uppercase">대화 기록</p>
              <Badge variant="secondary" className="border-white/20 bg-black/60 text-white">
                {sessions.length}
              </Badge>
            </div>

            <ScrollArea className="min-h-0 flex-1 px-2">
              <div className="space-y-1 pb-3">
                {sessions.length === 0 ? (
                  <p className="px-3 py-4 text-sm text-white/85">세션이 없습니다.</p>
                ) : (
                  sessions.map((session) => {
                    const isActive = session.id === activeSessionId;
                    const isEditing = editingSessionId === session.id;

                    return (
                      <div
                        key={session.id}
                        className={`group rounded-lg border px-2 py-2 transition-all duration-200 ${isActive ? 'border-[#5a7d9a]/40 bg-[#5a7d9a]/12' : 'border-transparent hover:border-white/10 hover:bg-black/50'
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
                              <p className={`truncate text-sm ${isActive ? 'font-semibold text-white' : 'text-white/90'}`}>
                                {session.title}
                              </p>
                              <p className="mt-0.5 text-xs text-white/85">
                                {session.messageCount}개 메시지 · {formatRelative(session.updatedAt)}
                              </p>
                            </button>

                            <div className="flex shrink-0 items-center gap-0.5 opacity-100">
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8 text-white/80 hover:text-white"
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
                                className="h-8 w-8 text-white/80 hover:text-rose-400"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSessionToDelete(session.id);
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


          <div className="flex min-h-0 flex-col border-t border-white/10">
            <div className="flex items-center justify-between px-4 py-3">
              <p className="text-xs font-semibold tracking-wide text-white/85 uppercase">소스 파일</p>
              <Badge variant="secondary" className="border-white/20 bg-black/60 text-white">
                {files.length}
              </Badge>
            </div>

            <ScrollArea className="max-h-56 px-2 pb-3">
              <div className="space-y-1">
                {files.length === 0 ? (
                  <p className="px-3 py-4 text-sm text-white/85">업로드된 파일이 없습니다.</p>
                ) : (
                  files.map((file) => (
                    <div key={file.id} className="flex items-center gap-2 rounded-lg border border-white/10 bg-black/50 px-2 py-2 transition-colors hover:bg-black/70">
                      <button
                        type="button"
                        onClick={() => onToggleFile(file.id)}
                        className={`h-4 w-4 rounded border transition-colors ${file.selected ? 'border-[#8fbc8f] bg-[#8fbc8f]' : 'border-white/20 bg-black/60'}`}
                        aria-label={file.selected ? 'selected file' : 'unselected file'}
                      >
                        {file.selected ? <Check className="h-3 w-3 text-white" /> : null}
                      </button>

                      <div className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-black/60">
                        {file.type === 'dataset' ? (
                          <Database className="h-4 w-4 text-[#8fbc8f]" />
                        ) : (
                          <FileText className="h-4 w-4 text-white/85" />
                        )}
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-medium text-white">{file.name}</p>
                        <p className="text-[11px] text-white/85">{formatFileSize(file.size)}</p>
                      </div>

                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8 text-white/80 hover:text-rose-400"
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
        </motion.aside>

        <main className="flex min-w-0 flex-1 flex-col overflow-hidden bg-[#0a0a0b]">
          <div className="glass-panel flex items-center gap-2 border-b border-white/10 px-4 py-2">
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setSidebarOpen((prev: boolean) => !prev)}
              className="h-8 w-8 rounded-lg text-white/80 transition-all hover:bg-black/70 hover:text-white"
              aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            >
              {sidebarOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
            </Button>
            <div className="flex-1" />
            <Button variant="outline" onClick={onOpenUpload} className="h-8 border-white/[0.22] bg-black/60 text-white transition-all hover:bg-black/80 hover:text-white text-sm">
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              Upload
            </Button>
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
              <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-[#0a0a0b]/90 backdrop-blur-sm">
                <div className="rounded-2xl border border-[#5a7d9a]/40 bg-[#5a7d9a]/12 px-8 py-6 text-center shadow-[0_0_30px_rgba(90,125,154,0.18)]">
                  <FolderUp className="mx-auto h-7 w-7 text-[#7b9eb8]" />
                  <p className="mt-3 text-sm text-white">파일을 놓으면 자동 업로드합니다</p>
                </div>
              </div>
            ) : null}

            <ScrollArea className="h-full">
              {isInitialState ? (
                <div className="mx-auto flex min-h-full w-full max-w-4xl flex-col items-center justify-center px-6 py-16">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
                    className="flex flex-col items-center text-center"
                  >
                    <div className="particle-field">
                      <div className="particle-dot-1" />
                      <div className="particle-dot-2" />
                      <div className="particle-dot-3" />
                      <div className="particle-dot-4" />
                      <div className="particle-dot-5" />
                      <div className="hero-sparkle">
                        <Sparkles className="h-7 w-7 text-[#7b9eb8]" />
                      </div>
                    </div>
                    <h2 className="mt-6 text-3xl typo-display text-white font-bold">제조 데이터를 분석할 준비가 되었습니다</h2>
                    <p className="mt-3 max-w-md text-base typo-body leading-relaxed text-white/90">
                      파일을 드래그하거나 아래 입력창에 명령을 입력하세요.
                      AI가 자동으로 요약하고 다음 단계를 추천합니다.
                    </p>
                    <div className="mt-3 flex items-center gap-2">
                      <div className="agent-status-dot" />
                      <span className="text-xs typo-body text-white/85">에이전트 대기 중</span>
                    </div>

                    <div
                      className="mt-8 w-full max-w-sm rounded-xl border border-dashed border-white/20 bg-black/45 px-6 py-8 text-center transition-all duration-300 hover:border-[#7b9eb8]/45 hover:bg-black/60"
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={async (event) => {
                        event.preventDefault();
                        await handleDropUpload(event.dataTransfer.files);
                      }}
                    >
                      <FolderUp className="mx-auto h-5 w-5 text-white/80" />
                      <p className="mt-3 text-sm typo-body text-white">여기에 파일을 드롭하세요</p>
                      <p className="mt-1 text-xs text-white/80">
                        csv · xlsx · parquet · json · pdf · doc · txt
                      </p>
                      {isDropUploading ? (
                        <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-[#7b9eb8]">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" /> 업로드 중...
                        </p>
                      ) : null}
                    </div>

                    <Button
                      onClick={onOpenUpload}
                      className="mt-5 bg-[#5a7d9a] px-6 font-medium text-white transition-all hover:bg-[#4f6f8a] shadow-[0_2px_12px_rgba(90,125,154,0.25)]"
                    >
                      <Plus className="mr-1.5 h-4 w-4" />
                      파일 선택
                    </Button>

                    {/* Workflow shortcuts — moved from sidebar */}
                    <div className="mt-8 w-full max-w-lg">
                      <p className="mb-3 text-xs font-semibold tracking-wide text-white/85 uppercase">빠른 시작</p>
                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                        {WORKFLOW_ORDER.map((workflow) => {
                          const meta = WORKFLOWS[workflow];
                          const Icon = meta.icon;
                          return (
                            <button
                              key={workflow}
                              type="button"
                              onClick={() => handleWorkflowShortcut(workflow)}
                              className="bento-card sage-glow-hover p-3 text-left"
                            >
                              <div className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-black/60">
                                <Icon className="h-4 w-4 text-[#7b9eb8]" />
                              </div>
                              <p className="mt-2 text-xs font-semibold text-white">{meta.label}</p>
                              <p className="mt-0.5 text-[11px] text-white/85">{meta.description}</p>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </motion.div>
                </div>
              ) : (
                <div className="mx-auto w-full max-w-4xl space-y-4 px-6 py-6">
                  <AnimatePresence mode="popLayout">
                    {renderableTimeline.map((item, index) => {
                      if (item.type === 'artifact') {
                        if (item.artifact.type === 'card') {
                          return (
                            <motion.div
                              key={item.key}
                              initial={{ opacity: 0, y: 12, scale: 0.97 }}
                              animate={{ opacity: 1, y: 0, scale: 1 }}
                              transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
                            >
                              <CanvasCardRenderer
                                card={item.artifact.card}
                                onAction={(card, action) => handleCardAction(card, action)}
                              />
                            </motion.div>
                          );
                        }

                        return (
                          <motion.div
                            key={item.key}
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.35, delay: index * 0.06 }}
                          >
                            <Card className="glass-panel-medium rounded-2xl">
                              <CardHeader className="pb-2">
                                <CardTitle className="text-base typo-title text-white font-bold">다음 단계 추천</CardTitle>
                                <CardDescription className="typo-body text-white/90">
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
                                        className="bento-card px-3 py-3 text-left"
                                      >
                                        <div className="workflow-icon">
                                          <Icon className="h-4 w-4 text-white/80" />
                                        </div>
                                        <p className="mt-2 text-sm font-semibold text-white">{meta.label}</p>
                                        <p className="mt-0.5 text-xs text-white/85">{meta.description}</p>
                                      </button>
                                    );
                                  })}
                                </div>
                              </CardContent>
                            </Card>
                          </motion.div>
                        );
                      }

                      const message = item.message;
                      if (message.role === 'user') {
                        return (
                          <motion.div
                            key={item.key}
                            initial={{ opacity: 0, x: 12 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.25 }}
                            className="flex justify-end"
                          >
                            <div className="chat-bubble-user max-w-[75%] px-4 py-3 text-sm shadow-sm">
                              <p className="whitespace-pre-wrap">{message.content}</p>
                              <p className="mt-1 text-right text-[11px] text-white/80">{formatClock(message.timestamp)}</p>
                            </div>
                          </motion.div>
                        );
                      }

                      return (
                        <motion.div
                          key={item.key}
                          initial={{ opacity: 0, x: -12 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ duration: 0.25 }}
                          className="flex justify-start gap-2"
                        >
                          <div className="mt-1 inline-flex h-7 w-7 items-center justify-center rounded-full border border-white/10 bg-black/60 text-white/80">
                            <Bot className="h-3.5 w-3.5" />
                          </div>
                          <div className="chat-bubble-assistant max-w-[75%] px-4 py-3 text-sm shadow-sm">
                            <p className="whitespace-pre-wrap">{message.content}</p>
                            <p className="mt-1 text-[11px] text-white/85">{formatClock(message.timestamp)}</p>
                          </div>
                        </motion.div>
                      );
                    })}
                  </AnimatePresence>
                </div>
              )}
            </ScrollArea>
          </div>

          <div className="border-t border-white/10 bg-[#0a0a0b] px-6 py-4">
            {selectedFiles.length > 0 ? (
              <div className="mb-2 flex flex-wrap gap-1.5">
                {selectedFiles.map((file) => (
                  <span key={file.id} className="badge-neon-green inline-flex items-center">
                    {file.type === 'dataset' ? <Database className="mr-1 h-3 w-3" /> : <FileText className="mr-1 h-3 w-3" />}
                    {file.name}
                  </span>
                ))}
              </div>
            ) : null}

            <div className="floating-input glow-ring mx-auto flex w-full max-w-4xl items-center gap-2 px-4 py-3">
              <Button
                size="icon"
                variant="ghost"
                onClick={onOpenUpload}
                disabled={isResponding || isDropUploading}
                className="h-9 w-9 text-white/80 hover:text-white hover:bg-black/70"
              >
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
                placeholder="메시지를 입력하세요... 파일을 업로드하면 자동 분석을 시작합니다."
                className="min-h-[52px] max-h-28 resize-none border-0 bg-transparent text-base text-white placeholder:text-white/80 focus-visible:ring-0"
                rows={1}
                disabled={!activeSessionId || isDropUploading}
              />

              <Button
                size="icon"
                onClick={handleSend}
                disabled={isResponding || isDropUploading || !draft.trim() || !activeSessionId}
                className="h-9 w-9 rounded-xl bg-[#5a7d9a] text-white transition-all hover:bg-[#4f6f8a] disabled:opacity-30"
              >
                {isResponding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </main>
      </div>

      <AlertDialog open={!!sessionToDelete} onOpenChange={(open) => !open && setSessionToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>세션 삭제</AlertDialogTitle>
            <AlertDialogDescription>
              정말 이 세션을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700 text-white dark:bg-red-600 dark:text-white"
              onClick={() => {
                if (sessionToDelete) {
                  onDeleteSession(sessionToDelete);
                  setSessionToDelete(null);
                }
              }}
            >
              삭제
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
