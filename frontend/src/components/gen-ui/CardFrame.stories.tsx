import type { Meta, StoryObj } from '@storybook/react';
import { CardFrame } from './CardFrame';
import { BaseCardProps } from './types';

const meta = {
  title: 'GenUI/CardFrame',
  component: CardFrame,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    // Add controls here if needed
  },
} satisfies Meta<typeof CardFrame>;

export default meta;
type Story = StoryObj<typeof meta>;

const baseCard: BaseCardProps = {
  cardId: 'card-1',
  cardType: 'dataset_summary',
  title: 'Sample Dataset Analysis',
  sessionId: 'session-1',
  status: 'idle',
  source: {
    kind: 'dataset',
    datasetId: 'dataset-123',
    fileId: 'file-456'
  },
  createdAt: new Date().toISOString(),
};

export const Idle: Story = {
  args: {
    card: { ...baseCard, status: 'idle', summary: 'Waiting for task to start...' },
    children: (
      <div className="flex h-32 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 text-slate-400">
        Card Content Placeholder
      </div>
    ),
  },
};

export const Running: Story = {
  args: {
    card: { ...baseCard, status: 'running', title: 'Processing Data...', summary: 'Analyzing columns and rows.' },
    children: (
      <div className="flex h-32 items-center justify-center rounded-lg border border-slate-100 bg-indigo-50/50 text-indigo-500">
        Processing...
      </div>
    ),
  },
};

export const Success: Story = {
  args: {
    card: { ...baseCard, status: 'success', title: 'Analysis Complete', summary: 'Found 12 columns and 500 rows.', severity: 'success' },
    children: (
      <div className="flex h-32 items-center justify-center rounded-lg border border-emerald-100 bg-emerald-50/50 text-emerald-600">
        Analysis Result Data
      </div>
    ),
  },
};

export const Error: Story = {
  args: {
    card: { 
      ...baseCard, 
      status: 'failed', 
      title: 'Analysis Failed', 
      summary: 'Could not parse CSV file format.', 
      severity: 'error',
      actions: [{ type: 'retry', label: 'Retry Analysis' }]
    },
    children: (
      <div className="flex h-32 items-center justify-center rounded-lg border border-rose-100 bg-rose-50/50 text-rose-600">
        Error Details
      </div>
    ),
  },
};

export const NeedInput: Story = {
  args: {
    card: { 
      ...baseCard, 
      status: 'needs_user', 
      title: 'Confirm Column Types', 
      summary: 'Please review the detected data types.',
      actions: [
        { type: 'apply', label: 'Confirm' },
        { type: 'cancel', label: 'Cancel' }
      ]
    },
    children: (
      <div className="flex h-32 items-center justify-center rounded-lg border border-amber-100 bg-amber-50/50 text-amber-600">
        User Input Form
      </div>
    ),
  },
};
