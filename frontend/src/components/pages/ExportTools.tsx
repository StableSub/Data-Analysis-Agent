import { useState } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Checkbox } from '../ui/checkbox';
import { toast } from 'sonner';

function buildUrl(path: string) {
  const base = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  return `${base}${path.startsWith('/') ? path : `/${path}`}`;
}

export function ExportToolsPage() {
  // CSV Export form
  const [resultId, setResultId] = useState('');
  const [viewToken, setViewToken] = useState('');
  const [columns, setColumns] = useState('');
  const [limit, setLimit] = useState('');
  const [includeHeader, setIncludeHeader] = useState(true);
  const [csvLoading, setCsvLoading] = useState(false);

  // Chart PNG Export form
  const [chartId, setChartId] = useState('');
  const [scale, setScale] = useState('2');
  const [bg, setBg] = useState('transparent');
  const [pngLoading, setPngLoading] = useState(false);

  const downloadBlob = (blob: Blob, fallbackName: string, disposition?: string | null) => {
    let filename = fallbackName;
    if (disposition) {
      const match = /filename="?([^";]+)"?/i.exec(disposition);
      if (match && match[1]) filename = match[1];
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const handleCsvExport = async () => {
    if (!resultId && !viewToken) {
      toast.error('result_id 또는 view_token 중 하나는 필요합니다.');
      return;
    }
    try {
      setCsvLoading(true);
      const payload: any = {};
      if (resultId) payload.result_id = resultId;
      if (viewToken) payload.view_token = viewToken;
      if (columns.trim()) payload.columns = columns.split(',').map((c) => c.trim()).filter(Boolean);
      if (limit.trim()) payload.limit = Number(limit);
      payload.include_header = includeHeader;

      const res = await fetch(buildUrl('/export/csv'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const ct = res.headers.get('content-type') || '';
        if (ct.includes('application/json')) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.detail || `요청 실패 (${res.status})`);
        } else {
          const text = await res.text();
          throw new Error(text || `요청 실패 (${res.status})`);
        }
      }

      const blob = await res.blob();
      const disposition = res.headers.get('content-disposition');
      downloadBlob(blob, 'result.csv', disposition);
      toast.success('CSV 다운로드를 시작했습니다.');
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'CSV 내보내기 실패');
    } finally {
      setCsvLoading(false);
    }
  };

  const handlePngExport = async () => {
    if (!chartId) {
      toast.error('chart_id를 입력하세요.');
      return;
    }
    try {
      setPngLoading(true);
      const params = new URLSearchParams();
      params.set('chart_id', chartId);
      if (scale.trim()) params.set('scale', scale);
      if (bg.trim()) params.set('bg', bg);

      const url = buildUrl(`/export/chart/png?${params.toString()}`);
      const res = await fetch(url, { method: 'GET' });
      if (!res.ok) {
        const ct = res.headers.get('content-type') || '';
        if (ct.includes('application/json')) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.detail || `요청 실패 (${res.status})`);
        } else {
          const text = await res.text();
          throw new Error(text || `요청 실패 (${res.status})`);
        }
      }
      const blob = await res.blob();
      const disposition = res.headers.get('content-disposition');
      downloadBlob(blob, 'chart.png', disposition);
      toast.success('PNG 다운로드를 시작했습니다.');
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '차트 PNG 내보내기 실패');
    } finally {
      setPngLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h2 className="text-gray-900 mb-2">Export 도구</h2>
        <p className="text-gray-600">CSV와 차트 PNG 다운로드</p>
      </div>

      {/* CSV Export */}
      <Card className="p-6 space-y-4">
        <h3 className="text-gray-900">CSV 다운로드</h3>
        <p className="text-sm text-gray-600">result_id 또는 view_token 중 하나를 입력하세요.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <Label htmlFor="resultId">result_id</Label>
            <Input id="resultId" value={resultId} onChange={(e) => setResultId(e.target.value)} placeholder="예: res_123" />
          </div>
          <div>
            <Label htmlFor="viewToken">view_token</Label>
            <Input id="viewToken" value={viewToken} onChange={(e) => setViewToken(e.target.value)} placeholder="예: vtok_abc" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <Label htmlFor="columns">컬럼 제한(선택, 콤마구분)</Label>
            <Input id="columns" value={columns} onChange={(e) => setColumns(e.target.value)} placeholder="colA,colB,colC" />
          </div>
          <div>
            <Label htmlFor="limit">행 수 제한(선택)</Label>
            <Input id="limit" value={limit} onChange={(e) => setLimit(e.target.value)} placeholder="예: 1000" />
          </div>
          <div className="flex items-end gap-2">
            <Checkbox id="includeHeader" checked={includeHeader} onCheckedChange={(v) => setIncludeHeader(Boolean(v))} />
            <Label htmlFor="includeHeader">헤더 포함</Label>
          </div>
        </div>

        <div className="flex justify-end">
          <Button onClick={handleCsvExport} disabled={csvLoading}>
            {csvLoading ? '내보내는 중...' : 'CSV 다운로드'}
          </Button>
        </div>
      </Card>

      {/* Chart PNG Export */}
      <Card className="p-6 space-y-4">
        <h3 className="text-gray-900">차트 PNG 다운로드</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <Label htmlFor="chartId">chart_id</Label>
            <Input id="chartId" value={chartId} onChange={(e) => setChartId(e.target.value)} placeholder="예: ch_123" />
          </div>
          <div>
            <Label htmlFor="scale">scale(1~5)</Label>
            <Input id="scale" value={scale} onChange={(e) => setScale(e.target.value)} placeholder="기본 2" />
          </div>
          <div>
            <Label htmlFor="bg">bg(배경색)</Label>
            <Input id="bg" value={bg} onChange={(e) => setBg(e.target.value)} placeholder="transparent 또는 #ffffff" />
          </div>
        </div>

        <div className="flex justify-end">
          <Button onClick={handlePngExport} disabled={pngLoading}>
            {pngLoading ? '다운로드 중...' : 'PNG 다운로드'}
          </Button>
        </div>
      </Card>
    </div>
  );
}

