import { useState } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Badge } from '../ui/badge';
import { useStore } from '../../store/useStore';
import { mockAnalysisResult } from '../../lib/mockData';
import { Play, Loader2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner@2.0.3';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ScatterChart, Scatter, Cell } from 'recharts';

export function Analysis() {
  const { uploadedFile, analysisResult, setAnalysisResult, isAnalyzing, setIsAnalyzing } = useStore();
  const [activeTab, setActiveTab] = useState('eda');

  const handleStartAnalysis = () => {
    if (!uploadedFile) {
      toast.error('먼저 Upload 탭에서 파일을 업로드하세요');
      return;
    }

    setIsAnalyzing(true);
    
    // Simulate analysis delay
    setTimeout(() => {
      setAnalysisResult(mockAnalysisResult);
      setIsAnalyzing(false);
      toast.success('분석이 완료되었습니다');
    }, 2000);
  };

  if (!uploadedFile) {
    return (
      <div className="p-8">
        <div className="mb-8">
          <h2 className="text-gray-900 mb-2">Analysis</h2>
          <p className="text-gray-600">데이터 분석 결과를 확인하세요</p>
        </div>
        <Card className="p-12 text-center">
          <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <h3 className="text-gray-900 mb-2">업로드된 데이터가 없습니다</h3>
          <p className="text-gray-500 mb-6">Upload 탭에서 먼저 CSV 파일을 업로드하세요</p>
        </Card>
      </div>
    );
  }

  if (!analysisResult) {
    return (
      <div className="p-8">
        <div className="mb-8">
          <h2 className="text-gray-900 mb-2">Analysis</h2>
          <p className="text-gray-600">데이터 분석 결과를 확인하세요</p>
        </div>
        <Card className="p-12 text-center">
          <div className="bg-blue-50 text-blue-600 p-4 rounded-full w-20 h-20 mx-auto mb-4 flex items-center justify-center">
            <Play className="w-10 h-10" />
          </div>
          <h3 className="text-gray-900 mb-2">분석 준비 완료</h3>
          <p className="text-gray-500 mb-6">
            파일: {uploadedFile.name} ({uploadedFile.rowCount} rows)
          </p>
          <Button onClick={handleStartAnalysis} disabled={isAnalyzing}>
            {isAnalyzing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                분석 중...
              </>
            ) : (
              '분석 시작'
            )}
          </Button>
        </Card>
      </div>
    );
  }

  const distributionData = analysisResult.eda.distributions.map(d => ({
    name: d.name,
    mean: d.mean,
    median: d.median,
    std: d.std,
  }));

  const severityColors: { [key: string]: string } = {
    High: '#ef4444',
    Medium: '#f59e0b',
    Low: '#3b82f6',
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-gray-900 mb-2">Analysis</h2>
        <p className="text-gray-600">EDA 및 이상 탐지 결과</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="eda">EDA</TabsTrigger>
          <TabsTrigger value="anomaly">이상 탐지</TabsTrigger>
        </TabsList>

        <TabsContent value="eda" className="space-y-6">
          {/* Summary Card */}
          <Card className="p-6">
            <h3 className="text-gray-900 mb-4">데이터 요약</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-600">총 행 수</p>
                <p className="text-gray-900 mt-1">{analysisResult.eda.summary.totalRows}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">총 열 수</p>
                <p className="text-gray-900 mt-1">{analysisResult.eda.summary.totalColumns}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">기간</p>
                <p className="text-gray-900 mt-1">{analysisResult.eda.summary.dateRange}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">결측치</p>
                <p className="text-gray-900 mt-1">{analysisResult.eda.summary.missingValues}</p>
              </div>
            </div>
          </Card>

          {/* Distributions */}
          <Card className="p-6">
            <h3 className="text-gray-900 mb-4">분포 통계</h3>
            <div className="mb-6">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={distributionData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="mean" fill="#3b82f6" name="평균" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="median" fill="#10b981" name="중앙값" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>변수</TableHead>
                  <TableHead>최소</TableHead>
                  <TableHead>최대</TableHead>
                  <TableHead>평균</TableHead>
                  <TableHead>중앙값</TableHead>
                  <TableHead>표준편차</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {analysisResult.eda.distributions.map((dist, index) => (
                  <TableRow key={index}>
                    <TableCell>{dist.name}</TableCell>
                    <TableCell>{dist.min}</TableCell>
                    <TableCell>{dist.max}</TableCell>
                    <TableCell>{dist.mean}</TableCell>
                    <TableCell>{dist.median}</TableCell>
                    <TableCell>{dist.std}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>

          {/* Correlations */}
          <Card className="p-6">
            <h3 className="text-gray-900 mb-4">상관관계 분석</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>변수 1</TableHead>
                  <TableHead>변수 2</TableHead>
                  <TableHead>상관계수</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {analysisResult.eda.correlations.map((corr, index) => (
                  <TableRow key={index}>
                    <TableCell>{corr.var1}</TableCell>
                    <TableCell>{corr.var2}</TableCell>
                    <TableCell>
                      <Badge variant={Math.abs(corr.correlation) > 0.5 ? 'default' : 'secondary'}>
                        {corr.correlation.toFixed(2)}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        <TabsContent value="anomaly" className="space-y-6">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-gray-900">이상 탐지 결과</h3>
              <Badge variant="destructive">
                {analysisResult.anomalies.detected}건 감지
              </Badge>
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>시간</TableHead>
                  <TableHead>설비 ID</TableHead>
                  <TableHead>유형</TableHead>
                  <TableHead>심각도</TableHead>
                  <TableHead>값</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {analysisResult.anomalies.items.map((anomaly, index) => (
                  <TableRow key={index}>
                    <TableCell>{anomaly.timestamp}</TableCell>
                    <TableCell>{anomaly.machine_id}</TableCell>
                    <TableCell>{anomaly.type}</TableCell>
                    <TableCell>
                      <Badge 
                        variant={anomaly.severity === 'High' ? 'destructive' : 'secondary'}
                        style={{ 
                          backgroundColor: anomaly.severity === 'High' ? undefined : severityColors[anomaly.severity] + '20',
                          color: severityColors[anomaly.severity]
                        }}
                      >
                        {anomaly.severity}
                      </Badge>
                    </TableCell>
                    <TableCell>{anomaly.value}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
