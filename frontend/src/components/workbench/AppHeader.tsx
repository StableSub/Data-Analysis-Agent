import { ReactNode } from 'react';
import { Moon, Sun } from 'lucide-react';

interface AppHeaderProps {
  title: string;
  subtitle: string;
  isDark: boolean;
  onToggleTheme: () => void;
  center?: ReactNode;
}

export function AppHeader({ title, subtitle, isDark, onToggleTheme, center }: AppHeaderProps) {
  return (
    <header className="h-16 px-6 border-b border-gray-200 dark:border-white/10 bg-white dark:bg-[#212121] flex items-center gap-4">
      <div className="min-w-[180px]">
        <h1 className="text-base text-gray-900 dark:text-white leading-tight">{title}</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>
      </div>

      <div className="flex-1 flex justify-center">{center}</div>

      <button
        type="button"
        onClick={onToggleTheme}
        className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-[#2f2f2f] text-gray-700 dark:text-white inline-flex items-center justify-center"
        aria-label="테마 전환"
      >
        {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      </button>
    </header>
  );
}
