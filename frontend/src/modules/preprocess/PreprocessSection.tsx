import { Card } from '../../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Button } from '../../components/ui/button';

interface PreprocessSectionProps {
  inputId: string;
  setInputId: (v: string) => void;
  previewCols: string[];
  previewRows: any[];
  onPreviewCall: () => void;
}

export function PreprocessSection({ inputId, setInputId, previewCols, previewRows, onPreviewCall }: PreprocessSectionProps) {
  return (
    <Card className="p-4 space-y-4">
      <h3 className="text-gray-900">전처리 · 미리보기</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
        <div className="md:col-span-2">
          <Label htmlFor="datasetId">dataset_id 입력</Label>
          <Input id="datasetId" placeholder="예: demo-sales" value={inputId} onChange={(e) => setInputId(e.target.value)} />
        </div>
        <div>
          <Button onClick={onPreviewCall}>미리보기 호출</Button>
        </div>
      </div>

      {previewRows.length > 0 ? (
        <div>
          <h4 className="text-gray-900 mb-2">미리보기 (상위 5행)</h4>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {previewCols.map((c) => (
                    <TableHead key={c}>{c}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {previewRows.map((row, i) => (
                  <TableRow key={i}>
                    {previewCols.map((c) => (
                      <TableCell key={c}>{String(row[c])}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      ) : (
        <p className="text-gray-600">dataset_id를 입력하고 미리보기를 눌러주세요. (현재는 데모 데이터만 제공)</p>
      )}
    </Card>
  );
}

