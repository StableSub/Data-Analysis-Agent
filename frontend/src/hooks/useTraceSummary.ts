import { useState, useEffect } from 'react';
import { TraceSummary } from '../types/chat';

export function useTraceSummary(pollingInterval = 10000) {
  const [summary, setSummary] = useState<TraceSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        // In production, this would call /api/trace/summary
        // Initialize with empty summary
        const emptySummary: TraceSummary = {
          totalEvents: 0,
          suspiciousCount: 0,
          topProcesses: [],
          recentEvents: [],
        };

        setSummary(emptySummary);
        setIsLoading(false);
        setError(null);
      } catch (err) {
        // On error, keep last valid data
        setError('Trace 데이터를 가져오는데 실패했습니다');
        setIsLoading(false);
      }
    };

    // Initial fetch
    fetchSummary();

    // Set up polling
    const interval = setInterval(fetchSummary, pollingInterval);

    return () => clearInterval(interval);
  }, [pollingInterval]);

  return { summary, isLoading, error };
}
