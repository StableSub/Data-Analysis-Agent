import { useCopilotAction } from '@copilotkit/react-core';
import { z } from 'zod';

/**
 * DataTableRenderer - Static Generative UI component for table visualization
 * 
 * This component uses useCopilotAction to allow AI to display data in table format.
 */

interface TableData {
    columns: string[];
    rows: any[][];
}

interface DataTableProps {
    columns: string[];
    rows: any[][];
    title?: string;
}

/**
 * Actual table rendering component
 */
export function DataTable({ columns, rows, title }: DataTableProps) {
    return (
        <div className="w-full p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
            {title && (
                <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
                    {title}
                </h3>
            )}
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead className="bg-gray-50 dark:bg-gray-700">
                        <tr>
                            {columns.map((col, idx) => (
                                <th
                                    key={idx}
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
                                >
                                    {col}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                        {rows.map((row, rowIdx) => (
                            <tr key={rowIdx} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                                {row.map((cell, cellIdx) => (
                                    <td
                                        key={cellIdx}
                                        className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100"
                                    >
                                        {String(cell)}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                {rows.length} rows × {columns.length} columns
            </div>
        </div>
    );
}

/**
 * Hook to register data table action with CopilotKit
 */
export function useDataTableRenderer() {
    useCopilotAction({
        name: 'display_table',
        description: 'Display data in a table format',
        parameters: z.object({
            columns: z.array(z.string()).describe('Column headers'),
            rows: z.array(z.array(z.any())).describe('Table rows (array of arrays)'),
            title: z.string().optional().describe('Table title')
        }),
        handler: async ({ columns, rows, title }) => {
            return { columns, rows, title };
        },
        render: ({ status, result }) => {
            if (status === 'executing') {
                return (
                    <div className="w-full p-4 bg-white dark:bg-gray-800 rounded-lg shadow animate-pulse">
                        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
                        <div className="space-y-2">
                            {[...Array(5)].map((_, i) => (
                                <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
                            ))}
                        </div>
                    </div>
                );
            }

            if (status === 'complete' && result) {
                return <DataTable {...result} />;
            }

            return null;
        }
    });
}
