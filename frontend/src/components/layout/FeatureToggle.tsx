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
    <div className="absolute left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-xl border border-white/20 bg-black/60 p-1 backdrop-blur-lg">
      {items.map(({ id, icon: Icon, label }) => {
        const isActive = activeId === id;
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            className={
              `flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ` +
              (isActive
                ? 'bg-[#5a7d9a] text-white shadow-[0_2px_10px_rgba(90,125,154,0.28)]'
                : 'text-white/90 hover:text-white hover:bg-black/80')
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
