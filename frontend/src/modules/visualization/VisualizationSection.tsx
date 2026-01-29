import { useEffect } from 'react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/label';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ZAxis,
} from 'recharts';

export type Dataset = {
  id: string;
  name: string;
  createdAt: string;
  rows: any[];
  columns: string[];
};

type ChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap';

interface VisualizationSectionProps {
  datasets: Dataset[];
  selectedDataset: Dataset | null;
  chartType: ChartType;
  setChartType: (t: ChartType) => void;
  sourceId: string;
  setSourceId: (v: string) => void;
  xCol: string; setXCol: (v: string) => void;
  yCol: string; setYCol: (v: string) => void;
  colorCol: string; setColorCol: (v: string) => void;
  groupCol: string; setGroupCol: (v: string) => void;
  onGenerate: (sourceId: string) => void;
  heatmapData: { x: string; y: string; value: number }[];
}

export function VisualizationSection(props: VisualizationSectionProps) {
  const { datasets, selectedDataset, chartType, setChartType, sourceId, setSourceId, xCol, setXCol, yCol, setYCol, colorCol, setColorCol, groupCol, setGroupCol, onGenerate, heatmapData } = props;

  useEffect(() => {
    if (selectedDataset) {
      setSourceId(selectedDataset.id);
      if (!xCol) setXCol(selectedDataset.columns[0] || '');
      if (!yCol) setYCol(selectedDataset.columns[1] || '');
      if (!colorCol) setColorCol(selectedDataset.columns[2] || '');
      if (!groupCol) setGroupCol(selectedDataset.columns[3] || '');
    }
  }, [selectedDataset?.id]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <Card className="p-4 space-y-4 lg:col-span-1">
        <h3 className="text-gray-900">시각화 설정</h3>

        <div>
          <Label>차트 타입</Label>
          <Select value={chartType} onValueChange={(v) => setChartType(v as ChartType)}>
            <SelectTrigger className="mt-1">
              <SelectValue placeholder="차트 타입 선택" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="bar">bar</SelectItem>
              <SelectItem value="line">line</SelectItem>
              <SelectItem value="pie">pie</SelectItem>
              <SelectItem value="scatter">scatter</SelectItem>
              <SelectItem value="heatmap">heatmap</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label>데이터셋 선택/입력 (source_id)</Label>
          <Select value={sourceId} onValueChange={setSourceId}>
            <SelectTrigger className="mt-1">
              <SelectValue placeholder="데이터셋 선택" />
            </SelectTrigger>
            <SelectContent>
              {datasets.map((d) => (
                <SelectItem key={d.id} value={d.id}>{d.id}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input className="mt-2" placeholder="직접 입력 (선택 사항)" value={sourceId} onChange={(e) => setSourceId(e.target.value)} />
        </div>

        <div>
          <Label>x 컬럼</Label>
          <Select value={xCol} onValueChange={setXCol}>
            <SelectTrigger className="mt-1">
              <SelectValue placeholder="x 컬럼 선택" />
            </SelectTrigger>
            <SelectContent>
              {(selectedDataset?.columns || []).map((c) => (
                <SelectItem key={c} value={c}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label>y 컬럼</Label>
          <Select value={yCol} onValueChange={setYCol}>
            <SelectTrigger className="mt-1">
              <SelectValue placeholder="y 컬럼 선택" />
            </SelectTrigger>
            <SelectContent>
              {(selectedDataset?.columns || []).map((c) => (
                <SelectItem key={c} value={c}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label>color 컬럼</Label>
          <Select value={colorCol} onValueChange={setColorCol}>
            <SelectTrigger className="mt-1">
              <SelectValue placeholder="color 컬럼 선택" />
            </SelectTrigger>
            <SelectContent>
              {(selectedDataset?.columns || []).map((c) => (
                <SelectItem key={c} value={c}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label>group 컬럼</Label>
          <Select value={groupCol} onValueChange={setGroupCol}>
            <SelectTrigger className="mt-1">
              <SelectValue placeholder="group 컬럼 선택" />
            </SelectTrigger>
            <SelectContent>
              {(selectedDataset?.columns || []).map((c) => (
                <SelectItem key={c} value={c}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button onClick={() => onGenerate(sourceId)}>시각화 생성</Button>
      </Card>

      <Card className="p-4 lg:col-span-2">
        <h3 className="text-gray-900 mb-2">결과 렌더링</h3>
        <div className="w-full h-[360px]">
          {selectedDataset ? (
            <ResponsiveContainer width="100%" height="100%">
              {chartType === 'bar' ? (
                <BarChart data={selectedDataset.rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey={xCol} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey={yCol}>
                    {selectedDataset.rows.map((_, i) => (
                      <Cell key={`cell-${i}`} fill={`var(--chart-${(i % 5) + 1})`} />
                    ))}
                  </Bar>
                </BarChart>
              ) : chartType === 'line' ? (
                <LineChart data={selectedDataset.rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey={xCol} />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey={yCol} stroke="var(--chart-1)" />
                </LineChart>
              ) : chartType === 'pie' ? (
                <PieChart>
                  <Tooltip />
                  <Pie data={selectedDataset.rows} dataKey={yCol} nameKey={xCol} outerRadius={120}>
                    {selectedDataset.rows.map((_, i) => (
                      <Cell key={`cell-${i}`} fill={`var(--chart-${(i % 5) + 1})`} />
                    ))}
                  </Pie>
                </PieChart>
              ) : chartType === 'scatter' ? (
                <ScatterChart>
                  <CartesianGrid />
                  <XAxis dataKey={xCol} name={xCol} />
                  <YAxis dataKey={yCol} name={yCol} />
                  <ZAxis range={[60, 400]} />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={selectedDataset.rows} fill="var(--chart-1)" />
                </ScatterChart>
              ) : (
                <svg width="100%" height="100%" viewBox="0 0 800 360">
                  {(() => {
                    const data = heatmapData;
                    if (data.length === 0) return null;
                    const xs = Array.from(new Set(data.map((d) => d.x)));
                    const ys = Array.from(new Set(data.map((d) => d.y)));
                    const cellW = 800 / Math.max(xs.length, 1);
                    const cellH = 300 / Math.max(ys.length, 1);
                    const max = Math.max(...data.map((d) => d.value));
                    return (
                      <g>
                        {ys.map((yv, yi) =>
                          xs.map((xv, xi) => {
                            const v = data.find((d) => d.x === xv && d.y === yv)?.value || 0;
                            const ratio = max ? v / max : 0;
                            const color = `rgba(10,132,255,${0.1 + ratio * 0.9})`;
                            return (
                              <rect
                                key={`${xi}-${yi}`}
                                x={xi * cellW}
                                y={yi * cellH}
                                width={cellW - 2}
                                height={cellH - 2}
                                fill={color}
                              />
                            );
                          })
                        )}
                      </g>
                    );
                  })()}
                </svg>
              )}
            </ResponsiveContainer>
          ) : (
            <div className="w-full h-full grid place-items-center text-gray-600">데이터셋을 선택하세요</div>
          )}
        </div>
      </Card>
    </div>
  );
}

