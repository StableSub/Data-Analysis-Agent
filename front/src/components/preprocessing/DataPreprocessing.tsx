import { useState, useCallback, useEffect } from 'react';
import { Upload, Download, FileSpreadsheet, CheckCircle2, Settings, Database, Info, TrendingUp, MoreVertical, Trash2, Undo2, Redo2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { ScrollArea } from '../ui/scroll-area';
import { Separator } from '../ui/separator';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuSub, DropdownMenuSubContent, DropdownMenuSubTrigger } from '../ui/dropdown-menu';
import { useDataStore, ColumnInfo } from '../../store/useDataStore';
import * as XLSX from 'xlsx';

interface DataPreprocessingProps {
  isDark: boolean;
}

export function DataPreprocessing({ isDark }: DataPreprocessingProps) {
  const { 
    file, 
    data, 
    columns, 
    columnInfo, 
    setFileData, 
    updateData, 
    clearData,
    undo,
    redo,
    canUndo,
    canRedo
  } = useDataStore();
  
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [scalingMethod, setScalingMethod] = useState<'standardization' | 'normalization'>('standardization');

  // 키보드 단축키 (Ctrl+Z, Ctrl+Y)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        redo();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo]);
  
  // 파일 업로드 처리
  const handleFileUpload = useCallback((uploadedFile: File) => {
    const fileExtension = uploadedFile.name.split('.').pop()?.toLowerCase();
    
    if (fileExtension === 'csv') {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        parseCSV(text, uploadedFile);
      };
      reader.readAsText(uploadedFile);
    } else if (fileExtension === 'xlsx' || fileExtension === 'xls') {
      const reader = new FileReader();
      reader.onload = (e) => {
        const data = e.target?.result;
        parseExcel(data as ArrayBuffer, uploadedFile);
      };
      reader.readAsArrayBuffer(uploadedFile);
    }
  }, []);

  // CSV 파싱
  const parseCSV = (text: string, uploadedFile: File) => {
    const lines = text.split('\n').filter(line => line.trim());
    const headers = lines[0].split(',').map(h => h.trim());
    
    const parsedData = lines.slice(1).map(line => {
      const values = line.split(',');
      const row: any = {};
      headers.forEach((header, index) => {
        row[header] = values[index]?.trim() || '';
      });
      return row;
    });

    const info = analyzeColumns(headers, parsedData);
    setFileData(uploadedFile, parsedData, headers, info);
  };

  // Excel 파싱
  const parseExcel = (arrayBuffer: ArrayBuffer, uploadedFile: File) => {
    const workbook = XLSX.read(arrayBuffer, { type: 'array' });
    const firstSheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[firstSheetName];
    
    const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as any[][];
    
    if (jsonData.length === 0) return;
    
    const headers = jsonData[0].map((h: any) => h?.toString() || '');
    const parsedData = jsonData.slice(1).map(row => {
      const rowData: any = {};
      headers.forEach((header, index) => {
        rowData[header] = row[index]?.toString() || '';
      });
      return rowData;
    });

    const info = analyzeColumns(headers, parsedData);
    setFileData(uploadedFile, parsedData, headers, info);
  };

  // 열 분석
  const analyzeColumns = (headers: string[], parsedData: any[]): ColumnInfo[] => {
    return headers.map(col => {
      const values = parsedData.map(row => row[col]).filter(v => v !== '' && v !== null && v !== undefined);
      const numericValues = values.map(v => parseFloat(v)).filter(v => !isNaN(v));
      
      const isNumeric = numericValues.length > values.length * 0.8;
      const missing = parsedData.length - values.length;
      const unique = new Set(values).size;

      let columnData: ColumnInfo = {
        name: col,
        type: isNumeric ? 'number' : 'string',
        missing,
        unique,
      };

      if (isNumeric && numericValues.length > 0) {
        const sorted = [...numericValues].sort((a, b) => a - b);
        const sum = numericValues.reduce((a, b) => a + b, 0);
        const mean = sum / numericValues.length;
        const median = sorted[Math.floor(sorted.length / 2)];
        
        const variance = numericValues.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / numericValues.length;
        const std = Math.sqrt(variance);

        columnData = {
          ...columnData,
          mean: parseFloat(mean.toFixed(2)),
          median: parseFloat(median.toFixed(2)),
          min: Math.min(...numericValues),
          max: Math.max(...numericValues),
          std: parseFloat(std.toFixed(2)),
        };
      }

      return columnData;
    });
  };

  // Standardization
  const handleStandardization = () => {
    if (selectedColumns.length === 0) return;

    const newData = data.map(row => {
      const newRow = { ...row };
      selectedColumns.forEach(col => {
        const colInfo = columnInfo.find(c => c.name === col);
        if (colInfo?.type === 'number' && colInfo.mean !== undefined && colInfo.std !== undefined) {
          const value = parseFloat(row[col]);
          if (!isNaN(value)) {
            newRow[col] = ((value - colInfo.mean) / colInfo.std).toFixed(4);
          }
        }
      });
      return newRow;
    });

    const newColumnInfo = analyzeColumns(columns, newData);
    updateData(newData, columns, newColumnInfo);
  };

  // Normalization
  const handleNormalization = () => {
    if (selectedColumns.length === 0) return;

    const newData = data.map(row => {
      const newRow = { ...row };
      selectedColumns.forEach(col => {
        const colInfo = columnInfo.find(c => c.name === col);
        if (colInfo?.type === 'number' && colInfo.min !== undefined && colInfo.max !== undefined) {
          const value = parseFloat(row[col]);
          if (!isNaN(value)) {
            const range = colInfo.max - colInfo.min;
            newRow[col] = range === 0 ? 0 : ((value - colInfo.min) / range).toFixed(4);
          }
        }
      });
      return newRow;
    });

    const newColumnInfo = analyzeColumns(columns, newData);
    updateData(newData, columns, newColumnInfo);
  };

  // 결측치 채우기
  const handleFillMissing = (column: string, method: 'mean' | 'median' | 'mode' | 'custom', customValue?: string) => {
    const colInfo = columnInfo.find(c => c.name === column);
    if (!colInfo) return;

    const newData = data.map(row => {
      if (row[column] === '' || row[column] === null || row[column] === undefined) {
        let fillValue = '';
        
        if (method === 'mean' && colInfo.mean !== undefined) {
          fillValue = colInfo.mean.toString();
        } else if (method === 'median' && colInfo.median !== undefined) {
          fillValue = colInfo.median.toString();
        } else if (method === 'mode') {
          const values = data.map(r => r[column]).filter(v => v !== '' && v !== null && v !== undefined);
          const frequency: Record<string, number> = {};
          values.forEach(v => frequency[v] = (frequency[v] || 0) + 1);
          fillValue = Object.keys(frequency).reduce((a, b) => frequency[a] > frequency[b] ? a : b);
        } else if (method === 'custom' && customValue) {
          fillValue = customValue;
        }
        
        return { ...row, [column]: fillValue };
      }
      return row;
    });

    const newColumnInfo = analyzeColumns(columns, newData);
    updateData(newData, columns, newColumnInfo);
  };

  // 데이터 타입 변경
  const handleChangeType = (column: string, newType: 'number' | 'string') => {
    const newData = data.map(row => {
      if (newType === 'number') {
        const num = parseFloat(row[column]);
        return { ...row, [column]: isNaN(num) ? '' : num };
      } else {
        return { ...row, [column]: row[column].toString() };
      }
    });

    const newColumnInfo = analyzeColumns(columns, newData);
    updateData(newData, columns, newColumnInfo);
  };

  // 이상치 제거
  const handleRemoveOutliers = (column: string) => {
    const colInfo = columnInfo.find(c => c.name === column);
    if (!colInfo || colInfo.type !== 'number') return;

    const values = data.map(row => parseFloat(row[column])).filter(v => !isNaN(v));
    const sorted = [...values].sort((a, b) => a - b);
    
    const q1 = sorted[Math.floor(sorted.length * 0.25)];
    const q3 = sorted[Math.floor(sorted.length * 0.75)];
    const iqr = q3 - q1;
    const lowerBound = q1 - 1.5 * iqr;
    const upperBound = q3 + 1.5 * iqr;

    const newData = data.filter(row => {
      const val = parseFloat(row[column]);
      return isNaN(val) || (val >= lowerBound && val <= upperBound);
    });

    const newColumnInfo = analyzeColumns(columns, newData);
    updateData(newData, columns, newColumnInfo);
  };

  // 열 삭제
  const handleDeleteColumn = (column: string) => {
    const newColumns = columns.filter(c => c !== column);
    const newData = data.map(row => {
      const newRow = { ...row };
      delete newRow[column];
      return newRow;
    });

    const newColumnInfo = analyzeColumns(newColumns, newData);
    updateData(newData, newColumns, newColumnInfo);
    setSelectedColumns(prev => prev.filter(c => c !== column));
  };

  // 열 선택/해제
  const toggleColumnSelection = (column: string) => {
    setSelectedColumns(prev => 
      prev.includes(column) 
        ? prev.filter(c => c !== column)
        : [...prev, column]
    );
  };

  // CSV 다운로드
  const handleDownload = () => {
    if (data.length === 0) return;

    const csv = [
      columns.join(','),
      ...data.map(row => columns.map(col => row[col]).join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `preprocessed_${file?.name || 'data.csv'}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 드래그 앤 드롭
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && (droppedFile.name.endsWith('.csv') || droppedFile.name.endsWith('.xlsx') || droppedFile.name.endsWith('.xls'))) {
      handleFileUpload(droppedFile);
    }
  };

  // 통계 계산
  const totalMissing = columnInfo.reduce((sum, col) => sum + col.missing, 0);
  const numericColumns = columnInfo.filter(c => c.type === 'number').length;

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-[#1c1c1e] overflow-hidden">
      {/* 파일이 없을 때 - 업로드 영역 */}
      {!file ? (
        <div className="flex-1 flex items-center justify-center p-8 overflow-auto">
          <Card className="max-w-2xl w-full p-8">
            <div className="text-center space-y-6">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500 to-purple-600 text-white text-4xl">
                <FileSpreadsheet className="w-10 h-10" />
              </div>
              
              <div>
                <h2 className="text-2xl text-gray-900 dark:text-white mb-2">
                  데이터 전처리
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                  CSV 또는 Excel 파일을 업로드하여 데이터를 정제하고 변환하세요
                </p>
              </div>

              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`
                  relative border-2 border-dashed rounded-xl p-12 transition-all cursor-pointer
                  ${isDragging 
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
                    : 'border-gray-300 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-600'
                  }
                `}
              >
                <input
                  type="file"
                  accept=".csv, .xlsx, .xls"
                  onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                
                <div className="space-y-3">
                  <Upload className="w-12 h-12 mx-auto text-gray-400" />
                  <div>
                    <p className="text-gray-900 dark:text-white mb-1">
                      파일을 드래그하거나 클릭하여 업로드
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      CSV, XLSX, XLS 형식 지원 (최대 50MB)
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-4">
                <div className="text-left p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <CheckCircle2 className="w-5 h-5 text-green-500 mb-2" />
                  <p className="text-sm text-gray-900 dark:text-white mb-1">데이터 분석</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">결측치, 이상치, 통계 정보 자동 분석</p>
                </div>
                <div className="text-left p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <Settings className="w-5 h-5 text-blue-500 mb-2" />
                  <p className="text-sm text-gray-900 dark:text-white mb-1">데이터 정제</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">스케일링, 결측치 처리, 이상치 제거</p>
                </div>
              </div>
            </div>
          </Card>
        </div>
      ) : (
        /* 파일이 있을 때 - 전처리 작업 영역 */
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* 파일 정보 헤더 */}
          <div className="flex items-center justify-between px-6 py-4 bg-white dark:bg-[#171717] border-b border-gray-200 dark:border-white/10">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Database className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="text-lg text-gray-900 dark:text-white">{file.name}</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {data.length}행 × {columns.length}열
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              {/* Undo/Redo 버튼 */}
              <div className="flex items-center gap-1 mr-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={undo}
                  disabled={!canUndo()}
                  title="실행 취소 (Ctrl+Z)"
                >
                  <Undo2 className="w-4 h-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={redo}
                  disabled={!canRedo()}
                  title="다시 실행 (Ctrl+Y)"
                >
                  <Redo2 className="w-4 h-4" />
                </Button>
              </div>
              
              <Button
                variant="outline"
                onClick={() => {
                  clearData();
                  setSelectedColumns([]);
                }}
              >
                새 파일
              </Button>
              <Button
                onClick={handleDownload}
                className="gap-2 bg-blue-600 hover:bg-blue-700"
              >
                <Download className="w-4 h-4" />
                전처리 완료 및 다운로드
              </Button>
            </div>
          </div>

          {/* 2분할 레이아웃 */}
          <div className="flex-1 flex flex-col gap-0 overflow-hidden bg-gray-50 dark:bg-[#1c1c1e]">
            {/* 상단: 데이터 요약 */}
            <div className="px-6 pt-6 pb-4">
              <Card className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-lg text-gray-900 dark:text-white mb-1">데이터 요약</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">업로드된 데이터의 전체 개요</p>
                  </div>
                  <Info className="w-5 h-5 text-gray-400" />
                </div>

                <div className="grid grid-cols-5 gap-4">
                  <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">총 행 수</p>
                    <p className="text-2xl text-gray-900 dark:text-white">{data.length}</p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">총 열 수</p>
                    <p className="text-2xl text-gray-900 dark:text-white">{columns.length}</p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">숫자형 열</p>
                    <p className="text-2xl text-gray-900 dark:text-white">{numericColumns}</p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">문자형 열</p>
                    <p className="text-2xl text-gray-900 dark:text-white">{columns.length - numericColumns}</p>
                  </div>
                  <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                    <p className="text-xs text-red-600 dark:text-red-400 mb-1">총 결측치</p>
                    <p className="text-2xl text-red-600 dark:text-red-400">{totalMissing}</p>
                  </div>
                </div>
              </Card>
            </div>

            {/* 하단: 열 정보 및 전처리 도구 */}
            <div className="flex-1 flex gap-4 px-6 pb-6 overflow-hidden min-h-0">
              {/* 좌측: 열 정보 테이블 */}
              <Card className="flex-1 overflow-hidden flex flex-col">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-lg text-gray-900 dark:text-white">열 상세 정보</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">각 열의 통계 정보 및 데이터 품질</p>
                </div>
                
                <div className="flex-1 overflow-auto">
                  <ScrollArea className="h-full">
                    <table className="w-full">
                      <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0 z-10">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs text-gray-500 dark:text-gray-400">
                            <input
                              type="checkbox"
                              checked={selectedColumns.length === columns.length}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedColumns([...columns]);
                                } else {
                                  setSelectedColumns([]);
                                }
                              }}
                              className="rounded"
                            />
                          </th>
                          <th className="px-4 py-3 text-left text-xs text-gray-500 dark:text-gray-400">열 이름</th>
                          <th className="px-4 py-3 text-left text-xs text-gray-500 dark:text-gray-400">타입</th>
                          <th className="px-4 py-3 text-left text-xs text-gray-500 dark:text-gray-400">결측치</th>
                          <th className="px-4 py-3 text-left text-xs text-gray-500 dark:text-gray-400">고유값</th>
                          <th className="px-4 py-3 text-left text-xs text-gray-500 dark:text-gray-400">평균</th>
                          <th className="px-4 py-3 text-left text-xs text-gray-500 dark:text-gray-400">표준편차</th>
                          <th className="px-4 py-3 text-left text-xs text-gray-500 dark:text-gray-400">최소값</th>
                          <th className="px-4 py-3 text-left text-xs text-gray-500 dark:text-gray-400">최대값</th>
                          <th className="px-4 py-3 text-left text-xs text-gray-500 dark:text-gray-400"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {columnInfo.map((col) => (
                          <tr
                            key={col.name}
                            className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                          >
                            <td className="px-4 py-3">
                              <input
                                type="checkbox"
                                checked={selectedColumns.includes(col.name)}
                                onChange={() => toggleColumnSelection(col.name)}
                                className="rounded"
                              />
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                              {col.name}
                            </td>
                            <td className="px-4 py-3">
                              <Badge variant="outline" className="text-xs">
                                {col.type}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-sm">
                              {col.missing > 0 ? (
                                <span className="text-red-600 dark:text-red-400">
                                  {col.missing} ({((col.missing / data.length) * 100).toFixed(1)}%)
                                </span>
                              ) : (
                                <span className="text-green-600 dark:text-green-400">0</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">{col.unique}</td>
                            <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                              {col.mean !== undefined ? col.mean : '-'}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                              {col.std !== undefined ? col.std : '-'}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                              {col.min !== undefined ? col.min : '-'}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                              {col.max !== undefined ? col.max : '-'}
                            </td>
                            <td className="px-4 py-3">
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="icon" className="h-8 w-8">
                                    <MoreVertical className="w-4 h-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="w-56">
                                  {/* 결측치 처리 */}
                                  {col.missing > 0 && (
                                    <>
                                      <DropdownMenuSub>
                                        <DropdownMenuSubTrigger>
                                          결측치 채우기
                                        </DropdownMenuSubTrigger>
                                        <DropdownMenuSubContent>
                                          {col.type === 'number' && (
                                            <>
                                              <DropdownMenuItem onClick={() => handleFillMissing(col.name, 'mean')}>
                                                평균값으로
                                              </DropdownMenuItem>
                                              <DropdownMenuItem onClick={() => handleFillMissing(col.name, 'median')}>
                                                중간값으로
                                              </DropdownMenuItem>
                                            </>
                                          )}
                                          <DropdownMenuItem onClick={() => handleFillMissing(col.name, 'mode')}>
                                            최빈값으로
                                          </DropdownMenuItem>
                                        </DropdownMenuSubContent>
                                      </DropdownMenuSub>
                                      <DropdownMenuSeparator />
                                    </>
                                  )}
                                  
                                  {/* 타입 변경 */}
                                  <DropdownMenuSub>
                                    <DropdownMenuSubTrigger>
                                      타입 변경
                                    </DropdownMenuSubTrigger>
                                    <DropdownMenuSubContent>
                                      <DropdownMenuItem onClick={() => handleChangeType(col.name, 'number')}>
                                        숫자형으로
                                      </DropdownMenuItem>
                                      <DropdownMenuItem onClick={() => handleChangeType(col.name, 'string')}>
                                        문자형으로
                                      </DropdownMenuItem>
                                    </DropdownMenuSubContent>
                                  </DropdownMenuSub>
                                  
                                  {/* 이상치 제거 */}
                                  {col.type === 'number' && (
                                    <>
                                      <DropdownMenuSeparator />
                                      <DropdownMenuItem onClick={() => handleRemoveOutliers(col.name)}>
                                        <TrendingUp className="w-4 h-4 mr-2" />
                                        이상치 제거 (IQR)
                                      </DropdownMenuItem>
                                    </>
                                  )}
                                  
                                  {/* 열 삭제 */}
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem 
                                    onClick={() => handleDeleteColumn(col.name)}
                                    className="text-red-600 dark:text-red-400"
                                  >
                                    <Trash2 className="w-4 h-4 mr-2" />
                                    열 삭제
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </ScrollArea>
                </div>
              </Card>

              {/* 우측: 전처리 도구 */}
              <Card className="w-80 overflow-hidden flex flex-col">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-lg text-gray-900 dark:text-white mb-1">전처리 도구</h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {selectedColumns.length > 0 
                      ? `${selectedColumns.length}개 열 선택됨`
                      : '왼쪽에서 열을 선택하세요'
                    }
                  </p>
                </div>

                <ScrollArea className="flex-1">
                  <div className="p-4 space-y-6">
                    {/* 스케일링 */}
                    <div>
                      <h4 className="text-sm text-gray-900 dark:text-white mb-3">스케일링</h4>
                      <RadioGroup value={scalingMethod} onValueChange={(v) => setScalingMethod(v as any)}>
                        <div className="flex items-center space-x-2 mb-2">
                          <RadioGroupItem value="standardization" id="standardization" />
                          <Label htmlFor="standardization" className="text-sm cursor-pointer">
                            Standardization (Z-score)
                          </Label>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 ml-6 mb-3">
                          평균 0, 표준편차 1로 변환
                        </p>
                        
                        <div className="flex items-center space-x-2 mb-2">
                          <RadioGroupItem value="normalization" id="normalization" />
                          <Label htmlFor="normalization" className="text-sm cursor-pointer">
                            Normalization (Min-Max)
                          </Label>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 ml-6 mb-3">
                          0과 1 사이로 변환
                        </p>
                      </RadioGroup>

                      <Button
                        onClick={() => {
                          if (scalingMethod === 'standardization') {
                            handleStandardization();
                          } else {
                            handleNormalization();
                          }
                        }}
                        disabled={selectedColumns.length === 0}
                        className="w-full mt-2"
                      >
                        선택한 열에 적용
                      </Button>
                    </div>

                    <Separator />

                    {/* 일괄 결측치 처리 */}
                    {selectedColumns.length === 1 && (() => {
                      const colInfo = columnInfo.find(c => c.name === selectedColumns[0]);
                      return colInfo && colInfo.missing > 0 ? (
                        <div>
                          <h4 className="text-sm text-gray-900 dark:text-white mb-3">
                            결측치 처리 ({colInfo.missing}개)
                          </h4>
                          <div className="space-y-2">
                            {colInfo.type === 'number' && (
                              <>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="w-full justify-start"
                                  onClick={() => handleFillMissing(selectedColumns[0], 'mean')}
                                >
                                  평균값으로 채우기
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="w-full justify-start"
                                  onClick={() => handleFillMissing(selectedColumns[0], 'median')}
                                >
                                  중간값으로 채우기
                                </Button>
                              </>
                            )}
                            <Button
                              variant="outline"
                              size="sm"
                              className="w-full justify-start"
                              onClick={() => handleFillMissing(selectedColumns[0], 'mode')}
                            >
                              최빈값으로 채우기
                            </Button>
                            <div className="space-y-2">
                              <Label className="text-xs">지정값으로 채우기</Label>
                              <div className="flex gap-2">
                                <Input
                                  placeholder="값 입력"
                                  id="custom-fill"
                                  className="flex-1"
                                />
                                <Button
                                  size="sm"
                                  onClick={() => {
                                    const input = document.getElementById('custom-fill') as HTMLInputElement;
                                    handleFillMissing(selectedColumns[0], 'custom', input.value);
                                  }}
                                >
                                  적용
                                </Button>
                              </div>
                            </div>
                          </div>
                        </div>
                      ) : null;
                    })()}

                    {selectedColumns.length === 1 && (() => {
                      const colInfo = columnInfo.find(c => c.name === selectedColumns[0]);
                      return colInfo && colInfo.missing > 0 ? <Separator /> : null;
                    })()}

                    {/* 이상치 제거 */}
                    {selectedColumns.length === 1 && (() => {
                      const colInfo = columnInfo.find(c => c.name === selectedColumns[0]);
                      return colInfo && colInfo.type === 'number' ? (
                        <div>
                          <h4 className="text-sm text-gray-900 dark:text-white mb-3">이상치 제거</h4>
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full justify-start gap-2"
                            onClick={() => handleRemoveOutliers(selectedColumns[0])}
                          >
                            <TrendingUp className="w-4 h-4" />
                            IQR 방식으로 제거
                          </Button>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                            Q1 - 1.5×IQR 미만 또는 Q3 + 1.5×IQR 초과하는 데이터를 제거합니다
                          </p>
                        </div>
                      ) : null;
                    })()}

                    {selectedColumns.length === 1 && (() => {
                      const colInfo = columnInfo.find(c => c.name === selectedColumns[0]);
                      return colInfo && colInfo.type === 'number' ? <Separator /> : null;
                    })()}

                    {/* 데이터 타입 변경 */}
                    {selectedColumns.length === 1 && (
                      <div>
                        <h4 className="text-sm text-gray-900 dark:text-white mb-3">데이터 타입 변경</h4>
                        <div className="space-y-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full justify-start"
                            onClick={() => handleChangeType(selectedColumns[0], 'number')}
                          >
                            숫자형으로 변환
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full justify-start"
                            onClick={() => handleChangeType(selectedColumns[0], 'string')}
                          >
                            문자형으로 변환
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </Card>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}