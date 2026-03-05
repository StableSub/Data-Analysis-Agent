import { FileSpreadsheet, FileText, MessageSquare, Pencil, Plus, Square, CheckSquare, Trash2 } from 'lucide-react';

export type FeatureType = 'chat' | 'visualization' | 'edit' | 'simulation';

interface SessionItem {
  id: string;
  title: string;
  updatedAt: Date | string;
  messageCount: number;
}

interface UploadedFile {
  id: string;
  name: string;
  type: 'dataset' | 'document';
  selected?: boolean;
}

interface WorkbenchNavProps {
  onNewChat: () => void;
  sessions: SessionItem[];
  activeSessionId: string | null;
  onSessionSelect: (id: string) => void;
  onSessionDelete: (id: string) => void | Promise<void>;
  onSessionRename: (id: string, title: string) => void | Promise<void>;
  files: UploadedFile[];
  onFileToggle: (fileId: string) => void;
  onFileRemove: (fileId: string) => void | Promise<void>;
}

function formatDate(value: Date | string) {
  const date = typeof value === 'string' ? new Date(value) : value;
  return date.toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' });
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
  return (
    <aside className="w-80 shrink-0 border-r border-gray-200 dark:border-white/10 bg-white dark:bg-[#212121] flex flex-col">
      <div className="p-4 border-b border-gray-200 dark:border-white/10">
        <button
          type="button"
          onClick={onNewChat}
          className="w-full h-10 rounded-xl bg-blue-500 text-white text-sm inline-flex items-center justify-center gap-2"
        >
          <Plus className="w-4 h-4" />
          새 채팅
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-6">
        <section className="space-y-2">
          <h2 className="text-xs text-gray-500 dark:text-gray-400">세션 목록</h2>
          {sessions.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">세션이 없습니다.</p>
          ) : (
            sessions.map((session) => {
              const isActive = session.id === activeSessionId;
              return (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => onSessionSelect(session.id)}
                  className={`w-full text-left rounded-xl border px-3 py-2 transition-colors ${
                    isActive
                      ? 'border-blue-200 bg-blue-50 dark:border-blue-400/40 dark:bg-[#2f2f2f]'
                      : 'border-gray-200 bg-white dark:border-white/10 dark:bg-[#2a2a2a]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-sm text-gray-900 dark:text-white truncate">{session.title}</div>
                      <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 inline-flex items-center gap-2">
                        <MessageSquare className="w-3.5 h-3.5" />
                        <span>{session.messageCount}개</span>
                        <span>{formatDate(session.updatedAt)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <span
                        role="button"
                        tabIndex={0}
                        onClick={(event) => {
                          event.stopPropagation();
                          const nextTitle = window.prompt('세션 이름을 입력하세요.', session.title)?.trim();
                          if (nextTitle) {
                            onSessionRename(session.id, nextTitle);
                          }
                        }}
                        className="w-7 h-7 rounded-md inline-flex items-center justify-center text-gray-500 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-[#3a3a3a]"
                        aria-label="세션 이름 변경"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </span>
                      <span
                        role="button"
                        tabIndex={0}
                        onClick={(event) => {
                          event.stopPropagation();
                          onSessionDelete(session.id);
                        }}
                        className="w-7 h-7 rounded-md inline-flex items-center justify-center text-gray-500 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-[#3a3a3a]"
                        aria-label="세션 삭제"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </span>
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </section>

        <section className="space-y-2">
          <h2 className="text-xs text-gray-500 dark:text-gray-400">파일 관리</h2>
          {files.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">업로드된 파일이 없습니다.</p>
          ) : (
            files.map((file) => {
              const Icon = file.type === 'dataset' ? FileSpreadsheet : FileText;
              return (
                <div
                  key={file.id}
                  className="w-full rounded-xl border border-gray-200 dark:border-white/10 bg-white dark:bg-[#2a2a2a] px-3 py-2 flex items-center gap-2"
                >
                  <button
                    type="button"
                    onClick={() => onFileToggle(file.id)}
                    className="text-blue-500 dark:text-blue-300"
                    aria-label="파일 선택 토글"
                  >
                    {file.selected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                  </button>
                  <Icon className="w-4 h-4 text-gray-500 dark:text-gray-300" />
                  <span className="flex-1 text-sm text-gray-900 dark:text-white truncate">{file.name}</span>
                  <button
                    type="button"
                    onClick={() => onFileRemove(file.id)}
                    className="text-gray-500 dark:text-gray-300 hover:text-red-500"
                    aria-label="파일 제거"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              );
            })
          )}
        </section>
      </div>
    </aside>
  );
}
