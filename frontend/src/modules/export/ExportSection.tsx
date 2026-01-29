import { useRef } from 'react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Download } from 'lucide-react';
import { toast } from 'sonner';
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
  meta?: Record<string, any>;
};

type ChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap';

function toCsv(rows: any[], columns: string[]): string {
  const header = columns.join(',');
  const lines = rows.map((row) =>
    columns
      .map((c) => {
        const v = row[c];
        if (v == null) return '';
        const s = String(v).replace(/"/g, '""');
        return /[",\n]/.test(s) ? `"${s}"` : s;
      })
      .join(',')
  );
  return [header, ...lines].join('\n');
}

function downloadFile(filename: string, content: string, type = 'text/plain') {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function downloadChartPng(svgContainer: HTMLElement | null, filename: string) {
  if (!svgContainer) {
    toast.error('차트를 찾을 수 없습니다.');
    return;
  }
  const svg = svgContainer.querySelector('svg');
  if (!svg) {
    toast.error('차트 SVG를 찾을 수 없습니다.');
    return;
  }
  const serializer = new XMLSerializer();
  const svgString = serializer.serializeToString(svg);
  const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(svgBlob);
  const img = new Image();
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve();
    img.onerror = () => reject(new Error('SVG 로드 실패'));
    img.src = url;
  });
  const width = svg.viewBox.baseVal.width || svg.clientWidth || 800;
  const height = svg.viewBox.baseVal.height || svg.clientHeight || 300;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(img, 0, 0);
  await new Promise<void>((resolve) => {
    canvas.toBlob((blob) => {
      if (blob) {
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(blobUrl);
      }
      resolve();
    }, 'image/png');
  });
  URL.revokeObjectURL(url);
}

interface ExportSectionProps {
  selectedDataset: Dataset | null;
  chartType: ChartType;
  xCol: string;
  yCol: string;
  heatmapData: { x: string; y: string; value: number }[];
}

export function ExportSection({ selectedDataset, chartType, xCol, yCol, heatmapData }: ExportSectionProps) {
  const chartRef = useRef<HTMLDivElement | null>(null);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <Card className="p-4 space-y-4 lg:col-span-1">
        <h3 className="text-gray-900">내보내기</h3>
        <p className="text-gray-600">선택된 데이터셋을 CSV로, 현재 설정의 차트를 PNG로 저장합니다.</p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={!selectedDataset}
            onClick={() => selectedDataset && downloadFile(`${selectedDataset.id}.csv`, toCsv(selectedDataset.rows, selectedDataset.columns), 'text/csv;charset=utf-8')}
          >
            <Download className="w-4 h-4 mr-2" /> CSV 다운로드
          </Button>
          <Button variant="outline" onClick={() => downloadChartPng(chartRef.current, `${selectedDataset?.id || 'chart'}.png`)} disabled={!selectedDataset}>
            <Download className="w-4 h-4 mr-2" /> 차트 PNG 다운로드
          </Button>
        </div>
        <div className="text-sm text-gray-500">PNG 다운로드는 아래 미리보기 차트를 기반으로 저장됩니다.</div>
      </Card>

      <Card className="p-4 lg:col-span-2">
        <h4 className="text-gray-900 mb-2">차트 미리보기</h4>
        <div ref={chartRef} className="w-full h-[300px]">
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
                  <Pie data={selectedDataset.rows} dataKey={yCol} nameKey={xCol} outerRadius={110}>
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
                <svg width="100%" height="100%" viewBox="0 0 800 300">
                  {(() => {
                    const data = heatmapData;
                    if (data.length === 0) return null;
                    const xs = Array.from(new Set(data.map((d) => d.x)));
                    const ys = Array.from(new Set(data.map((d) => d.y)));
                    const cellW = 800 / Math.max(xs.length, 1);
                    const cellH = 260 / Math.max(ys.length, 1);
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

