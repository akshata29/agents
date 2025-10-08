import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api';
import type { ExecutionStatus } from '../types';
import { 
  Clock, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  Play,
  Loader2,
  Eye,
  Calendar
} from 'lucide-react';

interface ExecutionHistoryProps {
  onNavigateToExecution: (executionId: string) => void;
}

const ExecutionHistory: React.FC<ExecutionHistoryProps> = ({ onNavigateToExecution }) => {
  const { data: history, isLoading, error } = useQuery({
    queryKey: ['executionHistory'],
    queryFn: apiClient.getExecutionHistory,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-400" />;
      case 'completed':
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-green-400" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'cancelled':
        return <AlertCircle className="w-4 h-4 text-yellow-400" />;
      default:
        return <Clock className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-blue-400 bg-blue-500/10';
      case 'completed':
      case 'success':
        return 'text-green-400 bg-green-500/10';
      case 'failed':
        return 'text-red-400 bg-red-500/10';
      case 'cancelled':
        return 'text-yellow-400 bg-yellow-500/10';
      default:
        return 'text-slate-400 bg-slate-500/10';
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatDuration = (duration: number | null) => {
    if (!duration) return 'N/A';
    const seconds = Math.floor(duration);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return minutes > 0 
      ? `${minutes}m ${remainingSeconds}s`
      : `${remainingSeconds}s`;
  };

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
          <span className="ml-2 text-slate-400">Loading execution history...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="text-center py-8">
          <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Failed to Load History</h3>
          <p className="text-slate-400">Could not load execution history. Please try again.</p>
        </div>
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <h2 className="text-xl font-bold text-white mb-4">Execution History</h2>
        <div className="text-center py-8">
          <Calendar className="w-12 h-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">No Executions Yet</h3>
          <p className="text-slate-400">Execute a pattern to see your history here.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-800 rounded-lg p-6">
        <h2 className="text-xl font-bold text-white mb-2">Execution History</h2>
        <p className="text-slate-400">View and manage your pattern execution history</p>
        
        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-1">
              <Play className="w-4 h-4 text-primary-400" />
              <span className="text-sm text-slate-400">Total Executions</span>
            </div>
            <div className="text-xl font-semibold text-white">{history.length}</div>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-1">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              <span className="text-sm text-slate-400">Successful</span>
            </div>
            <div className="text-xl font-semibold text-white">
              {history.filter(h => h.status === 'completed' || h.status === 'success').length}
            </div>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-1">
              <XCircle className="w-4 h-4 text-red-400" />
              <span className="text-sm text-slate-400">Failed</span>
            </div>
            <div className="text-xl font-semibold text-white">
              {history.filter(h => h.status === 'failed').length}
            </div>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-1">
              <Loader2 className="w-4 h-4 text-blue-400" />
              <span className="text-sm text-slate-400">Running</span>
            </div>
            <div className="text-xl font-semibold text-white">
              {history.filter(h => h.status === 'running').length}
            </div>
          </div>
        </div>
      </div>

      {/* Execution List */}
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="space-y-4">
          {history.map((execution: ExecutionStatus) => (
            <div
              key={execution.execution_id}
              className="bg-slate-700/50 rounded-lg p-4 border border-slate-600 hover:border-slate-500 transition-colors"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-3">
                  {getStatusIcon(execution.status)}
                  <div>
                    <h4 className="font-medium text-white">
                      {execution.pattern ? `${execution.pattern} Pattern` : 'Pattern Execution'}
                    </h4>
                    <p className="text-sm text-slate-400">
                      ID: {execution.execution_id.slice(0, 8)}...
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${getStatusColor(execution.status)}`}>
                    {execution.status}
                  </span>
                  
                  <button
                    onClick={() => onNavigateToExecution(execution.execution_id)}
                    className="px-3 py-1 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm flex items-center space-x-1 transition-colors"
                  >
                    <Eye className="w-3 h-3" />
                    <span>View</span>
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-slate-400">Started:</span>
                  <div className="text-white">{formatDate(execution.start_time)}</div>
                </div>
                
                <div>
                  <span className="text-slate-400">Duration:</span>
                  <div className="text-white">{formatDuration(execution.duration)}</div>
                </div>
                
                <div>
                  <span className="text-slate-400">Progress:</span>
                  <div className="text-white">{Math.round((execution.progress || 0) * 100)}%</div>
                </div>
                
                <div>
                  <span className="text-slate-400">Agents:</span>
                  <div className="text-white">{execution.agent_outputs?.length || 0}</div>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mt-3">
                <div className="w-full bg-slate-600 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-300 ${
                      execution.status === 'failed' ? 'bg-red-500' :
                      execution.status === 'completed' || execution.status === 'success' ? 'bg-green-500' :
                      execution.status === 'running' ? 'bg-blue-500' : 'bg-slate-500'
                    }`}
                    style={{ width: `${(execution.progress || 0) * 100}%` }}
                  />
                </div>
              </div>

              {/* Current Task (for running executions) */}
              {execution.status === 'running' && execution.current_task && (
                <div className="mt-3 p-2 bg-blue-500/10 border border-blue-500/20 rounded">
                  <span className="text-blue-400 text-xs font-medium">Current: </span>
                  <span className="text-slate-300 text-xs">{execution.current_task}</span>
                </div>
              )}

              {/* Error (for failed executions) */}
              {execution.status === 'failed' && execution.error && (
                <div className="mt-3 p-2 bg-red-500/10 border border-red-500/20 rounded">
                  <span className="text-red-400 text-xs font-medium">Error: </span>
                  <span className="text-red-300 text-xs">{execution.error}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ExecutionHistory;