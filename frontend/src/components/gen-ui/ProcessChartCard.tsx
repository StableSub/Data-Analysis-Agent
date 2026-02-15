import { Activity, Gauge, TrendingUp } from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Badge } from '../ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

export type ProcessTrend = 'up' | 'down' | 'flat';
export type ProcessStatus = 'stable' | 'warning' | 'critical';

export interface ProcessChartPoint {
  label: string;
  throughput: number;
  baseline?: number;
}

export interface ProcessMetric {
  label: string;
  value: string;
  trend: ProcessTrend;
}

export interface ProcessChartCardProps {
  title?: string;
  description: string;
  status: ProcessStatus;
  points: ProcessChartPoint[];
  metrics: ProcessMetric[];
}

function statusLabel(status: ProcessStatus): string {
  if (status === 'critical') return 'Critical';
  if (status === 'warning') return 'Watch';
  return 'Stable';
}

function statusClass(status: ProcessStatus): string {
  if (status === 'critical') return 'bg-rose-600 text-white dark:bg-rose-500';
  if (status === 'warning') return 'bg-amber-500 text-white dark:bg-amber-400 dark:text-black';
  return 'bg-emerald-600 text-white dark:bg-emerald-500';
}

function trendClass(trend: ProcessTrend): string {
  if (trend === 'up') return 'text-emerald-600 dark:text-emerald-400';
  if (trend === 'down') return 'text-rose-600 dark:text-rose-400';
  return 'text-slate-500 dark:text-slate-400';
}

function trendSymbol(trend: ProcessTrend): string {
  if (trend === 'up') return '▲';
  if (trend === 'down') return '▼';
  return '•';
}

export function ProcessChartCard({
  title = 'Process Performance',
  description,
  status,
  points,
  metrics,
}: ProcessChartCardProps) {
  return (
    <Card className="border-slate-200/80 shadow-sm dark:border-white/10 dark:bg-[#1c1c1e]">
      <CardHeader className="space-y-3 border-b border-slate-200/80 pb-4 dark:border-white/10">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base text-slate-900 dark:text-white">{title}</CardTitle>
            <CardDescription className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              {description}
            </CardDescription>
          </div>
          <Badge className={statusClass(status)}>{statusLabel(status)}</Badge>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {metrics.map((metric) => (
            <div key={metric.label} className="rounded-lg border border-slate-200/80 bg-white px-3 py-2 dark:border-white/10 dark:bg-[#202024]">
              <p className="text-xs text-slate-500 dark:text-slate-400">{metric.label}</p>
              <p className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{metric.value}</p>
              <p className={`mt-1 text-xs ${trendClass(metric.trend)}`}>
                {trendSymbol(metric.trend)} {metric.trend}
              </p>
            </div>
          ))}
        </div>
      </CardHeader>

      <CardContent className="pt-4">
        <div className="rounded-lg border border-slate-200/80 p-3 dark:border-white/10">
          <div className="mb-3 flex items-center justify-between">
            <p className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
              <Activity className="h-3.5 w-3.5" />
              Throughput Trend
            </p>
            <p className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
              <Gauge className="h-3.5 w-3.5" />
              window: last 7 runs
            </p>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={points} margin={{ top: 10, right: 8, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.35)" />
                <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis tickLine={false} axisLine={false} fontSize={12} />
                <Tooltip
                  contentStyle={{
                    borderRadius: 10,
                    border: '1px solid rgba(148, 163, 184, 0.25)',
                    boxShadow: '0 8px 24px rgba(15, 23, 42, 0.12)',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="throughput"
                  stroke="#2563eb"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: '#2563eb', strokeWidth: 0 }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  type="monotone"
                  dataKey="baseline"
                  stroke="#94a3b8"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-blue-600" />
              current run
            </span>
            <span className="inline-flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5" />
              baseline
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
