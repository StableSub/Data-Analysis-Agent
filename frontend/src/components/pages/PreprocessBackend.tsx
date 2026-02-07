import { useMemo, useState } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Checkbox } from '../ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { toast } from 'sonner';
import { apiRequest } from '../../lib/api';

type ColumnPreview = {
  name: string;
  dtype: string;
  missing: number;
};

type PreviewResponse = {
  dataset_id: number;
  version_id?: number | null;
  columns: ColumnPreview[];
  sample_rows: Record<string, any>[];
};

type OpType =
  | 'drop_missing'
  | 'impute'
  | 'drop_columns'
  | 'rename_columns'
  | 'scale'
  | 'derived_column';

type Operation = {
  op: OpType;
  params: Record<string, any>;
};

type ApplyResponse = {
  dataset_id: number;
  base_version_id?: number | null;
  new_version_id: number;
  version_no: number;
  row_count: number;
  col_count: number;
};

export function PreprocessBackendPage() {
  const [datasetId, setDatasetId] = useState<string>('');
  const [versionId, setVersionId] = useState<string>('');
  const [baseVersionId, setBaseVersionId] = useState<string>('');
  const [createdBy, setCreatedBy] = useState<string>('');
  const [note, setNote] = useState<string>('');
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [applyResult, setApplyResult] = useState<ApplyResponse | null>(null);

  // Operations queue
  const [operations, setOperations] = useState<Operation[]>([]);

  // UI for adding an operation
  const [newOpType, setNewOpType] = useState<OpType>('drop_missing');
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [dropHow, setDropHow] = useState<'any' | 'all'>('any');
  const [imputeMethod, setImputeMethod] = useState<'mean' | 'median' | 'mode' | 'value'>('mean');
  const [imputeValue, setImputeValue] = useState<string>('');
  const [scaleMethod, setScaleMethod] = useState<'standardize' | 'normalize'>('standardize');
  const [renamePairs, setRenamePairs] = useState<Array<{ from: string; to: string }>>([{ from: '', to: '' }]);
  const [derivedName, setDerivedName] = useState<string>('');
  const [derivedExpr, setDerivedExpr] = useState<string>('');

  const columns = useMemo(() => preview?.columns?.map((c) => c.name) || [], [preview]);

  const toggleColumn = (col: string) => {
    setSelectedColumns((prev) => (prev.includes(col) ? prev.filter((c) => c !== col) : [...prev, col]));
  };

  const handleAddOperation = () => {
    const op: Operation = { op: newOpType, params: {} };
    try {
      switch (newOpType) {
        case 'drop_missing':
          op.params = { columns: selectedColumns, how: dropHow };
          break;
        case 'impute':
          op.params = { columns: selectedColumns, method: imputeMethod };
          if (imputeMethod === 'value') op.params.value = imputeValue;
          break;
        case 'drop_columns':
          op.params = { columns: selectedColumns };
          break;
        case 'rename_columns':
          const mapping: Record<string, string> = {};
          renamePairs.forEach((p) => {
            if (p.from && p.to) mapping[p.from] = p.to;
          });
          op.params = { mapping };
          break;
        case 'scale':
          op.params = { columns: selectedColumns, method: scaleMethod };
          break;
        case 'derived_column':
          op.params = { name: derivedName, expression: derivedExpr };
          break;
      }
      setOperations((prev) => [...prev, op]);
      toast.success('작업이 큐에 추가되었습니다');
    } catch (e) {
      toast.error('작업 추가 중 오류');
    }
  };

  const handleRemoveOperation = (index: number) => {
    setOperations((prev) => prev.filter((_, i) => i !== index));
  };

  const handlePreview = async () => {
    setApplyResult(null);
    if (!datasetId) {
      toast.error('dataset_id를 입력하세요');
      return;
    }
    try {
      setLoadingPreview(true);
      const payload: any = { dataset_id: Number(datasetId) };
      if (versionId) payload.version_id = Number(versionId);
      const data = await apiRequest<PreviewResponse>('/preprocess/preview', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setPreview(data);
      toast.success('미리보기를 불러왔습니다');
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '미리보기 요청 실패');
      setPreview(null);
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleApply = async () => {
    if (!datasetId) {
      toast.error('dataset_id를 입력하세요');
      return;
    }
    try {
      setSaving(true);
      const payload: any = {
        dataset_id: Number(datasetId),
        base_version_id: baseVersionId ? Number(baseVersionId) : null,
        operations,
        created_by: createdBy || null,
        note: note || null,
      };
      const res = await apiRequest<ApplyResponse>('/preprocess/apply', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setApplyResult(res);
      toast.success('전처리 적용 완료');
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '전처리 적용 실패');
      setApplyResult(null);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h2 className="text-gray-900 mb-2">전처리(백엔드 연동)</h2>
        <p className="text-gray-600">dataset_id 기반 미리보기 및 작업 적용</p>
      </div>

      {/* Controls */}
      <Card className="p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <Label htmlFor="datasetId">dataset_id</Label>
            <Input id="datasetId" value={datasetId} onChange={(e) => setDatasetId(e.target.value)} placeholder="예: 1" />
          </div>
          <div>
            <Label htmlFor="versionId">미리보기 version_id (선택)</Label>
            <Input id="versionId" value={versionId} onChange={(e) => setVersionId(e.target.value)} placeholder="예: 10" />
          </div>
          <div className="flex items-end">
            <Button onClick={handlePreview} disabled={loadingPreview}>
              {loadingPreview ? '불러오는 중...' : '미리보기 호출'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Preview Result */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-gray-900">미리보기 결과</h3>
          {preview && (
            <span className="text-sm text-gray-500">dataset_id: {preview.dataset_id}{preview.version_id ? `, version_id: ${preview.version_id}` : ''}</span>
          )}
        </div>

        {!preview ? (
          <p className="text-gray-600">미리보기를 호출하세요.</p>
        ) : (
          <div className="space-y-6">
            <div>
              <h4 className="text-gray-900 mb-2">컬럼</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {preview.columns.map((c) => (
                  <div key={c.name} className="border rounded-lg p-3">
                    <div className="font-medium text-gray-900">{c.name}</div>
                    <div className="text-sm text-gray-500">{c.dtype} · 결측치 {c.missing}</div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-gray-900 mb-2">샘플 행 (상위 20)</h4>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {(preview.sample_rows[0] ? Object.keys(preview.sample_rows[0]) : columns).map((col) => (
                        <TableHead key={col}>{col}</TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {preview.sample_rows.map((row, idx) => (
                      <TableRow key={idx}>
                        {(preview.sample_rows[0] ? Object.keys(preview.sample_rows[0]) : columns).map((col) => (
                          <TableCell key={col}>{String((row as any)[col] ?? '')}</TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Operations Builder */}
      <Card className="p-6 space-y-4">
        <h3 className="text-gray-900">전처리 작업 추가</h3>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <Label>작업 유형</Label>
            <Select value={newOpType} onValueChange={(v) => setNewOpType(v as OpType)}>
              <SelectTrigger>
                <SelectValue placeholder="작업 선택" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="drop_missing">결측치 행 제거</SelectItem>
                <SelectItem value="impute">결측치 대체</SelectItem>
                <SelectItem value="drop_columns">컬럼 삭제</SelectItem>
                <SelectItem value="rename_columns">컬럼명 변경</SelectItem>
                <SelectItem value="scale">스케일링</SelectItem>
                <SelectItem value="derived_column">파생 변수 생성</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {(newOpType === 'drop_missing' || newOpType === 'impute' || newOpType === 'drop_columns' || newOpType === 'scale') && (
            <div className="md:col-span-3">
              <Label className="mb-2 block">대상 컬럼</Label>
              <div className="flex flex-wrap gap-3">
                {columns.length === 0 && <div className="text-sm text-gray-500">미리보기 후 컬럼을 선택할 수 있습니다</div>}
                {columns.map((c) => (
                  <label key={c} className="flex items-center gap-2 border rounded-md px-3 py-2 cursor-pointer select-none">
                    <Checkbox checked={selectedColumns.includes(c)} onCheckedChange={() => toggleColumn(c)} />
                    <span className="text-sm">{c}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {newOpType === 'drop_missing' && (
            <div>
              <Label>how</Label>
              <Select value={dropHow} onValueChange={(v) => setDropHow(v as 'any' | 'all')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">any</SelectItem>
                  <SelectItem value="all">all</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {newOpType === 'impute' && (
            <>
              <div>
                <Label>method</Label>
                <Select value={imputeMethod} onValueChange={(v) => setImputeMethod(v as any)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="mean">mean</SelectItem>
                    <SelectItem value="median">median</SelectItem>
                    <SelectItem value="mode">mode</SelectItem>
                    <SelectItem value="value">value</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {imputeMethod === 'value' && (
                <div>
                  <Label>value</Label>
                  <Input value={imputeValue} onChange={(e) => setImputeValue(e.target.value)} placeholder="대체 값" />
                </div>
              )}
            </>
          )}

          {newOpType === 'rename_columns' && (
            <div className="md:col-span-4 space-y-3">
              <Label>컬럼명 매핑</Label>
              {renamePairs.map((p, idx) => (
                <div key={idx} className="grid grid-cols-1 md:grid-cols-5 gap-2 items-end">
                  <div className="md:col-span-2">
                    <Label className="text-xs">from</Label>
                    <Input value={p.from} onChange={(e) => setRenamePairs((arr) => arr.map((a, i) => i === idx ? { ...a, from: e.target.value } : a))} placeholder="원래 컬럼명" />
                  </div>
                  <div className="md:col-span-2">
                    <Label className="text-xs">to</Label>
                    <Input value={p.to} onChange={(e) => setRenamePairs((arr) => arr.map((a, i) => i === idx ? { ...a, to: e.target.value } : a))} placeholder="새 컬럼명" />
                  </div>
                  <div className="flex gap-2">
                    <Button type="button" variant="outline" onClick={() => setRenamePairs((arr) => arr.filter((_, i) => i !== idx))}>삭제</Button>
                    {idx === renamePairs.length - 1 && (
                      <Button type="button" variant="outline" onClick={() => setRenamePairs((arr) => [...arr, { from: '', to: '' }])}>추가</Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {newOpType === 'scale' && (
            <div>
              <Label>method</Label>
              <Select value={scaleMethod} onValueChange={(v) => setScaleMethod(v as any)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="standardize">standardize</SelectItem>
                  <SelectItem value="normalize">normalize</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {newOpType === 'derived_column' && (
            <>
              <div>
                <Label>새 컬럼명</Label>
                <Input value={derivedName} onChange={(e) => setDerivedName(e.target.value)} placeholder="예: total" />
              </div>
              <div className="md:col-span-3">
                <Label>표현식</Label>
                <Input value={derivedExpr} onChange={(e) => setDerivedExpr(e.target.value)} placeholder="예: colA + colB" />
              </div>
            </>
          )}
        </div>

        <div className="flex justify-end">
          <Button type="button" onClick={handleAddOperation}>작업 추가</Button>
        </div>
      </Card>

      {/* Operations Queue and Apply */}
      <Card className="p-6 space-y-4">
        <h3 className="text-gray-900">작업 큐</h3>
        {operations.length === 0 ? (
          <p className="text-gray-600">추가된 작업이 없습니다.</p>
        ) : (
          <div className="space-y-2">
            {operations.map((op, idx) => (
              <div key={idx} className="flex items-center justify-between border rounded-md p-3">
                <pre className="text-sm whitespace-pre-wrap mr-3">{JSON.stringify(op, null, 2)}</pre>
                <Button variant="outline" onClick={() => handleRemoveOperation(idx)}>제거</Button>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 pt-2">
          <div>
            <Label>base_version_id (선택)</Label>
            <Input value={baseVersionId} onChange={(e) => setBaseVersionId(e.target.value)} placeholder="예: 10" />
          </div>
          <div>
            <Label>created_by (선택)</Label>
            <Input value={createdBy} onChange={(e) => setCreatedBy(e.target.value)} placeholder="작성자" />
          </div>
          <div className="md:col-span-2">
            <Label>note (선택)</Label>
            <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="설명/메모" />
          </div>
          <div className="flex items-end">
            <Button onClick={handleApply} disabled={saving || !datasetId}>적용</Button>
          </div>
        </div>

        {applyResult && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="border rounded-md p-3">
              <div className="text-sm text-gray-500">new_version_id</div>
              <div className="text-gray-900">{applyResult.new_version_id}</div>
            </div>
            <div className="border rounded-md p-3">
              <div className="text-sm text-gray-500">version_no</div>
              <div className="text-gray-900">{applyResult.version_no}</div>
            </div>
            <div className="border rounded-md p-3">
              <div className="text-sm text-gray-500">row_count</div>
              <div className="text-gray-900">{applyResult.row_count}</div>
            </div>
            <div className="border rounded-md p-3">
              <div className="text-sm text-gray-500">col_count</div>
              <div className="text-gray-900">{applyResult.col_count}</div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

