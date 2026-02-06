import { useTheme } from '../../hooks/useTheme';
import { Button } from '../ui/button';
import { Menu, X, Sun, Moon, Bot } from 'lucide-react';
import { ModelSelector } from './ModelSelector';
import { DEFAULT_MODEL_ID } from '../../lib/models';

interface HeaderProps {
  currentSessionTitle?: string;
  showSidebar: boolean;
  showAgent: boolean;
  onToggleSidebar: () => void;
  onToggleAgent: () => void;
  selectedModelId?: string;
  onSelectModel?: (modelId: string) => void;
  hasMessages?: boolean;
}

export function Header({
  currentSessionTitle,
  showSidebar,
  showAgent,
  onToggleSidebar,
  onToggleAgent,
  selectedModelId,
  onSelectModel,
}: HeaderProps) {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="bg-white dark:bg-[#2c2c2e] border-b border-gray-200 dark:border-white/10 px-4 sm:px-6 py-3 transition-colors">
      <div className="flex items-center justify-between gap-4 h-10">
        {/* Left Side */}
        <div className="flex items-center gap-3 flex-1 min-w-0 h-10">
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            className="shrink-0 h-10 w-10"
          >
            {showSidebar ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </Button>

          <div className="min-w-0 flex-1 flex items-center h-10">
            <div className="flex flex-col justify-center min-w-0">
              <h2 className="text-gray-900 dark:text-white truncate text-sm sm:text-base leading-tight">
                {currentSessionTitle || '새 대화'}
              </h2>
              <p className="text-xs text-gray-500 dark:text-[#98989d] hidden sm:block leading-tight">
                Manufacturing AI Assistant
              </p>
            </div>
          </div>
        </div>

        {/* Right Side */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0 h-10">
          {/* Model Selector */}
          {onSelectModel && (
            <ModelSelector
              selectedModelId={selectedModelId || DEFAULT_MODEL_ID}
              onSelectModel={onSelectModel}
              variant="compact"
            />
          )}

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="shrink-0 h-10 w-10"
          >
            {theme === 'light' ? (
              <Moon className="w-4 h-4" />
            ) : (
              <Sun className="w-4 h-4" />
            )}
          </Button>

          {/* Agent Widget Toggle - Only show when hidden */}
          {!showAgent && (
            <Button
              variant="outline"
              size="sm"
              onClick={onToggleAgent}
              className="gap-2 hidden md:flex h-10"
            >
              <Bot className="w-4 h-4" />
              <span className="hidden lg:inline">Agent</span>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
