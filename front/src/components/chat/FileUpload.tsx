import { useCallback, useState } from 'react';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { FileIcon, X, Upload, File } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

interface FileUploadProps {
  onFilesSelect: (files: File[]) => void;
  maxFiles?: number;
  maxSize?: number; // in MB
  acceptedTypes?: string[];
}

export function FileUpload({
  onFilesSelect,
  maxFiles = 5,
  maxSize = 10,
  acceptedTypes = ['.csv', '.xlsx', '.json', '.txt'],
}: FileUploadProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileSelect = useCallback(
    (files: FileList | null) => {
      if (!files) return;

      const fileArray = Array.from(files);
      
      // Validate file count
      if (fileArray.length > maxFiles) {
        toast.error(`최대 ${maxFiles}개의 파일만 업로드할 수 있습니다`);
        return;
      }

      // Validate file sizes
      const oversizedFiles = fileArray.filter(
        (file) => file.size > maxSize * 1024 * 1024
      );
      if (oversizedFiles.length > 0) {
        toast.error(`파일 크기는 ${maxSize}MB를 초과할 수 없습니다`);
        return;
      }

      setSelectedFiles(fileArray);
      onFilesSelect(fileArray);
      toast.success(`${fileArray.length}개 파일이 선택되었습니다`);
    },
    [maxFiles, maxSize, onFilesSelect]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      handleFileSelect(e.dataTransfer.files);
    },
    [handleFileSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const removeFile = (index: number) => {
    const newFiles = selectedFiles.filter((_, i) => i !== index);
    setSelectedFiles(newFiles);
    onFilesSelect(newFiles);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="space-y-3">
      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-all cursor-pointer
          ${
            isDragging
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20'
              : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
          }`}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input
          id="file-input"
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={(e) => handleFileSelect(e.target.files)}
          className="hidden"
        />
        
        <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-1">
          파일을 드래그하거나 클릭하여 업로드
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {acceptedTypes.join(', ')} · 최대 {maxSize}MB
        </p>
      </div>

      {/* Selected Files */}
      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          {selectedFiles.map((file, index) => (
            <Card
              key={index}
              className="p-3 flex items-center justify-between bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700"
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded flex items-center justify-center shrink-0">
                  <File className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900 dark:text-gray-100 truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {formatFileSize(file.size)}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => removeFile(index)}
                className="shrink-0"
              >
                <X className="w-4 h-4" />
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
