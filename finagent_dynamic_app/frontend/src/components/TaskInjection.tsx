/**
 * Task Injection Component
 * 
 * Allows users to inject new tasks into an in-progress plan
 * Features conversational AI to validate and intelligently position tasks
 */

import React, { useState } from 'react';
import { Plus, Send, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { apiClient } from '../lib/api';

interface TaskInjectionProps {
  planId: string;
  sessionId: string;
  objective: string;
  currentSteps: Array<{
    id: string;
    order: number;
    action: string;
    agent: string;
    status: string;
  }>;
  onTaskInjected: () => void; // Callback to refresh the plan
}

interface InjectionResponse {
  success: boolean;
  message: string;
  action: 'added' | 'duplicate' | 'unsupported' | 'clarification_needed';
  inserted_at?: number;
  new_step_id?: string;
  suggestions?: string[];
}

export const TaskInjection: React.FC<TaskInjectionProps> = ({
  planId,
  sessionId,
  objective,
  currentSteps,
  onTaskInjected
}) => {
  const [taskInput, setTaskInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [response, setResponse] = useState<InjectionResponse | null>(null);
  const [showInput, setShowInput] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!taskInput.trim()) return;

    setIsSubmitting(true);
    setResponse(null);

    try {
      const result = await apiClient.injectTask({
        session_id: sessionId,
        plan_id: planId,
        task_request: taskInput.trim(),
        objective: objective,
        current_steps: currentSteps
      });

      setResponse(result);

      // If task was successfully added, refresh the plan and clear input
      if (result.success && result.action === 'added') {
        setTaskInput('');
        setTimeout(() => {
          onTaskInjected();
          setResponse(null);
          setShowInput(false);
        }, 2000); // Show success message for 2 seconds
      }
    } catch (error: any) {
      setResponse({
        success: false,
        message: error.message || 'Failed to process task injection request',
        action: 'unsupported'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getResponseIcon = (action: string) => {
    switch (action) {
      case 'added':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'duplicate':
        return <AlertCircle className="w-5 h-5 text-yellow-400" />;
      case 'unsupported':
        return <AlertCircle className="w-5 h-5 text-red-400" />;
      case 'clarification_needed':
        return <AlertCircle className="w-5 h-5 text-blue-400" />;
      default:
        return <AlertCircle className="w-5 h-5 text-slate-400" />;
    }
  };

  const getResponseColor = (action: string) => {
    switch (action) {
      case 'added':
        return 'bg-green-900/30 border-green-700 text-green-300';
      case 'duplicate':
        return 'bg-yellow-900/30 border-yellow-700 text-yellow-300';
      case 'unsupported':
        return 'bg-red-900/30 border-red-700 text-red-300';
      case 'clarification_needed':
        return 'bg-blue-900/30 border-blue-700 text-blue-300';
      default:
        return 'bg-slate-800 border-slate-600 text-slate-300';
    }
  };

  if (!showInput) {
    return (
      <button
        onClick={() => setShowInput(true)}
        className="w-full px-4 py-3 bg-slate-800 hover:bg-slate-750 border border-slate-600 hover:border-primary-500 rounded-lg text-slate-300 hover:text-primary-300 transition-all flex items-center justify-center gap-2 font-medium"
      >
        <Plus className="w-4 h-4" />
        Add New Task
      </button>
    );
  }

  return (
    <div className="border border-slate-600 rounded-lg bg-slate-800 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Add New Task to Plan
        </h4>
        <button
          onClick={() => {
            setShowInput(false);
            setTaskInput('');
            setResponse(null);
          }}
          className="text-xs text-slate-400 hover:text-slate-300"
        >
          Cancel
        </button>
      </div>

      <p className="text-xs text-slate-400">
        Describe the task you'd like to add. I'll validate it and find the best place to insert it.
      </p>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="relative">
          <textarea
            value={taskInput}
            onChange={(e) => setTaskInput(e.target.value)}
            placeholder="e.g., 'Can you also add stock price prediction?' or 'Get analyst recommendations'"
            className="w-full px-3 py-2 bg-slate-900 border border-slate-600 text-slate-100 placeholder-slate-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm resize-none"
            rows={3}
            disabled={isSubmitting}
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            type="submit"
            disabled={isSubmitting || !taskInput.trim()}
            className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader className="w-4 h-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Submit Task
              </>
            )}
          </button>
        </div>
      </form>

      {/* Response Message */}
      {response && (
        <div className={`p-3 rounded-lg border flex items-start gap-3 ${getResponseColor(response.action)}`}>
          {getResponseIcon(response.action)}
          <div className="flex-1 space-y-2">
            <p className="text-sm font-medium">{response.message}</p>
            
            {response.inserted_at && (
              <p className="text-xs opacity-80">
                Inserted at step {response.inserted_at}
              </p>
            )}

            {response.suggestions && response.suggestions.length > 0 && (
              <div className="mt-2 space-y-1">
                <p className="text-xs font-semibold">Suggestions:</p>
                <ul className="text-xs space-y-0.5 pl-4">
                  {response.suggestions.map((suggestion, idx) => (
                    <li key={idx} className="list-disc">{suggestion}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
