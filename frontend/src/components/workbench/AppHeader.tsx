import { ReactNode } from 'react';

interface AppHeaderProps {
  title: string;
  subtitle: string;
  center?: ReactNode;
  rightSlot?: ReactNode;
}

export function AppHeader({ title, subtitle, center, rightSlot }: AppHeaderProps) {
  return (
    <div className="border-b border-white/20 bg-black/90 px-5 py-2.5 backdrop-blur-xl">
      <div className="flex items-center justify-between">
        <div className="min-w-[220px]">
          <h1 className="text-base font-semibold tracking-tight text-white">{title}</h1>
          <p className="mt-0.5 text-xs text-white/80">{subtitle}</p>
        </div>

        {center}

        <div className="flex min-w-[48px] items-center justify-end gap-3">{rightSlot}</div>
      </div>
    </div>
  );
}
