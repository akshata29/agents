import axios from 'axios';
import type { PatternRequest, PatternResponse, ExecutionStatus, PatternInfo, SystemStatus } from './types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export const apiClient = {
  // Get available patterns
  getPatterns: async (): Promise<PatternInfo[]> => {
    const response = await api.get('/patterns');
    return response.data;
  },

  // Execute a pattern
  executePattern: async (request: PatternRequest): Promise<PatternResponse> => {
    const response = await api.post('/patterns/execute', request);
    return response.data;
  },

  // Get execution status
  getExecutionStatus: async (executionId: string): Promise<ExecutionStatus> => {
    const response = await api.get(`/patterns/status/${executionId}`);
    return response.data;
  },

  // Cancel execution
  cancelExecution: async (executionId: string): Promise<void> => {
    await api.post(`/patterns/cancel/${executionId}`);
  },

  // Get system status
  getSystemStatus: async (): Promise<SystemStatus> => {
    const response = await api.get('/system/status');
    return response.data;
  },

  // Get execution history
  getExecutionHistory: async (): Promise<ExecutionStatus[]> => {
    const response = await api.get('/patterns/history');
    return response.data;
  },

  // Get pattern details
  getPatternDetails: async (patternName: string): Promise<PatternInfo> => {
    const response = await api.get(`/patterns/${patternName}`);
    return response.data;
  }
};

// Stream execution results (for real-time updates)
export const createExecutionStream = (executionId: string, onUpdate: (status: ExecutionStatus) => void): (() => void) => {
  let cancelled = false;
  
  const poll = async (): Promise<void> => {
    while (!cancelled) {
      try {
        const status = await apiClient.getExecutionStatus(executionId);
        onUpdate(status);
        
        if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
          break;
        }
        
        await new Promise<void>(resolve => setTimeout(resolve, 1000)); // Poll every second
      } catch (error) {
        console.error('Error polling execution status:', error);
        await new Promise<void>(resolve => setTimeout(resolve, 2000)); // Wait longer on error
      }
    }
  };
  
  poll();
  
  return (): void => {
    cancelled = true;
  };
};