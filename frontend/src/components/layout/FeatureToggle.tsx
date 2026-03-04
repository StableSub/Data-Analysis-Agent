import { LucideIcon } from 'lucide-react';

interface FeatureToggleItem {
  id: string;
  icon: LucideIcon;
  label: string;
}

interface FeatureToggleProps {
  items: FeatureToggleItem[];
  activeId: string;
  onChange: (id: string) => void;
}

export function FeatureToggle({ items, activeId, onChange }: FeatureToggleProps) {
  return (
    <div className="inline-flex items-center rounded-xl bg-gray-100 dark:bg-[#2f2f2f] p-1 gap-1">
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = item.id === activeId;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onChange(item.id)}
            className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
              isActive
                ? 'bg-white dark:bg-[#212121] text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <Icon className="w-4 h-4" />
            <span>{item.label}</span>
          </button>
        );
      })}
    </div>
  );
}
