/**
 * API Client for Financial Research Backend
 */

import axios from 'axios';

// Use relative URLs in production (same domain), localhost for development
const API_BASE_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:8000' 
  : '';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface SequentialResearchRequest {
  ticker: string;
  scope: string[];
  depth: 'standard' | 'deep' | 'comprehensive';
  includePdf: boolean;
  year?: string;
}

export interface ConcurrentResearchRequest {
  ticker: string;
  modules: string[];
  aggregationStrategy: 'merge' | 'weighted' | 'consensus';
  includePdf: boolean;
  year?: string;
}

export interface OrchestrationResponse {
  run_id: string;
  ticker: string;
  pattern: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  steps: ExecutionStep[];
  messages: AgentMessage[];
  artifacts: ResearchArtifact[];
  summary?: string;
  error?: string;
}

export interface ExecutionStep {
  step_number: number;
  agent: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  error?: string;
}

export interface AgentMessage {
  agent_id: string;
  agent_name: string;
  timestamp: string;
  content: string;
  metadata?: Record<string, any>;
}

export interface ResearchArtifact {
  id: string;
  type: string;
  title: string;
  content: any;
  timestamp: string;
  metadata?: Record<string, any>;
}

// API Functions

export const api = {
  // Orchestration
  async runSequential(request: SequentialResearchRequest): Promise<OrchestrationResponse> {
    const response = await apiClient.post('/orchestration/sequential', request);
    return response.data;
  },

  async runConcurrent(request: ConcurrentResearchRequest): Promise<OrchestrationResponse> {
    const response = await apiClient.post('/orchestration/concurrent', request);
    return response.data;
  },

  async getRunStatus(runId: string): Promise<OrchestrationResponse> {
    const response = await apiClient.get(`/orchestration/runs/${runId}`);
    return response.data;
  },

  async listRuns(): Promise<OrchestrationResponse[]> {
    const response = await apiClient.get('/orchestration/runs');
    return response.data;
  },

  // Agents
  async listAgents() {
    const response = await apiClient.get('/agents');
    return response.data;
  },

  async getAgentHealth(agentId: string) {
    const response = await apiClient.get(`/agents/${agentId}/health`);
    return response.data;
  },

  // System
  async getSystemStatus() {
    const response = await apiClient.get('/status');
    return response.data;
  },

  async healthCheck() {
    const response = await apiClient.get('/health');
    return response.data;
  },
};

// WebSocket Connection
export class ResearchWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;

  constructor(
    private url: string = 'ws://localhost:8000/ws',
    private onMessage?: (data: any) => void,
    private onError?: (error: Event) => void
  ) {}

  connect() {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onMessage?.(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error', error);
        this.onError?.(error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.attemptReconnect();
      };
    } catch (error) {
      console.error('Failed to create WebSocket', error);
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      setTimeout(() => this.connect(), this.reconnectDelay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not open');
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
