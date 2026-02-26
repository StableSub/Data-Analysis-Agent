import { useState } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { useStore } from '../../store/useStore';
import { FileText, Download, Loader2, Send, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { Separator } from '../ui/separator';

export function Report() {
  const { analysisResult, report, setReport } = useStore();
  const [isGenerating, setIsGenerating] = useState(false);
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState<Array<{ role: 'user' | 'assistant', content: string }>>([]);
  const [isAsking, setIsAsking] = useState(false);

  const handleGenerateReport = () => {
    if (!analysisResult) {
      toast.error('먼저 Analysis 탭에서 분석을 완료하세요');
      return;
    }

    setIsGenerating(true);

    // Simulate report generation
    setTimeout(() => {
      setReport('데이터 분석이 완료되었습니다. 관측된 모든 지표가 정상 범위 내에 있습니다.');
      setIsGenerating(false);
      toast.success('리포트가 생성되었습니다');
    }, 2000);
  };

  const handleDownloadPDF = () => {
    if (!report) return;

    // In a real app, this would generate and download a PDF
    toast.success('PDF 다운로드 시작 (데모 모드)');
  };

  const handleAskQuestion = () => {
    if (!question.trim() || !analysisResult) return;

    setIsAsking(true);
    const userMessage = question;

    setChatHistory(prev => [...prev, { role: 'user', content: userMessage }]);
    setQuestion('');

    // Simulate answer generation
    setTimeout(() => {
      const answer = '분석된 데이터에 따르면 현재 시스템은 안정적인 상태를 유지하고 있습니다. 구체적으로 궁금한 지표가 있으신가요?';

      setChatHistory(prev => [...prev, { role: 'assistant', content: answer }]);
      setIsAsking(false);
    }, 1500);
  };

  if (!analysisResult) {
    return (
      <div className="p-8">
        <div className="mb-8">
          <h2 className="text-gray-900 mb-2">Report</h2>
          <p className="text-gray-600">AI 생성 리포트 및 질의응답</p>
        </div>
        <Card className="p-12 text-center">
          <FileText className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <h3 className="text-gray-900 mb-2">분석 결과가 없습니다</h3>
          <p className="text-gray-500">Analysis 탭에서 먼저 데이터를 분석하세요</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-gray-900 mb-2">Report</h2>
        <p className="text-gray-600">AI 생성 리포트 및 질의응답</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report Section */}
        <div className="lg:col-span-2 space-y-6">
          {!report ? (
            <Card className="p-12 text-center">
              <div className="bg-purple-50 text-purple-600 p-4 rounded-full w-20 h-20 mx-auto mb-4 flex items-center justify-center">
                <Sparkles className="w-10 h-10" />
              </div>
              <h3 className="text-gray-900 mb-2">리포트 생성 준비</h3>
              <p className="text-gray-500 mb-6">
                LLM을 사용하여 분석 결과를 자동으로 요약합니다
              </p>
              <Button onClick={handleGenerateReport} disabled={isGenerating}>
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    생성 중...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    리포트 생성
                  </>
                )}
              </Button>
            </Card>
          ) : (
            <>
              <Card className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-gray-900">생성된 리포트</h3>
                  <Button onClick={handleDownloadPDF} variant="outline" size="sm">
                    <Download className="w-4 h-4 mr-2" />
                    PDF 다운로드
                  </Button>
                </div>
                <div className="prose prose-sm max-w-none">
                  <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">
                    {report}
                  </div>
                </div>
              </Card>
            </>
          )}
        </div>

        {/* Q&A Section */}
        <div className="space-y-6">
          <Card className="p-6">
            <h3 className="text-gray-900 mb-4">질의응답</h3>

            {/* Chat History */}
            <div className="space-y-4 mb-4 max-h-96 overflow-y-auto">
              {chatHistory.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-sm text-gray-500">분석 결과에 대해 질문하세요</p>
                </div>
              ) : (
                chatHistory.map((message, index) => (
                  <div
                    key={index}
                    className={`p-3 rounded-lg ${message.role === 'user'
                      ? 'bg-blue-50 text-blue-900 ml-4'
                      : 'bg-gray-50 text-gray-900 mr-4'
                      }`}
                  >
                    <p className="text-xs mb-1 opacity-70">
                      {message.role === 'user' ? '질문' : 'AI 답변'}
                    </p>
                    <p className="text-sm">{message.content}</p>
                  </div>
                ))
              )}
            </div>

            <Separator className="my-4" />

            {/* Input */}
            <div className="space-y-3">
              <Textarea
                placeholder="예: M001 설비의 온도 상승 원인은 무엇인가요?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleAskQuestion();
                  }
                }}
                rows={3}
              />
              <Button
                onClick={handleAskQuestion}
                disabled={!question.trim() || isAsking}
                className="w-full"
              >
                {isAsking ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    답변 생성 중...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4 mr-2" />
                    질문하기
                  </>
                )}
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
