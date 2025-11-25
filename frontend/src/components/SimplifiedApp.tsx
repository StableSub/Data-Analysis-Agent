import { useState } from 'react';
import { SimplifiedNav, FeatureType } from './layout/SimplifiedNav';
import { SimplifiedChatLayout } from './chat/SimplifiedChatLayout';

/**
 * 단순화된 앱 레이아웃
 * - 좌측: 새 대화 버튼 + 5개 기능 메뉴
 * - 우측: 대화창 (파일 업로드 포함)
 */
export function SimplifiedApp() {
  const [activeFeature, setActiveFeature] = useState<FeatureType>('chat');
  const [sessionId, setSessionId] = useState(0);

  const handleNewChat = () => {
    setSessionId(prev => prev + 1);
  };

  const handleFeatureChange = (feature: FeatureType) => {
    setActiveFeature(feature);
    setSessionId(prev => prev + 1);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* 좌측 네비게이션 */}
      <SimplifiedNav
        activeFeature={activeFeature}
        onFeatureChange={handleFeatureChange}
        onNewChat={handleNewChat}
      />

      {/* 우측 대화 영역 */}
      <div className="flex-1 overflow-hidden">
        <SimplifiedChatLayout key={sessionId} feature={activeFeature} />
      </div>
    </div>
  );
}
