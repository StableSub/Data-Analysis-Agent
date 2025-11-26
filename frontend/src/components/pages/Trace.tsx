import { useEffect } from 'react';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { useStore } from '../../store/useStore';
import { mockTraceEvents, mockDashboardStats } from '../../lib/mockData';
import { Activity, AlertTriangle, Terminal, Network, File } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';

export function Trace() {
  const { traceEvents, setTraceEvents } = useStore();

  useEffect(() => {
    // Initialize with mock data
    if (traceEvents.length === 0) {
      setTraceEvents(mockTraceEvents);
    }

    // Simulate real-time updates every 10 seconds
    const interval = setInterval(() => {
      const newEvent = {
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        type: ['exec', 'open', 'tcp_connect'][Math.floor(Math.random() * 3)] as 'exec' | 'open' | 'tcp_connect',
        process: ['python3', 'node', 'analyze_data'][Math.floor(Math.random() * 3)],
        details: 'System activity detected',
        suspicious: Math.random() > 0.9,
      };
      
      setTraceEvents([newEvent, ...traceEvents.slice(0, 99)]);
    }, 10000);

    return () => clearInterval(interval);
  }, [traceEvents, setTraceEvents]);

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

  const suspiciousEvents = traceEvents.filter(e => e.suspicious);
  const topProcesses = mockDashboardStats.topProcesses;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-gray-900 mb-2">Trace</h2>
        <p className="text-gray-600">시스템 이벤트 실시간 모니터링</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">총 이벤트</p>
              <p className="text-gray-900">{traceEvents.length}</p>
            </div>
            <div className="bg-blue-50 text-blue-600 p-3 rounded-lg">
              <Activity className="w-6 h-6" />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">의심 이벤트</p>
              <p className="text-orange-600">{suspiciousEvents.length}</p>
            </div>
            <div className="bg-orange-50 text-orange-600 p-3 rounded-lg">
              <AlertTriangle className="w-6 h-6" />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div>
            <p className="text-sm text-gray-600 mb-2">주요 프로세스</p>
            <div className="space-y-1">
              {topProcesses.slice(0, 3).map((process, index) => (
                <div key={index} className="flex items-center justify-between text-sm">
                  <span className="text-gray-700">{process.name}</span>
                  <span className="text-gray-500">{process.count}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* Events Table */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-gray-900">최근 이벤트</h3>
          <Badge variant="secondary">10초마다 자동 갱신</Badge>
        </div>

        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>시간</TableHead>
                <TableHead>유형</TableHead>
                <TableHead>프로세스</TableHead>
                <TableHead>상세</TableHead>
                <TableHead>상태</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {traceEvents.map((event, index) => {
                const Icon = getEventIcon(event.type);
                return (
                  <TableRow key={index} className={event.suspicious ? 'bg-orange-50' : ''}>
                    <TableCell className="text-sm">{event.timestamp}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Icon className="w-4 h-4 text-gray-500" />
                        <span className="text-sm">{event.type}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{event.process}</TableCell>
                    <TableCell className="text-sm text-gray-600">{event.details}</TableCell>
                    <TableCell>
                      {event.suspicious ? (
                        <Badge variant="destructive">
                          <AlertTriangle className="w-3 h-3 mr-1" />
                          의심
                        </Badge>
                      ) : (
                        <Badge variant="secondary">정상</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  );
}
