import { useTraceSummary } from '../../hooks/useTraceSummary';
import { usePermissions } from '../../hooks/usePermissions';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Activity, AlertTriangle, Terminal, File, Network, Lock } from 'lucide-react';
import { ScrollArea } from '../ui/scroll-area';
import { Skeleton } from '../ui/skeleton';

export function TraceWidget() {
  const { canAccessTrace } = usePermissions();
  const { summary, isLoading, error } = useTraceSummary(10000);
  
  // Permission check
  if (!canAccessTrace()) {
    return (
      <div className="w-80 bg-white dark:bg-[#2c2c2e] border-l border-gray-200 dark:border-white/10 flex flex-col transition-colors">
        <div className="p-4 border-b border-gray-200 dark:border-white/10">
          <div className="flex items-center gap-2 mb-1">
            <Activity className="w-4 h-4 text-gray-400 dark:text-[#98989d]" />
            <h3 className="text-gray-900 dark:text-white">Trace Monitor</h3>
          </div>
          <p className="text-xs text-gray-500 dark:text-[#98989d]">관리자 전용</p>
        </div>
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center">
            <Lock className="w-12 h-12 text-gray-300 dark:text-[#3a3a3c] mx-auto mb-3" />
            <p className="text-sm text-gray-600 dark:text-white mb-1">접근 권한 없음</p>
            <p className="text-xs text-gray-500 dark:text-[#98989d]">
              TraceAgent는 관리자 전용 기능입니다
            </p>
          </div>
        </div>
      </div>
    );
  }

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'exec':
        return Terminal;
      case 'open':
        return File;
      case 'tcp_connect':
        return Network;
      default:
        return Activity;
    }
  };

  return (
    <div className="w-80 bg-white dark:bg-[#2c2c2e] border-l border-gray-200 dark:border-white/10 flex flex-col transition-colors">
      <div className="p-4 border-b border-gray-200 dark:border-white/10">
        <div className="flex items-center gap-2 mb-1">
          <Activity className="w-4 h-4 text-blue-600 dark:text-[#0a84ff]" />
          <h3 className="text-gray-900 dark:text-white">Trace Monitor</h3>
        </div>
        <p className="text-xs text-gray-500 dark:text-[#98989d]">10초마다 자동 갱신</p>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {isLoading ? (
            <>
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-32 w-full" />
            </>
          ) : error ? (
            <Card className="p-4 bg-red-50 dark:bg-[#ff453a]/10 border-red-200 dark:border-[#ff453a]/30">
              <p className="text-sm text-red-600 dark:text-[#ff453a]">{error}</p>
            </Card>
          ) : summary ? (
            <>
              {/* Summary Cards */}
              <Card className="p-4 dark:bg-[#3a3a3c] dark:border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600 dark:text-white">총 이벤트</span>
                  <Badge variant="secondary">{summary.totalEvents}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-white">의심 이벤트</span>
                  <Badge variant={summary.suspiciousCount > 0 ? 'destructive' : 'secondary'}>
                    {summary.suspiciousCount}
                  </Badge>
                </div>
              </Card>

              {/* Top Processes */}
              <Card className="p-4 dark:bg-[#3a3a3c] dark:border-white/10">
                <h4 className="text-sm text-gray-900 dark:text-white mb-3">주요 프로세스</h4>
                <div className="space-y-2">
                  {summary.topProcesses.slice(0, 3).map((proc, index) => (
                    <div key={index} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <Terminal className="w-3 h-3 text-gray-400 dark:text-[#98989d] flex-shrink-0" />
                        <span className="text-gray-700 dark:text-white truncate">{proc.name}</span>
                      </div>
                      <span className="text-gray-500 dark:text-[#98989d] ml-2">{proc.count}</span>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Recent Events */}
              <Card className="p-4 dark:bg-[#3a3a3c] dark:border-white/10">
                <h4 className="text-sm text-gray-900 dark:text-white mb-3">최근 이벤트</h4>
                <div className="space-y-3">
                  {summary.recentEvents.map((event, index) => {
                    const Icon = getEventIcon(event.type);
                    return (
                      <div
                        key={index}
                        className={`p-2 rounded-lg ${
                          event.suspicious
                            ? 'bg-orange-50 dark:bg-[#ffd60a]/10 border border-orange-200 dark:border-[#ffd60a]/30'
                            : 'bg-gray-50 dark:bg-[#2c2c2e]'
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <Icon className="w-3 h-3 text-gray-500 dark:text-[#98989d] mt-0.5 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs text-gray-600 dark:text-white">{event.type}</span>
                              {event.suspicious && (
                                <AlertTriangle className="w-3 h-3 text-orange-500 dark:text-[#ffd60a]" />
                              )}
                            </div>
                            <p className="text-xs text-gray-700 dark:text-white truncate">{event.process}</p>
                            <p className="text-xs text-gray-400 dark:text-[#98989d] mt-1">
                              {new Date(event.timestamp).toLocaleTimeString('ko-KR')}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Card>
            </>
          ) : null}
        </div>
      </ScrollArea>
    </div>
  );
}
