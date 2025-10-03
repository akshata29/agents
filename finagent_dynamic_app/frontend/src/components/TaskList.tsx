import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, FolderOpen, Trash2 } from 'lucide-react';
import { apiClient, TaskListItem } from '../lib/api';

interface TaskListProps {
  onTaskSelect: (sessionId: string, planId: string) => void;
  selectedPlanId?: string | null;
}

export function TaskList({ onTaskSelect, selectedPlanId }: TaskListProps) {
  const queryClient = useQueryClient();
  
  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => apiClient.getAllTasks(),
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) => apiClient.deleteSession(sessionId),
    onSuccess: () => {
      // Refetch tasks after deletion
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      // Refresh the page to reset the view
      window.location.reload();
    },
  });

  const handleDelete = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation(); // Prevent task selection
    if (confirm('Are you sure you want to delete this research task?')) {
      deleteMutation.mutate(sessionId);
    }
  };

  if (isLoading) {
    return (
      <div className="h-full bg-slate-800 border-r border-slate-700 p-3">
        <div className="animate-pulse space-y-2">
          <div className="h-10 bg-slate-700 rounded"></div>
          <div className="h-10 bg-slate-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-slate-800 border-r border-slate-700 flex flex-col">
      {/* Header */}
      <div className="p-3 border-b border-slate-700">
        <div className="flex items-center space-x-2">
          <FolderOpen className="w-4 h-4 text-slate-300" />
          <h2 className="text-sm font-medium text-white">My Research</h2>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          {tasks?.length || 0} tasks
        </p>
      </div>

      {/* Minimal Task List - Compact Icons */}
      <div className="flex-1 overflow-y-auto">
        {tasks && tasks.length > 0 ? (
          <div className="p-2 space-y-1">
            {tasks.map((task: TaskListItem) => (
              <div
                key={task.id}
                className={`group relative w-full flex items-center space-x-2 rounded hover:bg-slate-700 transition-colors ${
                  selectedPlanId === task.id ? 'bg-slate-700 border-l-2 border-primary-500' : ''
                }`}
              >
                <button
                  onClick={() => onTaskSelect(task.session_id, task.id)}
                  className="flex-1 flex items-center space-x-2 px-2 py-2"
                  title={task.initial_goal}
                >
                  <FileText className="w-4 h-4 text-slate-300 flex-shrink-0" />
                  <div className="flex-1 min-w-0 text-left">
                    <p className="text-xs text-white truncate">
                      {task.ticker || 'Research'}
                    </p>
                    <p className="text-xs text-slate-400">
                      {task.completed_steps}/{task.total_steps}
                    </p>
                  </div>
                </button>
                
                {/* Delete Icon - Shows on hover */}
                <button
                  onClick={(e) => handleDelete(e, task.session_id)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1 mr-2 hover:bg-error-500/20 rounded"
                  title="Delete task"
                >
                  <Trash2 className="w-3.5 h-3.5 text-error-400" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 text-center text-slate-400">
            <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-xs">No tasks yet</p>
          </div>
        )}
      </div>
    </div>
  );
}
