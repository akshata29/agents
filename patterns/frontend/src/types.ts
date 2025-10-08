// API Types for Patterns
export interface PatternRequest {
  pattern: string;
  task: string;
  session_id?: string;
}

export interface PatternResponse {
  execution_id: string;
  status: string;
  message: string;
  pattern: string;
}

export interface AgentActivity {
  agent: string;
  input: string;
  output: string;
  timestamp?: string;
}

export interface ExecutionStatus {
  execution_id: string;
  status: 'pending' | 'running' | 'success' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_task: string | null;
  completed_tasks: string[];
  failed_tasks: string[];
  start_time: string | null;
  end_time: string | null;
  duration: number | null;
  result: any;
  error: string | null;
  pattern?: string;
  agent_outputs?: AgentActivity[];
}

export interface PatternInfo {
  name: string;
  description: string;
  icon: string;
  agents: string[];
  example_scenario: string;
  use_cases: string[];
}

export interface SystemStatus {
  azure_openai_configured: boolean;
  agent_framework_available: boolean;
  endpoint: string;
  model: string;
}

export type PatternType = 'sequential' | 'concurrent' | 'group_chat' | 'handoff' | 'magentic';