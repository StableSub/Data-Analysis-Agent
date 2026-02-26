import { useState, useEffect } from 'react';
import { useSessions } from '../../hooks/useSessions';
import { useChatStream } from '../../hooks/useChatStream';
import { ChatMessage } from '../../types/chat';
import { SessionSidebar } from './SessionSidebar';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { AgentWidget } from './AgentWidget';
import { Header } from './Header';
import { FeatureNav, FeatureType } from '../layout/FeatureNav';
import { DataUploadFeature } from '../features/DataUploadFeature';
import { ComingSoonFeature } from '../features/ComingSoonFeature';
import { motion, AnimatePresence } from 'motion/react';
import { DEFAULT_MODEL_ID } from '../../lib/models';
import {
  Database,
  Filter,
  BarChart3,
  FileEdit,
  Activity,
  Shield
} from 'lucide-react';

export function ChatLayout() {
  const [activeFeature, setActiveFeature] = useState<FeatureType>('chat');
  const [showSidebar, setShowSidebar] = useState(true);
  const [showAgent, setShowAgent] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);

  const {
    sessions,
    currentSessionId,
    createSession,
    addMessage,
    updateMessage,
    getCurrentSession,
    regenerateLastMessage,
    setSessionModel,
  } = useSessions();

  const { isStreaming, send, stop } = useChatStream();

  // Create initial session
  useEffect(() => {
    if (sessions.length === 0) {
      createSession('새 대화', DEFAULT_MODEL_ID);
    }
  }, []);

  const currentSession = getCurrentSession();

  const handleSendMessage = async (content: string, files?: File[]) => {
    if (!currentSessionId || isStreaming) return;

    // Prepare content with file info if files are attached
    let messageContent = content;
    if (files && files.length > 0) {
      const fileInfo = files.map(f => `[파일: ${f.name} (${(f.size / 1024).toFixed(1)}KB)]`).join('\n');
      messageContent = `${content}\n\n${fileInfo}`;
    }

    // Add user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: messageContent,
      createdAt: new Date().toISOString(),
    };
    addMessage(userMessage);

    // Clear attached files
    setAttachedFiles([]);

    // Add streaming assistant message
    const assistantMessageId = `assistant-${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
      isStreaming: true,
    };
    addMessage(assistantMessage);

    // Start streaming
    let accumulatedContent = '';

    await send(
      [...currentSession?.messages || [], userMessage],
      (delta, messageId) => {
        accumulatedContent += delta;
        updateMessage(messageId, accumulatedContent);
      },
      (messageId) => {
        // Mark streaming as complete
      },
      {
        modelId: currentSession?.modelId || DEFAULT_MODEL_ID,
        sessionId: currentSessionId || undefined,
        assistantMessageId: assistantMessageId
      }
    );
  };

  const handleRegenerate = async () => {
    if (!currentSession || isStreaming) return;

    regenerateLastMessage();

    // Get the last user message
    const lastUserMessage = currentSession.messages
      .slice()
      .reverse()
      .find((m) => m.role === 'user');

    if (lastUserMessage) {
      // Re-send the last user message
      const assistantMessageId = `assistant-${Date.now()}`;
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        createdAt: new Date().toISOString(),
        isStreaming: true,
      };
      addMessage(assistantMessage);

      let accumulatedContent = '';

      await send(
        currentSession.messages,
        (delta, messageId) => {
          accumulatedContent += delta;
          updateMessage(messageId, accumulatedContent);
        },
        () => { },
        {
          modelId: currentSession.modelId || DEFAULT_MODEL_ID,
          sessionId: currentSessionId || undefined,
          assistantMessageId: assistantMessageId
        }
      );
    }
  };

  // Render feature content based on active feature
  const renderFeatureContent = () => {
    switch (activeFeature) {
      case 'chat':
        return (
          <>
            {/* Session Sidebar */}
            {showSidebar && <SessionSidebar />}

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col min-w-0 h-screen">
              {/* Header - Fixed */}
              <div className="flex-shrink-0">
                <Header
                  currentSessionTitle={currentSession?.title}
                  showSidebar={showSidebar}
                  showAgent={showAgent}
                  onToggleSidebar={() => setShowSidebar(!showSidebar)}
                  onToggleAgent={() => setShowAgent(!showAgent)}
                  selectedModelId={currentSession?.modelId || DEFAULT_MODEL_ID}
                  onSelectModel={(modelId) => {
                    if (currentSessionId) {
                      setSessionModel(currentSessionId, modelId);
                    }
                  }}
                  hasMessages={(currentSession?.messages?.length || 0) > 0}
                />
              </div>

              {/* Messages - Scrollable Area */}
              <div className="flex-1 overflow-hidden">
                <MessageList
                  messages={currentSession?.messages || []}
                  onRegenerate={handleRegenerate}
                  selectedModelId={currentSession?.modelId || DEFAULT_MODEL_ID}
                  onSelectModel={(modelId) => {
                    if (currentSessionId) {
                      setSessionModel(currentSessionId, modelId);
                    }
                  }}
                />
              </div>

              {/* Input - Fixed at Bottom */}
              <div className="flex-shrink-0">
                <ChatInput
                  onSend={handleSendMessage}
                  onStop={stop}
                  isStreaming={isStreaming}
                  disabled={!currentSessionId}
                  attachedFiles={attachedFiles}
                  onFilesChange={setAttachedFiles}
                />
              </div>
            </div>
          </>
        );

      case 'data-upload':
        return <DataUploadFeature />;

      case 'data-snapshot':
        return (
          <ComingSoonFeature
            icon={Database}
            title="데이터 스냅샷"
            description="데이터 버전 관리 및 스냅샷 기능"
            features={[
              '데이터 버전 저장 및 관리',
              '특정 시점으로 복원',
              '버전 간 비교 분석',
              '자동 스냅샷 스케줄링'
            ]}
          />
        );

      case 'data-filter':
        return (
          <ComingSoonFeature
            icon={Filter}
            title="데이터 필터링"
            description="조건별 데이터 추출 및 필터링"
            features={[
              '다중 조건 필터링',
              '고급 쿼리 빌더',
              '필터 템플릿 저장',
              '실시간 결과 미리보기'
            ]}
          />
        );

      case 'visualization':
        return (
          <ComingSoonFeature
            icon={BarChart3}
            title="데이터 시각화"
            description="다양한 차트와 그래프로 데이터 시각화"
            features={[
              '차트 타입: 선, 막대, 원형, 산점도 등',
              '인터랙티브 차트',
              '대시보드 구성',
              '차트 내보내기 (PNG, PDF)'
            ]}
          />
        );

      case 'data-edit':
        return (
          <ComingSoonFeature
            icon={FileEdit}
            title="데이터 편집"
            description="AI 기반 데이터 수정 및 보정"
            features={[
              'AI 추천 데이터 보정',
              '일괄 편집 기능',
              '데이터 유효성 검사',
              '변경 이력 추적'
            ]}
          />
        );

      case 'simulation':
        return (
          <ComingSoonFeature
            icon={Activity}
            title="시뮬레이션"
            description="제조 공정 시뮬레이션 및 예측"
            features={[
              '공정 시뮬레이션',
              '예측 분석',
              '시나리오 비교',
              '최적화 제안'
            ]}
          />
        );

      case 'audit-log':
        return (
          <ComingSoonFeature
            icon={Shield}
            title="감사 로그"
            description="사용자 활동 추적 및 보안 모니터링"
            features={[
              '사용자 활동 로그',
              '데이터 접근 기록',
              '보안 이벤트 모니터링',
              '로그 검색 및 필터링'
            ]}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-[#1c1c1e] transition-colors relative overflow-hidden">
      {/* Feature Navigation */}
      <FeatureNav
        activeFeature={activeFeature}
        onFeatureChange={setActiveFeature}
      />

      {/* Feature Content Area */}
      <div className="flex-1 flex min-w-0 h-screen bg-white dark:bg-[#1c1c1e]">
        {renderFeatureContent()}
      </div>

      {/* Agent Widget Panel - Only show for chat feature */}
      {activeFeature === 'chat' && (
        <AnimatePresence>
          {showAgent && (
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="fixed right-0 top-0 h-full z-40"
            >
              <AgentWidget onClose={() => setShowAgent(false)} />
            </motion.div>
          )}
        </AnimatePresence>
      )}
    </div>
  );
}
