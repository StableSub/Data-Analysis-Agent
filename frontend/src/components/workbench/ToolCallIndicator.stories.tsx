import type { Meta, StoryObj } from '@storybook/react-vite';

import { ToolCallIndicator } from './ToolCallIndicator';

const meta = {
  title: 'Workbench/ToolCallIndicator',
  component: ToolCallIndicator,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof ToolCallIndicator>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Running: Story = {
  args: {
    toolName: 'propose_preprocess_plan',
    status: 'running',
  },
};

export const Completed: Story = {
  args: {
    toolName: 'csv_visualization_workflow',
    status: 'completed',
  },
};

export const Failed: Story = {
  args: {
    toolName: 'build_report_outline',
    status: 'failed',
    error: '리포트 템플릿 로딩 실패',
  },
};
