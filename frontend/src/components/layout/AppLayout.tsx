import { Outlet } from 'react-router-dom';
import { Toaster } from '../ui/sonner';

export function AppLayout() {
  return (
    <div className="min-h-screen">
      <Outlet />
      <Toaster />
    </div>
  );
}

