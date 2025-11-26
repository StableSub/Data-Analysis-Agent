// Mock data for development and demonstration

export const mockCSVPreview = [
  { timestamp: '2025-11-01 08:00:00', machine_id: 'M001', temperature: 72.5, pressure: 101.3, quality: 'OK' },
  { timestamp: '2025-11-01 08:05:00', machine_id: 'M001', temperature: 73.2, pressure: 101.5, quality: 'OK' },
  { timestamp: '2025-11-01 08:10:00', machine_id: 'M002', temperature: 71.8, pressure: 100.9, quality: 'OK' },
  { timestamp: '2025-11-01 08:15:00', machine_id: 'M001', temperature: 85.4, pressure: 102.8, quality: 'WARNING' },
  { timestamp: '2025-11-01 08:20:00', machine_id: 'M003', temperature: 70.1, pressure: 101.1, quality: 'OK' },
];

export const mockAnalysisResult = {
  eda: {
    summary: {
      totalRows: 1250,
      totalColumns: 5,
      dateRange: '2025-11-01 ~ 2025-11-04',
      missingValues: 12,
    },
    distributions: [
      { name: 'Temperature', min: 68.2, max: 92.1, mean: 73.5, median: 72.8, std: 4.2 },
      { name: 'Pressure', min: 99.5, max: 105.3, mean: 101.2, median: 101.1, std: 1.1 },
    ],
    correlations: [
      { var1: 'Temperature', var2: 'Pressure', correlation: 0.67 },
      { var1: 'Temperature', var2: 'Quality', correlation: -0.42 },
    ],
  },
  anomalies: {
    detected: 23,
    items: [
      { timestamp: '2025-11-01 08:15:00', machine_id: 'M001', type: 'Temperature Spike', severity: 'High', value: 85.4 },
      { timestamp: '2025-11-02 14:30:00', machine_id: 'M002', type: 'Pressure Drop', severity: 'Medium', value: 99.2 },
      { timestamp: '2025-11-03 10:45:00', machine_id: 'M003', type: 'Temperature Spike', severity: 'High', value: 88.7 },
      { timestamp: '2025-11-03 16:20:00', machine_id: 'M001', type: 'Quality Degradation', severity: 'Low', value: 0 },
    ],
  },
};

export const mockReport = `# 제조 데이터 분석 리포트

**분석 기간**: 2025-11-01 ~ 2025-11-04  
**생성 일시**: 2025-11-06 14:30:00

## 📊 주요 발견사항

### 1. 데이터 개요
- 총 **1,250개** 레코드 분석 완료
- **3대**의 제조 설비(M001, M002, M003) 모니터링
- 결측치: 12건 (전체의 0.96%)

### 2. 온도 분석
평균 온도는 **73.5°C**로 정상 범위 내에 있으나, M001 설비에서 간헐적인 온도 급상승(85°C 이상)이 관찰되었습니다.

**권장사항**: M001 설비의 냉각 시스템 점검 필요

### 3. 이상 탐지 결과
총 **23건**의 이상 패턴이 감지되었습니다:
- 고온도 경고: 15건
- 압력 이상: 5건  
- 품질 저하: 3건

### 4. 상관관계 분석
- 온도와 압력 간 **양의 상관관계(0.67)** 확인
- 온도 상승 시 품질 저하 경향 **음의 상관관계(-0.42)**

## 🎯 결론 및 권장사항

1. **즉시 조치**: M001 설비 냉각 시스템 정밀 점검
2. **예방 조치**: 온도 임계값 알람 설정 (80°C 이상)
3. **지속 모니터링**: 압력-온도 동시 모니터링 강화

---
*본 리포트는 AI 기반 분석 시스템에 의해 자동 생성되었습니다.*
`;

export const mockTraceEvents = [
  { 
    timestamp: '2025-11-06 14:28:35', 
    type: 'exec' as const, 
    process: 'python3', 
    details: 'analyze_data.py --input data.csv', 
    suspicious: false 
  },
  { 
    timestamp: '2025-11-06 14:28:32', 
    type: 'tcp_connect' as const, 
    process: 'node', 
    details: 'Connection to api.openai.com:443', 
    suspicious: false 
  },
  { 
    timestamp: '2025-11-06 14:28:28', 
    type: 'open' as const, 
    process: 'python3', 
    details: '/tmp/uploaded_data.csv', 
    suspicious: false 
  },
  { 
    timestamp: '2025-11-06 14:28:15', 
    type: 'exec' as const, 
    process: 'unknown', 
    details: 'Suspicious binary execution detected', 
    suspicious: true 
  },
  { 
    timestamp: '2025-11-06 14:28:10', 
    type: 'tcp_connect' as const, 
    process: 'curl', 
    details: 'Connection to unknown-domain.xyz:8080', 
    suspicious: true 
  },
];

export const mockDashboardStats = {
  totalAnalyses: 47,
  filesProcessed: 124,
  anomaliesDetected: 23,
  systemHealth: 98,
  recentActivity: [
    { time: '14:28', action: 'Analysis completed', status: 'success' },
    { time: '14:15', action: 'CSV uploaded: production_data.csv', status: 'success' },
    { time: '14:02', action: 'Report generated', status: 'success' },
    { time: '13:45', action: 'Anomaly detection started', status: 'processing' },
  ],
  topProcesses: [
    { name: 'python3', count: 145, percentage: 45 },
    { name: 'node', count: 87, percentage: 27 },
    { name: 'analyze_data', count: 56, percentage: 17 },
  ],
};
