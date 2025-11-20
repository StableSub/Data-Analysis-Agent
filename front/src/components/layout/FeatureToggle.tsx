import React from 'react';

type ToggleItem = {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
};

interface FeatureToggleProps {
  items: ToggleItem[];
  activeId: string;
  onChange: (id: string) => void;
}

export function FeatureToggle({ items, activeId, onChange }: FeatureToggleProps) {
  return (
    <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2">
      {items.map(({ id, icon: Icon, label }) => {
        const isActive = activeId === id;
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            className={
              `flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all ` +
              (isActive
                ? 'bg-blue-600 dark:bg-[#0084ff] text-white shadow-sm'
                : 'bg-gray-100 dark:bg-white/5 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-white/10')
            }
          >
            <Icon className="w-4 h-4" />
            <span>{label}</span>
          </button>
        );
      })}
    </div>
  );
}

