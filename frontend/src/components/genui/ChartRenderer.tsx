import { useCopilotAction } from '@copilotkit/react-core';
import { z } from 'zod';
import { BarChart, Bar, LineChart, Line, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

/**
 * ChartRenderer - Static Generative UI component for chart visualization
 * 
 * This component uses useCopilotAction to allow AI to render charts dynamically.
 * The AI can choose chart type, data, and configuration.
 */

// Chart Types
type ChartType = 'bar' | 'line' | 'scatter';

interface ChartData {
    [key: string]: any;
}

interface ChartRendererProps {
    type: ChartType;
    data: ChartData[];
    xKey: string;
    yKey: string;
    title?: string;
}

/**
 * Actual chart rendering component
 */
export function ChartDisplay({ type, data, xKey, yKey, title }: ChartRendererProps) {
    const renderChart = () => {
        const commonProps = {
            data,
            margin: { top: 5, right: 30, left: 20, bottom: 5 }
        };

        switch (type) {
            case 'bar':
                return (
                    <BarChart {...commonProps}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey={xKey} />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey={yKey} fill="#8884d8" />
                    </BarChart>
                );
            case 'line':
                return (
                    <LineChart {...commonProps}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey={xKey} />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey={yKey} stroke="#8884d8" />
                    </LineChart>
                );
            case 'scatter':
                return (
                    <ScatterChart {...commonProps}>
                        <CartesianGrid />
                        <XAxis dataKey={xKey} />
                        <YAxis dataKey={yKey} />
                        <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                        <Legend />
                        <Scatter name={yKey} data={data} fill="#8884d8" />
                    </ScatterChart>
                );
            default:
                return <div>Unknown chart type</div>;
        }
    };

    return (
        <div className="w-full p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
            {title && (
                <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
                    {title}
                </h3>
            )}
            <ResponsiveContainer width="100%" height={300}>
                {renderChart()}
            </ResponsiveContainer>
        </div>
    );
}

/**
 * Hook to register chart rendering action with CopilotKit
 * 
 * This must be called in a component that's inside the CopilotKit provider
 */
export function useChartRenderer() {
    useCopilotAction({
        name: 'render_chart',
        description: 'Display a chart visualization (bar, line, or scatter plot)',
        parameters: z.object({
            chartType: z.enum(['bar', 'line', 'scatter']).describe('Type of chart to display'),
            data: z.array(z.record(z.any())).describe('Array of data objects'),
            xKey: z.string().describe('Key for X-axis data'),
            yKey: z.string().describe('Key for Y-axis data'),
            title: z.string().optional().describe('Chart title')
        }),
        handler: async ({ chartType, data, xKey, yKey, title }) => {
            // Return the chart component configuration
            // The UI will render this via the render function
            return {
                type: chartType,
                data,
                xKey,
                yKey,
                title
            };
        },
        render: ({ status, result }) => {
            if (status === 'executing') {
                return (
                    <div className="w-full p-4 bg-white dark:bg-gray-800 rounded-lg shadow animate-pulse">
                        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
                        <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
                    </div>
                );
            }

            if (status === 'complete' && result) {
                return <ChartDisplay {...result} />;
            }

            return null;
        }
    });
}
