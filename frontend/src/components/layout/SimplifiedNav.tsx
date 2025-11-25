import { MessageSquare, BarChart3, FileEdit, Activity, Shield, Plus } from 'lucide-react';
import { Button } from '../ui/button';

export type FeatureType = 'chat' | 'visualization' | 'edit' | 'simulation' | 'audit';

interface SimplifiedNavProps {
  activeFeature: FeatureType;
  onFeatureChange: (feature: FeatureType) => void;
  onNewChat: () => void;
}

const features = [
  { id: 'chat' as FeatureType, icon: MessageSquare, label: 'AI 챗봇' },
  { id: 'visualization' as FeatureType, icon: BarChart3, label: '데이터 시각화' },
  { id: 'edit' as FeatureType, icon: FileEdit, label: '데이터 편집' },
  { id: 'simulation' as FeatureType, icon: Activity, label: '시뮬레이션' },
  { id: 'audit' as FeatureType, icon: Shield, label: '감사 로그' },
];

export function SimplifiedNav({ activeFeature, onFeatureChange, onNewChat }: SimplifiedNavProps) {
  return (
    <div className="w-64 h-full bg-white dark:bg-[#171717] border-r border-gray-200 dark:border-white/10 flex flex-col">
      {/* 새 대화 버튼 */}
      <div className="p-4 border-b border-gray-200 dark:border-white/10">
        <Button
          onClick={onNewChat}
          className="w-full justify-start gap-3 h-12 bg-blue-600 hover:bg-blue-700 dark:bg-[#0a84ff] dark:hover:bg-[#0077ed] text-white shadow-sm"
        >
          <Plus className="w-5 h-5" />
          <span className="text-sm font-medium">새 대화</span>
        </Button>
      </div>

      {/* 기능 메뉴 */}
      <div className="flex-1 p-3 space-y-1">
        {features.map(({ id, icon: Icon, label }) => {
          const isActive = activeFeature === id;
          
          return (
            <button
              key={id}
              onClick={() => onFeatureChange(id)}
              className={`
                w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all
                ${isActive 
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-[#0a84ff]' 
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/5'
                }
              `}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'text-blue-600 dark:text-[#0a84ff]' : ''}`} />
              <span className="text-sm font-medium">{label}</span>
            </button>
          );
        })}
      </div>

      {/* 하단 정보 */}
      <div className="p-4 border-t border-gray-200 dark:border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm">
            U
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-gray-900 dark:text-white truncate">사용자</p>
            <p className="text-xs text-gray-500 dark:text-[#98989d] truncate">user@example.com</p>
          </div>
        </div>
      </div>
    </div>
  );
}
