export type Role = "user" | "assistant" | "tool" | "system";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  createdAt: string;
  isStreaming?: boolean;
  meta?: {
    fileId?: string;
    citations?: Array<{ title: string; href?: string }>;
    trace?: {
      suspicious: boolean;
      topProcs: string[];
      execCount: number;
    };
  };
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
  modelId?: string;
}

export interface StreamChunk {
  id: string;
  delta: string;
  done?: boolean;
  usage?: {
    promptTokens: number;
    completionTokens: number;
  };
}

export interface TraceSummary {
  totalEvents: number;
  suspiciousCount: number;
  topProcesses: Array<{ name: string; count: number }>;
  recentEvents: Array<{
    timestamp: string;
    type: 'exec' | 'open' | 'tcp_connect';
    process: string;
    suspicious: boolean;
  }>;
}
