export interface AIModel {
  id: string;
  name: string;
  provider: string;
  description: string;
  contextWindow: number;
  capabilities?: string[];
  icon?: string;
}

export const AI_MODELS: AIModel[] = [
  {
    id: 'gpt-5-nano',
    name: 'GPT-5-nano',
    provider: 'OpenAI',
    description: '가장 저렴한 GPT-5 모델',
    contextWindow: 128000,
    capabilities: ['텍스트', '이미지', '코드', '분석'],
    icon: '🚀',
  },
  {
    id: 'gpt-5-mini',
    name: 'GPT-5 mini',
    provider: 'OpenAI',
    description: '저렴하고 강력한 GPT-5 모델',
    contextWindow: 128000,
    capabilities: ['텍스트', '코드', '분석'],
    icon: '🤖',
  },
  {
    id: 'gpt-5',
    name: 'GPT-5',
    provider: 'OpenAI',
    description: '가장 빠르고 강력한 GPT-5 모델',
    contextWindow: 8192,
    capabilities: ['텍스트', '코드', '분석'],
    icon: '🤖',
  }
];

export const DEFAULT_MODEL_ID = 'gpt-5';

export function getModelById(id: string): AIModel | undefined {
  return AI_MODELS.find(model => model.id === id);
}

export function getDefaultModel(): AIModel {
  const model = AI_MODELS.find(model => model.id === DEFAULT_MODEL_ID);
  if (model) return model;
  return AI_MODELS[0]!;
}
