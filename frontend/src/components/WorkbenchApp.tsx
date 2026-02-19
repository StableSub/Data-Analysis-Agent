import { useEffect, useMemo, useState } from 'react';
import { BarChart3, FileEdit } from 'lucide-react';

import { WorkbenchUpload } from './chat/WorkbenchUpload';
import { FeatureToggle } from './layout/FeatureToggle';
import { DataPreprocessing } from './preprocessing/DataPreprocessing';
import { AgenticCanvasPanel } from './workbench/AgenticCanvasPanel';
import { AppHeader } from './workbench/AppHeader';

import { apiRequest } from '../lib/api';
import { useStore } from '../store/useStore';

import { toast } from 'sonner';

export type AppFeature = 'analysis' | 'preprocessing';

const featureButtons = [
  { id: 'analysis' as AppFeature, icon: BarChart3, label: '데이터 분석' },
  { id: 'preprocessing' as AppFeature, icon: FileEdit, label: '데이터 전처리' },
];

interface WorkbenchAppProps {
  initialFeature?: AppFeature;
}

export function WorkbenchApp({ initialFeature = 'analysis' }: WorkbenchAppProps) {
  const [activeFeature, setActiveFeature] = useState<AppFeature>(initialFeature);
  const [showUpload, setShowUpload] = useState(false);

  const {
    sessions,
    activeSessionId,
    createSession,
    deleteSession,
    setActiveSession,
    addMessage,
    updateSessionTitle,
    addFile,
    removeFile,
    toggleFileSelection,
  } = useStore();

  const activeSession = sessions.find((session) => session.id === activeSessionId);

  useEffect(() => {
    if (sessions.length === 0) {
      createSession('chat');
    }
  }, [createSession, sessions.length]);

  useEffect(() => {
    const fallbackSession = sessions[0];
    if (!activeSessionId && fallbackSession) {
      setActiveSession(fallbackSession.id);
    }
  }, [activeSessionId, sessions, setActiveSession]);

  const sessionSummaries = useMemo(
    () =>
      sessions.map((session) => ({
        id: session.id,
        title: session.title,
        updatedAt: session.updatedAt,
        messageCount: session.messages.length,
      })),
    [sessions],
  );

  const handleFeatureChange = (feature: AppFeature) => {
    setActiveFeature(feature);
  };

  const handleNewSession = () => {
    createSession('chat');
  };

  const handleFileUpload = async (file: File, type: 'dataset' | 'document') => {
    if (!activeSessionId) return;

    try {
      const formData = new FormData();
      formData.append('file', file);

      const uploadToast = toast.loading(`${file.name} 업로드 중...`);

      const response = await apiRequest<{
        source_id: string;
        id: number;
        filename: string;
      }>('/datasets/', {
        method: 'POST',
        body: formData,
      });

      toast.dismiss(uploadToast);
      toast.success('파일 업로드 완료');

      const success = addFile(activeSessionId, {
        name: response.filename || file.name,
        size: file.size,
        type,
        sourceId: response.source_id,
      });

      if (success) {
        setShowUpload(false);
      } else {
        toast.warning(`"${file.name}" 파일이 이미 추가되어 있습니다.`);
      }
    } catch (error) {
      toast.error(`파일 업로드 실패: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
    }
  };

  const handleFileRemove = async (fileId: string) => {
    if (!activeSessionId) return;

    const currentSession = sessions.find((session) => session.id === activeSessionId);
    const file = currentSession?.files.find((item) => item.id === fileId);

    if (file?.sourceId) {
      try {
        const deleteToast = toast.loading('파일 삭제 중...');
        await apiRequest(`/datasets/${file.sourceId}`, { method: 'DELETE' });
        toast.dismiss(deleteToast);
        toast.success('파일이 삭제되었습니다.');
      } catch (error) {
        console.error('Failed to delete file from backend:', error);
        toast.error('파일 삭제 실패: 서버 오류');
      }
    }

    removeFile(activeSessionId, fileId);
  };

  return (
    <div className="agentic-theme">
      <div className="flex h-screen bg-[#0a0a0b]">
        <div className="flex min-w-0 flex-1 flex-col">
          <AppHeader
            title={activeFeature === 'analysis' ? 'Agentic Workbench' : 'Preprocessing Workbench'}
            subtitle={
              activeFeature === 'analysis'
                ? 'History + Center Chat 기반 에이전틱 워크벤치'
                : '데이터 정제, 변환 및 특성 추출'
            }
            center={
              <FeatureToggle
                items={featureButtons}
                activeId={activeFeature}
                onChange={(id) => handleFeatureChange(id as AppFeature)}
              />
            }
          />

          {activeFeature === 'preprocessing' ? (
            <DataPreprocessing isDark={false} />
          ) : (
            <AgenticCanvasPanel
              sessions={sessionSummaries}
              activeSessionId={activeSessionId}
              messages={activeSession?.messages || []}
              files={activeSession?.files || []}
              onOpenUpload={() => setShowUpload(true)}
              onUploadFile={handleFileUpload}
              onNewSession={handleNewSession}
              onSelectSession={setActiveSession}
              onDeleteSession={(sessionId) => {
                void deleteSession(sessionId);
              }}
              onRenameSession={updateSessionTitle}
              onToggleFile={(fileId) => activeSessionId && toggleFileSelection(activeSessionId, fileId)}
              onRemoveFile={handleFileRemove}
              onAddMessage={(sessionId, role, content) => {
                addMessage(sessionId, { role, content });
              }}
            />
          )}
        </div>

        {showUpload && <WorkbenchUpload onClose={() => setShowUpload(false)} onUpload={handleFileUpload} />}
      </div>
    </div>
  );
}
