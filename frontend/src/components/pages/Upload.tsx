import { useRef, useState } from 'react';
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
import { parseCSV, type CSVParseError } from '../../lib/csvParser';

const UPLOAD_VALIDATION_CONFIG = {
  // Pre-upload limits
  allowedExtensions: ['.csv'],
  maxFileSizeBytes: 10 * 1024 * 1024, // 10MB
  maxColumns: 50,
  // Schema (optional): set to enable schema mismatch checks
  expectedSchema: {
    columns: [] as string[],
    // types: { id: 'number', timestamp: 'date', value: 'number' as const },
  },
  missingThreshold: 0.5, // >=50% considered excessive
};

export function Upload() {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<any[]>([]);
  const [errors, setErrors] = useState<CSVParseError[]>([]);
  const [warnings, setWarnings] = useState<CSVParseError[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileReaderRef = useRef<FileReader | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { setUploadedFile } = useStore();

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
    processFile(droppedFile);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      processFile(selectedFile);
    }
  };

  const processFile = (file: File) => {
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

    // Begin reading with cancel support
    const reader = new FileReader();
    fileReaderRef.current = reader;
    setIsUploading(true);
    setProgress(0);
    setErrors([]);
    setWarnings([]);
    setPreview([]);
    setColumns([]);
    setFile(file);

    // Progress (best effort; may not fire consistently)
    reader.onprogress = (evt) => {
      if (evt.lengthComputable) {
        const pct = Math.round((evt.loaded / evt.total) * 100);
        setProgress(Math.min(99, pct));
      }
    };

    reader.onerror = () => {
      setIsUploading(false);
      toast.error('파일을 읽는 중 오류가 발생했습니다.');
    };

    reader.onabort = () => {
      setIsUploading(false);
      setProgress(0);
      setFile(null);
      setPreview([]);
      setColumns([]);
      setErrors([]);
      setWarnings([]);
      toast.message('업로드가 취소되었습니다.');
    };

    reader.onload = () => {
      try {
        const text = String(reader.result || '');
        // Parse CSV and validate header/columns limits (pre-upload validations continue here)
        const result = parseCSV(text, {
          maxColumns: UPLOAD_VALIDATION_CONFIG.maxColumns,
          requireHeader: true,
          expectedSchema: UPLOAD_VALIDATION_CONFIG.expectedSchema,
          missingThreshold: UPLOAD_VALIDATION_CONFIG.missingThreshold,
        });

        setErrors(result.errors);
        setWarnings(result.warnings);

        if (result.errors.length) {
          // Pre-upload specific surfaces
          const critical = result.errors.find((e) =>
            ['empty_file', 'missing_header', 'too_many_columns', 'parse_error', 'inconsistent_columns'].includes(e.code)
          );
          if (critical) {
            setIsUploading(false);
            setProgress(100);
            toast.error(critical.message);
            return;
          }
        }

        setColumns(result.columns);
        // Preview up to 5 rows
        setPreview(result.rows.slice(0, 5));
        setProgress(100);
        setIsUploading(false);
        toast.success('파일이 성공적으로 업로드되었습니다');
      } catch (e) {
        setIsUploading(false);
        toast.error('CSV 파싱 에러가 발생했습니다.');
        setErrors((prev) => [...prev, { code: 'parse_error', message: 'CSV 파싱 에러가 발생했습니다.' }]);
      }
    };

    reader.readAsText(file);
  };

  const handleUpload = () => {
    if (!file || preview.length === 0) return;

    // Post-upload validation gates: fail if critical issues exist
    const hasParseError = errors.some((e) => e.code === 'parse_error' || e.code === 'inconsistent_columns');
    if (hasParseError) {
      toast.error('CSV 파싱 오류가 있어 업로드를 완료할 수 없습니다.');
      return;
    }

    const hasSchemaMismatch = errors.some((e) => e.code === 'schema_mismatch');
    if (hasSchemaMismatch) {
      toast.error('스키마 불일치로 업로드를 완료할 수 없습니다.');
      return;
    }

    const excessiveMissing = warnings.find((w) => w.code === 'excessive_missing');
    if (excessiveMissing) {
      toast.message('결측치가 과도합니다. 계속 진행하려면 확인해주세요.');
    }

    const datatypeMismatch = warnings.find((w) => w.code === 'datatype_mismatch');
    if (datatypeMismatch) {
      toast.message('일부 컬럼 데이터 타입이 예상과 다릅니다.');
    }

    setUploadedFile({
      name: file.name,
      size: file.size,
      uploadedAt: new Date(),
      columns,
      rowCount: preview.length,
      preview,
    });

    toast.success('데이터가 저장되었습니다. Analysis 탭에서 분석을 시작하세요');
  };

  const handleReset = () => {
    if (isUploading && fileReaderRef.current) {
      // During-upload cancel
      fileReaderRef.current.abort();
      return;
    }
    setFile(null);
    setPreview([]);
    setColumns([]);
    setErrors([]);
    setWarnings([]);
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
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
              isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
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
            <Button onClick={() => fileInputRef.current?.click()}>
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

          {/* Errors & Warnings */}
          {(errors.length > 0 || warnings.length > 0) && (
            <Card className="p-4">
              {errors.length > 0 && (
                <div className="mb-3">
                  <h4 className="text-sm font-medium text-red-600">오류</h4>
                  <ul className="list-disc pl-5 text-sm text-red-700 mt-1">
                    {errors.map((e, idx) => (
                      <li key={`err-${idx}`}>{e.message}</li>
                    ))}
                  </ul>
                </div>
              )}
              {warnings.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-amber-600">경고</h4>
                  <ul className="list-disc pl-5 text-sm text-amber-700 mt-1">
                    {warnings.map((w, idx) => (
                      <li key={`warn-${idx}`}>{w.message}</li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          )}

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
            <Button onClick={handleUpload} className="flex-1" disabled={errors.length > 0}>
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
