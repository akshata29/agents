import axios from 'axios';
import type { ResearchRequest, ResearchResponse, ExecutionStatus, WorkflowInfo } from './types';

// Use relative URLs in production (same domain), localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || (
  window.location.hostname === 'localhost' ? 'http://localhost:8000' : ''
);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiClient = {
  // Health check
  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },

  // Get workflow information
  getWorkflowInfo: async (): Promise<WorkflowInfo> => {
    const response = await api.get<WorkflowInfo>('/api/workflow/info');
    return response.data;
  },

  // Start research
  startResearch: async (request: ResearchRequest): Promise<ResearchResponse> => {
    const response = await api.post<ResearchResponse>('/api/research/start', request);
    return response.data;
  },

  // Get execution status
  getExecutionStatus: async (executionId: string): Promise<ExecutionStatus> => {
    const response = await api.get<ExecutionStatus>(`/api/research/status/${executionId}`);
    return response.data;
  },

  // List all executions
  listExecutions: async () => {
    const response = await api.get('/api/research/list');
    return response.data;
  },

  // WebSocket connection
  connectWebSocket: (executionId: string) => {
    const wsUrl = API_BASE_URL.replace('http', 'ws') + `/ws/research/${executionId}`;
    return new WebSocket(wsUrl);
  },

  // Session history APIs
  getSessions: async (limit: number = 50) => {
    const response = await api.get(`/api/sessions?limit=${limit}`);
    return response.data;
  },

  createSession: async () => {
    const response = await api.post('/api/sessions/create');
    return response.data;
  },

  getSession: async (sessionId: string) => {
    const response = await api.get(`/api/sessions/${sessionId}`);
    return response.data;
  },

  getSessionRuns: async (sessionId: string) => {
    const response = await api.get(`/api/sessions/${sessionId}/runs`);
    return response.data;
  },

  getRun: async (sessionId: string, runId: string) => {
    const response = await api.get(`/api/sessions/${sessionId}/runs/${runId}`);
    return response.data;
  },

  searchRunsByTopic: async (topic: string) => {
    const response = await api.get(`/api/sessions/topic/${encodeURIComponent(topic)}`);
    return response.data;
  },

  getUserHistory: async (limit: number = 50) => {
    const response = await api.get(`/api/sessions/user/history?limit=${limit}`);
    return response.data;
  },

  deleteSession: async (sessionId: string) => {
    const response = await api.delete(`/api/sessions/${sessionId}`);
    return response.data;
  },
};

export default api;
