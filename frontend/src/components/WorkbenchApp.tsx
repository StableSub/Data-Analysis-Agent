import { useState, useEffect, useRef } from 'react';
import { CopilotKit } from '@copilotkit/react-core';
import '@copilotkit/react-ui/styles.css';
import { WorkbenchNav, FeatureType } from './layout/WorkbenchNav';
import { FeatureToggle } from './layout/FeatureToggle';
import { WorkbenchUpload } from './chat/WorkbenchUpload';
import { DataPreprocessing } from './preprocessing/DataPreprocessing';
import { useStore } from '../store/useStore';
import { BarChart3, FileEdit } from 'lucide-react';
import { DEFAULT_MODEL_ID } from '../lib/models';
import { AppHeader } from './workbench/AppHeader';
import { SelectedFilesBar } from './workbench/SelectedFilesBar';
import { ChatMessages } from './workbench/ChatMessages';
import { ChatInputBar } from './workbench/ChatInputBar';
import { apiRequest } from '../lib/api';
import { toast } from 'sonner';
import { useChartRenderer, useDataTableRenderer } from './genui';

// 데이터 분석(AI 챗봇)과 데이터 전처리 2가지 기능만
type AppFeature = 'analysis' | 'preprocessing';

const featureButtons = [
  { id: 'analysis' as AppFeature, icon: BarChart3, label: '데이터 분석' },
  { id: 'preprocessing' as AppFeature, icon: FileEdit, label: '데이터 전처리' },
];

/**
 * workbench 스타일 메인 앱
 */
interface WorkbenchAppProps {
  initialFeature?: AppFeature; // 'analysis' | 'preprocessing'
}

export function WorkbenchApp({ initialFeature = 'analysis' }: WorkbenchAppProps) {
  const [isDark, setIsDark] = useState(false);
  const [activeFeature, setActiveFeature] = useState<AppFeature>(initialFeature); // 기본값: 라우트에서 전달 가능
  const [message, setMessage] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [selectedModelId, setSelectedModelId] = useState(DEFAULT_MODEL_ID);
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const {
    sessions,
    activeSessionId,
    createSession,
    setActiveSession,
    deleteSession,
    updateSessionTitle,
    setSessionBackendId,
    fetchMessages,
    addMessage,
    addFile,
    removeFile,
    toggleFileSelection,
  } = useStore();

  // Register GenUI components with CopilotKit
  useChartRenderer();
  useDataTableRenderer();

  const activeSession = sessions.find(s => s.id === activeSessionId);

  // 첫 로드 시 세션이 없으면 생성
  useEffect(() => {
    if (sessions.length === 0) {
      createSession('chat'); // 내부적으로는 chat 타입 유지
    }
  }, []);

  // 세션 변경 시 백엔드 메시지 동기화
  useEffect(() => {
    if (activeSessionId) {
      fetchMessages(activeSessionId);
    }
  }, [activeSessionId]);

  // 메시지가 업데이트될 때마다 스크롤을 최하단으로 이동
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeSession?.messages]);

  const handleNewChat = () => {
    createSession('chat');
  };

  const handleFeatureChange = (feature: AppFeature) => {
    setActiveFeature(feature);
  };

  const handleSend = async () => {
    if (!message.trim() || !activeSessionId || isGenerating) return;

    const userMessage = message;
    const currentSession = sessions.find(s => s.id === activeSessionId);

    // 첫 메시지인 경우 제목 자동 생성
    const isFirstMessage = activeSession?.messages.length === 0;
    if (isFirstMessage && activeSessionId) {
      // 메시지를 요약해서 제목으로 사용 (최대 30자)
      let title = userMessage.trim();
      if (title.length > 30) {
        title = title.substring(0, 30) + '...';
      }
      updateSessionTitle(activeSessionId, title);
    }

    addMessage(activeSessionId, {
      role: 'user',
      content: userMessage,
    });

    setMessage('');

    // Textarea 높이 초기화
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    setIsGenerating(true);
    setStreamingContent('응답 생성 중...');

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      // Collect selected file source IDs
      const selectedSourceIds = currentSession?.files
        .filter(f => f.selected && f.sourceId)
        .map(f => f.sourceId!) || [];

      const response = await apiRequest<{ answer: string; session_id: number }>('/chats', {
        method: 'POST',
        body: JSON.stringify({
          question: userMessage,
          session_id: currentSession?.backendSessionId ?? undefined,
          data_source_id: selectedSourceIds.length > 0 ? selectedSourceIds[0] : undefined,
          model_id: selectedModelId,
        }),
        signal: abortController.signal,
      });

      if (activeSessionId) {
        if (!currentSession?.backendSessionId) {
          setSessionBackendId(activeSessionId, response.session_id);
        }
        addMessage(activeSessionId, {
          role: 'assistant',
          content: response.answer,
        });
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }
      toast.error(error instanceof Error ? error.message : '채팅 요청에 실패했습니다.');
    } finally {
      setIsGenerating(false);
      setStreamingContent('');
      abortControllerRef.current = null;
    }
  };

  const handleStopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsGenerating(false);
    setStreamingContent('');
  };

  const handleFileUpload = async (file: File, type: 'dataset' | 'document') => {
    if (!activeSessionId) return;

    try {
      // 1. Upload to Backend
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

      // 2. Add to Store with sourceId
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
      toast.error('파일 업로드 실패: ' + (error instanceof Error ? error.message : '알 수 없는 오류'));
    }
  };

  const chatHistorySessions = sessions.map(s => ({
    id: s.id,
    title: s.title,
    updatedAt: s.updatedAt,
    messageCount: s.messages.length,
  }));

  return (
    // <CopilotKit runtimeUrl="/api/copilotkit">
    <div className={isDark ? 'dark' : ''}>
      <div className="flex h-screen bg-gray-50 dark:bg-[#212121]">
        {/* 데이터 전처리 화면 */}
        {activeFeature === 'preprocessing' ? (
          <div className="flex-1 flex flex-col">
            <AppHeader
              title="AI 챗봇"
              subtitle="제조 데이터 분석 AI 어시스턴트"
              isDark={isDark}
              onToggleTheme={() => setIsDark(!isDark)}
              center={
                <FeatureToggle
                  items={featureButtons}
                  activeId={activeFeature}
                  onChange={(id) => handleFeatureChange(id as AppFeature)}
                />
              }
            />
            {(() => {
              const selectedDatasetSourceId = (activeSession?.files || [])
                .find(f => f.selected && f.type === 'dataset' && f.sourceId)?.sourceId || null;
              return <DataPreprocessing isDark={isDark} selectedSourceId={selectedDatasetSourceId} />;
            })()}
          </div>
        ) : (
          <>
            {/* 좌측 네비게이션 */}
            <WorkbenchNav
              onNewChat={handleNewChat}
              sessions={chatHistorySessions}
              activeSessionId={activeSessionId}
              onSessionSelect={setActiveSession}
              onSessionDelete={deleteSession}
              onSessionRename={updateSessionTitle}
              files={activeSession?.files || []}
              onFileToggle={(fileId) => activeSessionId && toggleFileSelection(activeSessionId, fileId)}
              onFileRemove={async (fileId) => {
                if (!activeSessionId) return;

                const currentSession = sessions.find(s => s.id === activeSessionId);
                const file = currentSession?.files.find(f => f.id === fileId);

                if (file && file.sourceId) {
                  try {
                    const deleteToast = toast.loading('파일 삭제 중...');
                    await apiRequest(`/datasets/${file.sourceId}`, { method: 'DELETE' });
                    toast.dismiss(deleteToast);
                    toast.success('파일이 삭제되었습니다.');
                  } catch (error) {
                    console.error('Failed to delete file from backend:', error);
                    toast.error('파일 삭제 실패: 서버 오류');
                    // 서버 삭제 실패해도 로컬에서는 지우고 싶다면 아래 코드를 try 밖으로 뺍니다.
                  }
                }

                // Ensure store update happens
                removeFile(activeSessionId, fileId);
              }}
            />

            {/* 우측 대화 영역 */}
            <div className="flex-1 flex flex-col bg-white dark:bg-[#212121]">
              <AppHeader
                title="AI 챗봇"
                subtitle="제조 데이터 분석 AI 어시스턴트"
                isDark={isDark}
                onToggleTheme={() => setIsDark(!isDark)}
                center={
                  <FeatureToggle
                    items={featureButtons}
                    activeId={activeFeature}
                    onChange={(id) => handleFeatureChange(id as AppFeature)}
                  />
                }
              />

              {activeSession && <SelectedFilesBar files={activeSession.files} />}

              <ChatMessages
                messages={activeSession?.messages || []}
                isGenerating={isGenerating}
                streamingContent={streamingContent}
                emptyTitle={activeFeature === 'analysis' ? 'AI 챗봇' : '데이터 전처리'}
                emptySubtitle={
                  activeFeature === 'analysis'
                    ? '제조 데이터 분석 AI 어시스턴트'
                    : '데이터 정제, 변환 및 특성 추출'
                }
                endRef={messagesEndRef}
              />

              <ChatInputBar
                message={message}
                setMessage={setMessage}
                isGenerating={isGenerating}
                onSend={handleSend}
                onStop={handleStopGenerating}
                onOpenUpload={() => setShowUpload(true)}
                selectedModelId={selectedModelId}
                setSelectedModelId={setSelectedModelId}
                textareaRef={textareaRef as React.RefObject<HTMLTextAreaElement>}
              />
            </div>

            {/* Upload Modal */}
            {showUpload && (
              <WorkbenchUpload
                onClose={() => setShowUpload(false)}
                onUpload={handleFileUpload}
              />
            )}
          </>
        )}
      </div>
    </div>
    // </CopilotKit>
  );
}
