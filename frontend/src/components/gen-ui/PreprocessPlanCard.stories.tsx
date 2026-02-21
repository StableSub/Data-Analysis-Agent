import type { Meta, StoryObj } from '@storybook/react';
import { PreprocessPlanCard } from './PreprocessPlanCard';
import { PreprocessPlanCardProps } from './types';

const meta = {
  title: 'GenUI/PreprocessPlanCard',
  component: PreprocessPlanCard,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof PreprocessPlanCard>;

export default meta;
type Story = StoryObj<typeof meta>;

const baseProps: PreprocessPlanCardProps = {
  cardId: 'card-plan-1',
  cardType: 'preprocess_plan',
  title: 'Data Cleaning Plan',
  sessionId: 'session-1',
  status: 'needs_user',
  createdAt: new Date().toISOString(),
  source: { kind: 'pipeline', datasetId: 'ds-123' },
  subtitle: 'Suggested cleaning steps based on data quality analysis',
  plan: {
    planId: 'plan-1',
    datasetId: 'ds-123',
    rationale: 'The dataset has missing values in the "category" column and duplicates in "id".',
    steps: [
      {
        stepId: 'step-1',
        type: 'remove_duplicates',
        title: 'Remove Duplicate Rows',
        why: 'Found 2 duplicate rows that might skew analysis.',
        enabled: true,
        params: { subset: ['id'] }
      },
      {
        stepId: 'step-2',
        type: 'handle_missing',
        title: 'Impute Missing Categories',
        why: '5% of category entries are missing.',
        enabled: true,
        risk: 'Imputation might introduce bias if data is not missing at random.',
        params: { column: 'category', strategy: 'mode' }
      },
      {
        stepId: 'step-3',
        type: 'type_cast',
        title: 'Convert Date Column',
        why: 'Field "date_str" looks like a date but is stored as string.',
        enabled: false,
        params: { column: 'date_str', toType: 'datetime' }
      }
    ]
  },
  actions: [
    { type: 'apply', label: 'Apply Plan' },
    { type: 'edit', label: 'Customize' }
  ]
};

export const Default: Story = {
  args: {
    card: { ...baseProps }
  }
};

export const AllEnabled: Story = {
  args: {
    card: {
      ...baseProps,
      plan: {
        ...baseProps.plan,
        steps: baseProps.plan.steps.map(s => ({ ...s, enabled: true }))
      }
    }
  }
};

export const Applied: Story = {
  args: {
    card: {
      ...baseProps,
      status: 'success' as const,
      title: 'Plan Applied',
      subtitle: 'Transformation completed successfully',
      actions: [],
      plan: {
        ...baseProps.plan,
        steps: baseProps.plan.steps.map(s => ({ ...s, enabled: true }))
      }
    }
  }
};
