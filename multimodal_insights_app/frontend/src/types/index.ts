// API Types
export interface FileMetadata {
  id: string;
  session_id: string;
  user_id: string;
  filename: string;
  file_type: 'audio' | 'video' | 'pdf';
  file_size: number;
  file_path: string;
  processing_status: string;
  uploaded_at: string;
  processed_at?: string;
  extracted_content_path?: string;
}

export interface Step {
  id: string;
  plan_id: string;
  session_id: string;
  user_id: string;
  action: string;
  agent: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  order: number;
  agent_reply?: string;
  error_message?: string;
  file_ids: string[];
  parameters?: Record<string, any>;
}

export interface Plan {
  id: string;
  session_id: string;
  user_id: string;
  initial_goal: string;
  summary?: string;
  overall_status: 'pending' | 'in_progress' | 'completed' | 'failed';
  file_ids: string[];
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
  timestamp: string;
}

export interface PlanWithSteps extends Plan {
  steps: Step[];
  status?: 'pending' | 'in_progress' | 'completed' | 'failed'; // Alias for overall_status
}

export interface ExecutionStatus {
  plan_id: string;
  session_id: string;
  overall_status: string;
  current_step?: string;
  current_agent?: string;
  completed_steps: number;
  total_steps: number;
  progress_percentage: number;
  recent_messages: string[];
}

export interface ActionResponse {
  status: string;
  message: string;
  data?: any;
}

export interface UploadResponse {
  status: string;
  message: string;
  data: {
    session_id: string;
    files: Array<{
      id: string;
      filename: string;
      file_type: string;
      file_size: number;
    }>;
  };
}

export interface ExportResponse {
  status: string;
  message: string;
  data: {
    filename: string;
    format: string;
    size_bytes: number;
    download_url: string;
  };
}

// UI Types
export interface UploadedFile {
  id: string;
  file: File;
  metadata?: FileMetadata;
  status: 'pending' | 'uploading' | 'uploaded' | 'error';
  progress?: number;
  error?: string;
}

export interface Message {
  id: string;
  type: 'user' | 'system' | 'agent' | 'error';
  content: string;
  timestamp: Date;
  agent?: string;
}

export interface SessionData {
  id: string;
  createdAt: Date;
  files: UploadedFile[];
  plans: Plan[];
  currentPlan?: PlanWithSteps;
  status: ExecutionStatus | null;
  executing?: boolean; // True when plan is executing
}

// Backend Session model (from Cosmos DB)
export interface Session {
  id: string;
  session_id: string;
  user_id: string;
  type: 'session';
  timestamp: string;
  metadata?: Record<string, any>;
  // Enriched fields from API
  latest_objective?: string;
  file_count?: number;
  file_types?: string[];
}
