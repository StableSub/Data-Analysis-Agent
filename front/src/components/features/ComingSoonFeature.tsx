import { LucideIcon } from 'lucide-react';
import { Card } from '../ui/card';

interface ComingSoonFeatureProps {
  icon: LucideIcon;
  title: string;
  description: string;
  features?: string[];
}

export function ComingSoonFeature({ 
  icon: Icon, 
  title, 
  description,
  features = []
}: ComingSoonFeatureProps) {
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-white/10">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <Icon className="w-5 h-5 text-blue-600 dark:text-[#0a84ff]" />
          </div>
          <div>
            <h2 className="text-gray-900 dark:text-white text-xl">{title}</h2>
            <p className="text-sm text-gray-500 dark:text-[#98989d]">{description}</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-3xl mx-auto">
          <Card className="p-12 text-center">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/30 dark:to-purple-900/30 flex items-center justify-center mx-auto mb-6">
              <Icon className="w-10 h-10 text-blue-600 dark:text-[#0a84ff]" />
            </div>
            
            <h3 className="text-2xl text-gray-900 dark:text-white mb-3">
              곧 출시 예정
            </h3>
            
            <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md mx-auto">
              {description}
            </p>

            {features.length > 0 && (
              <div className="inline-block text-left">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                  예정된 기능:
                </h4>
                <ul className="space-y-2">
                  {features.map((feature, idx) => (
                    <li key={idx} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-8 pt-8 border-t border-gray-200 dark:border-white/10">
              <p className="text-xs text-gray-500 dark:text-[#98989d]">
                이 기능은 현재 개발 중입니다
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
