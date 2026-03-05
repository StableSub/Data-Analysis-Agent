import { FileSpreadsheet, FileText } from 'lucide-react';

interface UploadedFile {
  id: string;
  name: string;
  type: 'dataset' | 'document';
  selected?: boolean;
}

interface SelectedFilesBarProps {
  files: UploadedFile[];
}

export function SelectedFilesBar({ files }: SelectedFilesBarProps) {
  if (!files || files.length === 0) {
    return null;
  }

  return (
    <div className="px-4 py-2 border-b border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-[#212121]">
      <div className="flex items-center gap-2 overflow-x-auto scrollbar-thin">
        {files.map((file) => {
          const Icon = file.type === 'dataset' ? FileSpreadsheet : FileText;
          return (
            <div
              key={file.id}
              className={`inline-flex shrink-0 items-center gap-2 px-3 py-1.5 rounded-full text-xs border ${
                file.selected
                  ? 'bg-blue-50 border-blue-200 text-blue-700 dark:bg-[#2f2f2f] dark:border-blue-400/40 dark:text-blue-200'
                  : 'bg-white border-gray-200 text-gray-600 dark:bg-[#2f2f2f] dark:border-white/10 dark:text-gray-300'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{file.name}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
