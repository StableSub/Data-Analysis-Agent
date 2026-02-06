import { MessageSquare, MoreVertical, Trash2, Edit2, Check, X, CheckSquare } from 'lucide-react';
import React, { useState } from 'react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Input } from '../ui/input';
import { Checkbox } from '../ui/checkbox';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from '../ui/context-menu';

interface ChatSession {
  id: string;
  title: string;
  updatedAt: Date | string; // LocalStorage에서 로드 시 문자열
  messageCount: number;
}

interface ChatHistoryProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
  onRename: (sessionId: string, newTitle: string) => void;
}

/**
 * ChatGPT/workbench 스타일 대화 기록
 */
export function ChatHistory({
  sessions,
  activeSessionId,
  onSelect,
  onDelete,
  onRename
}: ChatHistoryProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const formatDate = (date: Date | string) => {
    const now = new Date();
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    const diff = now.getTime() - dateObj.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return '오늘';
    if (days === 1) return '어제';
    if (days < 7) return `${days}일 전`;
    if (days < 30) return `${Math.floor(days / 7)}주 전`;
    return `${Math.floor(days / 30)}개월 전`;
  };

  const handleRename = (sessionId: string) => {
    if (editTitle.trim()) {
      onRename(sessionId, editTitle);
    }
    setEditingId(null);
    setEditTitle('');
  };

  const handleEnterSelectionMode = () => {
    setIsSelectionMode(true);
    setSelectedIds(new Set());
  };

  const handleExitSelectionMode = () => {
    setIsSelectionMode(false);
    setSelectedIds(new Set());
  };

  const handleToggleSelection = (sessionId: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(sessionId)) {
      newSelected.delete(sessionId);
    } else {
      newSelected.add(sessionId);
    }
    setSelectedIds(newSelected);
  };

  const handleDeleteSelected = () => {
    if (selectedIds.size === 0) return;

    if (confirm(`선택한 ${selectedIds.size}개의 대화를 삭제하시겠습니까?`)) {
      selectedIds.forEach(id => onDelete(id));
      handleExitSelectionMode();
    }
  };

  // Group by date
  const groupedSessions = sessions.reduce((acc, session) => {
    const key = formatDate(session.updatedAt);
    if (!acc[key]) acc[key] = [];
    acc[key].push(session);
    return acc;
  }, {} as Record<string, ChatSession[]>);

  if (sessions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 dark:bg-white/5 mb-3">
          💬
        </div>
        <p className="text-sm text-gray-500 dark:text-[#98989d]">
          아직 대화 기록이 없습니다
        </p>
        <p className="text-xs text-gray-400 dark:text-[#636366] mt-1">
          새 대화를 시작해보세요
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Selection Mode Header */}
      {isSelectionMode && (
        <div className="flex-shrink-0 px-4 py-3 border-b border-gray-200 dark:border-white/10 bg-blue-50 dark:bg-blue-950/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span className="text-sm text-gray-900 dark:text-white">
                {selectedIds.size}개 선택됨
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="destructive"
                onClick={handleDeleteSelected}
                disabled={selectedIds.size === 0}
                className="h-8"
              >
                <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                삭제
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleExitSelectionMode}
                className="h-8"
              >
                취소
              </Button>
            </div>
          </div>
        </div>
      )}

      <ScrollArea className="flex-1 min-h-0">
        <ContextMenu>
          <ContextMenuTrigger asChild>
            <div className="p-2 space-y-6">{/* min-h-full 제거 */}
              {Object.entries(groupedSessions).map(([dateLabel, sessions]) => (
                <div key={dateLabel}>
                  {/* Date Label */}
                  <div className="px-3 py-2">
                    <h3 className="text-xs font-medium text-gray-500 dark:text-[#98989d] uppercase tracking-wider">
                      {dateLabel}
                    </h3>
                  </div>

                  {/* Session List */}
                  <div className="space-y-1">
                    {sessions.map((session) => (
                      <div
                        key={session.id}
                        className={`
                          group relative rounded-lg transition-all
                          ${activeSessionId === session.id
                            ? 'bg-gray-200 dark:bg-white/10'
                            : 'hover:bg-gray-100 dark:hover:bg-white/5'
                          }
                        `}
                      >
                        {editingId === session.id ? (
                          // Edit Mode
                          <div className="flex items-center gap-1 px-3 py-2">
                            <Input
                              value={editTitle}
                              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditTitle(e.target.value)}
                              onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                                if (e.key === 'Enter') handleRename(session.id);
                                if (e.key === 'Escape') {
                                  setEditingId(null);
                                  setEditTitle('');
                                }
                              }}
                              className="h-7 text-sm"
                              autoFocus
                            />
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-7 w-7 flex-shrink-0"
                              onClick={() => handleRename(session.id)}
                            >
                              <Check className="w-3 h-3" />
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-7 w-7 flex-shrink-0"
                              onClick={() => {
                                setEditingId(null);
                                setEditTitle('');
                              }}
                            >
                              <X className="w-3 h-3" />
                            </Button>
                          </div>
                        ) : (
                          // Normal Mode
                          <div className="grid grid-cols-[16px_1fr_24px] gap-2 items-center px-3 py-2.5">
                            {/* Checkbox in Selection Mode */}
                            {isSelectionMode && (
                              <Checkbox
                                checked={selectedIds.has(session.id)}
                                onCheckedChange={() => handleToggleSelection(session.id)}
                                className="h-4 w-4"
                                onClick={(e: React.MouseEvent) => e.stopPropagation()}
                              />
                            )}

                            {/* Icon + Title - min-w-0으로 overflow 방지 */}
                            <div
                              className="min-w-0 flex items-start gap-2 cursor-pointer"
                              style={{ gridColumn: isSelectionMode ? '2 / 3' : '1 / 3' }}
                              onClick={() => {
                                if (isSelectionMode) {
                                  handleToggleSelection(session.id);
                                } else {
                                  onSelect(session.id);
                                }
                              }}
                              onDoubleClick={(e: React.MouseEvent) => {
                                if (!isSelectionMode) {
                                  e.stopPropagation();
                                  setEditingId(session.id);
                                  setEditTitle(session.title);
                                }
                              }}
                            >
                              <MessageSquare className={`
                                w-4 h-4 flex-shrink-0 mt-0.5
                                ${activeSessionId === session.id
                                  ? 'text-gray-900 dark:text-white'
                                  : 'text-gray-500 dark:text-[#98989d]'
                                }
                              `} />

                              <div className="flex-1 min-w-0">
                                <p
                                  className={`
                                    text-sm overflow-hidden text-ellipsis whitespace-nowrap
                                    ${activeSessionId === session.id
                                      ? 'text-gray-900 dark:text-white font-medium'
                                      : 'text-gray-700 dark:text-gray-300'
                                    }
                                  `}
                                  style={{ maxWidth: '100%' }}
                                >
                                  {session.title}
                                </p>
                                {session.messageCount > 0 && (
                                  <p className="text-xs text-gray-500 dark:text-[#98989d] truncate">
                                    {session.messageCount}개 메시지
                                  </p>
                                )}
                              </div>
                            </div>

                            {/* More Menu */}
                            {!isSelectionMode && (
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    className="opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6"
                                    onClick={(e: React.MouseEvent) => e.stopPropagation()}
                                  >
                                    <MoreVertical className="w-3 h-3" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem
                                    onClick={(e: React.MouseEvent) => {
                                      e.stopPropagation();
                                      setEditingId(session.id);
                                      setEditTitle(session.title);
                                    }}
                                  >
                                    <Edit2 className="w-4 h-4 mr-2" />
                                    이름 변경
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onClick={(e: React.MouseEvent) => {
                                      e.stopPropagation();
                                      if (confirm('이 대화를 삭제하시겠습니까?')) {
                                        onDelete(session.id);
                                      }
                                    }}
                                    className="text-red-600 dark:text-red-400"
                                  >
                                    <Trash2 className="w-4 h-4 mr-2" />
                                    삭제
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </ContextMenuTrigger>
          <ContextMenuContent>
            <ContextMenuItem
              onClick={handleEnterSelectionMode}
              className="text-gray-900 dark:text-white"
            >
              선택 모드
            </ContextMenuItem>
          </ContextMenuContent>
        </ContextMenu>
      </ScrollArea>
    </div>
  );
}
