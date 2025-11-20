import { usePermissions } from '../../hooks/usePermissions';
import { useTraceSummary } from '../../hooks/useTraceSummary';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { AuditLog } from './AuditLog';
import { CaptureConsole } from './CaptureConsole';
import {
  Activity,
  AlertTriangle,
  Terminal,
  File,
  Network,
  Shield,
  Lock,
  TrendingUp,
  Database,
  ArrowLeft,
} from 'lucide-react';
import { useStore } from '../../store/useStore';

interface TraceDetailPageProps {
  onNavigateBack?: () => void;
}

export function TraceDetailPage({ onNavigateBack }: TraceDetailPageProps) {
  const { canAccessTrace, isAdmin, role } = usePermissions();
  const { summary } = useTraceSummary(10000);
  const { user } = useStore();

  // Permission check
  if (!canAccessTrace()) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <Card className="p-12 max-w-md text-center">
          <Lock className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-gray-900 mb-2">접근 권한 없음</h2>
          <p className="text-sm text-gray-600 mb-4">
            TraceAgent는 관리자 전용 기능입니다.
          </p>
          <div className="bg-gray-50 p-4 rounded-lg text-left">
            <p className="text-xs text-gray-600 mb-1">현재 역할: <strong>{role}</strong></p>
            <p className="text-xs text-gray-600">필요 권한: <strong>ADMIN</strong></p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#1c1c1e] transition-colors p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-1">
            {onNavigateBack && (
              <Button
                variant="outline"
                onClick={onNavigateBack}
                className="gap-2 shrink-0"
              >
                <ArrowLeft className="w-4 h-4" />
                대화로 돌아가기
              </Button>
            )}
            <div>
              <h1 className="text-gray-900 dark:text-gray-100 mb-2">TraceAgent 관리 콘솔</h1>
              <p className="text-gray-600 dark:text-gray-400">
                eBPF 기반 시스템 이벤트 모니터링 및 보안 관제
              </p>
            </div>
          </div>
          <div className="text-right shrink-0">
            <Badge variant="default" className="mb-2">
              <Shield className="w-3 h-3 mr-1" />
              ADMIN
            </Badge>
            <p className="text-sm text-gray-600 dark:text-gray-400">{user?.name}</p>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center justify-between mb-2">
              <Terminal className="w-8 h-8 text-blue-600" />
              <Badge variant="secondary">{summary?.totalEvents || 0}</Badge>
            </div>
            <p className="text-sm text-gray-600">총 이벤트</p>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between mb-2">
              <AlertTriangle className="w-8 h-8 text-orange-600" />
              <Badge variant="destructive">{summary?.suspiciousCount || 0}</Badge>
            </div>
            <p className="text-sm text-gray-600">의심 이벤트</p>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between mb-2">
              <Activity className="w-8 h-8 text-green-600" />
              <Badge variant="default">실시간</Badge>
            </div>
            <p className="text-sm text-gray-600">모니터링 상태</p>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between mb-2">
              <Database className="w-8 h-8 text-purple-600" />
              <Badge variant="secondary">S1</Badge>
            </div>
            <p className="text-sm text-gray-600">운영 모드</p>
          </Card>
        </div>

        {/* Top Processes */}
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-blue-600" />
            <h3 className="text-gray-900">주요 프로세스 (Top Processes)</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {summary?.topProcesses.slice(0, 6).map((proc, index) => (
              <div
                key={index}
                className="p-4 bg-gray-50 rounded-lg flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                    <span className="text-sm text-blue-600">#{index + 1}</span>
                  </div>
                  <div>
                    <p className="text-sm text-gray-900">{proc.name}</p>
                    <p className="text-xs text-gray-500">{proc.count} 이벤트</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Tabs */}
        <Tabs defaultValue="capture" className="space-y-4">
          <TabsList>
            <TabsTrigger value="capture">
              <Terminal className="w-4 h-4 mr-2" />
              온디맨드 캡처
            </TabsTrigger>
            <TabsTrigger value="audit">
              <Shield className="w-4 h-4 mr-2" />
              감사 로그
            </TabsTrigger>
            <TabsTrigger value="events">
              <Activity className="w-4 h-4 mr-2" />
              이벤트 히스토리
            </TabsTrigger>
          </TabsList>

          <TabsContent value="capture">
            <CaptureConsole />
          </TabsContent>

          <TabsContent value="audit">
            <AuditLog />
          </TabsContent>

          <TabsContent value="events">
            <Card className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-5 h-5 text-blue-600" />
                <h3 className="text-gray-900">최근 이벤트</h3>
              </div>
              <div className="space-y-2">
                {summary?.recentEvents.map((event, index) => (
                  <div
                    key={index}
                    className={`p-3 rounded-lg border ${
                      event.suspicious
                        ? 'bg-orange-50 border-orange-200'
                        : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {event.type === 'exec' && <Terminal className="w-4 h-4 text-blue-600" />}
                        {event.type === 'open' && <File className="w-4 h-4 text-green-600" />}
                        {event.type === 'tcp_connect' && <Network className="w-4 h-4 text-purple-600" />}
                        <div>
                          <p className="text-sm text-gray-900">{event.process}</p>
                          <p className="text-xs text-gray-500">
                            {new Date(event.timestamp).toLocaleString('ko-KR')}
                          </p>
                        </div>
                      </div>
                      {event.suspicious && (
                        <Badge variant="destructive" className="text-xs">
                          <AlertTriangle className="w-3 h-3 mr-1" />
                          의심
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
