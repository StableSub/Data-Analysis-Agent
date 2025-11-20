import { useState } from 'react';
import { Upload, FileSpreadsheet, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription } from '../ui/alert';

export function DataUploadFeature() {
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setUploadedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setUploadedFile(e.target.files[0]);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-white/10">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <Upload className="w-5 h-5 text-blue-600 dark:text-[#0a84ff]" />
          </div>
          <div>
            <h2 className="text-gray-900 dark:text-white text-xl">데이터 업로드</h2>
            <p className="text-sm text-gray-500 dark:text-[#98989d]">
              제조 데이터 파일을 업로드하여 분석을 시작하세요
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Info Alert */}
          <Alert className="border-blue-200 dark:border-blue-900/30 bg-blue-50 dark:bg-blue-900/10">
            <AlertCircle className="h-4 w-4 text-blue-600 dark:text-[#0a84ff]" />
            <AlertDescription className="text-blue-700 dark:text-blue-300">
              CSV, Excel (.xlsx, .xls) 파일을 지원합니다. 최대 파일 크기: 100MB
            </AlertDescription>
          </Alert>

          {/* Upload Area */}
          <Card className="p-8">
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`
                border-2 border-dashed rounded-xl p-12 text-center transition-all
                ${dragActive 
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/10' 
                  : 'border-gray-300 dark:border-white/20 hover:border-blue-400 dark:hover:border-[#0a84ff]/50'
                }
              `}
            >
              <div className="flex flex-col items-center gap-4">
                <div className={`
                  w-16 h-16 rounded-full flex items-center justify-center transition-colors
                  ${dragActive 
                    ? 'bg-blue-100 dark:bg-blue-900/30' 
                    : 'bg-gray-100 dark:bg-white/10'
                  }
                `}>
                  <FileSpreadsheet className={`
                    w-8 h-8 transition-colors
                    ${dragActive 
                      ? 'text-blue-600 dark:text-[#0a84ff]' 
                      : 'text-gray-400 dark:text-gray-500'
                    }
                  `} />
                </div>
                
                <div>
                  <p className="text-gray-700 dark:text-white mb-1">
                    파일을 드래그하여 업로드하거나
                  </p>
                  <label htmlFor="file-upload">
                    <span className="text-blue-600 dark:text-[#0a84ff] cursor-pointer hover:underline">
                      파일 선택
                    </span>
                  </label>
                  <input
                    id="file-upload"
                    type="file"
                    className="hidden"
                    accept=".csv,.xlsx,.xls"
                    onChange={handleFileChange}
                  />
                </div>
                
                <p className="text-sm text-gray-500 dark:text-[#98989d]">
                  CSV, XLSX, XLS
                </p>
              </div>
            </div>
          </Card>

          {/* Uploaded File Info */}
          {uploadedFile && (
            <Card className="p-6 bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-900/30">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-green-900 dark:text-green-100 font-medium mb-1">
                    파일 업로드 완료
                  </h3>
                  <p className="text-sm text-green-700 dark:text-green-300 mb-3">
                    {uploadedFile.name} ({(uploadedFile.size / 1024).toFixed(1)} KB)
                  </p>
                  <div className="flex gap-2">
                    <Button size="sm" className="bg-green-600 hover:bg-green-700">
                      분석 시작
                    </Button>
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => setUploadedFile(null)}
                      className="border-green-300 dark:border-green-700"
                    >
                      다른 파일 선택
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Recent Uploads */}
          <Card className="p-6">
            <h3 className="text-gray-900 dark:text-white font-medium mb-4">
              최근 업로드 파일
            </h3>
            <div className="space-y-3">
              {[
                { name: 'manufacturing_data_2024.csv', date: '2024.11.08', rows: '15,234' },
                { name: 'production_log.xlsx', date: '2024.11.05', rows: '8,912' },
                { name: 'quality_metrics.csv', date: '2024.11.03', rows: '12,456' },
              ].map((file, idx) => (
                <div 
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                    <div>
                      <p className="text-sm text-gray-700 dark:text-white">{file.name}</p>
                      <p className="text-xs text-gray-500 dark:text-[#98989d]">
                        {file.date} · {file.rows} rows
                      </p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">
                    불러오기
                  </Button>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
