import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { apiClient, createExecutionStream } from '../api';
import type { ExecutionStatus, AgentActivity } from '../types';
import { 
  Play, 
  Pause, 
  Square, 
  Clock, 
  Users, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  Loader2,
  Download,
  Eye,
  RotateCcw
} from 'lucide-react';

interface ExecutionMonitorProps {
  executionId: string;
}

const ExecutionMonitor: React.FC<ExecutionMonitorProps> = ({ executionId }) => {
  const [streamCanceller, setStreamCanceller] = useState<(() => void) | null>(null);
  const [realTimeStatus, setRealTimeStatus] = useState<ExecutionStatus | null>(null);

  // Query for initial status
  const { data: initialStatus, isLoading, refetch } = useQuery({
    queryKey: ['executionStatus', executionId],
    queryFn: () => apiClient.getExecutionStatus(executionId),
    enabled: !!executionId,
  });

  const status = realTimeStatus || initialStatus;

  // Set up real-time streaming
  useEffect(() => {
    if (!executionId) return;

    const canceller = createExecutionStream(executionId, (updatedStatus) => {
      setRealTimeStatus(updatedStatus);
    });

    setStreamCanceller(() => canceller);

    return () => {
      if (canceller) canceller();
    };
  }, [executionId]);

  // Cancel execution
  const handleCancel = async () => {
    try {
      await apiClient.cancelExecution(executionId);
      refetch();
    } catch (error) {
      console.error('Failed to cancel execution:', error);
    }
  };

  const handleRetry = () => {
    // Reset real-time status and refetch
    setRealTimeStatus(null);
    refetch();
  };

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
          <span className="ml-2 text-slate-400">Loading execution status...</span>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="text-center py-8">
          <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Execution Not Found</h3>
          <p className="text-slate-400">Could not find execution with ID: {executionId}</p>
        </div>
      </div>
    );
  }

  const getStatusIcon = () => {
    switch (status.status) {
      case 'running':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-400" />;
      case 'completed':
      case 'success':
        return <CheckCircle2 className="w-5 h-5 text-green-400" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-400" />;
      case 'cancelled':
        return <Square className="w-5 h-5 text-yellow-400" />;
      default:
        return <Clock className="w-5 h-5 text-slate-400" />;
    }
  };

  const getStatusColor = () => {
    switch (status.status) {
      case 'running':
        return 'text-blue-400';
      case 'completed':
      case 'success':
        return 'text-green-400';
      case 'failed':
        return 'text-red-400';
      case 'cancelled':
        return 'text-yellow-400';
      default:
        return 'text-slate-400';
    }
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

  const exportResults = () => {
    const data = {
      execution_id: status.execution_id,
      pattern: status.pattern,
      status: status.status,
      result: status.result,
      agent_outputs: status.agent_outputs,
      execution_time: status.duration,
      timestamp: status.end_time || status.start_time
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `execution-${executionId}-results.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Execution Header */}
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            {getStatusIcon()}
            <div>
              <h2 className="text-xl font-bold text-white">
                Execution Monitor
              </h2>
              <p className="text-slate-400">ID: {executionId}</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {status.status === 'running' && (
              <button
                onClick={handleCancel}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center space-x-2 transition-colors"
              >
                <Square className="w-4 h-4" />
                <span>Cancel</span>
              </button>
            )}
            
            {(status.status === 'completed' || status.status === 'success') && (
              <button
                onClick={exportResults}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg flex items-center space-x-2 transition-colors"
              >
                <Download className="w-4 h-4" />
                <span>Export</span>
              </button>
            )}

            {status.status === 'failed' && (
              <button
                onClick={handleRetry}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center space-x-2 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Retry</span>
              </button>
            )}
          </div>
        </div>

        {/* Pattern and Objective Information */}
        {(status.pattern || status.task) && (
          <div className="mb-4 space-y-3">
            {status.pattern && (
              <div className="bg-slate-700/50 rounded-lg p-3">
                <div className="text-sm text-slate-400 mb-1">Pattern</div>
                <div className="text-white font-medium capitalize">{status.pattern.replace('_', ' ')}</div>
              </div>
            )}
            {status.task && (
              <div className="bg-slate-700/50 rounded-lg p-3">
                <div className="text-sm text-slate-400 mb-1">Objective</div>
                <div className="text-white">{status.task}</div>
              </div>
            )}
          </div>
        )}

        {/* Status Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-1">
              <div className={`w-2 h-2 rounded-full ${
                status.status === 'running' ? 'bg-blue-400' :
                status.status === 'completed' || status.status === 'success' ? 'bg-green-400' :
                status.status === 'failed' ? 'bg-red-400' : 'bg-slate-400'
              }`} />
              <span className="text-sm text-slate-400">Status</span>
            </div>
            <div className={`font-semibold ${getStatusColor()} capitalize`}>
              {status.status}
            </div>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-1">
              <Clock className="w-4 h-4 text-slate-400" />
              <span className="text-sm text-slate-400">Duration</span>
            </div>
            <div className="font-semibold text-white">
              {formatDuration(status.duration)}
            </div>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-1">
              <div className="w-4 h-4 bg-blue-400 rounded" />
              <span className="text-sm text-slate-400">Progress</span>
            </div>
            <div className="font-semibold text-white">
              {Math.round(status.progress * 100)}%
            </div>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-1">
              <Users className="w-4 h-4 text-slate-400" />
              <span className="text-sm text-slate-400">Agents</span>
            </div>
            <div className="font-semibold text-white">
              {status.agent_outputs?.length || 0}
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="flex justify-between text-sm text-slate-400 mb-1">
            <span>Progress</span>
            <span>{Math.round(status.progress * 100)}%</span>
          </div>
          <div className="w-full bg-slate-600 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                status.status === 'failed' ? 'bg-red-500' :
                status.status === 'completed' || status.status === 'success' ? 'bg-green-500' :
                'bg-blue-500'
              }`}
              style={{ width: `${status.progress * 100}%` }}
            />
          </div>
        </div>

        {/* Current Task */}
        {status.current_task && (
          <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
            <div className="flex items-center space-x-2 mb-1">
              <Play className="w-4 h-4 text-blue-400" />
              <span className="text-sm font-medium text-blue-400">Current Task</span>
            </div>
            <p className="text-slate-300 text-sm">{status.current_task}</p>
          </div>
        )}
      </div>

      {/* Real-Time Agent Activities */}
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Agent Activities</h3>
          <div className="text-sm text-slate-400">
            {status.agent_outputs?.length || 0} agents completed
          </div>
        </div>
        
        {status.agent_outputs && status.agent_outputs.length > 0 ? (
          <div className="space-y-4">
            {status.agent_outputs.map((activity: AgentActivity, index: number) => (
              <div 
                key={`${activity.agent}-${activity.timestamp}-${index}`}
                className="bg-slate-700/50 rounded-lg p-4 border border-slate-600 animate-fade-in activity-card completed"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-gradient-to-r from-primary-600 to-primary-500 rounded-lg flex items-center justify-center shadow-lg">
                      <Users className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <h4 className="font-medium text-white">{activity.agent}</h4>
                      <p className="text-xs text-slate-400">
                        Completed at {activity.timestamp ? new Date(activity.timestamp).toLocaleTimeString() : 'Unknown time'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="w-5 h-5 text-green-400" />
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <h5 className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">Input</h5>
                    <div className="p-3 bg-slate-800/70 rounded-lg border border-slate-600/50">
                      <p className="text-sm text-slate-300 leading-relaxed">
                        {activity.input.length > 150 
                          ? (
                            <details className="cursor-pointer">
                              <summary className="text-primary-400 hover:text-primary-300">
                                {activity.input.substring(0, 150)}... (click to expand)
                              </summary>
                              <div className="mt-2 pt-2 border-t border-slate-600">
                                {activity.input}
                              </div>
                            </details>
                          )
                          : activity.input
                        }
                      </p>
                    </div>
                  </div>

                  <div>
                    <h5 className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">Output</h5>
                    <div className="p-3 bg-slate-800/70 rounded-lg border border-slate-600/50">
                      <div className="text-sm text-slate-300 leading-relaxed result-content">
                        {activity.output.length > 300 
                          ? (
                            <details className="cursor-pointer">
                              <summary className="text-primary-400 hover:text-primary-300 mb-2">
                                <ReactMarkdown 
                                  remarkPlugins={[remarkGfm]}
                                  className="inline prose prose-invert prose-sm max-w-none"
                                >
                                  {activity.output.substring(0, 200) + "..."}
                                </ReactMarkdown>
                                {" (click to expand)"}
                              </summary>
                              <div className="mt-3 pt-3 border-t border-slate-600/50">
                                <ReactMarkdown 
                                  remarkPlugins={[remarkGfm]}
                                  className="prose prose-invert prose-sm max-w-none
                                    prose-headings:text-slate-200
                                    prose-strong:text-slate-200
                                    prose-code:text-primary-400 prose-code:bg-slate-800 prose-code:px-1 prose-code:rounded
                                    prose-pre:bg-slate-800 prose-pre:border prose-pre:border-slate-600
                                    prose-ul:text-slate-300 prose-ol:text-slate-300
                                    prose-li:text-slate-300
                                    prose-a:text-primary-400 prose-a:hover:text-primary-300"
                                >
                                  {activity.output}
                                </ReactMarkdown>
                              </div>
                            </details>
                          )
                          : (
                            <ReactMarkdown 
                              remarkPlugins={[remarkGfm]}
                              className="prose prose-invert prose-sm max-w-none
                                prose-headings:text-slate-200
                                prose-strong:text-slate-200
                                prose-code:text-primary-400 prose-code:bg-slate-800 prose-code:px-1 prose-code:rounded
                                prose-pre:bg-slate-800 prose-pre:border prose-pre:border-slate-600
                                prose-ul:text-slate-300 prose-ol:text-slate-300
                                prose-li:text-slate-300
                                prose-a:text-primary-400 prose-a:hover:text-primary-300"
                            >
                              {activity.output}
                            </ReactMarkdown>
                          )
                        }
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            {status.status === 'running' ? (
              <div className="flex flex-col items-center space-y-3">
                <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
                <p className="text-slate-400">Waiting for agent activities...</p>
                <p className="text-xs text-slate-500">{status.current_task || 'Initializing agents'}</p>
              </div>
            ) : (
              <div className="flex flex-col items-center space-y-2">
                <Users className="w-8 h-8 text-slate-500" />
                <p className="text-slate-400">No agent activities yet</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Execution Result */}
      {status.result && (status.status === 'completed' || status.status === 'success') && (
        <div className="bg-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Execution Result</h3>
          
          <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
            <div className="result-content text-slate-300 leading-relaxed">
              {typeof status.result === 'string' ? (
                <pre className="whitespace-pre-wrap font-sans">{status.result}</pre>
              ) : (
                <pre className="whitespace-pre-wrap font-mono text-sm">
                  {JSON.stringify(status.result, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {status.error && status.status === 'failed' && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <h3 className="font-semibold text-red-400">Execution Failed</h3>
          </div>
          <p className="text-red-300 text-sm">{status.error}</p>
        </div>
      )}

      {/* Completed Tasks */}
      {status.completed_tasks && status.completed_tasks.length > 0 && (
        <div className="bg-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Completed Tasks</h3>
          
          <div className="space-y-2">
            {status.completed_tasks.map((task: string, index: number) => (
              <div key={index} className="flex items-center space-x-3 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                <CheckCircle2 className="w-4 h-4 text-green-400" />
                <span className="text-green-300 text-sm">{task}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Failed Tasks */}
      {status.failed_tasks && status.failed_tasks.length > 0 && (
        <div className="bg-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Failed Tasks</h3>
          
          <div className="space-y-2">
            {status.failed_tasks.map((task: string, index: number) => (
              <div key={index} className="flex items-center space-x-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <XCircle className="w-4 h-4 text-red-400" />
                <span className="text-red-300 text-sm">{task}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExecutionMonitor;