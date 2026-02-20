import { useState, useEffect, useRef } from 'react';
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
import { apiRequest, buildApiUrl } from '../lib/api';
import { toast } from 'sonner';

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

type ThinkingStatus = 'active' | 'completed' | 'failed';

interface ThinkingStep {
  phase: string;
  message: string;
  status?: ThinkingStatus;
}

interface PreprocessResultPayload {
  status?: string;
  output_source_id?: string;
  output_filename?: string;
}

function parseThinkingStep(payload: unknown): ThinkingStep | null {
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const step = payload as Record<string, unknown>;
  const message = typeof step.message === 'string' ? step.message.trim() : '';
  if (!message) {
    return null;
  }
  const phase = typeof step.phase === 'string' && step.phase.trim() ? step.phase.trim() : 'thinking';
  const status: ThinkingStatus | undefined =
    step.status === 'active' || step.status === 'completed' || step.status === 'failed'
      ? step.status
      : undefined;
  return {
    phase,
    message,
    status,
  };
}

export function WorkbenchApp({ initialFeature = 'analysis' }: WorkbenchAppProps) {
  const [isDark, setIsDark] = useState(false);
  const [activeFeature, setActiveFeature] = useState<AppFeature>(initialFeature); // 기본값: 라우트에서 전달 가능
  const [message, setMessage] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [selectedModelId, setSelectedModelId] = useState(DEFAULT_MODEL_ID);
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);
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
    setStreamingContent('');
    setThinkingSteps([
      {
        phase: 'analysis',
        message: '요청을 분석하고 있습니다.',
        status: 'active',
      },
    ]);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    let typingTimer: ReturnType<typeof setInterval> | null = null;

    try {
      const selectedSourceId = currentSession?.files.find(
        (f) => f.selected && typeof f.sourceId === 'string'
      )?.sourceId;

      const streamResponse = await fetch(buildApiUrl('/chats/stream'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userMessage,
          session_id: currentSession?.backendSessionId ?? undefined,
          model_id: selectedModelId,
          source_id: selectedSourceId,
        }),
        signal: abortController.signal,
      });

      if (!streamResponse.ok) {
        const detail = await streamResponse.text();
        throw new Error(detail || '채팅 요청에 실패했습니다.');
      }

      if (!streamResponse.body) {
        throw new Error('스트리밍 응답을 받을 수 없습니다.');
      }

      const reader = streamResponse.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let streamedAnswer = '';
      let displayedAnswer = '';
      let pendingAnswer = '';
      let finalAnswerFromDone = '';
      let hasStartedAnswer = false;
      let doneReceived = false;
      let assistantSaved = false;

      const appendThinkingStep = (step: ThinkingStep) => {
        setThinkingSteps((prev) => {
          if (prev.some((item) => item.phase === step.phase && item.message === step.message)) {
            return prev;
          }
          return [...prev, step];
        });
      };

      const stopTypingLoop = () => {
        if (typingTimer !== null) {
          clearInterval(typingTimer);
          typingTimer = null;
        }
      };

      const tryFinalizeAnswer = () => {
        if (!doneReceived || assistantSaved || pendingAnswer.length > 0) {
          return;
        }
        const finalAnswer = (finalAnswerFromDone || streamedAnswer || displayedAnswer).trim();
        if (activeSessionId && finalAnswer) {
          addMessage(activeSessionId, {
            role: 'assistant',
            content: finalAnswer,
          });
          assistantSaved = true;
        }
      };

      const startTypingLoop = () => {
        if (typingTimer !== null) {
          return;
        }
        typingTimer = setInterval(() => {
          if (!pendingAnswer) {
            tryFinalizeAnswer();
            if (doneReceived) {
              stopTypingLoop();
            }
            return;
          }
          const delta = pendingAnswer.slice(0, 2);
          pendingAnswer = pendingAnswer.slice(2);
          displayedAnswer += delta;
          setStreamingContent(displayedAnswer);
          tryFinalizeAnswer();
          if (!pendingAnswer && doneReceived) {
            stopTypingLoop();
          }
        }, 18);
      };

      const handleEvent = (rawEvent: string) => {
        const lines = rawEvent.split('\n');
        let eventName = 'message';
        const dataLines: string[] = [];

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trim());
          }
        }

        const dataRaw = dataLines.join('\n');
        let payload: unknown = {};
        if (dataRaw) {
          try {
            payload = JSON.parse(dataRaw);
          } catch {
            payload = { message: dataRaw };
          }
        }

        const record = payload && typeof payload === 'object'
          ? (payload as Record<string, unknown>)
          : {};

        if (eventName === 'session') {
          const backendSessionId = record.session_id;
          if (activeSessionId && typeof backendSessionId === 'number') {
            setSessionBackendId(activeSessionId, backendSessionId);
          }
          return;
        }

        if (eventName === 'thought') {
          const step = parseThinkingStep(record);
          if (step) {
            appendThinkingStep(step);
          }
          return;
        }

        if (eventName === 'chunk') {
          const delta = record.delta;
          if (typeof delta === 'string' && delta) {
            if (!hasStartedAnswer) {
              hasStartedAnswer = true;
              displayedAnswer = '';
              setStreamingContent('');
            }
            streamedAnswer += delta;
            pendingAnswer += delta;
            startTypingLoop();
          }
          return;
        }

        if (eventName === 'done') {
          doneReceived = true;

          const backendSessionId = record.session_id;
          if (activeSessionId && typeof backendSessionId === 'number') {
            setSessionBackendId(activeSessionId, backendSessionId);
          }

          const eventThoughtSteps = record.thought_steps;
          if (Array.isArray(eventThoughtSteps)) {
            const parsed = eventThoughtSteps
              .map((item) => parseThinkingStep(item))
              .filter((item): item is ThinkingStep => item !== null);
            if (parsed.length > 0) {
              setThinkingSteps(parsed);
            }
          }

          const finalAnswer = typeof record.answer === 'string'
            ? record.answer
            : streamedAnswer;
          finalAnswerFromDone = finalAnswer;

          const preprocessResult = record.preprocess_result as PreprocessResultPayload | undefined;
          if (
            preprocessResult?.status === 'applied' &&
            typeof preprocessResult.output_source_id === 'string' &&
            preprocessResult.output_source_id &&
            typeof preprocessResult.output_filename === 'string' &&
            preprocessResult.output_filename
          ) {
            handlePreprocessApplyResult({
              output_source_id: preprocessResult.output_source_id,
              output_filename: preprocessResult.output_filename,
            }, currentSession?.id ?? activeSessionId);
          }

          if (finalAnswerFromDone && !hasStartedAnswer) {
            hasStartedAnswer = true;
            displayedAnswer = '';
            setStreamingContent('');
            streamedAnswer = finalAnswerFromDone;
            pendingAnswer += finalAnswerFromDone;
            startTypingLoop();
          } else if (
            finalAnswerFromDone &&
            finalAnswerFromDone.startsWith(streamedAnswer) &&
            finalAnswerFromDone.length > streamedAnswer.length
          ) {
            const remain = finalAnswerFromDone.slice(streamedAnswer.length);
            streamedAnswer = finalAnswerFromDone;
            pendingAnswer += remain;
            startTypingLoop();
          } else if (
            finalAnswerFromDone &&
            !finalAnswerFromDone.startsWith(streamedAnswer)
          ) {
            streamedAnswer = finalAnswerFromDone;
            displayedAnswer = '';
            pendingAnswer = finalAnswerFromDone;
            setStreamingContent('');
            startTypingLoop();
          }

          tryFinalizeAnswer();
          return;
        }

        if (eventName === 'error') {
          const errorMessage = typeof record.message === 'string'
            ? record.message
            : '스트리밍 처리 중 오류가 발생했습니다.';
          throw new Error(errorMessage);
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
        while (true) {
          const separatorIndex = buffer.indexOf('\n\n');
          if (separatorIndex < 0) {
            break;
          }
          const rawEvent = buffer.slice(0, separatorIndex).trim();
          buffer = buffer.slice(separatorIndex + 2);
          if (!rawEvent) {
            continue;
          }
          handleEvent(rawEvent);
        }
      }

      const tail = decoder.decode();
      if (tail) {
        buffer += tail.replace(/\r\n/g, '\n');
      }
      if (buffer.trim()) {
        handleEvent(buffer.trim());
      }

      if (!assistantSaved) {
        let waitCount = 0;
        while (!assistantSaved && waitCount < 200) {
          tryFinalizeAnswer();
          if (assistantSaved) {
            break;
          }
          await new Promise((resolve) => setTimeout(resolve, 10));
          waitCount += 1;
        }

        if (!assistantSaved) {
          const fallbackAnswer = (finalAnswerFromDone || streamedAnswer || displayedAnswer).trim();
          if (activeSessionId && fallbackAnswer) {
            addMessage(activeSessionId, {
              role: 'assistant',
              content: fallbackAnswer,
            });
            assistantSaved = true;
          }
        }
      }

      if (!doneReceived && !assistantSaved) {
        throw new Error('응답 스트리밍이 비정상적으로 종료되었습니다.');
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
      if (typingTimer !== null) {
        clearInterval(typingTimer);
      }
      setIsGenerating(false);
      setStreamingContent('');
      setThinkingSteps([]);
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
    setThinkingSteps([]);
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

  const handlePreprocessApplyResult = (
    result: { output_source_id: string; output_filename: string },
    targetSessionId?: string | null,
  ) => {
    const sessionId = targetSessionId ?? activeSessionId;
    if (!sessionId) return;

    useStore.setState((prev) => {
      const nextSessions = prev.sessions.map((session) => {
        if (session.id !== sessionId) {
          return session;
        }

        const existing = session.files.find(
          (file) => file.type === 'dataset' && file.sourceId === result.output_source_id
        );
        const unselected = session.files.map((file) =>
          file.type === 'dataset' ? { ...file, selected: false } : file
        );

        if (existing) {
          return {
            ...session,
            files: unselected.map((file) =>
              file.id === existing.id ? { ...file, selected: true } : file
            ),
            updatedAt: new Date(),
          };
        }

        const newFile = {
          id: `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          name: result.output_filename,
          size: 0,
          type: 'dataset' as const,
          sourceId: result.output_source_id,
          uploadedAt: new Date(),
          selected: true,
        };

        return {
          ...session,
          files: [...unselected, newFile],
          updatedAt: new Date(),
        };
      });

      return { sessions: nextSessions };
    });
  };

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
            {(() => {
              const selectedDatasetSourceId = (activeSession?.files || [])
                .find(f => f.selected && f.type === 'dataset' && f.sourceId)?.sourceId || null;
              return (
                <DataPreprocessing
                  isDark={isDark}
                  selectedSourceId={selectedDatasetSourceId}
                  onServerApplyResult={handlePreprocessApplyResult}
                />
              );
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
                thinkingSteps={thinkingSteps}
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
  );
}
