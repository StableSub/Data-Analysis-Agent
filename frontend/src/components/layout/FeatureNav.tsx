import { 
  Upload, 
  MessageSquare, 
  BarChart3, 
  FileEdit, 
  Shield, 
  Activity,
  Database,
  FileSpreadsheet,
  Filter
} from 'lucide-react';
import { Button } from '../ui/button';
import { cn } from '../ui/utils';
import { ScrollArea } from '../ui/scroll-area';
import { Separator } from '../ui/separator';

export type FeatureType = 
  | 'chat'
  | 'data-upload'
  | 'data-snapshot'
  | 'data-filter'
  | 'visualization'
  | 'data-edit'
  | 'simulation'
  | 'audit-log';

interface FeatureNavProps {
  activeFeature: FeatureType;
  onFeatureChange: (feature: FeatureType) => void;
}

interface FeatureCategory {
  title: string;
  features: {
    id: FeatureType;
    label: string;
    icon: any;
    description: string;
  }[];
}

const FEATURE_CATEGORIES: FeatureCategory[] = [
  {
    title: 'AI 분석',
    features: [
      {
        id: 'chat',
        label: 'AI 챗봇',
        icon: MessageSquare,
        description: '자연어 대화형 분석'
      },
    ]
  },
  {
    title: '데이터 관리',
    features: [
      {
        id: 'data-upload',
        label: '데이터 업로드',
        icon: Upload,
        description: '파일 임포트 & 업로드'
      },
      {
        id: 'data-snapshot',
        label: '데이터 스냅샷',
        icon: Database,
        description: '데이터 버전 관리'
      },
      {
        id: 'data-filter',
        label: '데이터 필터링',
        icon: Filter,
        description: '조건별 데이터 추출'
      },
    ]
  },
  {
    title: '분석 & 시각화',
    features: [
      {
        id: 'visualization',
        label: '데이터 시각화',
        icon: BarChart3,
        description: '차트 & 그래프'
      },
      {
        id: 'data-edit',
        label: '데이터 편집',
        icon: FileEdit,
        description: 'AI 기반 데이터 수정'
      },
      {
        id: 'simulation',
        label: '시뮬레이션',
        icon: Activity,
        description: '제조 공정 시뮬레이션'
      },
    ]
  },
  {
    title: '보안 & 로그',
    features: [
      {
        id: 'audit-log',
        label: '감사 로그',
        icon: Shield,
        description: '사용자 활동 추적'
      },
    ]
  },
];

export function FeatureNav({ activeFeature, onFeatureChange }: FeatureNavProps) {
  return (
    <div className="w-64 h-screen bg-white dark:bg-[#2c2c2e] border-r border-gray-200 dark:border-white/10 flex flex-col">
      {/* Logo / Title */}
      <div className="p-4 border-b border-gray-200 dark:border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <FileSpreadsheet className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-gray-900 dark:text-white font-semibold">제조 데이터 분석</h1>
            <p className="text-xs text-gray-500 dark:text-[#98989d]">AI Assistant</p>
          </div>
        </div>
      </div>

      {/* Feature Navigation */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-6">
          {FEATURE_CATEGORIES.map((category, idx) => (
            <div key={category.title}>
              {idx > 0 && <Separator className="my-3" />}
              <div className="mb-2 px-2">
                <span className="text-xs text-gray-500 dark:text-[#98989d] uppercase tracking-wider">
                  {category.title}
                </span>
              </div>
              <div className="space-y-1">
                {category.features.map((feature) => {
                  const Icon = feature.icon;
                  const isActive = activeFeature === feature.id;
                  
                  return (
                    <Button
                      key={feature.id}
                      variant="ghost"
                      onClick={() => onFeatureChange(feature.id)}
                      className={cn(
                        "w-full justify-start gap-3 h-auto py-2.5 px-3 hover:bg-gray-100 dark:hover:bg-white/10",
                        isActive && "bg-blue-50 dark:bg-[#0a84ff]/10 hover:bg-blue-100 dark:hover:bg-[#0a84ff]/15"
                      )}
                    >
                      <Icon className={cn(
                        "w-4 h-4 flex-shrink-0",
                        isActive 
                          ? "text-blue-600 dark:text-[#0a84ff]" 
                          : "text-gray-500 dark:text-[#98989d]"
                      )} />
                      <div className="flex-1 text-left min-w-0">
                        <div className={cn(
                          "text-sm",
                          isActive
                            ? "text-blue-700 dark:text-[#0a84ff] font-medium"
                            : "text-gray-700 dark:text-white"
                        )}>
                          {feature.label}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-[#98989d] truncate">
                          {feature.description}
                        </div>
                      </div>
                    </Button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Footer Info */}
      <div className="p-4 border-t border-gray-200 dark:border-white/10">
        <div className="text-xs text-gray-500 dark:text-[#98989d]">
          <div className="flex items-center justify-between mb-1">
            <span>버전</span>
            <span className="font-mono">v1.0.0</span>
          </div>
          <div className="flex items-center justify-between">
            <span>상태</span>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              <span className="text-green-600 dark:text-green-400">활성</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
