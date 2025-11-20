import { FeatureNav } from '../layout/FeatureNav';
import { Upload, FileSpreadsheet, AlertCircle } from 'lucide-react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription } from '../ui/alert';

/**
 * 데이터 업로드 - 기본 상태
 * 피그마 디자인 참고용
 */
export function UploadDefault() {
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-[#1c1c1e]">
      {/* 좌측 네비게이션 */}
      <FeatureNav 
        activeFeature="data-upload"
        onFeatureChange={() => {}}
      />

      {/* 메인 컨텐츠 */}
      <div className="flex-1 h-full flex flex-col bg-white dark:bg-[#1c1c1e]">
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
              <div className="border-2 border-dashed border-gray-300 dark:border-white/20 rounded-xl p-12 text-center hover:border-blue-400 dark:hover:border-[#0a84ff]/50 transition-all cursor-pointer">
                <div className="flex flex-col items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-white/10 flex items-center justify-center">
                    <FileSpreadsheet className="w-8 h-8 text-gray-400 dark:text-gray-500" />
                  </div>
                  
                  <div>
                    <p className="text-gray-700 dark:text-white mb-1">
                      파일을 드래그하여 업로드하거나
                    </p>
                    <span className="text-blue-600 dark:text-[#0a84ff] cursor-pointer hover:underline">
                      파일 선택
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-500 dark:text-[#98989d]">
                    CSV, XLSX, XLS
                  </p>
                </div>
              </div>
            </Card>

            {/* Recent Uploads */}
            <Card className="p-6">
              <h3 className="text-gray-900 dark:text-white font-medium mb-4">
                최근 업로드 파일
              </h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                    <div>
                      <p className="text-sm text-gray-700 dark:text-white">manufacturing_data_2024.csv</p>
                      <p className="text-xs text-gray-500 dark:text-[#98989d]">
                        2024.11.08 · 15,234 rows
                      </p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">
                    불러오기
                  </Button>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                    <div>
                      <p className="text-sm text-gray-700 dark:text-white">production_log.xlsx</p>
                      <p className="text-xs text-gray-500 dark:text-[#98989d]">
                        2024.11.05 · 8,912 rows
                      </p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">
                    불러오기
                  </Button>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                    <div>
                      <p className="text-sm text-gray-700 dark:text-white">quality_metrics.csv</p>
                      <p className="text-xs text-gray-500 dark:text-[#98989d]">
                        2024.11.03 · 12,456 rows
                      </p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">
                    불러오기
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
