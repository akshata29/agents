/**
 * API Client for Dynamic Planning Backend
 */

import axios from 'axios';

// Use relative URLs in production (same domain), localhost for development
const API_BASE_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:8000' 
  : '';

// ============= TypeScript Interfaces =============

export interface InputTask {
  description: string;
  ticker?: string;
  session_id?: string;
  scope?: string[];
  depth?: string;
}

export interface Step {
  id: string;
  order?: number;
  action: string;
  agent: string;
  status: 'planned' | 'awaiting_feedback' | 'approved' | 'rejected' | 'action_requested' | 'executing' | 'completed' | 'failed';
  agent_reply?: string;
  error_message?: string;
  human_feedback?: string;
  human_approval_status?: 'requested' | 'accepted' | 'rejected';
  updated_action?: string;
  timestamp: string;
  dependencies?: string[];  // List of step IDs this step depends on
  required_artifacts?: string[];  // Types of artifacts needed
  tools?: string[];  // Specific tools/functions to call
  manually_injected?: boolean;  // True if added via task injection feature
}

export interface Plan {
  id: string;
  session_id: string;
  user_id: string;
  initial_goal: string;
  summary?: string;
  overall_status: 'in_progress' | 'completed' | 'failed' | 'cancelled';
  human_clarification_request?: string;
  human_clarification_response?: string;
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
  ticker?: string;
  scope?: string[];
  steps: Step[];
  steps_requiring_approval: number;
  timestamp: string;
}

export interface HumanFeedback {
  session_id: string;
  plan_id: string;
  step_id: string;
  approved: boolean;
  human_feedback?: string;
  updated_action?: string;
}

export interface AgentMessage {
  id: string;
  session_id: string;
  plan_id: string;
  step_id?: string;
  agent_name: string;
  content: string;
  message_type: 'info' | 'action' | 'result' | 'error' | 'progress' | 'action_response';
  timestamp: string;
}

export interface ActionResponse {
  plan: Plan;
  message?: string;
}

export interface TaskListItem {
  id: string;
  session_id: string;
  initial_goal: string;
  overall_status: 'in_progress' | 'completed' | 'failed' | 'cancelled';
  total_steps: number;
  completed_steps: number;
  timestamp: string;
  ticker?: string;
}

export interface UserHistoryItem {
  ticker: any;
  session_id: string;
  plan_id: string;
  objective: string;
  status: 'in_progress' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  steps_count: number;
  user_id: string;
}

export interface TaskInjectionRequest {
  session_id: string;
  plan_id: string;
  task_request: string;
  objective: string;
  current_steps: Array<{
    id: string;
    order: number;
    action: string;
    agent: string;
    status: string;
  }>;
}

export interface TaskInjectionResponse {
  success: boolean;
  message: string;
  action: 'added' | 'duplicate' | 'unsupported' | 'clarification_needed';
  inserted_at?: number;
  new_step_id?: string;
  suggestions?: string[];
}

// ============= API Client =============

class APIClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  async createPlan(inputTask: InputTask): Promise<Plan> {
    const response = await axios.post<Plan>(
      `${this.baseURL}/api/input_task`,
      inputTask
    );
    return response.data;
  }

  async getPlan(sessionId: string, planId: string): Promise<Plan> {
    const response = await axios.get<Plan>(
      `${this.baseURL}/api/plans/${sessionId}/${planId}`
    );
    return response.data;
  }

  async listPlans(sessionId: string): Promise<Plan[]> {
    const response = await axios.get<Plan[]>(
      `${this.baseURL}/api/plans/${sessionId}`
    );
    return response.data;
  }

  async getAllTasks(): Promise<TaskListItem[]> {
    const response = await axios.get<TaskListItem[]>(
      `${this.baseURL}/api/tasks`
    );
    return response.data;
  }

  async getUserHistory(limit: number = 20): Promise<UserHistoryItem[]> {
    const response = await axios.get<UserHistoryItem[]>(
      `${this.baseURL}/api/history?limit=${limit}`
    );
    return response.data;
  }

  async deleteSession(sessionId: string): Promise<{ message: string }> {
    const response = await axios.delete<{ message: string }>(
      `${this.baseURL}/api/sessions/${sessionId}`
    );
    return response.data;
  }

  async approveStep(feedback: HumanFeedback): Promise<ActionResponse> {
    const response = await axios.post<ActionResponse>(
      `${this.baseURL}/api/approve_step`,
      feedback
    );
    return response.data;
  }

  async approveSteps(feedbacks: HumanFeedback[]): Promise<ActionResponse> {
    const response = await axios.post<ActionResponse>(
      `${this.baseURL}/api/approve_steps`,
      feedbacks
    );
    return response.data;
  }

  async getSteps(sessionId: string, planId: string): Promise<Step[]> {
    const response = await axios.get<Step[]>(
      `${this.baseURL}/api/steps/${sessionId}/${planId}`
    );
    return response.data;
  }

  async getMessages(sessionId: string): Promise<AgentMessage[]> {
    const response = await axios.get<AgentMessage[]>(
      `${this.baseURL}/api/messages/${sessionId}`
    );
    return response.data;
  }

  async getMessagesByPlan(sessionId: string, planId: string): Promise<AgentMessage[]> {
    const response = await axios.get<AgentMessage[]>(
      `${this.baseURL}/api/messages/${sessionId}?plan_id=${planId}`
    );
    return response.data;
  }

  async healthCheck(): Promise<{ status: string; service: string }> {
    const response = await axios.get(`${this.baseURL}/health`);
    return response.data;
  }

  async injectTask(request: TaskInjectionRequest): Promise<TaskInjectionResponse> {
    const response = await axios.post<TaskInjectionResponse>(
      `${this.baseURL}/api/inject_task`,
      request
    );
    return response.data;
  }
}

export const apiClient = new APIClient(API_BASE_URL);
