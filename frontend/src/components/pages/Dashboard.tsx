import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Activity, FileCheck, AlertTriangle, Cpu } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export function Dashboard() {
  const stats = {
    totalAnalyses: 0,
    filesProcessed: 0,
    anomaliesDetected: 0,
    systemHealth: 100,
    recentActivity: [] as Array<{ action: string; time: string; status: string }>,
    topProcesses: [] as Array<{ name: string; count: number; percentage: number }>
  };

  const cards = [
    {
      title: '총 분석 건수',
      value: stats.totalAnalyses,
      icon: Activity,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50'
    },
    {
      title: '처리된 파일',
      value: stats.filesProcessed,
      icon: FileCheck,
      color: 'text-green-600',
      bgColor: 'bg-green-50'
    },
    {
      title: '이상 탐지',
      value: stats.anomaliesDetected,
      icon: AlertTriangle,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50'
    },
    {
      title: '시스템 상태',
      value: `${stats.systemHealth}%`,
      icon: Cpu,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50'
    },
  ];

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-gray-900 mb-2">Dashboard</h2>
        <p className="text-gray-600">전체 시스템 현황을 한눈에 확인하세요</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {cards.map((card, index) => {
          const Icon = card.icon;
          return (
            <Card key={index} className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">{card.title}</p>
                  <p className={`text-gray-900 ${card.color}`}>{card.value}</p>
                </div>
                <div className={`${card.bgColor} ${card.color} p-3 rounded-lg`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <Card className="p-6">
          <h3 className="text-gray-900 mb-4">최근 활동</h3>
          <div className="space-y-3">
            {stats.recentActivity.map((activity, index) => (
              <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                <div className="flex-1">
                  <p className="text-sm text-gray-900">{activity.action}</p>
                  <p className="text-xs text-gray-500 mt-1">{activity.time}</p>
                </div>
                <Badge variant={activity.status === 'success' ? 'default' : 'secondary'}>
                  {activity.status}
                </Badge>
              </div>
            ))}
          </div>
        </Card>

        {/* Top Processes */}
        <Card className="p-6">
          <h3 className="text-gray-900 mb-4">주요 프로세스</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={stats.topProcesses}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-4 space-y-2">
            {stats.topProcesses.map((process, index) => (
              <div key={index} className="flex items-center justify-between text-sm">
                <span className="text-gray-700">{process.name}</span>
                <span className="text-gray-500">{process.percentage}%</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
