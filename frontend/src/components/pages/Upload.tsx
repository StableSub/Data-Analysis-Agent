import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Upload as UploadIcon, FileCheck, X, AlertCircle } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { toast } from 'sonner';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { Alert, AlertDescription } from '../ui/alert';
import { apiRequest } from '../../lib/api';

const UPLOAD_VALIDATION_CONFIG = {
  // Pre-upload limits
  allowedExtensions: ['.csv'],
  maxFileSizeBytes: 10 * 1024 * 1024, // 10MB
};

export function Upload() {
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<any[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [datasetSourceId, setDatasetSourceId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const uploadAbortRef = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const {
    setUploadedFile,
    activeSessionId,
    createSession,
    setActiveSession,
    addFile,
  } = useStore();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      processFile(droppedFile);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      processFile(selectedFile);
    }
  };

  const processFile = async (file: File) => {
    // Pre-upload: extension check
    const ext = (file.name.match(/\.[^.]+$/)?.[0] || '').toLowerCase();
    if (!UPLOAD_VALIDATION_CONFIG.allowedExtensions.includes(ext)) {
      toast.error('파일 형식 오류: CSV 파일만 허용됩니다.');
      return;
    }

    // Pre-upload: size check
    if (file.size > UPLOAD_VALIDATION_CONFIG.maxFileSizeBytes) {
      toast.error('파일 크기 초과: 최대 10MB까지 허용됩니다.');
      return;
    }

    setIsUploading(true);
    setProgress(0);
    setPreview([]);
    setColumns([]);
    setDatasetSourceId(null);
    setFile(file);

    const abortController = new AbortController();
    uploadAbortRef.current = abortController;

    try {
      const formData = new FormData();
      formData.append('file', file);

      const uploadResponse = await apiRequest<{
        source_id: string;
      }>('/datasets', {
        method: 'POST',
        body: formData,
        signal: abortController.signal,
      });

      const sampleResponse = await apiRequest<{
        columns: string[];
        rows: Record<string, any>[];
      }>(`/datasets/${uploadResponse.source_id}/sample`, {
        signal: abortController.signal,
      });

      setColumns(sampleResponse.columns || []);
      setPreview(sampleResponse.rows || []);
      setDatasetSourceId(uploadResponse.source_id);
      setProgress(100);
      toast.success('파일이 성공적으로 업로드되었습니다');
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') {
        toast.message('업로드가 취소되었습니다.');
      } else if (e instanceof Error && e.name === 'AbortError') {
        toast.message('업로드가 취소되었습니다.');
      } else {
        toast.error(e instanceof Error ? e.message : '파일 업로드에 실패했습니다.');
      }
      setFile(null);
      setPreview([]);
      setColumns([]);
      setDatasetSourceId(null);
      setProgress(0);
    } finally {
      setIsUploading(false);
      uploadAbortRef.current = null;
    }
  };

  const handleUpload = () => {
    if (!file || preview.length === 0 || !datasetSourceId) return;

    // 워크벤치에서 사용하는 세션 파일 상태와도 동기화
    let targetSessionId = activeSessionId;
    if (!targetSessionId) {
      targetSessionId = createSession('chat');
      setActiveSession(targetSessionId);
    }

    addFile(targetSessionId, {
      name: file.name,
      size: file.size,
      type: 'dataset',
      sourceId: datasetSourceId,
      columns,
      rowCount: preview.length,
      preview,
    });

    // 레거시 상태도 유지 (기존 분석 화면 호환)
    setUploadedFile({
      id: datasetSourceId,
      name: file.name,
      size: file.size,
      type: 'dataset',
      sourceId: datasetSourceId,
      uploadedAt: new Date(),
      columns,
      rowCount: preview.length,
      preview,
    });

    toast.success('데이터가 저장되었습니다. 채팅 화면에서 바로 사용할 수 있습니다.');
    navigate('/chat');
  };

  const handleReset = () => {
    if (isUploading && uploadAbortRef.current) {
      uploadAbortRef.current.abort();
      return;
    }
    setFile(null);
    setPreview([]);
    setColumns([]);
    setDatasetSourceId(null);
    setProgress(0);
    setIsUploading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-gray-900 mb-2">Upload</h2>
        <p className="text-gray-600">CSV 파일을 업로드하고 데이터를 미리 확인하세요</p>
      </div>

      {!file ? (
        <Card className="p-8">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
              }`}
          >
            <UploadIcon className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <h3 className="text-gray-900 mb-2">파일을 드래그하거나 클릭하여 업로드</h3>
            <p className="text-gray-500 mb-6">CSV 파일, 최대 10MB</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileSelect}
              className="hidden"
            />
            <Button onClick={() => fileInputRef.current?.click()} disabled={isUploading}>
              파일 선택
            </Button>
            {isUploading && (
              <div className="mt-6">
                <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                  <div className="bg-blue-600 h-2" style={{ width: `${progress}%` }} />
                </div>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-sm text-gray-600">업로드 중... {progress}%</span>
                  <Button variant="outline" size="sm" onClick={handleReset}>취소</Button>
                </div>
              </div>
            )}
          </div>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* File Info */}
          <Card className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div className="bg-green-50 text-green-600 p-3 rounded-lg">
                  <FileCheck className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-gray-900">{file.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {(file.size / 1024).toFixed(2)} KB · {preview.length} rows
                  </p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={handleReset}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          </Card>

          {/* Preview Alert */}
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              데이터 미리보기 (최대 5행). 전체 데이터는 업로드 후 분석됩니다.
            </AlertDescription>
          </Alert>

          {/* Data Preview */}
          <Card className="p-6">
            <h3 className="text-gray-900 mb-4">데이터 미리보기</h3>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    {(columns.length ? columns : Object.keys(preview[0] || {})).map((column) => (
                      <TableHead key={column}>{column}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.map((row, index) => (
                    <TableRow key={index}>
                      {(columns.length ? columns : Object.keys(row)).map((col, cellIndex) => (
                        <TableCell key={cellIndex}>{(row as any)[col]}</TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <Button onClick={handleUpload} className="flex-1" disabled={isUploading || !datasetSourceId}>
              데이터 저장 및 분석 준비
            </Button>
            <Button variant="outline" onClick={handleReset}>
              취소
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
