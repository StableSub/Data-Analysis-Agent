import { useStore } from '../../store/useStore';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Shield, CheckCircle, XCircle } from 'lucide-react';

export function AuditLog() {
  const { auditLogs } = useStore();

  const getResultBadge = (result: 'success' | 'failure') => {
    if (result === 'success') {
      return (
        <Badge variant="default" className="bg-green-100 text-green-700 border-green-200">
          <CheckCircle className="w-3 h-3 mr-1" />
          성공
        </Badge>
      );
    }
    return (
      <Badge variant="destructive">
        <XCircle className="w-3 h-3 mr-1" />
        실패
      </Badge>
    );
  };

  return (
    <Card className="p-6">
      <div className="flex items-center gap-2 mb-4">
        <Shield className="w-5 h-5 text-blue-600" />
        <h3 className="text-gray-900">감사 로그 (Audit Log)</h3>
        <Badge variant="secondary" className="ml-auto">
          {auditLogs.length}개 항목
        </Badge>
      </div>

      {auditLogs.length === 0 ? (
        <div className="text-center py-12">
          <Shield className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-600">감사 로그가 없습니다</p>
        </div>
      ) : (
        <ScrollArea className="h-[500px]">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>시간</TableHead>
                <TableHead>사용자</TableHead>
                <TableHead>작업</TableHead>
                <TableHead>대상</TableHead>
                <TableHead>결과</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {auditLogs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="text-xs text-gray-600">
                    {new Date(log.timestamp).toLocaleString('ko-KR')}
                  </TableCell>
                  <TableCell className="text-sm">{log.user}</TableCell>
                  <TableCell>
                    <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                      {log.action}
                    </code>
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {log.target || '-'}
                  </TableCell>
                  <TableCell>{getResultBadge(log.result)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ScrollArea>
      )}
    </Card>
  );
}
