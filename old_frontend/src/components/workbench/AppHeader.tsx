import { ReactNode } from 'react';
import { ThemeToggleButton } from '../layout/ThemeToggleButton';

interface AppHeaderProps {
  title: string;
  subtitle: string;
  isDark: boolean;
  onToggleTheme: () => void;
  center?: ReactNode;
}

export function AppHeader({ title, subtitle, isDark, onToggleTheme, center }: AppHeaderProps) {
  return (
    <div className="bg-white dark:bg-[#171717] border-b border-gray-200 dark:border-white/10 px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl text-gray-900 dark:text-white">{title}</h1>
          <p className="text-sm text-gray-500 dark:text-[#98989d]">{subtitle}</p>
        </div>

        {/* Center content (e.g., FeatureToggle) */}
        {center}

        <div className="flex items-center gap-3">
          <ThemeToggleButton isDark={isDark} onToggle={onToggleTheme} />
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm">
            U
          </div>
        </div>
      </div>
    </div>
  );
}
