import { useEffect, useMemo, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { toast } from 'sonner';
import { DatasetSection } from '../../modules/dataset/DatasetSection';
import { PreprocessSection } from '../../modules/preprocess/PreprocessSection';
import { ExportSection } from '../../modules/export/ExportSection';
import { VisualizationSection } from '../../modules/visualization/VisualizationSection';

type Dataset = {
  id: string; // dataset_id / source_id
  name: string;
  createdAt: string;
  rows: any[];
  columns: string[];
  meta?: Record<string, any>;
};

type ChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap';

// 데모 데이터 (백엔드 연동 전)
const DEMO_DATASETS: Dataset[] = [
  {
    id: 'demo-sales',
    name: '매출 데이터',
    createdAt: new Date().toISOString(),
    columns: ['month', 'revenue', 'category', 'region'],
    rows: [
      { month: 'Jan', revenue: 120, category: 'A', region: 'Seoul' },
      { month: 'Feb', revenue: 90, category: 'B', region: 'Busan' },
      { month: 'Mar', revenue: 150, category: 'A', region: 'Seoul' },
      { month: 'Apr', revenue: 80, category: 'C', region: 'Incheon' },
      { month: 'May', revenue: 170, category: 'B', region: 'Busan' },
      { month: 'Jun', revenue: 140, category: 'A', region: 'Seoul' },
    ],
    meta: { description: '월별 매출 데이터 (데모)' },
  },
  {
    id: 'demo-scatter',
    name: '산점도 데이터',
    createdAt: new Date().toISOString(),
    columns: ['x', 'y', 'group'],
    rows: Array.from({ length: 30 }, (_, i) => ({ x: i, y: Math.round(Math.random() * 100), group: i % 3 === 0 ? 'G1' : i % 3 === 1 ? 'G2' : 'G3' })),
    meta: { description: '무작위 산점도 샘플' },
  },
];

export function DatasetConsole() {
  // 데이터셋 상태 (UI-only)
  const [datasets, setDatasets] = useState<Dataset[]>(DEMO_DATASETS);
  const [selectedId, setSelectedId] = useState<string | null>(datasets[0]?.id ?? null);

  // 전처리: dataset_id 입력 + 미리보기
  const [inputId, setInputId] = useState('');
  const [previewRows, setPreviewRows] = useState<any[]>([]);
  const [previewCols, setPreviewCols] = useState<string[]>([]);

  // 시각화 설정
  const [chartType, setChartType] = useState<ChartType>('bar');
  const [sourceId, setSourceId] = useState<string>('');
  const [xCol, setXCol] = useState<string>('');
  const [yCol, setYCol] = useState<string>('');
  const [colorCol, setColorCol] = useState<string>('');
  const [groupCol, setGroupCol] = useState<string>('');

  const selectedDataset = useMemo(
    () => datasets.find((d) => d.id === selectedId) || null,
    [datasets, selectedId]
  );

  useEffect(() => {
    if (selectedDataset) {
      setSourceId(selectedDataset.id);
      setXCol(selectedDataset.columns[0] || '');
      setYCol(selectedDataset.columns[1] || '');
      setColorCol(selectedDataset.columns[2] || '');
      setGroupCol(selectedDataset.columns[3] || '');
    }
  }, [selectedDataset?.id]);

  const handleDelete = (id: string) => {
    setDatasets((prev) => prev.filter((d) => d.id !== id));
    if (selectedId === id) setSelectedId(null);
  };

  const handlePreviewCall = () => {
    const ds = datasets.find((d) => d.id === inputId);
    if (ds) {
      setPreviewCols(ds.columns);
      setPreviewRows(ds.rows.slice(0, 5));
      toast.success('데모 데이터로 미리보기를 표시합니다');
    } else {
      setPreviewCols([]);
      setPreviewRows([]);
      toast.message('해당 ID의 데이터셋을 찾을 수 없습니다 (데모)');
    }
  };

  // heatmap 데이터 변환
  const heatmapData = useMemo(() => {
    if (!selectedDataset || !xCol || !yCol) return [] as { x: string; y: string; value: number }[];
    const map = new Map<string, number>();
    const xs = new Set<string>();
    const ys = new Set<string>();
    for (const r of selectedDataset.rows) {
      const xv = String(r[xCol]);
      const yv = String(r[yCol]);
      const key = `${xv}__${yv}`;
      map.set(key, (map.get(key) || 0) + 1);
      xs.add(xv);
      ys.add(yv);
    }
    const res: { x: string; y: string; value: number }[] = [];
    xs.forEach((xi) => {
      ys.forEach((yi) => {
        const key = `${xi}__${yi}`;
        res.push({ x: xi, y: yi, value: map.get(key) || 0 });
      });
    });
    return res;
  }, [selectedDataset?.id, xCol, yCol]);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-gray-900 mb-1">데이터셋 콘솔</h2>
        <p className="text-gray-600">Dataset / Export / Preprocess / Visualization 모듈로 분리</p>
      </div>

      <Tabs defaultValue="dataset">
        <TabsList>
          <TabsTrigger value="dataset">dataset</TabsTrigger>
          <TabsTrigger value="export">export</TabsTrigger>
          <TabsTrigger value="preprocess">preprocess</TabsTrigger>
          <TabsTrigger value="viz">visualization</TabsTrigger>
        </TabsList>

        <TabsContent value="dataset">
          <DatasetSection
            datasets={datasets}
            selectedId={selectedId}
            setSelectedId={setSelectedId}
            onDelete={handleDelete}
          />
        </TabsContent>

        <TabsContent value="export">
          <ExportSection
            selectedDataset={selectedDataset}
            chartType={chartType}
            xCol={xCol}
            yCol={yCol}
            heatmapData={heatmapData}
          />
        </TabsContent>

        <TabsContent value="preprocess">
          <PreprocessSection
            inputId={inputId}
            setInputId={setInputId}
            previewCols={previewCols}
            previewRows={previewRows}
            onPreviewCall={handlePreviewCall}
          />
        </TabsContent>

        <TabsContent value="viz">
          <VisualizationSection
            datasets={datasets}
            selectedDataset={selectedDataset}
            chartType={chartType}
            setChartType={(t) => setChartType(t)}
            sourceId={sourceId}
            setSourceId={setSourceId}
            xCol={xCol}
            setXCol={setXCol}
            yCol={yCol}
            setYCol={setYCol}
            colorCol={colorCol}
            setColorCol={setColorCol}
            groupCol={groupCol}
            setGroupCol={setGroupCol}
            onGenerate={(sid) => {
              const ds = datasets.find((d) => d.id === sid) || selectedDataset;
              if (!ds) {
                toast.error('데이터셋을 선택하거나 입력하세요');
                return;
              }
              setSelectedId(ds.id);
              toast.success('시각화를 생성했습니다');
            }}
            heatmapData={heatmapData}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

