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

      // In production, this would call a real API
      const emptyStatus: AgentStatus = {
        totalTasks: 0,
        activeTasks: 0,
        capabilities: [
          { name: '데이터 분석', status: 'idle' },
          { name: '패턴 인식', status: 'idle' },
          { name: '리포트 생성', status: 'idle' },
          { name: '이상 탐지', status: 'idle' },
        ],
        recentActivities: [],
      };

      setStatus(emptyStatus);
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
