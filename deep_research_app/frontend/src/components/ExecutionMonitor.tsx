import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api';
import { ExecutionStatus, WebSocketMessage } from '../types';
import {
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  AlertCircle,
  FileText,
} from 'lucide-react';

interface ExecutionMonitorProps {
  executionId: string;
}

export default function ExecutionMonitor({ executionId }: ExecutionMonitorProps) {
  const [wsMessages, setWsMessages] = useState<WebSocketMessage[]>([]);
  const [wsConnected, setWsConnected] = useState(false);

  // Fetch execution status
  const { data: status, refetch } = useQuery({
    queryKey: ['executionStatus', executionId],
    queryFn: () => apiClient.getExecutionStatus(executionId),
    refetchInterval: 2000, // Poll every 2 seconds
    enabled: !!executionId,
  });

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!executionId) return;

    const ws = apiClient.connectWebSocket(executionId);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      setWsMessages((prev) => [...prev, message]);
      // Trigger a refetch when we get updates
      refetch();
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setWsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [executionId, refetch]);

  if (!status) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  const getStatusIcon = (statusValue: string) => {
    switch (statusValue) {
      case 'success':
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-success-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-error-500" />;
      case 'running':
        return <Loader2 className="w-5 h-5 text-primary-500 animate-spin" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-warning-500" />;
      default:
        return <AlertCircle className="w-5 h-5 text-slate-500" />;
    }
  };

  const getStatusColor = (statusValue: string) => {
    switch (statusValue) {
      case 'success':
      case 'completed':
        return 'text-success-500 bg-success-500/10 border-success-500';
      case 'failed':
        return 'text-error-500 bg-error-500/10 border-error-500';
      case 'running':
        return 'text-primary-500 bg-primary-500/10 border-primary-500';
      case 'pending':
        return 'text-warning-500 bg-warning-500/10 border-warning-500';
      default:
        return 'text-slate-500 bg-slate-500/10 border-slate-500';
    }
  };

  return (
    <div className="space-y-6">
      {/* Status Header */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                <Activity className="w-5 h-5" />
                <span>Execution Monitor</span>
              </h2>
              <p className="text-sm text-slate-400 mt-1">ID: {executionId}</p>
            </div>
            <div className="flex items-center space-x-3">
              {wsConnected ? (
                <div className="flex items-center space-x-2 px-3 py-1 bg-success-500/20 text-success-400 rounded-full text-sm">
                  <div className="w-2 h-2 bg-success-500 rounded-full animate-pulse" />
                  <span>Live</span>
                </div>
              ) : (
                <div className="flex items-center space-x-2 px-3 py-1 bg-slate-700 text-slate-400 rounded-full text-sm">
                  <div className="w-2 h-2 bg-slate-500 rounded-full" />
                  <span>Polling</span>
                </div>
              )}
              <div className={`px-4 py-2 rounded-lg border-2 font-medium ${getStatusColor(status.status)}`}>
                <div className="flex items-center space-x-2">
                  {getStatusIcon(status.status)}
                  <span className="uppercase text-sm">{status.status}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="card">
        <div className="card-body">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-300">Overall Progress</span>
              <span className="font-bold text-white">{Math.round(status.progress)}%</span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
              <div
                className="bg-gradient-to-r from-primary-600 to-primary-400 h-full transition-all duration-500 ease-out"
                style={{ width: `${status.progress}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>
                {status.completed_tasks.length} completed, {status.failed_tasks.length} failed
              </span>
              {status.duration && <span>{Math.round(status.duration)}s elapsed</span>}
            </div>
          </div>
        </div>
      </div>

      {/* Current Task */}
      {status.current_task && (
        <div className="card border-2 border-primary-500/30">
          <div className="card-body">
            <div className="flex items-center space-x-3">
              {status.status === 'running' ? (
                <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
              ) : (
                <CheckCircle className="w-6 h-6 text-success-500" />
              )}
              <div>
                <p className="text-sm text-slate-400">
                  {status.status === 'running' ? 'Currently Executing' : 'Last Task'}
                </p>
                <p className="text-lg font-bold text-white">{status.current_task}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Task Progress */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Technical Details */}
        {status.metadata && (
          <div className="card border-2 border-primary-500/30">
            <div className="card-header">
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <Activity className="w-5 h-5 text-primary-500" />
                <span>Technical Details</span>
              </h3>
            </div>
            <div className="card-body space-y-4">
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Execution Mode</p>
                <p className="text-sm font-medium text-white">
                  {status.metadata.execution_mode === 'workflow' ? '🔄 Workflow Engine' : '⚙️ Code-Based'}
                </p>
                <p className="text-xs text-slate-400 mt-0.5">{status.metadata.workflow_engine}</p>
              </div>

              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Orchestration Pattern</p>
                <p className="text-sm font-medium text-primary-400">{status.metadata.orchestration_pattern}</p>
              </div>

              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Framework</p>
                <p className="text-sm font-medium text-white">{status.metadata.framework}</p>
              </div>

              <div className="pt-3 border-t border-slate-700">
                <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Execution Stats</p>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Total Agents</span>
                    <span className="text-sm font-medium text-white">{status.metadata.agent_count}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Parallel Tasks</span>
                    <span className="text-sm font-medium text-white">{status.metadata.parallel_tasks}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Total Phases</span>
                    <span className="text-sm font-medium text-white">{status.metadata.total_phases}</span>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-700">
                <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Agents Used</p>
                <div className="flex flex-wrap gap-1">
                  {status.metadata.agents_used.map((agent, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 text-xs bg-primary-500/20 text-primary-300 rounded border border-primary-500/30"
                    >
                      {agent}
                    </span>
                  ))}
                </div>
              </div>

              {status.metadata.pattern_details && (
                <div className="pt-3 border-t border-slate-700">
                  <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Pattern Details</p>
                  <div className="space-y-1.5">
                    {Object.entries(status.metadata.pattern_details).map(([key, value]) => (
                      <div key={key} className="text-xs">
                        <span className="text-slate-500">{key.replace(/_/g, ' ')}:</span>{' '}
                        <span className="text-slate-300">{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Completed Tasks */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-success-500" />
              <span>Completed Tasks ({status.completed_tasks.length})</span>
            </h3>
          </div>
          <div className="card-body">
            {status.completed_tasks.length === 0 ? (
              <p className="text-slate-500 text-sm">No tasks completed yet</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {status.completed_tasks.map((task, index) => (
                  <div
                    key={index}
                    className="flex items-center space-x-2 p-3 bg-success-500/10 border border-success-500/30 rounded-lg"
                  >
                    <CheckCircle className="w-4 h-4 text-success-500 flex-shrink-0" />
                    <span className="text-sm text-slate-200">{task}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Failed Tasks */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <XCircle className="w-5 h-5 text-error-500" />
              <span>Failed Tasks ({status.failed_tasks.length})</span>
            </h3>
          </div>
          <div className="card-body">
            {status.failed_tasks.length === 0 ? (
              <p className="text-slate-500 text-sm">No failed tasks</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {status.failed_tasks.map((task, index) => (
                  <div
                    key={index}
                    className="flex items-center space-x-2 p-3 bg-error-500/10 border border-error-500/30 rounded-lg"
                  >
                    <XCircle className="w-4 h-4 text-error-500 flex-shrink-0" />
                    <span className="text-sm text-slate-200">{task}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Results */}
      {(status.status === 'success' || status.status === 'completed') && status.result && (
        <div className="card border-2 border-success-500/30">
          <div className="card-header">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <FileText className="w-5 h-5 text-success-500" />
              <span>Research Results</span>
            </h3>
          </div>
          <div className="card-body space-y-6">
            {/* Executive Summary */}
            {status.result.executive_summary && (
              <div>
                <h4 className="text-md font-bold text-primary-400 mb-3 flex items-center space-x-2">
                  <FileText className="w-4 h-4" />
                  <span>Executive Summary</span>
                </h4>
                <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
                  <p className="whitespace-pre-wrap text-sm text-slate-200 leading-relaxed">
                    {status.result.executive_summary}
                  </p>
                </div>
              </div>
            )}

            {/* Research Plan */}
            {status.result.research_plan && (
              <div>
                <h4 className="text-md font-bold text-primary-400 mb-3">Research Plan</h4>
                <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
                  <p className="whitespace-pre-wrap text-sm text-slate-200 leading-relaxed">
                    {status.result.research_plan}
                  </p>
                </div>
              </div>
            )}

            {/* Research Findings Sections */}
            {['core_concepts', 'current_state', 'applications', 'challenges', 'future_trends'].map((key) => {
              if (status.result[key]) {
                return (
                  <div key={key}>
                    <h4 className="text-md font-bold text-primary-400 mb-3 capitalize">
                      {key.replace(/_/g, ' ')}
                    </h4>
                    <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
                      <p className="whitespace-pre-wrap text-sm text-slate-200 leading-relaxed">
                        {status.result[key]}
                      </p>
                    </div>
                  </div>
                );
              }
              return null;
            })}

            {/* Final Report */}
            {status.result.final_report && (
              <div>
                <h4 className="text-md font-bold text-success-400 mb-3 flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4" />
                  <span>Final Research Report</span>
                </h4>
                <div className="p-6 bg-gradient-to-br from-slate-700/50 to-slate-800/50 rounded-lg border-2 border-success-500/30">
                  <div className="prose prose-invert max-w-none">
                    <p className="whitespace-pre-wrap text-sm text-slate-100 leading-relaxed">
                      {status.result.final_report}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Validation Results */}
            {status.result.validation_results && (
              <div>
                <h4 className="text-md font-bold text-primary-400 mb-3">Validation Results</h4>
                <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
                  <p className="whitespace-pre-wrap text-sm text-slate-200 leading-relaxed">
                    {status.result.validation_results}
                  </p>
                </div>
              </div>
            )}

            {/* All Other Results (fallback) */}
            {!status.result.final_report && 
             !status.result.executive_summary && 
             !status.result.research_plan && (
              <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
                <pre className="whitespace-pre-wrap text-sm text-slate-200 font-mono overflow-x-auto">
                  {JSON.stringify(status.result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error Display */}
      {status.error && (
        <div className="card border-2 border-error-500/30">
          <div className="card-header">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-error-500" />
              <span>Error</span>
            </h3>
          </div>
          <div className="card-body">
            <div className="p-4 bg-error-500/10 rounded-lg">
              <p className="text-error-400 text-sm font-mono">{status.error}</p>
            </div>
          </div>
        </div>
      )}

      {/* WebSocket Messages Log */}
      {wsMessages.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-bold text-white">Real-Time Event Log</h3>
          </div>
          <div className="card-body">
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {wsMessages.slice(-10).reverse().map((msg, index) => (
                <div key={index} className="p-2 bg-slate-700/50 rounded text-xs font-mono">
                  <span className="text-slate-500">[{msg.type}]</span>{' '}
                  <span className="text-slate-300">
                    {msg.message || msg.task_name || 'Update received'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
