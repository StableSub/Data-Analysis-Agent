import React, { useState } from 'react';
import { useSessions } from '../../hooks/useSessions';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Input } from '../ui/input';
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
import { MessageSquarePlus, Trash2, MessageSquare, Edit2, Check, X } from 'lucide-react';
import { cn } from '../ui/utils';
import { DEFAULT_MODEL_ID } from '../../lib/models';

export function SessionSidebar() {
  const { sessions, currentSessionId, createSession, deleteSession, setCurrentSession, renameSession } = useSessions();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);

  const handleNewChat = () => {
    createSession('새 대화', DEFAULT_MODEL_ID);
  };

  const startEditing = (id: string, currentTitle: string) => {
    setEditingId(id);
    setEditTitle(currentTitle);
  };

  const saveEdit = () => {
    if (editingId && editTitle.trim()) {
      renameSession(editingId, editTitle.trim());
      setEditingId(null);
      setEditTitle('');
    }
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditTitle('');
  };

  const confirmDelete = (id: string) => {
    setSessionToDelete(id);
    setDeleteDialogOpen(true);
  };

  const handleDelete = () => {
    if (sessionToDelete) {
      deleteSession(sessionToDelete);
      setSessionToDelete(null);
      setDeleteDialogOpen(false);
    }
  };

  return (
    <div className="w-64 bg-white dark:bg-[#171717] border-r border-gray-200 dark:border-white/10 flex flex-col transition-colors">
      <div className="p-3 border-b border-gray-200 dark:border-white/10">
        <Button
          onClick={handleNewChat}
          className="w-full justify-start gap-3 h-11 bg-white dark:bg-white/5 hover:bg-gray-100 dark:hover:bg-white/10 border border-gray-200 dark:border-white/20 text-gray-900 dark:text-white shadow-none transition-colors"
          size="sm"
        >
          <MessageSquarePlus className="w-4 h-4" />
          새 대화
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {sessions.length === 0 ? (
            <div className="text-center py-8 px-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">대화 기록이 없습니다</p>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                className={cn(
                  'group relative flex items-center gap-2 px-3 py-2.5 rounded-lg transition-all cursor-pointer',
                  editingId === session.id
                    ? 'bg-gray-100 dark:bg-white/10'
                    : currentSessionId === session.id
                      ? 'bg-gray-100 dark:bg-white/5'
                      : 'hover:bg-gray-50 dark:hover:bg-white/5'
                )}
                onClick={() => editingId !== session.id && setCurrentSession(session.id)}
              >
                <MessageSquare className={cn(
                  "w-4 h-4 flex-shrink-0",
                  currentSessionId === session.id
                    ? "text-gray-900 dark:text-white"
                    : "text-gray-500 dark:text-gray-400"
                )} />

                {editingId === session.id ? (
                  <div className="flex-1 flex items-center gap-1.5">
                    <Input
                      value={editTitle}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditTitle(e.target.value)}
                      onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                        if (e.key === 'Enter') saveEdit();
                        if (e.key === 'Escape') cancelEdit();
                      }}
                      className="h-8 text-sm bg-white dark:bg-[#2c2c2e] border-gray-300 dark:border-white/20"
                      autoFocus
                      onClick={(e: React.MouseEvent) => e.stopPropagation()}
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 flex-shrink-0 hover:bg-green-100 dark:hover:bg-green-900/30 hover:text-green-700 dark:hover:text-green-400"
                      onClick={(e: React.MouseEvent) => {
                        e.stopPropagation();
                        saveEdit();
                      }}
                    >
                      <Check className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 flex-shrink-0 hover:bg-red-100 dark:hover:bg-red-900/30 hover:text-red-700 dark:hover:text-red-400"
                      onClick={(e: React.MouseEvent) => {
                        e.stopPropagation();
                        cancelEdit();
                      }}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ) : (
                  <>
                    <div className="flex-1 min-w-0 pr-2">
                      <p className={cn(
                        "text-sm truncate",
                        currentSessionId === session.id
                          ? "text-gray-900 dark:text-white"
                          : "text-gray-700 dark:text-gray-300"
                      )}>
                        {session.title}
                      </p>
                    </div>

                    {/* 호버 시 나타나는 액션 버튼들 */}
                    <div className={cn(
                      "absolute right-2 flex gap-1 items-center bg-gradient-to-l from-white dark:from-[#171717] via-white dark:via-[#171717] to-transparent pl-8 pr-1",
                      "opacity-0 group-hover:opacity-100 transition-opacity"
                    )}>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 hover:bg-gray-200 dark:hover:bg-white/10 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
                        onClick={(e: React.MouseEvent) => {
                          e.stopPropagation();
                          startEditing(session.id, session.title);
                        }}
                        title="제목 수정"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                        onClick={(e: React.MouseEvent) => {
                          e.stopPropagation();
                          confirmDelete(session.id);
                        }}
                        title="대화 삭제"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-gray-200 dark:border-white/10">
        <div className="text-xs text-gray-500 dark:text-gray-400">
          <p>총 {sessions.length}개의 대화</p>
        </div>
      </div>

      {/* 삭제 확인 다이얼로그 */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle>대화를 삭제하시겠습니까?</AlertDialogTitle>
            <AlertDialogDescription>
              이 작업은 되돌릴 수 없습니다. 대화의 모든 메시지가 영구적으로 삭제됩니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setSessionToDelete(null)}>
              취소
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              삭제
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
