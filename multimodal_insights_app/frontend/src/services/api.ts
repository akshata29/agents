import axios from 'axios';
import type {
  FileMetadata,
  PlanWithSteps,
  ExecutionStatus,
  ActionResponse,
  UploadResponse,
  ExportResponse,
  Session,
  Plan,
} from '../types';

const API_BASE_URL = 'http://localhost:8000'; // In production, use environment variable

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// File Upload API
export const uploadFiles = async (
  files: File[],
  sessionId: string,
  userId: string = 'default_user'
): Promise<UploadResponse> => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });
  formData.append('session_id', sessionId);
  formData.append('user_id', userId);

  const response = await api.post<UploadResponse>('/api/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const getSessionFiles = async (sessionId: string): Promise<FileMetadata[]> => {
  const response = await api.get<FileMetadata[]>(`/api/files/session/${sessionId}`);
  return response.data;
};

export const downloadFile = async (fileId: string, sessionId: string): Promise<Blob> => {
  const response = await api.get(`/api/files/${fileId}/download`, {
    params: { session_id: sessionId },
    responseType: 'blob',
  });
  return response.data;
};

export const deleteFile = async (fileId: string, sessionId: string): Promise<ActionResponse> => {
  const response = await api.delete<ActionResponse>(`/api/files/${fileId}`, {
    params: { session_id: sessionId },
  });
  return response.data;
};

// Orchestration API
export const createAndExecutePlan = async (
  sessionId: string,
  userId: string,
  description: string,
  fileIds: string[],
  summaryType?: string,
  persona?: string
): Promise<ActionResponse> => {
  const response = await api.post<ActionResponse>('/api/orchestration/execute-direct', {
    session_id: sessionId,
    user_id: userId,
    description,
    file_ids: fileIds,
    summary_type: summaryType || 'detailed',
    persona: persona || 'executive',
  });
  return response.data;
};

export const getPlan = async (planId: string, sessionId: string): Promise<PlanWithSteps> => {
  const response = await api.get<PlanWithSteps>(`/api/orchestration/plans/${planId}`, {
    params: { session_id: sessionId },
  });
  return response.data;
};

export const getPlanStatus = async (planId: string, sessionId: string): Promise<ExecutionStatus> => {
  const response = await api.get<ExecutionStatus>(`/api/orchestration/plans/${planId}/status`, {
    params: { session_id: sessionId },
  });
  return response.data;
};

// Export API
export const exportPlanResults = async (
  planId: string,
  sessionId: string,
  format: 'markdown' | 'html' | 'pdf' | 'json' = 'markdown',
  includeMetadata: boolean = true
): Promise<ExportResponse> => {
  const response = await api.post<ExportResponse>(`/api/export/plans/${planId}`, null, {
    params: {
      session_id: sessionId,
      export_format: format,
      include_metadata: includeMetadata,
    },
  });
  return response.data;
};

export const downloadExport = async (filename: string): Promise<Blob> => {
  const response = await api.get(`/api/export/download/${filename}`, {
    responseType: 'blob',
  });
  return response.data;
};

export const listExports = async (sessionId?: string): Promise<any[]> => {
  const response = await api.get('/api/export/list', {
    params: sessionId ? { session_id: sessionId } : undefined,
  });
  return response.data;
};

// Health Check
export const healthCheck = async (): Promise<any> => {
  const response = await api.get('/health');
  return response.data;
};

// Sessions API
export const listSessions = async (limit: number = 50): Promise<Session[]> => {
  const response = await api.get<Session[]>('/api/sessions', {
    params: { limit },
  });
  return response.data;
};

export const getSession = async (sessionId: string): Promise<Session> => {
  const response = await api.get<Session>(`/api/sessions/${sessionId}`);
  return response.data;
};

export const getSessionPlans = async (sessionId: string): Promise<Plan[]> => {
  const response = await api.get<Plan[]>(`/api/sessions/${sessionId}/plans`);
  return response.data;
};

export const getSessionPlanWithSteps = async (
  sessionId: string,
  planId: string
): Promise<PlanWithSteps> => {
  const response = await api.get<PlanWithSteps>(
    `/api/sessions/${sessionId}/plans/${planId}`
  );
  return response.data;
};

export const deleteSession = async (sessionId: string): Promise<{ message: string; session_id: string }> => {
  const response = await api.delete<{ message: string; session_id: string }>(
    `/api/sessions/${sessionId}`
  );
  return response.data;
};

export default api;
