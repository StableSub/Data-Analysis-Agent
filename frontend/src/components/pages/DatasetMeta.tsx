import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { apiRequest } from '../../lib/api';

type MetaResponse = {
  source_id: string;
  encoding?: string | null;
  delimiter?: string | null;
  line_ending?: string | null;
  quotechar?: string | null;
  escapechar?: string | null;
  has_header?: boolean | null;
  parse_status?: string | null;
};

type MetaUpdateRequest = {
  encoding?: string | null;
  delimiter?: string | null;
  has_header?: boolean | null;
};

const COMMON_ENCODINGS = [
  'utf-8',
  'euc-kr',
  'cp949',
  'latin1',
  'utf-16',
  'utf-8-sig',
];

const COMMON_DELIMITERS: Array<{ label: string; value: string }> = [
  { label: '콤마 (,)', value: ',' },
  { label: '탭 (\\t)', value: '\\t' },
  { label: '세미콜론 (;)', value: ';' },
  { label: '파이프 (|)', value: '|' },
];

export function DatasetMetaPage() {
  const params = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [encoding, setEncoding] = useState<string>('');
  const [delimiter, setDelimiter] = useState<string>('');
  const [hasHeader, setHasHeader] = useState<boolean | null>(null);
  const sourceId = params.sourceId as string | undefined;

  const currentDelimiterLabel = useMemo(() => {
    const found = COMMON_DELIMITERS.find((d) => d.value === delimiter);
    return found ? found.label : delimiter || '구분자 선택';
  }, [delimiter]);

  useEffect(() => {
    if (!sourceId) return;
    (async () => {
      try {
        setLoading(true);
        const data = await apiRequest<MetaResponse>(`/datasets/${sourceId}/meta`);
        setMeta(data);
        setEncoding(data.encoding || '');
        setDelimiter(data.delimiter || '');
        setHasHeader(typeof data.has_header === 'boolean' ? data.has_header : null);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : '메타데이터 조회에 실패했습니다.');
      } finally {
        setLoading(false);
      }
    })();
  }, [sourceId]);

  const handleRefresh = async () => {
    if (!sourceId) return;
    try {
      setLoading(true);
      const data = await apiRequest<MetaResponse>(`/datasets/${sourceId}/meta`);
      setMeta(data);
      setEncoding(data.encoding || '');
      setDelimiter(data.delimiter || '');
      setHasHeader(typeof data.has_header === 'boolean' ? data.has_header : null);
      toast.success('메타데이터를 새로고침했습니다.');
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '새로고침에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourceId) return;
    const payload: MetaUpdateRequest = {
      encoding: encoding || null,
      delimiter: delimiter || null,
      has_header: hasHeader,
    };
    try {
      setSaving(true);
      const res = await apiRequest<MetaResponse>(`/datasets/${sourceId}/meta`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
      toast.success('메타데이터가 업데이트되었습니다.');
      setMeta((prev) => ({ ...(prev || { source_id: sourceId }), ...res }));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '업데이트에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  if (!sourceId) {
    return (
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-gray-900 mb-2">Dataset Meta</h2>
          <p className="text-gray-600">URL에 유효한 source_id가 필요합니다.</p>
        </div>
        <Card className="p-6">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const form = e.target as HTMLFormElement & { sourceId: { value: string } };
              const id = form.sourceId.value.trim();
              if (id) navigate(`/datasets/${id}/meta`);
            }}
            className="flex items-end gap-3"
          >
            <div className="flex-1">
              <Label htmlFor="sourceId">Source ID</Label>
              <Input id="sourceId" name="sourceId" placeholder="예: ds_123456" />
            </div>
            <Button type="submit">메타 조회로 이동</Button>
          </form>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-gray-900 mb-2">Dataset Meta</h2>
          <p className="text-gray-600">소스 ID: {sourceId}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate('/datasets')}>업로드로 이동</Button>
          <Button variant="outline" onClick={handleRefresh} disabled={loading}>새로고침</Button>
        </div>
      </div>

      {/* 메타 조회 영역 */}
      <Card className="p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-gray-900">메타 조회 결과</h3>
          {meta?.parse_status && (
            <span className="text-sm text-gray-500">상태: {meta.parse_status}</span>
          )}
        </div>

        {loading ? (
          <p className="text-gray-600">불러오는 중...</p>
        ) : meta ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-gray-500">인코딩</div>
              <div className="text-gray-900">{meta.encoding || '-'}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">구분자</div>
              <div className="text-gray-900">{meta.delimiter === '\\t' ? '탭 (\\t)' : meta.delimiter || '-'}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">헤더 포함 여부</div>
              <div className="text-gray-900">{meta.has_header === true ? '예' : meta.has_header === false ? '아니오' : '-'}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">개행문자</div>
              <div className="text-gray-900">{meta.line_ending || '-'}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">인용 문자</div>
              <div className="text-gray-900">{meta.quotechar || '-'}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">이스케이프 문자</div>
              <div className="text-gray-900">{meta.escapechar || '-'}</div>
            </div>
          </div>
        ) : (
          <p className="text-gray-600">메타데이터가 없습니다.</p>
        )}
      </Card>

      {/* 메타 수정 폼 */}
      <Card className="p-6">
        <h3 className="text-gray-900 mb-4">메타 수정</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label className="mb-1 block">인코딩</Label>
              <Select value={encoding || ''} onValueChange={(v) => setEncoding(v)}>
                <SelectTrigger>
                  <SelectValue placeholder="인코딩 선택" />
                </SelectTrigger>
                <SelectContent>
                  {COMMON_ENCODINGS.map((enc) => (
                    <SelectItem key={enc} value={enc}>
                      {enc}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="mb-1 block">구분자</Label>
              <Select value={delimiter || ''} onValueChange={(v) => setDelimiter(v)}>
                <SelectTrigger>
                  <SelectValue placeholder="구분자 선택">{currentDelimiterLabel}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {COMMON_DELIMITERS.map((d) => (
                    <SelectItem key={d.value} value={d.value}>
                      {d.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end gap-2">
              <div>
                <Label className="mb-2 block">헤더 포함</Label>
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="hasHeader"
                    checked={hasHeader === true}
                    onCheckedChange={(v) => setHasHeader(Boolean(v))}
                  />
                  <Label htmlFor="hasHeader">첫 행이 헤더</Label>
                </div>
              </div>
            </div>
          </div>

          {/* 직접 입력 필드 (선택) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label className="mb-1 block">인코딩 직접 입력</Label>
              <Input
                placeholder="예: cp949"
                value={encoding}
                onChange={(e) => setEncoding(e.target.value)}
              />
            </div>
            <div>
              <Label className="mb-1 block">구분자 직접 입력</Label>
              <Input
                placeholder=", 또는 \t 등"
                value={delimiter}
                onChange={(e) => setDelimiter(e.target.value)}
              />
            </div>
          </div>

          <div className="flex gap-2 justify-end pt-2">
            <Button type="button" variant="outline" onClick={handleRefresh} disabled={loading}>
              현재값 불러오기
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? '저장 중...' : '메타 저장'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

