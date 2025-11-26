import { Moon, Sun } from 'lucide-react';
import { Button } from '../ui/button';

interface ThemeToggleButtonProps {
  isDark: boolean;
  onToggle: () => void;
}

export function ThemeToggleButton({ isDark, onToggle }: ThemeToggleButtonProps) {
  return (
    <Button size="icon" variant="ghost" onClick={onToggle} className="h-10 w-10">
      {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
    </Button>
  );
}

