import { Badge } from '../ui/badge';
import { BarChart3, FileEdit } from 'lucide-react';

type FileItem = {
  id: string;
  name: string;
  type: 'dataset' | 'document';
  selected?: boolean;
};

interface SelectedFilesBarProps {
  files: FileItem[];
}

export function SelectedFilesBar({ files }: SelectedFilesBarProps) {
  const selected = files.filter((f) => f.selected);
  if (selected.length === 0) return null;

  return (
    <div className="bg-blue-50 dark:bg-blue-900/10 border-b border-blue-200 dark:border-blue-900/30 px-6 py-2">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-blue-700 dark:text-blue-300">분석 중인 소스:</span>
        {selected.map((file) => (
          <Badge
            key={file.id}
            variant="secondary"
            className={`gap-1.5 text-xs ${
              file.type === 'dataset'
                ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                : 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
            }`}
          >
            {file.type === 'dataset' ? (
              <BarChart3 className="w-3 h-3" />
            ) : (
              <FileEdit className="w-3 h-3" />
            )}
            {file.name}
          </Badge>
        ))}
      </div>
    </div>
  );
}

