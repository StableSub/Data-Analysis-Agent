import { useState, useEffect, useRef } from 'react';
import { NotebookLMNav, FeatureType } from './layout/NotebookLMNav';
import { FeatureToggle } from './layout/FeatureToggle';
import { NotebookLMUpload } from './chat/NotebookLMUpload';
import { DataPreprocessing } from './preprocessing/DataPreprocessing';
import { useStore } from '../store/useStore';
import { BarChart3, FileEdit } from 'lucide-react';
import { DEFAULT_MODEL_ID } from '../lib/models';
import { AppHeader } from './notebooklm/AppHeader';
import { SelectedFilesBar } from './notebooklm/SelectedFilesBar';
import { ChatMessages } from './notebooklm/ChatMessages';
import { ChatInputBar } from './notebooklm/ChatInputBar';

// 데이터 분석(AI 챗봇)과 데이터 전처리 2가지 기능만
type AppFeature = 'analysis' | 'preprocessing';

const featureButtons = [
  { id: 'analysis' as AppFeature, icon: BarChart3, label: '데이터 분석' },
  { id: 'preprocessing' as AppFeature, icon: FileEdit, label: '데이터 전처리' },
];

/**
 * NotebookLM 스타일 메인 앱
 */
export function NotebookLMApp() {
  const [isDark, setIsDark] = useState(false);
  const [activeFeature, setActiveFeature] = useState<AppFeature>('analysis'); // 기본값: 데이터 분석
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
    addMessage,
    addFile,
    removeFile,
    toggleFileSelection,
  } = useStore();

  const activeSession = sessions.find(s => s.id === activeSessionId);

  // 첫 로드 시 세션이 없으면 생성
  useEffect(() => {
    if (sessions.length === 0) {
      createSession('chat'); // 내부적으로는 chat 타입 유지
    }
  }, []);

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

  const handleSend = () => {
    if (!message.trim() || !activeSessionId || isGenerating) return;

    const userMessage = message;

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

    // Mock AI response with streaming
    setIsGenerating(true);
    setStreamingContent('');

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setTimeout(() => {
      if (abortController.signal.aborted) return;

      const selectedFiles = sessions.find(s => s.id === activeSessionId)?.files.filter(f => f.selected) || [];
      let response = `데이터 분석 요청 "${userMessage}"을 처리하고 있습니다.`;
      
      if (selectedFiles.length > 0) {
        response += `\n\n선택된 소스 파일 (${selectedFiles.length}개):`;
        selectedFiles.forEach(file => {
          response += `\n- ${file.name} (${file.type === 'dataset' ? '데이터셋' : '문서'})`;
        });
      }

      // Simulate streaming response
      let index = 0;
      const streamInterval = setInterval(() => {
        if (abortController.signal.aborted) {
          clearInterval(streamInterval);
          setIsGenerating(false);
          setStreamingContent('');
          return;
        }

        if (index < response.length) {
          setStreamingContent(response.substring(0, index + 1));
          index++;
        } else {
          clearInterval(streamInterval);
          // 스트리밍 완료 후 메시지 저장
          if (activeSessionId) {
            addMessage(activeSessionId, {
              role: 'assistant',
              content: response,
            });
          }
          setIsGenerating(false);
          setStreamingContent('');
          abortControllerRef.current = null;
        }
      }, 30);
    }, 500);
  };

  const handleStopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsGenerating(false);
    setStreamingContent('');
  };

  const handleFileUpload = (file: File, type: 'dataset' | 'document') => {
    if (!activeSessionId) return;

    const success = addFile(activeSessionId, {
      name: file.name,
      size: file.size,
      type,
    });

    if (success) {
      setShowUpload(false);
      
      // 데이터셋 파일이면 전역 상태에도 저장 (전처리 화면에서 사용)
      if (type === 'dataset') {
        // 파일을 직접 전역 상태로 전달하기 위해 file 객체를 저장할 방법 필요
        // 여기서는 임시로 파일 업로드만 하고, 전처리 화면에서 다시 업로드하도록 유도
      }
    } else {
      // 중복 파일인 경우 알림
      alert(`"${file.name}" 파일이 이미 업로드되어 있습니다.`);
    }
  };

  const chatHistorySessions = sessions.map(s => ({
    id: s.id,
    title: s.title,
    updatedAt: s.updatedAt,
    messageCount: s.messages.length,
  }));

  return (
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
            <DataPreprocessing isDark={isDark} />
          </div>
        ) : (
          <>
            {/* 좌측 네비게이션 */}
            <NotebookLMNav
              onNewChat={handleNewChat}
              sessions={chatHistorySessions}
              activeSessionId={activeSessionId}
              onSessionSelect={setActiveSession}
              onSessionDelete={deleteSession}
              onSessionRename={updateSessionTitle}
              files={activeSession?.files || []}
              onFileToggle={(fileId) => activeSessionId && toggleFileSelection(activeSessionId, fileId)}
              onFileRemove={(fileId) => activeSessionId && removeFile(activeSessionId, fileId)}
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
                textareaRef={textareaRef}
              />
            </div>

            {/* Upload Modal */}
            {showUpload && (
              <NotebookLMUpload
                onClose={() => setShowUpload(false)}
                onUpload={handleFileUpload}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
