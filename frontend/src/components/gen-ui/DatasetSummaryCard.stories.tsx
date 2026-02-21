import type { Meta, StoryObj } from '@storybook/react';
import { DatasetSummaryCard } from './DatasetSummaryCard';
import { DatasetSummaryCardProps } from './types';

const meta = {
  title: 'GenUI/DatasetSummaryCard',
  component: DatasetSummaryCard,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof DatasetSummaryCard>;

export default meta;
type Story = StoryObj<typeof meta>;

const baseProps: DatasetSummaryCardProps = {
  cardId: 'card-ds-1',
  cardType: 'dataset_summary',
  title: 'Sales Dataset Overview',
  sessionId: 'session-1',
  status: 'success',
  summary: 'Loaded sales data from 2023. Contains 1000 rows and 5 columns.',
  createdAt: new Date().toISOString(),
  source: { kind: 'dataset', datasetId: 'ds-123' },
  dataset: {
    datasetId: 'ds-123',
    name: 'sales_2023.csv',
    fileType: 'csv',
    sizeBytes: 102400,
    rows: 1000,
    cols: 5,
    sampleStrategy: { kind: 'head', n: 5 }
  },
  schema: {
    columns: [
      { name: 'date', dtype: 'datetime', nonNullCount: 1000, missingCount: 0, missingRate: 0.0, exampleValues: ['2023-01-01', '2023-01-02'] },
      { name: 'product_id', dtype: 'string', nonNullCount: 1000, missingCount: 0, missingRate: 0.0, exampleValues: ['P001', 'P002'], cardinality: 50 },
      { name: 'category', dtype: 'category', nonNullCount: 950, missingCount: 50, missingRate: 0.05, exampleValues: ['Electronics', 'Books'], cardinality: 5 },
      { name: 'amount', dtype: 'float', nonNullCount: 1000, missingCount: 0, missingRate: 0.0, exampleValues: ['100.50', '250.00'] },
      { name: 'customer_id', dtype: 'string', nonNullCount: 1000, missingCount: 0, missingRate: 0.0, exampleValues: ['C001', 'C002'] }
    ]
  },
  quality: {
    missingRateTotal: 0.01,
    duplicateRowCount: 2,
    datetimeHint: { hasDatetime: true, columns: ['date'], inferredFreq: 'D' }
  },
  preview: {
    columns: ['date', 'product_id', 'category', 'amount', 'customer_id'],
    rows: [
      { date: '2023-01-01', product_id: 'P001', category: 'Electronics', amount: 100.50, customer_id: 'C001' },
      { date: '2023-01-02', product_id: 'P002', category: 'Books', amount: 25.00, customer_id: 'C002' },
      { date: '2023-01-03', product_id: 'P003', category: null, amount: 120.00, customer_id: 'C003' },
    ]
  },
  recommendedNext: [
    { kind: 'preprocess_plan', label: 'Clean Missing Values in Category' },
    { kind: 'visualize', label: 'Plot Monthly Sales Trend' }
  ]
};

export const Default: Story = {
  args: {
    card: { ...baseProps }
  }
};

export const WithMissingData: Story = {
  args: {
    card: {
      ...baseProps,
      quality: {
        missingRateTotal: 0.15,
        duplicateRowCount: 0,
      },
      schema: {
        columns: [
          { name: 'id', dtype: 'int', nonNullCount: 1000, missingCount: 0 },
          { name: 'email', dtype: 'string', nonNullCount: 850, missingCount: 150, missingRate: 0.15 },
          { name: 'age', dtype: 'float', nonNullCount: 900, missingCount: 100, missingRate: 0.10 }
        ]
      }
    }
  }
};
