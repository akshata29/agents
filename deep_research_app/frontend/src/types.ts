// API Types
export interface ResearchRequest {
  topic: string;
  depth: 'quick' | 'standard' | 'comprehensive' | 'exhaustive';
  max_sources: number;
  include_citations: boolean;
  execution_mode: 'workflow' | 'code' | 'maf-workflow';
}

export interface ResearchResponse {
  execution_id: string;
  status: string;
  message: string;
  execution_mode: string;
  orchestration_pattern: string;
}

export interface ExecutionMetadata {
  execution_mode: string;
  orchestration_pattern: string;
  framework: string;
  workflow_engine: string;
  agent_count: number;
  agents_used: string[];
  parallel_tasks: number;
  total_phases: number;
  pattern_details: {
    [key: string]: string;
  };
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
  metadata?: ExecutionMetadata;
}

export interface WorkflowVariable {
  name: string;
  type: string;
  default?: any;
  required: boolean;
  description: string;
}

export interface WorkflowTask {
  id: string;
  name: string;
  type: string;
  description: string;
  agent: string | null;
  depends_on: string[];
  timeout: number;
  parallel: boolean;
}

export interface WorkflowInfo {
  name: string;
  version: string;
  description: string;
  variables: WorkflowVariable[];
  tasks: WorkflowTask[];
  total_tasks: number;
  max_parallel_tasks: number;
  timeout: number;
  orchestration_pattern: string;
  execution_modes: string[];
}

export interface WebSocketMessage {
  type: 'status' | 'task_update' | 'progress' | 'completed';
  execution_id: string;
  status?: string;
  message?: string;
  task_id?: string;
  task_name?: string;
  result?: any;
  error?: string;
  tasks?: Record<string, { name: string; status: string }>;
}
