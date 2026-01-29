import { Card } from '../../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '../../components/ui/alert-dialog';
import { Button } from '../../components/ui/button';
import { Trash2 } from 'lucide-react';

export type Dataset = {
  id: string;
  name: string;
  createdAt: string;
  rows: any[];
  columns: string[];
  meta?: Record<string, any>;
};

interface DatasetSectionProps {
  datasets: Dataset[];
  selectedId: string | null;
  setSelectedId: (id: string | null) => void;
  onDelete: (id: string) => void;
}

export function DatasetSection({ datasets, selectedId, setSelectedId, onDelete }: DatasetSectionProps) {
  const selectedDataset = datasets.find((d) => d.id === selectedId) || null;

  return (
    <div className="space-y-6">
      <Card className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-gray-900">데이터셋 목록</h3>
          {selectedDataset && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive">
                  <Trash2 className="w-4 h-4 mr-2" /> 삭제
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>데이터셋을 삭제할까요?</AlertDialogTitle>
                  <AlertDialogDescription>
                    이 작업은 UI 목록에서만 제거합니다. 실제 데이터 삭제는 백엔드 연결 후 적용됩니다.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>취소</AlertDialogCancel>
                  <AlertDialogAction onClick={() => onDelete(selectedDataset.id)}>삭제</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>

        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>dataset_id</TableHead>
                <TableHead>이름</TableHead>
                <TableHead>생성일</TableHead>
                <TableHead>행 수</TableHead>
                <TableHead>컬럼</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {datasets.map((ds) => (
                <TableRow key={ds.id} className={selectedId === ds.id ? 'bg-gray-50' : ''} onClick={() => setSelectedId(ds.id)}>
                  <TableCell className="font-medium">{ds.id}</TableCell>
                  <TableCell>{ds.name}</TableCell>
                  <TableCell>{new Date(ds.createdAt).toLocaleString()}</TableCell>
                  <TableCell>{ds.rows.length}</TableCell>
                  <TableCell>{ds.columns.join(', ')}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="p-4 space-y-2">
          <h3 className="text-gray-900">데이터셋 상세</h3>
          {!selectedDataset ? (
            <p className="text-gray-600">목록에서 데이터셋을 선택하세요.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-500 mb-1">dataset_id</div>
                <div className="text-gray-900">{selectedDataset.id}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500 mb-1">이름</div>
                <div className="text-gray-900">{selectedDataset.name}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500 mb-1">생성일</div>
                <div className="text-gray-900">{new Date(selectedDataset.createdAt).toLocaleString()}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500 mb-1">행 수</div>
                <div className="text-gray-900">{selectedDataset.rows.length}</div>
              </div>
            </div>
          )}
        </Card>

        <Card className="p-4 space-y-2">
          <h3 className="text-gray-900">메타데이터 조회</h3>
          {!selectedDataset ? (
            <p className="text-gray-600">목록에서 데이터셋을 선택하세요.</p>
          ) : (
            <div>
              <div className="text-sm text-gray-500 mb-2">컬럼 목록</div>
              <ul className="list-disc pl-6 text-gray-900">
                {selectedDataset.columns.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
              {selectedDataset.meta && (
                <pre className="text-sm bg-gray-50 p-3 rounded border border-gray-200 overflow-auto mt-3">{JSON.stringify(selectedDataset.meta, null, 2)}</pre>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

