import { useAgentStatus } from '../../hooks/useAgentStatus';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Bot, CheckCircle2, Clock, Zap, Brain, FileSearch, BarChart, X } from 'lucide-react';
import { ScrollArea } from '../ui/scroll-area';
import { Skeleton } from '../ui/skeleton';

interface AgentWidgetProps {
  onClose?: () => void;
}

export function AgentWidget({ onClose }: AgentWidgetProps) {
  const { status, isLoading, error } = useAgentStatus(10000);

  const getTaskIcon = (type: string) => {
    switch (type) {
      case 'analysis':
        return BarChart;
      case 'search':
        return FileSearch;
      case 'thinking':
        return Brain;
      default:
        return Zap;
    }
  };

  return (
    <div className="w-80 h-screen bg-white dark:bg-[#2c2c2e] border-l border-gray-200 dark:border-white/10 flex flex-col transition-colors">
      <div className="p-4 border-b border-gray-200 dark:border-white/10 flex-shrink-0">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4 text-blue-600 dark:text-[#0a84ff]" />
            <h3 className="text-gray-900 dark:text-white">AI Agent</h3>
          </div>
          {onClose && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="h-7 w-7 hover:bg-gray-100 dark:hover:bg-white/10"
            >
              <X className="w-4 h-4 text-gray-500 dark:text-[#98989d]" />
            </Button>
          )}
        </div>
        <p className="text-xs text-gray-500 dark:text-[#98989d]">실시간 처리 상태</p>
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
          ) : status ? (
            <>
              {/* Status Summary */}
              <Card className="p-4 dark:bg-[#3a3a3c] dark:border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600 dark:text-white">처리된 작업</span>
                  <Badge variant="secondary">{status.totalTasks}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-white">진행 중</span>
                  <Badge variant={status.activeTasks > 0 ? 'default' : 'secondary'}>
                    {status.activeTasks}
                  </Badge>
                </div>
              </Card>

              {/* Agent Capabilities */}
              <Card className="p-4 dark:bg-[#3a3a3c] dark:border-white/10">
                <h4 className="text-sm text-gray-900 dark:text-white mb-3">활성 기능</h4>
                <div className="space-y-2">
                  {status.capabilities.map((capability, index) => (
                    <div key={index} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                          capability.status === 'active' 
                            ? 'bg-blue-600 dark:bg-[#0a84ff] animate-pulse' 
                            : 'bg-gray-400 dark:bg-gray-600'
                        }`} />
                        <span className="text-gray-700 dark:text-white truncate">{capability.name}</span>
                      </div>
                      <span className={`ml-2 text-xs ${
                        capability.status === 'active'
                          ? 'text-blue-600 dark:text-[#0a84ff]'
                          : 'text-gray-500 dark:text-[#98989d]'
                      }`}>
                        {capability.status}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Recent Activities */}
              <Card className="p-4 dark:bg-[#3a3a3c] dark:border-white/10">
                <h4 className="text-sm text-gray-900 dark:text-white mb-3">최근 활동</h4>
                <div className="space-y-2.5">
                  {status.recentActivities.map((activity, index) => {
                    const Icon = getTaskIcon(activity.type);
                    return (
                      <div
                        key={index}
                        className={`p-3 rounded-lg transition-all ${
                          activity.status === 'active'
                            ? 'bg-blue-50 dark:bg-[#0a84ff]/10 border border-blue-200 dark:border-[#0a84ff]/30'
                            : 'bg-gray-50 dark:bg-[#1c1c1e] border border-transparent'
                        }`}
                      >
                        <div className="flex items-start gap-2.5">
                          <div className={`flex items-center justify-center w-6 h-6 rounded-md flex-shrink-0 ${
                            activity.status === 'active'
                              ? 'bg-blue-100 dark:bg-[#0a84ff]/20'
                              : 'bg-gray-200 dark:bg-[#2c2c2e]'
                          }`}>
                            <Icon className={`w-3.5 h-3.5 ${
                              activity.status === 'active'
                                ? 'text-blue-600 dark:text-[#0a84ff]'
                                : 'text-gray-500 dark:text-[#98989d]'
                            }`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`text-xs font-medium ${
                                activity.status === 'active'
                                  ? 'text-blue-700 dark:text-[#0a84ff]'
                                  : 'text-gray-600 dark:text-white'
                              }`}>
                                {activity.type === 'analysis' ? '분석' : 
                                 activity.type === 'search' ? '검색' :
                                 activity.type === 'thinking' ? '사고' : '처리'}
                              </span>
                              {activity.status === 'active' && (
                                <div className="flex items-center gap-1">
                                  <div className="w-1.5 h-1.5 rounded-full bg-blue-600 dark:bg-[#0a84ff] animate-pulse" />
                                  <span className="text-xs text-blue-600 dark:text-[#0a84ff]">진행중</span>
                                </div>
                              )}
                              {activity.status === 'completed' && (
                                <CheckCircle2 className="w-3 h-3 text-green-600 dark:text-green-400" />
                              )}
                            </div>
                            <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                              {activity.description}
                            </p>
                            <p className="text-xs text-gray-400 dark:text-[#98989d] mt-1.5">
                              {new Date(activity.timestamp).toLocaleTimeString('ko-KR', {
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
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
