import { useState, useRef } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Upload as UploadIcon, FileCheck, X, AlertCircle } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { mockCSVPreview } from '../../lib/mockData';
import { toast } from 'sonner@2.0.3';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { Alert, AlertDescription } from '../ui/alert';

export function Upload() {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<any[]>([]);
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
    // Validate file type
    if (!file.name.endsWith('.csv')) {
      toast.error('CSV 파일만 업로드 가능합니다');
      return;
    }

    // Validate file size (10MB limit)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('파일 크기는 10MB를 초과할 수 없습니다');
      return;
    }

    setFile(file);
    
    // In a real app, parse the CSV here
    // For demo, use mock data
    setPreview(mockCSVPreview);
    
    toast.success('파일이 성공적으로 업로드되었습니다');
  };

  const handleUpload = () => {
    if (!file || preview.length === 0) return;

    const columns = Object.keys(preview[0]);
    
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
    setFile(null);
    setPreview([]);
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
                    {Object.keys(preview[0] || {}).map((column) => (
                      <TableHead key={column}>{column}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.map((row, index) => (
                    <TableRow key={index}>
                      {Object.values(row).map((value: any, cellIndex) => (
                        <TableCell key={cellIndex}>{value}</TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <Button onClick={handleUpload} className="flex-1">
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
