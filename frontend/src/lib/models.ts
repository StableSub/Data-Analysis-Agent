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
    id: 'gpt-4o',
    name: 'GPT-4o',
    provider: 'OpenAI',
    description: '가장 빠르고 강력한 최신 GPT-4 모델',
    contextWindow: 128000,
    capabilities: ['텍스트', '이미지', '코드', '분석'],
    icon: '🚀',
  },
  {
    id: 'gpt-4-turbo',
    name: 'GPT-4 Turbo',
    provider: 'OpenAI',
    description: '가장 강력한 범용 AI 모델',
    contextWindow: 128000,
    capabilities: ['텍스트', '코드', '분석'],
    icon: '🤖',
  },
  {
    id: 'gpt-4',
    name: 'GPT-4',
    provider: 'OpenAI',
    description: '고급 추론 및 복잡한 작업',
    contextWindow: 8192,
    capabilities: ['텍스트', '코드', '분석'],
    icon: '🤖',
  },
  {
    id: 'gpt-3.5-turbo',
    name: 'GPT-3.5 Turbo',
    provider: 'OpenAI',
    description: '빠르고 효율적인 범용 모델',
    contextWindow: 16384,
    capabilities: ['텍스트', '코드'],
    icon: '⚡',
  },
  {
    id: 'claude-3.5-sonnet',
    name: 'Claude 3.5 Sonnet',
    provider: 'Anthropic',
    description: '최신 Claude 모델, 향상된 추론 능력',
    contextWindow: 200000,
    capabilities: ['텍스트', '코드', '분석'],
    icon: '✨',
  },
  {
    id: 'claude-3-opus',
    name: 'Claude 3 Opus',
    provider: 'Anthropic',
    description: '복잡한 분석과 긴 문맥 처리',
    contextWindow: 200000,
    capabilities: ['텍스트', '분석', '긴 문서'],
    icon: '🧠',
  },
  {
    id: 'claude-3-sonnet',
    name: 'Claude 3 Sonnet',
    provider: 'Anthropic',
    description: '균형잡힌 성능과 속도',
    contextWindow: 200000,
    capabilities: ['텍스트', '분석'],
    icon: '🎯',
  },
  {
    id: 'gemini-pro',
    name: 'Gemini Pro',
    provider: 'Google',
    description: '구글의 최신 멀티모달 AI',
    contextWindow: 32768,
    capabilities: ['텍스트', '이미지', '코드'],
    icon: '✨',
  },
  {
    id: 'llama-3-70b',
    name: 'Llama 3 70B',
    provider: 'Meta',
    description: '오픈소스 대형 언어 모델',
    contextWindow: 8192,
    capabilities: ['텍스트', '코드'],
    icon: '🦙',
  },
];

export const DEFAULT_MODEL_ID = 'gpt-4o';

export function getModelById(id: string): AIModel | undefined {
  return AI_MODELS.find(model => model.id === id);
}

export function getDefaultModel(): AIModel {
  return AI_MODELS.find(model => model.id === DEFAULT_MODEL_ID) || AI_MODELS[0];
}