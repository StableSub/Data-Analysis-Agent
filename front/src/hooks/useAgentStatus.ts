import { useState, useEffect } from 'react';

export interface AgentCapability {
  name: string;
  status: 'active' | 'idle' | 'disabled';
}

export interface AgentActivity {
  timestamp: string;
  type: 'analysis' | 'search' | 'thinking' | 'processing';
  description: string;
  status: 'active' | 'completed' | 'failed';
}

export interface AgentStatus {
  totalTasks: number;
  activeTasks: number;
  capabilities: AgentCapability[];
  recentActivities: AgentActivity[];
}

export function useAgentStatus(pollingInterval = 10000) {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      // TODO: Replace with actual API call
      // const response = await fetch('/api/agent/status');
      // const data = await response.json();
      
      // Mock data for demonstration
      const activeCount = Math.floor(Math.random() * 2);
      const mockStatus: AgentStatus = {
        totalTasks: Math.floor(Math.random() * 50) + 95,
        activeTasks: activeCount,
        capabilities: [
          { name: '데이터 분석', status: activeCount > 0 ? 'active' : 'idle' },
          { name: '패턴 인식', status: 'active' },
          { name: '리포트 생성', status: 'active' },
          { name: '이상 탐지', status: 'idle' },
        ],
        recentActivities: [
          {
            timestamp: new Date(Date.now() - 15000).toISOString(),
            type: 'analysis',
            description: '제조 데이터 분석 중',
            status: activeCount > 0 ? 'active' : 'completed',
          },
          {
            timestamp: new Date(Date.now() - 80000).toISOString(),
            type: 'search',
            description: '데이터베이스 검색 완료',
            status: 'completed',
          },
          {
            timestamp: new Date(Date.now() - 140000).toISOString(),
            type: 'thinking',
            description: '응답 생성 완료',
            status: 'completed',
          },
        ],
      };

      setStatus(mockStatus);
      setIsLoading(false);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch agent status');
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, pollingInterval);
    return () => clearInterval(interval);
  }, [pollingInterval]);

  return { status, isLoading, error };
}
