import { FileText, Database, X, Check } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { ScrollArea } from '../ui/scroll-area';

interface SourceFile {
  id: string;
  name: string;
  type: 'dataset' | 'document';
  size: number;
  selected?: boolean;
}

interface SourceFilesProps {
  files: SourceFile[];
  onToggle: (fileId: string) => void;
  onRemove: (fileId: string) => void;
}

/**
 * NotebookLM 스타일 소스 파일 목록
 */
export function SourceFiles({ files, onToggle, onRemove }: SourceFilesProps) {
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (files.length === 0) {
    return (
      <div className="p-6 text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 dark:bg-white/5 mb-3">
          📁
        </div>
        <p className="text-sm text-gray-500 dark:text-[#98989d]">
          아직 업로드된 파일이 없습니다
        </p>
      </div>
    );
  }

  const selectedCount = files.filter(f => f.selected).length;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-gray-200 dark:border-white/10">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-gray-900 dark:text-white">
            소스 선택
          </h3>
          <Badge variant="secondary" className="text-xs">
            {selectedCount}/{files.length} 선택됨
          </Badge>
        </div>
        <p className="text-xs text-gray-500 dark:text-[#98989d]">
          분석에 사용할 파일을 선택하세요
        </p>
      </div>

      {/* File List */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-2 space-y-1">
          {files.map((file) => (
            <div
              key={file.id}
              className={`
                group relative rounded-lg transition-all
                ${file.selected 
                  ? 'bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900/50' 
                  : 'bg-white dark:bg-[#2c2c2e] border border-gray-200 dark:border-white/10 hover:bg-gray-50 dark:hover:bg-white/5'
                }
              `}
            >
              <div className="grid grid-cols-[16px_28px_1fr_24px] gap-2 items-center p-2">
                {/* Checkbox */}
                <Checkbox
                  checked={file.selected}
                  onCheckedChange={() => onToggle(file.id)}
                  className="h-4 w-4"
                  onClick={(e) => e.stopPropagation()}
                />

                {/* Icon */}
                <div className={`
                  w-7 h-7 rounded-lg flex items-center justify-center
                  ${file.type === 'dataset' 
                    ? 'bg-green-100 dark:bg-green-900/30' 
                    : 'bg-purple-100 dark:bg-purple-900/30'
                  }
                `}>
                  {file.type === 'dataset' ? (
                    <Database className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                  ) : (
                    <FileText className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
                  )}
                </div>

                {/* File Info - 최대 너비 제한 */}
                <div 
                  className="min-w-0 cursor-pointer"
                  onClick={() => onToggle(file.id)}
                  style={{ maxWidth: '100%' }}
                >
                  <p 
                    className={`
                      text-xs font-medium overflow-hidden text-ellipsis whitespace-nowrap
                      ${file.selected 
                        ? 'text-blue-700 dark:text-blue-300' 
                        : 'text-gray-900 dark:text-white'
                      }
                    `}
                    style={{ maxWidth: '100%' }}
                  >
                    {file.name}
                  </p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className={`
                      text-[10px] px-1.5 py-0.5 rounded flex-shrink-0
                      ${file.type === 'dataset' 
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' 
                        : 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                      }
                    `}>
                      {file.type === 'dataset' ? '데이터셋' : '문서'}
                    </span>
                    <span className="text-[10px] text-gray-500 dark:text-[#98989d]">
                      {formatFileSize(file.size)}
                    </span>
                  </div>
                </div>

                {/* Remove Button */}
                <Button
                  size="icon"
                  variant="ghost"
                  className="opacity-60 hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-600 dark:hover:text-red-400 transition-all h-6 w-6"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove(file.id);
                  }}
                  title="파일 삭제"
                >
                  <X className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Info */}
      <div className="px-4 py-3 border-t border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-[#1c1c1e]">
        <p className="text-xs text-gray-500 dark:text-[#98989d]">
          💡 체크된 파일만 AI가 참조합니다
        </p>
      </div>
    </div>
  );
}
