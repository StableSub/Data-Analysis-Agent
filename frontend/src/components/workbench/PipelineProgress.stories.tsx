import type { Meta, StoryObj } from '@storybook/react-vite';

import { PipelineProgress } from './PipelineProgress';

const meta = {
  title: 'Workbench/PipelineProgress',
  component: PipelineProgress,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof PipelineProgress>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Thinking: Story = {
  args: {
    phase: 'thinking',
    progress: 0.12,
  },
};

export const Analyzing: Story = {
  args: {
    phase: 'analyzing',
    progress: 0.46,
  },
};

export const Preprocessing: Story = {
  args: {
    phase: 'preprocessing',
    progress: 0.72,
  },
};

export const Reporting: Story = {
  args: {
    phase: 'reporting',
    progress: 0.94,
  },
};
