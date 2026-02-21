import type { WorkbenchCardProps } from '../components/gen-ui';

export const COAGENT_NAME = 'data_analysis_agent';

export type AgentPhase =
  | 'idle'
  | 'thinking'
  | 'analyzing'
  | 'preprocessing'
  | 'visualizing'
  | 'searching'
  | 'reporting';

export type ToolCallStatus = 'running' | 'completed' | 'failed';

export interface ToolCallState {
  id: string;
  name: string;
  status: ToolCallStatus;
  error?: string;
  updatedAt: string;
}

export interface StreamingState {
  isStreaming: boolean;
  phase: AgentPhase;
  progress: number;
  lastTool?: string;
  staleStream?: boolean;
  lastError?: string;
}

export interface SessionCardArtifact {
  id: string;
  createdAt: string;
  type: 'card';
  card: WorkbenchCardProps;
}

export type SessionArtifact = SessionCardArtifact;

export interface AgentState {
  cards: WorkbenchCardProps[];
  phase: AgentPhase;
  progress: number;
  last_tool?: string;
  session_id?: string;
  data_source_id?: string;
  tool_calls?: Array<{
    id: string;
    name: string;
    status: ToolCallStatus;
    error?: string;
  }>;
}

export const DEFAULT_STREAMING_STATE: StreamingState = {
  isStreaming: false,
  phase: 'idle',
  progress: 0,
};
