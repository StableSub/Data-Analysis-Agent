import { ReactNode } from 'react';

interface AppHeaderProps {
  title: string;
  subtitle: string;
  center?: ReactNode;
  rightSlot?: ReactNode;
}

export function AppHeader({ title, subtitle, center, rightSlot }: AppHeaderProps) {
  return (
    <div className="border-b border-zinc-200 bg-white px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl text-zinc-900">{title}</h1>
          <p className="text-sm text-zinc-500">{subtitle}</p>
        </div>

        {/* Center content (e.g., FeatureToggle) */}
        {center}

        <div className="flex min-w-[48px] items-center justify-end gap-3">{rightSlot}</div>
      </div>
    </div>
  );
}
