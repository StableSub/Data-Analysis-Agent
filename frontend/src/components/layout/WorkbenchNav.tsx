import { MessageSquare, Plus, ChevronRight, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { ChatHistory } from '../chat/ChatHistory';
import { SourceFiles } from '../chat/SourceFiles';

export type FeatureType = 'chat' | 'visualization' | 'edit';

interface WorkbenchNavProps {
  onNewChat: () => void;
  
  // Chat Sessions
  sessions: Array<{
    id: string;
    title: string;
    updatedAt: Date;
    messageCount: number;
  }>;
  activeSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onSessionDelete: (sessionId: string) => void;
  onSessionRename: (sessionId: string, title: string) => void;
  
  // Source Files
  files: Array<{
    id: string;
    name: string;
    type: 'dataset' | 'document';
    size: number;
    selected?: boolean;
  }>;
  onFileToggle: (fileId: string) => void;
  onFileRemove: (fileId: string) => void;
}

export function WorkbenchNav({
  onNewChat,
  sessions,
  activeSessionId,
  onSessionSelect,
  onSessionDelete,
  onSessionRename,
  files,
  onFileToggle,
  onFileRemove,
}: WorkbenchNavProps) {
  const [showSources, setShowSources] = useState(true);
  const [showHistory, setShowHistory] = useState(true);

  return (
    <div className="w-64 h-full bg-white dark:bg-[#171717] border-r border-gray-200 dark:border-white/10 flex flex-col">
      {/* 새 대화 버튼 */}
      <div className="px-3 py-[18px] border-b border-gray-200 dark:border-white/10">
        <Button
          onClick={onNewChat}
          className="w-full justify-start gap-3 h-11 bg-blue-600 hover:bg-blue-700 dark:bg-[#0a84ff] dark:hover:bg-[#0077ed] text-white shadow-sm"
        >
          <Plus className="w-5 h-5" />
          <span className="font-medium">새 대화</span>
        </Button>
      </div>

      {/* 대화 기록 (접을 수 있음) */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-white/10">
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="flex-shrink-0 w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
        >
          <span className="text-sm font-medium text-gray-900 dark:text-white">
            대화 기록 ({sessions.length})
          </span>
          {showHistory ? (
            <ChevronDown className="w-4 h-4 text-gray-500 dark:text-[#98989d]" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500 dark:text-[#98989d]" />
          )}
        </button>

        {showHistory && (
          <div className="h-[320px] border-t border-gray-200 dark:border-white/10">
            <ChatHistory
              sessions={sessions}
              activeSessionId={activeSessionId}
              onSelect={onSessionSelect}
              onDelete={onSessionDelete}
              onRename={onSessionRename}
            />
          </div>
        )}
      </div>

      {/* 소스 파일 (접을 수 있음) */}
      <div className="flex-1 flex flex-col min-h-0">
        <button
          onClick={() => setShowSources(!showSources)}
          className="flex-shrink-0 w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors border-b border-gray-200 dark:border-white/10"
        >
          <span className="text-sm font-medium text-gray-900 dark:text-white">
            소스 ({files.length})
          </span>
          {showSources ? (
            <ChevronDown className="w-4 h-4 text-gray-500 dark:text-[#98989d]" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500 dark:text-[#98989d]" />
          )}
        </button>
        
        {showSources && (
          <div className="flex-1 min-h-0 border-gray-200 dark:border-white/10 overflow-hidden w-full max-w-full border-t">
            <SourceFiles
              files={files}
              onToggle={onFileToggle}
              onRemove={onFileRemove}
            />
          </div>
        )}
      </div>

      {/* 하단 사용자 정보 */}
      <div className="px-3 py-[22px] border-t border-gray-200 dark:border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs flex-shrink-0">
            U
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-gray-900 dark:text-white truncate">사용자</p>
            <p className="text-xs text-gray-500 dark:text-[#98989d] truncate">user@example.com</p>
          </div>
        </div>
      </div>
    </div>
  );
}

