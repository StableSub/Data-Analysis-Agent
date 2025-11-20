import { LayoutDashboard, Upload, BarChart3, FileText, Activity, LogOut, User } from 'lucide-react';
import { cn } from '../ui/utils';
import { useStore } from '../../store/useStore';
import { Button } from '../ui/button';
import { Avatar, AvatarFallback } from '../ui/avatar';

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
}

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'upload', label: 'Upload', icon: Upload },
  { id: 'analysis', label: 'Analysis', icon: BarChart3 },
  { id: 'report', label: 'Report', icon: FileText },
  { id: 'trace', label: 'Trace', icon: Activity },
];

export function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  const { user, logout } = useStore();

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-blue-600">Manufacturing AI</h1>
        <p className="text-sm text-gray-500 mt-1">데이터 분석 에이전트</p>
      </div>
      
      {/* User Info */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <Avatar>
            <AvatarFallback className="bg-blue-100 text-blue-600">
              {user?.name.charAt(0) || 'U'}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-gray-900 truncate">{user?.name}</p>
            <p className="text-xs text-gray-500 truncate">{user?.role}</p>
          </div>
        </div>
      </div>
      
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            
            return (
              <li key={item.id}>
                <button
                  onClick={() => onNavigate(item.id)}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors",
                    isActive 
                      ? "bg-blue-50 text-blue-600" 
                      : "text-gray-700 hover:bg-gray-50"
                  )}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
      
      <div className="p-4 border-t border-gray-200 space-y-3">
        <Button 
          variant="outline" 
          size="sm" 
          className="w-full justify-start" 
          onClick={logout}
        >
          <LogOut className="w-4 h-4 mr-2" />
          로그아웃
        </Button>
        <div className="text-xs text-gray-500">
          <p>Version 1.0</p>
          <p className="mt-1">© 2025 이승현</p>
        </div>
      </div>
    </div>
  );
}
