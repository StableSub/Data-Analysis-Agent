import { useState } from 'react';
import { Upload, X, FileText, Database, File, Check } from 'lucide-react';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Badge } from '../ui/badge';

interface WorkbenchUploadProps {
  onClose: () => void;
  onUpload: (file: File, type: 'dataset' | 'document') => void;
}

/**
 * workbench 스타일 파일 업로드 컴포넌트
 * - 데이터셋 탭: CSV, XLSX
 * - 문서 탭: PDF, DOCX
 */
export function WorkbenchUpload({ onClose, onUpload }: WorkbenchUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [activeTab, setActiveTab] = useState<'dataset' | 'document'>('dataset');

  const handleDrop = (e: React.DragEvent, type: 'dataset' | 'document') => {
    e.preventDefault();
    setDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      onUpload(files[0], type);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>, type: 'dataset' | 'document') => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onUpload(files[0], type);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl bg-white dark:bg-[#1e1e1e] border-gray-200 dark:border-white/10 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-white/10">
          <div>
            <h2 className="text-xl text-gray-900 dark:text-white">소스 추가</h2>
            <p className="text-sm text-gray-500 dark:text-[#98989d] mt-1">
              분석할 데이터셋 또는 참고할 문서를 업로드하세요
            </p>
          </div>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Tabs */}
        <div className="p-6">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'dataset' | 'document')}>
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="dataset" className="flex items-center gap-2">
                <Database className="w-4 h-4" />
                <span>데이터셋</span>
              </TabsTrigger>
              <TabsTrigger value="document" className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                <span>문서</span>
              </TabsTrigger>
            </TabsList>

            {/* Dataset Tab */}
            <TabsContent value="dataset" className="space-y-4">
              <div
                className={`
                  border-2 border-dashed rounded-xl p-12 text-center transition-all
                  ${dragOver 
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20' 
                    : 'border-gray-300 dark:border-white/20 hover:border-blue-400 dark:hover:border-blue-600'
                  }
                `}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => handleDrop(e, 'dataset')}
              >
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/30 mb-4">
                  <Database className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                </div>
                
                <h3 className="text-lg text-gray-900 dark:text-white mb-2">
                  데이터셋 파일 업로드
                </h3>
                
                <p className="text-gray-600 dark:text-gray-400 mb-4">
                  CSV 또는 XLSX 파일을 드래그하여 놓거나
                </p>
                
                <label className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 dark:bg-[#0a84ff] dark:hover:bg-[#0077ed] text-white rounded-lg cursor-pointer transition-colors">
                  <Upload className="w-5 h-5" />
                  <span>파일 선택</span>
                  <input
                    type="file"
                    className="hidden"
                    accept=".csv,.xlsx,.xls"
                    onChange={(e) => handleFileInput(e, 'dataset')}
                  />
                </label>
                
                <div className="mt-6 flex items-center justify-center gap-4">
                  <Badge variant="secondary" className="gap-1">
                    <Check className="w-3 h-3" />
                    CSV
                  </Badge>
                  <Badge variant="secondary" className="gap-1">
                    <Check className="w-3 h-3" />
                    XLSX
                  </Badge>
                  <Badge variant="secondary" className="gap-1">
                    <Check className="w-3 h-3" />
                    XLS
                  </Badge>
                </div>
                
                <p className="text-xs text-gray-500 dark:text-[#98989d] mt-4">
                  최대 파일 크기: 100MB
                </p>
              </div>

              <div className="bg-blue-50 dark:bg-blue-900/10 rounded-lg p-4">
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  💡 <span className="font-medium">데이터셋</span>은 분석, 시각화, 통계 처리에 사용됩니다.
                </p>
              </div>
            </TabsContent>

            {/* Document Tab */}
            <TabsContent value="document" className="space-y-4">
              <div
                className={`
                  border-2 border-dashed rounded-xl p-12 text-center transition-all
                  ${dragOver 
                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-950/20' 
                    : 'border-gray-300 dark:border-white/20 hover:border-purple-400 dark:hover:border-purple-600'
                  }
                `}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => handleDrop(e, 'document')}
              >
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-purple-100 dark:bg-purple-900/30 mb-4">
                  <FileText className="w-8 h-8 text-purple-600 dark:text-purple-400" />
                </div>
                
                <h3 className="text-lg text-gray-900 dark:text-white mb-2">
                  문서 파일 업로드
                </h3>
                
                <p className="text-gray-600 dark:text-gray-400 mb-4">
                  PDF 또는 DOCX 파일을 드래그하여 놓거나
                </p>
                
                <label className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 dark:bg-purple-500 dark:hover:bg-purple-600 text-white rounded-lg cursor-pointer transition-colors">
                  <Upload className="w-5 h-5" />
                  <span>파일 선택</span>
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf,.docx,.doc,.txt,.md"
                    onChange={(e) => handleFileInput(e, 'document')}
                  />
                </label>
                
                <div className="mt-6 flex items-center justify-center gap-4">
                  <Badge variant="secondary" className="gap-1 bg-purple-100 dark:bg-purple-900/30">
                    <Check className="w-3 h-3" />
                    PDF
                  </Badge>
                  <Badge variant="secondary" className="gap-1 bg-purple-100 dark:bg-purple-900/30">
                    <Check className="w-3 h-3" />
                    DOCX
                  </Badge>
                  <Badge variant="secondary" className="gap-1 bg-purple-100 dark:bg-purple-900/30">
                    <Check className="w-3 h-3" />
                    TXT
                  </Badge>
                </div>
                
                <p className="text-xs text-gray-500 dark:text-[#98989d] mt-4">
                  최대 파일 크기: 50MB
                </p>
              </div>

              <div className="bg-purple-50 dark:bg-purple-900/10 rounded-lg p-4">
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  📄 <span className="font-medium">문서</span>는 RAG를 통해 참조 자료로 활용됩니다. (매뉴얼, 가이드 등)
                </p>
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-[#2c2c2e] border-t border-gray-200 dark:border-white/10 rounded-b-lg">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 dark:text-[#98989d]">
              업로드된 파일은 현재 대화에만 저장됩니다
            </p>
            <Button variant="ghost" onClick={onClose}>
              취소
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}

