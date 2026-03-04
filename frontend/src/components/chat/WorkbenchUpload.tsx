import { useRef, useState } from 'react';
import { Upload, X } from 'lucide-react';

type UploadType = 'dataset' | 'document';

interface WorkbenchUploadProps {
  onClose: () => void;
  onUpload: (file: File, type: UploadType) => void | Promise<void>;
}

function resolveUploadType(file: File): UploadType {
  const ext = file.name.split('.').pop()?.toLowerCase();
  if (ext === 'csv' || ext === 'xlsx' || ext === 'xls' || ext === 'tsv') {
    return 'dataset';
  }
  return 'document';
}

export function WorkbenchUpload({ onClose, onUpload }: WorkbenchUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const submitFile = (file: File) => {
    onUpload(file, resolveUploadType(file));
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className={`w-full max-w-md rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-[#212121] p-6 ${
          isDragging ? 'ring-2 ring-blue-400' : ''
        }`}
        onClick={(event) => event.stopPropagation()}
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setIsDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          const file = event.dataTransfer.files?.[0];
          if (file) {
            submitFile(file);
          }
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg text-gray-900 dark:text-white">파일 업로드</h2>
          <button type="button" onClick={onClose} className="text-gray-500 dark:text-gray-300" aria-label="닫기">
            <X className="w-4 h-4" />
          </button>
        </div>

        <button
          type="button"
          className="w-full rounded-xl border-2 border-dashed border-gray-300 dark:border-white/20 p-8 text-center hover:border-blue-400 transition-colors"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="w-8 h-8 mx-auto mb-2 text-gray-500 dark:text-gray-300" />
          <p className="text-sm text-gray-700 dark:text-gray-200">파일을 드래그하거나 클릭해서 선택하세요</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">CSV, XLSX, XLS, TSV는 데이터셋으로 자동 분류됩니다.</p>
        </button>

        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              submitFile(file);
            }
            event.currentTarget.value = '';
          }}
        />
      </div>
    </div>
  );
}
