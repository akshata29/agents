import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api';
import { Activity, CheckCircle, XCircle, Clock } from 'lucide-react';

export default function Dashboard() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: apiClient.healthCheck,
    refetchInterval: 10000, // Poll every 10 seconds
  });

  const { data: executions } = useQuery({
    queryKey: ['executions'],
    queryFn: apiClient.listExecutions,
    refetchInterval: 5000, // Poll every 5 seconds
  });

  const stats = {
    total: executions?.executions?.length || 0,
    running: executions?.executions?.filter((e: any) => e.status === 'running').length || 0,
    completed: executions?.executions?.filter((e: any) => 
      e.status === 'success' || e.status === 'completed'
    ).length || 0,
    failed: executions?.executions?.filter((e: any) => e.status === 'failed').length || 0,
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {/* System Status */}
      <div className="card">
        <div className="card-body">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-400">System Status</p>
              <p className="text-2xl font-bold text-white mt-1">
                {health?.status === 'healthy' ? 'Online' : 'Offline'}
              </p>
            </div>
            <Activity
              className={`w-10 h-10 ${
                health?.status === 'healthy' ? 'text-success-500' : 'text-error-500'
              }`}
            />
          </div>
          <div className="mt-4 text-xs text-slate-500">
            {health?.workflow_engine === 'ready' ? 'Workflow Engine Ready' : 'Initializing...'}
          </div>
        </div>
      </div>

      {/* Running Executions */}
      <div className="card">
        <div className="card-body">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-400">Running</p>
              <p className="text-2xl font-bold text-white mt-1">{stats.running}</p>
            </div>
            <Clock className="w-10 h-10 text-warning-500 animate-pulse" />
          </div>
          <div className="mt-4 text-xs text-slate-500">Active research workflows</div>
        </div>
      </div>

      {/* Completed */}
      <div className="card">
        <div className="card-body">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-400">Completed</p>
              <p className="text-2xl font-bold text-white mt-1">{stats.completed}</p>
            </div>
            <CheckCircle className="w-10 h-10 text-success-500" />
          </div>
          <div className="mt-4 text-xs text-slate-500">Successfully finished</div>
        </div>
      </div>

      {/* Failed */}
      <div className="card">
        <div className="card-body">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-400">Failed</p>
              <p className="text-2xl font-bold text-white mt-1">{stats.failed}</p>
            </div>
            <XCircle className="w-10 h-10 text-error-500" />
          </div>
          <div className="mt-4 text-xs text-slate-500">Encountered errors</div>
        </div>
      </div>
    </div>
  );
}
