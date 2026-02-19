import { Outlet } from 'react-router-dom';
import { Toaster } from '../ui/sonner';

export function AppLayout() {
  return (
    <div className="min-h-screen dark bg-background text-foreground">
      <Outlet />
      <Toaster />
    </div>
  );
}

